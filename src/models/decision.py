"""
Approve / review / decline policy.

Real fraud teams don't run a single 0.5 cut-off. Two thresholds on the
calibrated fraud probability:

  p >= decline_threshold  -> decline   (block automatically)
  p >= review_threshold   -> review    (hold for an analyst)
  otherwise               -> approve

Both are chosen on validation data:
  review threshold  - highest threshold that still catches `target_recall`
                      of fraud (the review queue's job is to catch fraud)
  decline threshold - lowest threshold where at least `decline_precision`
                      of declined transactions are really fraud (declining a
                      good customer is expensive)
"""
from dataclasses import asdict, dataclass
from typing import Dict, List

import numpy as np

SENSITIVITY_RECALL = {"low": 0.70, "medium": 0.80, "high": 0.90}
# Finer steps at the low end, where calibrated fraud probabilities cluster
GRID = np.unique(np.round(np.concatenate([[0.002, 0.005], np.linspace(0.01, 0.99, 99)]), 3))


@dataclass
class DecisionPolicy:
    review_threshold: float = 0.3
    decline_threshold: float = 0.8

    def decide(self, probability: float) -> str:
        if probability >= self.decline_threshold:
            return "decline"
        if probability >= self.review_threshold:
            return "review"
        return "approve"

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    def validate(self):
        if not (0 < self.review_threshold <= self.decline_threshold < 1):
            raise ValueError("Need 0 < review_threshold <= decline_threshold < 1")


def threshold_curve(y_true: np.ndarray, proba: np.ndarray) -> List[Dict[str, float]]:
    """Precision / recall / share of traffic flagged at each grid threshold."""
    y = np.asarray(y_true).astype(int)
    p = np.asarray(proba, dtype=float)
    positives = max(int(y.sum()), 1)
    curve = []
    for t in GRID:
        flagged = p >= t
        tp = int((flagged & (y == 1)).sum())
        n_flag = int(flagged.sum())
        curve.append({
            "threshold": float(t),
            "precision": tp / n_flag if n_flag else 1.0,
            "recall": tp / positives,
            "flag_rate": n_flag / len(p) if len(p) else 0.0,
        })
    return curve


def review_threshold_for_recall(curve: List[Dict[str, float]], target_recall: float) -> float:
    eligible = [pt["threshold"] for pt in curve if pt["recall"] >= target_recall]
    return max(eligible) if eligible else float(GRID[0])


def derive_policy(y_true, proba, target_recall: float = 0.80, decline_precision: float = 0.90) -> DecisionPolicy:
    curve = threshold_curve(y_true, proba)
    review = review_threshold_for_recall(curve, target_recall)
    precise = [pt["threshold"] for pt in curve if pt["precision"] >= decline_precision and pt["recall"] > 0]
    decline = min(precise) if precise else 0.95
    decline = max(decline, review)
    return DecisionPolicy(review_threshold=float(review), decline_threshold=float(decline))


def sensitivity_presets(curve: List[Dict[str, float]], decline_threshold: float) -> Dict[str, Dict[str, float]]:
    """Review thresholds for the dashboard's low / medium / high sensitivity."""
    out = {}
    for name, recall in SENSITIVITY_RECALL.items():
        review = min(review_threshold_for_recall(curve, recall), decline_threshold)
        point = next((pt for pt in curve if pt["threshold"] == review), None)
        out[name] = {
            "review_threshold": review,
            "decline_threshold": decline_threshold,
            "expected_recall": point["recall"] if point else None,
            "expected_flag_rate": point["flag_rate"] if point else None,
        }
    return out


def tier_metrics(y_true, proba, policy: DecisionPolicy) -> Dict[str, float]:
    """How the policy performs on labelled data."""
    y = np.asarray(y_true).astype(int)
    p = np.asarray(proba, dtype=float)
    review_or_more = p >= policy.review_threshold
    decline = p >= policy.decline_threshold
    positives = max(int(y.sum()), 1)
    return {
        "fraud_caught_rate": float((review_or_more & (y == 1)).sum() / positives),
        "fraud_auto_declined_rate": float((decline & (y == 1)).sum() / positives),
        "decline_precision": float((decline & (y == 1)).sum() / decline.sum()) if decline.any() else 0.0,
        "review_rate": float((review_or_more & ~decline).mean()),
        "decline_rate": float(decline.mean()),
        "false_decline_rate": float((decline & (y == 0)).sum() / max(int((y == 0).sum()), 1)),
    }
