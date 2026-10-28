import numpy as np
import pandas as pd
import pytest

from src.api.services.fraud_service import FraudDetectionService
from src.features.feature_engineering import MODEL_COLUMNS, build_feature_frame, engineer_transaction
from src.features.history import MemoryHistoryStore
from src.ingestion.kaggle_loader import map_kaggle_frame
from src.ingestion.simulator import LiveSimulator, generate_dataset
from src.models.decision import DecisionPolicy, derive_policy, threshold_curve
from src.pipelines.training_pipeline import TrainingPipeline
from src.storage.db import PredictionStore


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    """Train a small model once into a temp dir."""
    path = tmp_path_factory.mktemp("model")
    result = TrainingPipeline().run(
        source="synthetic", n_customers=400, days=40, model_path=str(path),
        include_feedback=False, models=("xgboost", "logistic_regression"),
    )
    return path, result


class TestHistoryFeatures:
    def test_velocity_and_new_country(self):
        store = MemoryHistoryStore()
        base = pd.Timestamp("2024-01-01 12:00")
        for i in range(5):  # normal history at home
            engineer_transaction({"card_id": "C1", "amount": 20, "merchant_category": "grocery",
                                  "device_type": "mobile", "location_country": "US",
                                  "timestamp": base + pd.Timedelta(days=i)}, store)
        burst_start = base + pd.Timedelta(days=6)
        feats = None
        for i in range(4):
            feats = engineer_transaction({"card_id": "C1", "amount": 900, "merchant_category": "electronics",
                                          "device_type": "web", "location_country": "NG",
                                          "timestamp": burst_start + pd.Timedelta(minutes=5 * i)}, store)
        assert feats["card_txn_count_1h"] == 3          # three earlier burst txns
        assert feats["amount_to_card_mean"] > 2
        first = engineer_transaction({"card_id": "C2", "amount": 10, "location_country": "US",
                                      "timestamp": base}, store)
        assert first["card_history_len_log"] == 0 and first["is_new_country"] == 0

    def test_no_card_id_means_no_history(self):
        store = MemoryHistoryStore()
        f = engineer_transaction({"amount": 50}, store)
        assert f["card_txn_count_24h"] == 0 and len(store) == 0

    def test_batch_equals_live(self):
        """Training (batch replay) and serving (one at a time) must produce identical features."""
        df = generate_dataset(n_customers=30, days=5, seed=3)
        batch = build_feature_frame(df)
        store = MemoryHistoryStore()
        live = pd.DataFrame([engineer_transaction(r, store) for r in df.to_dict("records")], index=df.index)
        pd.testing.assert_frame_equal(batch[MODEL_COLUMNS], live[MODEL_COLUMNS], check_dtype=False)

    def test_redis_store_matches_memory(self):
        fakeredis = pytest.importorskip("fakeredis")
        from src.features.history import RedisHistoryStore
        df = generate_dataset(n_customers=10, days=3, seed=5)
        mem = build_feature_frame(df, MemoryHistoryStore())
        red = build_feature_frame(df, RedisHistoryStore(client=fakeredis.FakeRedis(decode_responses=True)))
        pd.testing.assert_frame_equal(mem, red, check_dtype=False)


class TestData:
    def test_simulator_realistic_fraud_rate(self):
        df = generate_dataset(n_customers=300, days=30, seed=1)
        assert 0.002 < df["is_fraud"].mean() < 0.03
        assert df["timestamp"].is_monotonic_increasing
        assert {"account_takeover", "card_testing", "new_card_fraud"} <= set(df["scenario"])

    def test_new_cards_are_not_all_fraud(self):
        # Cards first seen after day 0: both legit late joiners and new-card fraud,
        # so "no history" alone can't be learned as the fraud signal
        df = generate_dataset(n_customers=300, days=30, seed=1)
        first = df.groupby("card_id").first()
        late = first[first["timestamp"] > df["timestamp"].min() + pd.Timedelta(days=7)]
        assert late["is_fraud"].sum() > 0 and (late["is_fraud"] == 0).sum() > 0

    def test_live_simulator_hides_truth(self):
        sim = LiveSimulator(seed=1)
        tx, truth = LiveSimulator.split_truth(sim.next_transaction())
        assert "is_fraud" not in tx and "scenario" not in tx
        assert set(truth) == {"is_fraud", "scenario"}

    def test_kaggle_mapping(self):
        raw = pd.DataFrame({
            "trans_date_trans_time": ["2019-01-01 00:00:18", "2019-01-01 00:00:44"],
            "cc_num": [2703186189652095, 630423337322],
            "category": ["misc_net", "grocery_pos"],
            "amt": [4.97, 107.23],
            "trans_num": ["a1", "b2"],
            "is_fraud": [0, 1],
        })
        df = map_kaggle_frame(raw)
        assert list(df["device_type"]) == ["web", "pos"]
        assert df["card_id"].iloc[0] == "2703186189652095"
        assert build_feature_frame(df).shape == (2, len(MODEL_COLUMNS))


class TestDecisionPolicy:
    def test_tiers(self):
        pol = DecisionPolicy(0.2, 0.8)
        assert [pol.decide(p) for p in (0.1, 0.5, 0.9)] == ["approve", "review", "decline"]
        with pytest.raises(ValueError):
            DecisionPolicy(0.9, 0.2).validate()

    def test_derived_thresholds_meet_targets(self):
        rng = np.random.default_rng(0)
        y = (rng.random(5000) < 0.05).astype(int)
        p = np.clip(y * rng.uniform(0.3, 1, 5000) + (1 - y) * rng.uniform(0, 0.5, 5000), 0, 1)
        pol = derive_policy(y, p, target_recall=0.8, decline_precision=0.9)
        curve = {round(pt["threshold"], 3): pt for pt in threshold_curve(y, p)}
        assert curve[round(pol.review_threshold, 3)]["recall"] >= 0.8
        assert pol.review_threshold <= pol.decline_threshold


class TestTrainedModel:
    def test_model_beats_chance_but_is_not_perfect(self, trained):
        _, result = trained
        m = result["test_metrics"]
        assert 0.2 < m["auc_pr"] < 0.99       # realistic, not a toy 0.999
        assert m["auc_roc"] > 0.85
        assert result["policy"]["review_threshold"] <= result["policy"]["decline_threshold"]

    def test_service_scores_and_explains(self, trained, tmp_path):
        path, _ = trained
        service = FraudDetectionService(store=PredictionStore(tmp_path / "t.db"), history=MemoryHistoryStore())
        assert service.initialize(str(path), replay_history=False)
        t0 = pd.Timestamp("2026-01-01 10:00")
        for i in range(6):
            service.predict({"transaction_id": f"N{i}", "card_id": "X", "amount": 25, "merchant_category": "grocery",
                             "device_type": "mobile", "location_country": "US",
                             "timestamp": (t0 + pd.Timedelta(days=i)).isoformat()})
        burst = None
        for i in range(5):
            burst = service.predict({"transaction_id": f"F{i}", "card_id": "X", "amount": 1400,
                                     "merchant_category": "cryptocurrency", "device_type": "web",
                                     "location_country": "BR",
                                     "timestamp": (t0 + pd.Timedelta(days=7, minutes=4 * i)).isoformat()})
        assert burst["decision"] in ("review", "decline")
        assert burst["drivers"], "flagged transaction should have explanations"
        assert {d["feature"] for d in burst["drivers"]} & {"card_txn_count_1h", "amount_to_card_mean",
                                                            "is_new_country", "merchant_category"}
        assert burst["prediction_id"] is not None

    def test_feedback_is_used_for_retraining(self, trained, tmp_path):
        path, _ = trained
        store = PredictionStore(tmp_path / "fb.db")
        service = FraudDetectionService(store=store, history=MemoryHistoryStore())
        service.initialize(str(path), replay_history=False)
        r = service.predict({"transaction_id": "L1", "card_id": "Z", "amount": 30})
        assert service.label(r["prediction_id"], True)["label"] is True
        rows = store.labeled_rows()
        assert len(rows) == 1 and rows[0]["is_fraud"] == 1
        assert set(MODEL_COLUMNS) <= set(rows[0])

    def test_rule_fallback_without_model(self, tmp_path):
        service = FraudDetectionService(store=PredictionStore(tmp_path / "r.db"), history=MemoryHistoryStore())
        assert service.initialize(str(tmp_path / "missing"), replay_history=False) is False
        r = service.predict({"transaction_id": "R", "amount": 10})
        assert r["model_type"] == "rule_based" and r["decision"] == "approve"
