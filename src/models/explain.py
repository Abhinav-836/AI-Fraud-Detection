"""
Per-prediction explanations: which features pushed THIS score up.

  XGBoost              exact TreeSHAP contributions (booster pred_contribs)
  Logistic regression  coefficient x scaled feature value
  other models         None (callers fall back to rule-based indicators)

Contributions are in log-odds of the uncalibrated model; they rank the
drivers of a prediction, they are not probabilities.

One-hot columns are summed back into their source feature, and each driver
is turned into a translatable message key + parameters for the dashboard.
"""
import math
from typing import Any, Dict, List, Optional

import numpy as np

# Messages (English). The frontend has translations for the same keys.
MESSAGES = {
    "card_txn_count_1h": "{count} transactions on this card in the last hour",
    "card_txn_count_24h": "{count} transactions on this card in the last 24 hours",
    "card_amount_24h_log": "{amount} spent on this card in the last 24 hours",
    "secs_since_last_txn_log": "Only {minutes} min since the card's previous transaction",
    "amount_to_card_mean": "{ratio}x this card's usual amount",
    "is_new_country": "First transaction from {country} on this card",
    "is_new_category": "First {category} purchase on this card",
    "is_new_device": "First {device} transaction on this card",
    "card_history_len_log": "New card with little history ({count} previous transactions)",
    "amount": "High amount ({amount})",
    "amount_log": "High amount ({amount})",
    "hour": "Unusual hour ({hour}:00)",
    "is_night": "Night-time transaction ({hour}:00)",
    "day_of_week": "Day-of-week pattern",
    "is_weekend": "Weekend transaction",
    "merchant_category": "Risky merchant category ({category})",
    "device_type": "Device type ({device})",
    "location_country": "Location ({country})",
}


def base_estimator(model):
    """Unwrap a CalibratedClassifierCV (with or without FrozenEstimator)."""
    if hasattr(model, "calibrated_classifiers_"):
        est = model.calibrated_classifiers_[0].estimator
        return getattr(est, "estimator", est)  # FrozenEstimator(...).estimator
    return model


def raw_contributions(model, X: np.ndarray) -> Optional[np.ndarray]:
    """Contribution of each model input for a single row, or None if unsupported."""
    est = base_estimator(model)
    name = type(est).__name__
    if name == "XGBClassifier":
        import xgboost as xgb
        contribs = est.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
        return np.asarray(contribs)[0, :-1]  # drop the bias column
    if hasattr(est, "coef_"):
        return (np.asarray(est.coef_)[0] * X[0])
    return None


def _params(feature: str, f: Dict[str, Any]) -> Dict[str, Any]:
    if feature == "card_txn_count_1h":
        return {"count": int(f["card_txn_count_1h"])}
    if feature == "card_txn_count_24h":
        return {"count": int(f["card_txn_count_24h"])}
    if feature == "card_amount_24h_log":
        return {"amount": round(math.expm1(f["card_amount_24h_log"]), 2)}
    if feature == "secs_since_last_txn_log":
        return {"minutes": max(round(math.expm1(f["secs_since_last_txn_log"]) / 60, 1), 0)}
    if feature == "amount_to_card_mean":
        return {"ratio": round(f["amount_to_card_mean"], 1)}
    if feature == "card_history_len_log":
        return {"count": int(round(math.expm1(f["card_history_len_log"])))}
    if feature in ("amount", "amount_log"):
        return {"amount": round(f["amount"], 2)}
    if feature in ("hour", "is_night"):
        return {"hour": int(f["hour"])}
    if feature in ("is_new_country", "location_country"):
        return {"country": f["location_country"]}
    if feature in ("is_new_category", "merchant_category"):
        return {"category": f["merchant_category"]}
    if feature in ("is_new_device", "device_type"):
        return {"device": f["device_type"]}
    return {}


def _is_meaningful(feature: str, f: Dict[str, Any]) -> bool:
    """Skip drivers whose wording would be false for this transaction."""
    if feature in ("day_of_week", "device_type"):
        return False                   # model nuance, not a reason an analyst can act on
    if feature.startswith("is_"):
        return bool(f.get(feature))
    if feature == "card_txn_count_1h":
        return f["card_txn_count_1h"] >= 2
    if feature == "card_txn_count_24h":
        return f["card_txn_count_24h"] >= 3
    if feature == "amount_to_card_mean":
        return f["amount_to_card_mean"] >= 2
    if feature == "secs_since_last_txn_log":
        return math.expm1(f["secs_since_last_txn_log"]) < 30 * 60
    if feature == "card_history_len_log":
        return math.expm1(f["card_history_len_log"]) < 5
    if feature == "amount":
        return f["amount"] >= 300      # "High amount ($36)" would be misleading
    if feature == "hour":
        return f["hour"] < 6 or f["hour"] > 22
    return True


def explain(model, transformer, X: np.ndarray, features: Dict[str, Any], top_k: int = 4) -> Optional[List[Dict[str, Any]]]:
    """
    Top risk drivers for one transaction:
      [{"feature", "impact", "key", "params", "text"}], highest impact first.
    Returns None when the model type has no explanation support.
    """
    contribs = raw_contributions(model, X)
    if contribs is None:
        return None

    grouped: Dict[str, float] = {}
    for name, value in zip(transformer.feature_names, contribs):
        source = transformer.source_feature_of(name)
        grouped[source] = grouped.get(source, 0.0) + float(value)
    # amount and amount_log describe the same thing; report once
    if "amount_log" in grouped:
        grouped["amount"] = grouped.get("amount", 0.0) + grouped.pop("amount_log")

    drivers = []
    for feature, impact in sorted(grouped.items(), key=lambda kv: kv[1], reverse=True):
        if impact <= 0.05 or feature not in MESSAGES or not _is_meaningful(feature, features):
            continue
        params = _params(feature, features)
        drivers.append({
            "feature": feature,
            "impact": round(impact, 3),
            "key": feature,
            "params": params,
            "text": MESSAGES[feature].format(**params),
        })
        if len(drivers) >= top_k:
            break
    return drivers
