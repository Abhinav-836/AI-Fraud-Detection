from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.services.fraud_service import fraud_service
from src.features.history import MemoryHistoryStore


@pytest.fixture
def client(tmp_path):
    with TestClient(app) as c:
        # Deterministic: rule engine, fresh history, empty database
        fraud_service.initialize(model_path=str(tmp_path / "no-model"), replay_history=False)
        fraud_service.history = MemoryHistoryStore()
        fraud_service.store.clear()
        yield c


VALID_TX = {
    "transaction_id": "TEST_001",
    "card_id": "CARD_A",
    "amount": 42.5,
    "merchant_category": "grocery",
    "device_type": "mobile",
    "location_country": "US",
}


def tx(i, **kw):
    return {**VALID_TX, "transaction_id": f"T{i}", **kw}


class TestPredict:
    def test_health_and_root(self, client):
        assert client.get("/health").json()["status"] == "healthy"
        assert "version" in client.get("/api").json()

    def test_normal_transaction_is_approved(self, client):
        data = client.post("/api/v1/predict", json=VALID_TX).json()
        assert data["decision"] == "approve" and data["is_fraud"] is False
        assert data["prediction_id"] is not None
        assert data["model_type"] == "rule_based"

    def test_velocity_burst_is_flagged_with_reasons(self, client):
        start = datetime(2026, 1, 1, 12, 0)
        for i in range(5):  # usual behaviour, one per day
            client.post("/api/v1/predict", json=tx(i, timestamp=(start + timedelta(days=i)).isoformat()))
        burst = [client.post("/api/v1/predict", json=tx(  # takeover burst abroad
            100 + i, amount=900, merchant_category="cryptocurrency", location_country="NG",
            timestamp=(start + timedelta(days=6, minutes=3 * i)).isoformat())).json() for i in range(4)]
        assert all(b["decision"] in ("review", "decline") for b in burst)
        first, last = ({d["feature"] for d in b["drivers"]} for b in (burst[0], burst[-1]))
        assert {"amount_to_card_mean", "is_new_country"} <= first   # unusual amount, new country
        assert "card_txn_count_1h" in last                           # velocity by the end of the burst
        assert all("text" in d and "params" in d for d in burst[-1]["drivers"])

    def test_validation(self, client):
        assert client.post("/api/v1/predict", json={**VALID_TX, "amount": -1}).status_code == 422
        assert client.post("/api/v1/predict", json={"amount": 5}).status_code == 422
        assert client.post("/api/v1/predict", json={"transaction_id": "X", "amount": 5}).status_code == 200

    def test_timestamps_carry_utc_offset(self, client):
        ts = client.post("/api/v1/predict", json=VALID_TX).json()["timestamp"]
        assert datetime.fromisoformat(ts.replace("Z", "+00:00")).tzinfo is not None

    def test_batch_is_scored_in_time_order(self, client):
        start = datetime(2026, 2, 1, 9, 0)
        txs = [tx(i, amount=700, merchant_category="gift_cards",
                  timestamp=(start + timedelta(minutes=2 * i)).isoformat()) for i in range(5)][::-1]
        data = client.post("/api/v1/predict/batch", json={"transactions": txs}).json()
        assert data["total_transactions"] == 5
        assert data["approved"] + data["in_review"] + data["declined"] == 5
        # the chronologically last transaction sees the 4 earlier ones
        last = data["predictions"][0]
        assert any(d["feature"] == "card_txn_count_1h" for d in last["drivers"])


class TestPersistenceAndFeedback:
    def test_stats_and_recent_persist(self, client):
        client.post("/api/v1/predict", json=VALID_TX)
        stats = client.get("/api/v1/stats").json()
        assert stats["total_predictions"] == 1 and stats["approved"] == 1
        recent = client.get("/api/v1/predictions/recent?limit=5").json()
        assert recent[0]["transaction_id"] == "TEST_001" and recent[0]["amount"] == 42.5

    def test_feedback_roundtrip(self, client):
        pid = client.post("/api/v1/predict", json=VALID_TX).json()["prediction_id"]
        r = client.post(f"/api/v1/predictions/{pid}/feedback", json={"is_fraud": True})
        assert r.status_code == 200 and r.json()["label"] is True
        assert client.get("/api/v1/stats").json()["labeled_fraud"] == 1
        assert client.post("/api/v1/predictions/999999/feedback", json={"is_fraud": False}).status_code == 404


class TestPolicyAndMonitoring:
    def test_policy_update_changes_decisions(self, client):
        policy = client.get("/api/v1/settings/decision").json()
        assert policy["review_threshold"] <= policy["decline_threshold"]
        r = client.put("/api/v1/settings/decision", json={"review_threshold": 0.05, "decline_threshold": 0.9})
        assert r.status_code == 200
        risky = client.post("/api/v1/predict", json=tx(1, merchant_category="gambling")).json()
        assert risky["decision"] == "review"
        assert client.put("/api/v1/settings/decision",
                          json={"review_threshold": 0.9, "decline_threshold": 0.2}).status_code == 422

    def test_monitoring(self, client):
        client.post("/api/v1/predict", json=VALID_TX)
        m = client.get("/api/v1/monitoring").json()
        assert m["latency_ms"]["p50"] is not None
        assert m["last_hour"]["total_predictions"] >= 1

    def test_cors_allows_put(self, client):
        r = client.options("/api/v1/settings/decision", headers={
            "Origin": "http://localhost:3000", "Access-Control-Request-Method": "PUT"})
        assert r.status_code == 200


class TestWebSocket:
    def test_rest_and_websocket_agree(self, client):
        rest = client.post("/api/v1/predict", json=tx(1, card_id=None)).json()
        with client.websocket_connect("/ws/live") as ws:
            assert ws.receive_json()["type"] == "connection"
            ws.send_json(tx(2, card_id=None))
            msg = ws.receive_json()
        assert msg["prediction"]["fraud_probability"] == rest["fraud_probability"]

    def test_bad_messages_keep_socket_open(self, client):
        with client.websocket_connect("/ws/live") as ws:
            ws.receive_json()
            ws.send_text("not json")
            assert ws.receive_json()["type"] == "error"
            ws.send_json({"transaction_id": "X", "amount": -5})
            assert ws.receive_json()["type"] == "error"
            ws.send_json(VALID_TX)
            assert ws.receive_json()["type"] in ("transaction_processed", "fraud_alert")

    def test_server_side_simulation(self, client):
        with client.websocket_connect("/ws/live") as ws:
            ws.receive_json()
            ws.send_json({"action": "start_simulation", "interval": 0.2})
            started = ws.receive_json()
            assert started["type"] == "simulation" and started["state"] == "started"
            msg = ws.receive_json()
            assert msg["type"] in ("transaction_processed", "fraud_alert")
            assert msg["truth"]["scenario"] and msg["transaction"]["card_id"]
            ws.send_json({"action": "stop_simulation"})


class TestApiKey:
    def test_key_required_when_configured(self, client, monkeypatch):
        monkeypatch.setenv("FRAUD_API_KEY", "s3cret")
        assert client.post("/api/v1/predict", json=VALID_TX).status_code == 401
        ok = client.post("/api/v1/predict", json=VALID_TX, headers={"X-API-Key": "s3cret"})
        assert ok.status_code == 200
        assert client.get("/health").status_code == 200  # health stays public

