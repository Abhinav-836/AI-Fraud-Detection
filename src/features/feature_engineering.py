"""
Feature engineering for fraud detection.

Two kinds of features:
  * row features      - from the transaction itself (amount, hour, ...)
  * history features  - from the card's previous transactions (see history.py)

`engineer_transaction` (live, one transaction) and `build_feature_frame`
(training / batch, many transactions replayed in time order) produce
identical columns from identical code.
"""
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..utils.logger import get_logger
from .history import HISTORY_FEATURES, MemoryHistoryStore

logger = get_logger(__name__)

HIGH_RISK_MERCHANTS = {"gambling", "money_transfer", "pawn_shop", "cryptocurrency"}
DOMESTIC_COUNTRIES = {"US", "CA", "UK", "AU"}

CATEGORICAL_FEATURES: List[str] = ["merchant_category", "device_type", "location_country"]
ROW_FEATURES: List[str] = ["amount", "amount_log", "hour", "day_of_week", "is_weekend", "is_night"]
NUMERIC_FEATURES: List[str] = ROW_FEATURES + HISTORY_FEATURES
MODEL_COLUMNS: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def _to_datetime(value: Any) -> datetime:
    if value is None or value == "" or (isinstance(value, float) and math.isnan(value)):
        return datetime.now()
    if isinstance(value, datetime):
        return value
    ts = pd.to_datetime(value, errors="coerce")
    return datetime.now() if pd.isna(ts) else ts.to_pydatetime()


def normalize_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
    """Clean one raw transaction into canonical fields."""
    when = _to_datetime(tx.get("timestamp"))
    hour = tx.get("hour_of_day")
    dow = tx.get("day_of_week")
    card = tx.get("card_id")
    return {
        "transaction_id": tx.get("transaction_id"),
        "card_id": str(card) if card not in (None, "") else None,
        "amount": max(float(tx.get("amount") or 0.0), 0.0),
        "merchant_category": str(tx.get("merchant_category") or "unknown").strip().lower(),
        "device_type": str(tx.get("device_type") or "unknown").strip().lower(),
        "location_country": str(tx.get("location_country") or "US").strip().upper(),
        # Explicit hour/day win over the timestamp (API callers may send only those)
        "hour": int(hour) if hour is not None and not pd.isna(hour) else when.hour,
        "day_of_week": int(dow) if dow is not None and not pd.isna(dow) else when.weekday(),
        "epoch": when.timestamp(),
        "timestamp": when.isoformat(),
    }


def row_features(n: Dict[str, Any]) -> Dict[str, float]:
    hour, dow = n["hour"], n["day_of_week"]
    return {
        "amount": n["amount"],
        "amount_log": math.log1p(n["amount"]),
        "hour": float(hour),
        "day_of_week": float(dow),
        "is_weekend": float(dow >= 5),
        "is_night": float(hour < 6 or hour > 22),
    }


def engineer_transaction(tx: Dict[str, Any], store, record: bool = True) -> Dict[str, Any]:
    """
    Full feature dict for one live transaction. With record=True the
    transaction is added to the card's history after its features are taken.
    """
    n = normalize_transaction(tx)
    args = (n["card_id"], n["epoch"], n["amount"], n["location_country"], n["merchant_category"], n["device_type"])
    hist = store.score_and_update(*args) if record else store.peek(*args)
    return {
        **row_features(n),
        **hist,
        "merchant_category": n["merchant_category"],
        "device_type": n["device_type"],
        "location_country": n["location_country"],
    }


def build_feature_frame(df: pd.DataFrame, store: Optional[object] = None) -> pd.DataFrame:
    """
    Engineer features for a batch of transactions by replaying them in time
    order through a history store (a fresh one unless given). Returns a frame
    aligned to the input index with MODEL_COLUMNS.
    """
    store = store if store is not None else MemoryHistoryStore()
    records = df.to_dict("records")
    order = np.argsort(pd.to_datetime(df["timestamp"], errors="coerce").values.astype("datetime64[ns]").astype(np.int64),
                       kind="stable") if "timestamp" in df.columns else np.arange(len(df))

    rows: List[Optional[Dict[str, Any]]] = [None] * len(records)
    for i in order:
        rows[i] = engineer_transaction(records[i], store, record=True)

    out = pd.DataFrame(rows, index=df.index)[MODEL_COLUMNS]
    logger.info(f"Engineered {len(out)} rows ({len(NUMERIC_FEATURES)} numeric, {len(CATEGORICAL_FEATURES)} categorical)")
    return out


class FeatureEngineer:
    """Backward-compatible wrapper used by older call sites."""

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        feats = build_feature_frame(df)
        extra = df.drop(columns=[c for c in feats.columns if c in df.columns])
        return pd.concat([extra, feats], axis=1)
