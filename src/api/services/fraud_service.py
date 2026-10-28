"""
The fraud engine used by every channel (REST, WebSocket, Kafka, desktop).

Per transaction:
  1. card-history features (velocity, usual amount, new country/device...)
     are computed from the card's previous activity, then the transaction
     is added to that history
  2. the calibrated model scores it (rule engine if no model is trained)
  3. the approve / review / decline policy turns the score into a decision
  4. the top risk drivers explain the score
  5. everything is stored in SQLite for the dashboard, monitoring and the
     analyst feedback loop
"""
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np

from ...features.feature_engineering import HIGH_RISK_MERCHANTS, engineer_transaction, normalize_transaction
from ...features.history import create_history_store
from ...models.decision import DecisionPolicy, sensitivity_presets
from ...models.explain import MESSAGES, explain
from ...models.train import FraudModelTrainer
from ...preprocessing.transform import DataTransformer
from ...storage.db import PredictionStore
from ...utils.config import bundled_model_dir, load_settings, model_dir
from ...utils.logger import get_logger

logger = get_logger(__name__)

RISK_LEVEL = {"approve": "low", "review": "medium", "decline": "high"}
RULE_POLICY = DecisionPolicy(review_threshold=0.4, decline_threshold=0.7)
RISKY = HIGH_RISK_MERCHANTS | {"gift_cards", "money_transfer", "cryptocurrency"}


def _driver(feature: str, impact: float, params: Dict[str, Any]) -> Dict[str, Any]:
    return {"feature": feature, "impact": round(impact, 3), "key": feature, "params": params,
            "text": MESSAGES[feature].format(**params)}


def rule_based_score(f: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """Transparent fallback used until a model is trained. Uses the same features."""
    drivers: List[Dict[str, Any]] = []
    score = 0.0

    def hit(weight, feature, params):
        nonlocal score
        score += weight
        drivers.append(_driver(feature, weight, params))

    if f["card_txn_count_1h"] >= 2:
        hit(0.30 if f["card_txn_count_1h"] >= 3 else 0.20, "card_txn_count_1h", {"count": int(f["card_txn_count_1h"])})
    if f["amount_to_card_mean"] >= 3:
        hit(0.25 if f["amount_to_card_mean"] >= 5 else 0.20, "amount_to_card_mean",
            {"ratio": round(f["amount_to_card_mean"], 1)})
    elif f["amount"] >= 1000:
        hit(0.20, "amount", {"amount": round(f["amount"], 2)})
    if f["is_new_country"]:
        hit(0.20, "is_new_country", {"country": f["location_country"]})
    if f["merchant_category"] in RISKY:
        hit(0.20, "merchant_category", {"category": f["merchant_category"]})
    if f["is_new_device"]:
        hit(0.10, "is_new_device", {"device": f["device_type"]})
    if f["is_night"]:
        hit(0.10, "is_night", {"hour": int(f["hour"])})
    drivers.sort(key=lambda d: d["impact"], reverse=True)
    return min(score, 0.99), drivers


def _psi(expected: List[float], actual: List[float]) -> Optional[float]:
    """Population Stability Index between two binned distributions."""
    if not expected or not actual:
        return None
    e = np.clip(np.asarray(expected, dtype=float), 1e-4, None)
    a = np.clip(np.asarray(actual, dtype=float), 1e-4, None)
    return float(np.sum((a - e) * np.log(a / e)))


class FraudDetectionService:
    def __init__(self, store: Optional[PredictionStore] = None, history=None, settings: Optional[dict] = None):
        self.settings = settings or load_settings()
        self.history = history if history is not None else create_history_store(self.settings)
        self._store = store
        self.trainer: Optional[FraudModelTrainer] = None
        self.transformer: Optional[DataTransformer] = None
        self.metadata: Dict[str, Any] = {}
        self.policy = RULE_POLICY
        self.model_path: Optional[str] = None
        self._latencies: Deque[float] = deque(maxlen=2000)
        self._retrain_lock = threading.Lock()
        self.retrain_status: Dict[str, Any] = {"state": "idle"}

    # ------------------------------------------------------------ setup
    @property
    def store(self) -> PredictionStore:
        if self._store is None:
            self._store = PredictionStore()
        return self._store

    @property
    def model_loaded(self) -> bool:
        return self.trainer is not None and self.transformer is not None

    @property
    def model_type(self) -> str:
        return self.metadata.get("model_type", "model") if self.model_loaded else "rule_based"

    def _candidate_dirs(self, model_path: Optional[str]) -> List[Path]:
        if model_path:
            return [Path(model_path)]
        dirs = [model_dir()]
        bundled = bundled_model_dir()
        if bundled != dirs[0]:
            dirs.append(bundled)  # pre-trained model shipped with the desktop app / image
        return dirs

    def initialize(self, model_path: Optional[str] = None, replay_history: bool = True) -> bool:
        """Load the trained model if one exists. Returns True when ML scoring is active."""
        # Build everything in locals and swap at the end, so predictions running
        # in other threads (e.g. during a background retrain) never see a
        # half-loaded engine.
        loaded = None
        for d in self._candidate_dirs(model_path):
            try:
                transformer = DataTransformer().load_transformers(d / "transformers")
                trainer = FraudModelTrainer()
                meta = trainer.load(d)
            except (FileNotFoundError, ValueError) as e:
                logger.info(f"No usable model in {d}: {e}")
                continue
            except Exception as e:  # corrupt / incompatible pickle
                logger.error(f"Failed to load model from {d}: {e}")
                continue
            pol = meta.get("policy") or {}
            loaded = (trainer, transformer, meta, str(d),
                      DecisionPolicy(pol.get("review_threshold", 0.3), pol.get("decline_threshold", 0.8)))
            break

        if loaded:
            self.trainer, self.transformer, self.metadata, self.model_path, self.policy = loaded
            logger.info(f"ML model active: {self.model_type} from {self.model_path} "
                        f"(review>={self.policy.review_threshold}, decline>={self.policy.decline_threshold})")
        else:
            self.trainer = self.transformer = None
            self.metadata, self.policy = {}, RULE_POLICY
            logger.warning("No trained model found; using rule-based scoring. "
                           "Train one with `python -m src.pipelines.training_pipeline`.")

        if replay_history:
            self._replay_history()
        return self.model_loaded

    def _replay_history(self, days: int = 7):
        """Rebuild card history from stored predictions after a restart."""
        try:
            rows = self.store.history_since((datetime.now() - timedelta(days=days)).timestamp())
        except Exception as e:
            logger.warning(f"Could not replay history: {e}")
            return
        for r in rows:
            n = normalize_transaction({**r, "timestamp": r["tx_timestamp"]})
            self.history.score_and_update(n["card_id"], n["epoch"], n["amount"], n["location_country"],
                                          n["merchant_category"], n["device_type"])
        if rows:
            logger.info(f"Replayed {len(rows)} stored transactions into card history")

    # ------------------------------------------------------------ scoring
    def predict(self, tx: Dict[str, Any], source: str = "api", sim_truth: Optional[Dict[str, Any]] = None,
                persist: bool = True) -> Dict[str, Any]:
        started = time.perf_counter()
        features = engineer_transaction(tx, self.history, record=True)

        if self.model_loaded:
            X = self.transformer.transform_one(features)
            probability = float(self.trainer.predict_proba(X)[0])
            drivers = explain(self.trainer.model, self.transformer, X, features)
            if drivers is None:  # model without explanation support
                drivers = rule_based_score(features)[1]
        else:
            probability, drivers = rule_based_score(features)

        decision = self.policy.decide(probability)
        elapsed = (time.perf_counter() - started) * 1000
        self._latencies.append(elapsed)

        n = normalize_transaction(tx)
        result = {
            "prediction_id": None,
            "transaction_id": tx.get("transaction_id"),
            "card_id": n["card_id"],
            "decision": decision,
            "is_fraud": decision != "approve",
            "fraud_probability": round(probability, 4),
            "risk_level": RISK_LEVEL[decision],
            "drivers": drivers,
            "factors": [d["text"] for d in drivers] or ["No significant risk factors detected"],
            "model_type": self.model_type,
            "processing_time_ms": round(elapsed, 2),
            "timestamp": datetime.now().astimezone().isoformat(),
        }
        if persist:
            record = {**tx, **{k: n[k] for k in ("card_id", "amount", "merchant_category", "device_type",
                                                  "location_country", "timestamp")}}
            result["prediction_id"] = self.store.insert(record, result, features, source, sim_truth)
        return result

    def predict_batch(self, transactions: List[Dict[str, Any]], source: str = "batch") -> List[Dict[str, Any]]:
        """Score in time order so velocity features see earlier transactions of the batch."""
        order = sorted(range(len(transactions)),
                       key=lambda i: normalize_transaction(transactions[i])["epoch"])
        results: List[Optional[Dict[str, Any]]] = [None] * len(transactions)
        for i in order:
            results[i] = self.predict(transactions[i], source=source)
        return results

    # ------------------------------------------------------------ policy
    def get_policy(self) -> Dict[str, Any]:
        presets = self.metadata.get("presets") or {}
        if not presets and self.metadata.get("curve"):
            presets = sensitivity_presets(self.metadata["curve"], self.policy.decline_threshold)
        trained = self.metadata.get("policy")
        return {**self.policy.to_dict(), "presets": presets, "trained_policy": trained,
                "model_type": self.model_type, "curve": self.metadata.get("curve", [])}

    def set_policy(self, review_threshold: float, decline_threshold: float) -> Dict[str, Any]:
        policy = DecisionPolicy(review_threshold, decline_threshold)
        policy.validate()
        self.policy = policy
        logger.info(f"Decision policy set: review>={review_threshold} decline>={decline_threshold}")
        return self.get_policy()

    # ------------------------------------------------------------ feedback
    def label(self, prediction_id: int, is_fraud: bool) -> Optional[Dict[str, Any]]:
        if not self.store.set_label(prediction_id, is_fraud):
            return None
        return self.store.get(prediction_id)

    # ------------------------------------------------------------ read models
    def get_statistics(self) -> Dict[str, Any]:
        return {**self.store.stats(), "model_type": self.model_type, "policy": self.policy.to_dict()}

    def get_recent(self, limit: int = 50, flagged_only: bool = False, unlabeled_only: bool = False):
        return self.store.recent(limit, flagged_only, unlabeled_only)

    def get_model_info(self) -> Dict[str, Any]:
        if not self.model_loaded:
            return {"model_type": "rule_based", "status": "active", "policy": self.policy.to_dict(),
                    "description": "Heuristic rules over card-history features (no trained model found)"}
        m = self.metadata
        return {
            "model_type": self.model_type,
            "status": "active",
            "trained_at": m.get("trained_at"),
            "data_source": m.get("data_source"),
            "training_rows": m.get("rows"),
            "feedback_rows": m.get("feedback_rows", 0),
            "candidates": m.get("candidates"),
            "test_metrics": m.get("test_metrics"),
            "policy": self.policy.to_dict(),
            "n_features": len(self.transformer.feature_names),
        }

    def get_monitoring(self) -> Dict[str, Any]:
        lat = sorted(self._latencies) or sorted(self.store.latency_ms())
        pct = (lambda q: round(lat[min(int(q * len(lat)), len(lat) - 1)], 2)) if lat else (lambda q: None)

        live = self.store.recent_probabilities(2000)
        drift = None
        reference = self.metadata.get("val_score_histogram")
        if reference and len(live) >= 200:
            hist, _ = np.histogram(live, bins=np.linspace(0, 1, 11))
            drift = _psi(reference, (hist / hist.sum()).tolist())

        return {
            "latency_ms": {"p50": pct(0.50), "p95": pct(0.95), "p99": pct(0.99), "samples": len(lat)},
            "last_hour": self.store.stats(since_hours=1),
            "last_24h": self.store.stats(since_hours=24),
            "score_drift_psi": None if drift is None else round(drift, 4),
            "drift_status": None if drift is None else ("stable" if drift < 0.1 else "moderate" if drift < 0.25 else "significant"),
            "simulation_scorecard": self.store.simulation_scorecard(),
            "retrain": self.retrain_status,
        }

    # ------------------------------------------------------------ retraining
    def start_retrain(self) -> Dict[str, Any]:
        """Retrain in the background on the original data + analyst labels, then hot-swap."""
        if not self._retrain_lock.acquire(blocking=False):
            return self.retrain_status
        self.retrain_status = {"state": "running", "started_at": datetime.now().astimezone().isoformat()}

        def job():
            try:
                from ...pipelines.training_pipeline import TrainingPipeline
                source = self.metadata.get("data_source", "synthetic")
                if source not in ("synthetic", "kaggle"):
                    source = "synthetic"
                result = TrainingPipeline().run(source=source, include_feedback=True)
                self.initialize(replay_history=False)
                self.retrain_status = {
                    "state": "done",
                    "finished_at": datetime.now().astimezone().isoformat(),
                    "model_type": result["best_model"],
                    "feedback_rows": result["feedback_rows"],
                    "test_pr_auc": result["test_metrics"]["auc_pr"],
                }
            except Exception as e:
                logger.exception("Retraining failed")
                self.retrain_status = {"state": "failed", "error": str(e)}
            finally:
                self._retrain_lock.release()

        threading.Thread(target=job, daemon=True, name="retrain").start()
        return self.retrain_status


# Process-wide singleton shared by REST, WebSocket and the stream processor
fraud_service = FraudDetectionService()
