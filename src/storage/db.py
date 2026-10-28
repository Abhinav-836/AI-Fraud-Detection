"""
SQLite persistence for predictions and analyst feedback.

Previously every prediction lived in a Python list and vanished on restart,
and the dashboard's "Resolve" button recorded nothing. Now each scored
transaction is stored with its features and explanation; analysts label
flagged ones as fraud / legitimate, and those labels feed retraining.

SQLite needs no server, works in the desktop app, and is shared by all
uvicorn workers on one machine (WAL mode).
"""
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.config import db_path
from ..utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id    TEXT,
    card_id           TEXT,
    amount            REAL,
    merchant_category TEXT,
    device_type       TEXT,
    location_country  TEXT,
    tx_timestamp      TEXT,
    scored_at         TEXT NOT NULL,
    epoch             REAL NOT NULL,
    probability       REAL NOT NULL,
    decision          TEXT NOT NULL,
    risk_level        TEXT NOT NULL,
    model_type        TEXT,
    source            TEXT,
    drivers           TEXT,
    features          TEXT,
    latency_ms        REAL,
    sim_truth         TEXT,
    label             INTEGER,
    labeled_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_pred_epoch ON predictions(epoch);
CREATE INDEX IF NOT EXISTS idx_pred_card ON predictions(card_id);
CREATE INDEX IF NOT EXISTS idx_pred_decision ON predictions(decision);
"""

FLAGGED = ("review", "decline")


def _now() -> datetime:
    return datetime.now().astimezone()


class PredictionStore:
    def __init__(self, path: Optional[Union[str, Path]] = None):
        self.path = Path(path) if path else db_path()
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        if str(self.path) != ":memory:":
            self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ------------------------------------------------------------ writes
    def insert(self, tx: Dict[str, Any], result: Dict[str, Any], features: Dict[str, Any],
               source: str, sim_truth: Optional[Dict[str, Any]] = None) -> int:
        now = _now()
        with self._lock:
            cur = self.conn.execute(
                """INSERT INTO predictions (transaction_id, card_id, amount, merchant_category, device_type,
                   location_country, tx_timestamp, scored_at, epoch, probability, decision, risk_level, model_type,
                   source, drivers, features, latency_ms, sim_truth)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    tx.get("transaction_id"), tx.get("card_id"), tx.get("amount"), tx.get("merchant_category"),
                    tx.get("device_type"), tx.get("location_country"), tx.get("timestamp"),
                    now.isoformat(), now.timestamp(), result["fraud_probability"], result["decision"],
                    result["risk_level"], result["model_type"], source,
                    json.dumps(result.get("drivers") or []), json.dumps(features, default=float),
                    result.get("processing_time_ms"), json.dumps(sim_truth) if sim_truth else None,
                ),
            )
            self.conn.commit()
            return int(cur.lastrowid)

    def set_label(self, prediction_id: int, is_fraud: bool) -> bool:
        with self._lock:
            cur = self.conn.execute(
                "UPDATE predictions SET label = ?, labeled_at = ? WHERE id = ?",
                (1 if is_fraud else 0, _now().isoformat(), prediction_id),
            )
            self.conn.commit()
            return cur.rowcount > 0

    def clear(self):
        with self._lock:
            self.conn.execute("DELETE FROM predictions")
            self.conn.commit()

    # ------------------------------------------------------------ reads
    @staticmethod
    def _row(r: sqlite3.Row) -> Dict[str, Any]:
        d = dict(r)
        d["drivers"] = json.loads(d["drivers"]) if d.get("drivers") else []
        d.pop("features", None)
        d["sim_truth"] = json.loads(d["sim_truth"]) if d.get("sim_truth") else None
        d["is_flagged"] = d["decision"] in FLAGGED
        d["is_fraud"] = d["is_flagged"]  # same meaning as in the /predict response
        d["label"] = None if d["label"] is None else bool(d["label"])
        d["timestamp"] = d["scored_at"]
        return d

    def recent(self, limit: int = 50, flagged_only: bool = False, unlabeled_only: bool = False) -> List[Dict[str, Any]]:
        where, args = [], []
        if flagged_only:
            where.append("decision IN ('review','decline')")
        if unlabeled_only:
            where.append("label IS NULL")
        sql = "SELECT * FROM predictions"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ?"
        with self._lock:
            rows = self.conn.execute(sql, (*args, limit)).fetchall()
        return [self._row(r) for r in rows]

    def get(self, prediction_id: int) -> Optional[Dict[str, Any]]:
        with self._lock:
            r = self.conn.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
        return self._row(r) if r else None

    def stats(self, since_hours: Optional[float] = None) -> Dict[str, Any]:
        where, args = "", ()
        if since_hours:
            where, args = " WHERE epoch >= ?", ((_now() - timedelta(hours=since_hours)).timestamp(),)
        with self._lock:
            total = self.conn.execute(f"SELECT COUNT(*) FROM predictions{where}", args).fetchone()[0]
            by_decision = dict(self.conn.execute(
                f"SELECT decision, COUNT(*) FROM predictions{where} GROUP BY decision", args).fetchall())
            labels = dict(self.conn.execute(
                "SELECT label, COUNT(*) FROM predictions WHERE label IS NOT NULL GROUP BY label").fetchall())
            last = self.conn.execute("SELECT MAX(scored_at) FROM predictions").fetchone()[0]
        flagged = by_decision.get("review", 0) + by_decision.get("decline", 0)
        return {
            "total_predictions": total,
            "approved": by_decision.get("approve", 0),
            "in_review": by_decision.get("review", 0),
            "declined": by_decision.get("decline", 0),
            "fraud_detected": flagged,
            "fraud_rate": flagged / total if total else 0.0,
            "labeled_fraud": labels.get(1, 0),
            "labeled_legit": labels.get(0, 0),
            "last_prediction_time": last,
        }

    def labeled_rows(self) -> List[Dict[str, Any]]:
        """(features, label) for every analyst-labelled prediction, for retraining."""
        with self._lock:
            rows = self.conn.execute(
                "SELECT features, label, scored_at FROM predictions WHERE label IS NOT NULL AND features IS NOT NULL"
            ).fetchall()
        return [{**json.loads(r["features"]), "is_fraud": int(r["label"]), "timestamp": r["scored_at"]} for r in rows]

    def recent_probabilities(self, limit: int = 2000) -> List[float]:
        with self._lock:
            rows = self.conn.execute("SELECT probability FROM predictions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [r[0] for r in rows]

    def history_since(self, since_epoch: float) -> List[Dict[str, Any]]:
        """Transactions to replay into the card-history store after a restart."""
        with self._lock:
            rows = self.conn.execute(
                """SELECT card_id, amount, merchant_category, device_type, location_country, tx_timestamp
                   FROM predictions WHERE card_id IS NOT NULL AND epoch >= ? ORDER BY id""",
                (since_epoch,),
            ).fetchall()
        return [dict(r) for r in rows]

    def latency_ms(self, limit: int = 1000) -> List[float]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT latency_ms FROM predictions WHERE latency_ms IS NOT NULL ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [r[0] for r in rows]

    def simulation_scorecard(self) -> Dict[str, int]:
        """For simulated traffic the ground truth is known: how did the engine do?"""
        with self._lock:
            rows = self.conn.execute(
                "SELECT sim_truth, decision FROM predictions WHERE sim_truth IS NOT NULL").fetchall()
        card = {"fraud_total": 0, "fraud_caught": 0, "legit_total": 0, "legit_flagged": 0}
        for r in rows:
            truth = json.loads(r["sim_truth"])
            flagged = r["decision"] in FLAGGED
            if truth.get("is_fraud"):
                card["fraud_total"] += 1
                card["fraud_caught"] += int(flagged)
            else:
                card["legit_total"] += 1
                card["legit_flagged"] += int(flagged)
        return card
