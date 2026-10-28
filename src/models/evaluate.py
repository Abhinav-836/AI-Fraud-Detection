import json

import numpy as np
from sklearn.metrics import (
    accuracy_score, average_precision_score, brier_score_loss, classification_report, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score
)

from ..utils.config import writable_path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ModelEvaluator:
    """Evaluate fraud detection models"""

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    @staticmethod
    def _binary_metrics(y_true, y_pred) -> dict:
        # zero_division=0: a threshold that flags nothing must give 0, not a
        # warning + undefined value.
        return {
            'accuracy': float(accuracy_score(y_true, y_pred)),
            'precision': float(precision_score(y_true, y_pred, zero_division=0)),
            'recall': float(recall_score(y_true, y_pred, zero_division=0)),
            'f1_score': float(f1_score(y_true, y_pred, zero_division=0)),
        }

    def evaluate(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        model_name: str = "model"
    ) -> dict:
        """Evaluate predicted probabilities against true labels"""
        logger.info(f"Evaluating {model_name}")
        y_true = np.asarray(y_true).astype(int)
        y_pred_proba = np.asarray(y_pred_proba, dtype=float)
        y_pred = (y_pred_proba >= self.threshold).astype(int)

        metrics = {
            'model_name': model_name,
            'threshold': self.threshold,
            **self._binary_metrics(y_true, y_pred),
            'confusion_matrix': confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        }
        # AUC metrics need both classes present
        if len(np.unique(y_true)) == 2:
            metrics['auc_roc'] = float(roc_auc_score(y_true, y_pred_proba))
            # PR-AUC is the more honest headline metric on imbalanced fraud data
            metrics['auc_pr'] = float(average_precision_score(y_true, y_pred_proba))
            # Calibration quality: mean squared error of the probabilities
            metrics['brier'] = float(brier_score_loss(y_true, y_pred_proba))
        else:
            metrics['auc_roc'] = float('nan')
            metrics['auc_pr'] = float('nan')
            metrics['brier'] = float('nan')

        metrics['classification_report'] = classification_report(
            y_true, y_pred, labels=[0, 1], output_dict=True, zero_division=0
        )

        for key in ('accuracy', 'precision', 'recall', 'f1_score', 'auc_roc', 'auc_pr'):
            logger.info(f"{key}: {metrics[key]:.4f}")
        return metrics

    def evaluate_at_thresholds(
        self,
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        thresholds: list = None
    ) -> dict:
        """Evaluate model at different thresholds (does not mutate self.threshold)"""
        thresholds = thresholds or [0.3, 0.4, 0.5, 0.6, 0.7]
        y_pred_proba = np.asarray(y_pred_proba, dtype=float)
        return {
            str(t): self._binary_metrics(y_true, (y_pred_proba >= t).astype(int))
            for t in thresholds
        }

    def calculate_cost_savings(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        fraud_cost: float = 100.0,
        investigation_cost: float = 5.0
    ) -> dict:
        """Calculate cost savings from fraud detection"""
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

        fraud_prevented = tp * fraud_cost
        investigation_costs = (tp + fp) * investigation_cost
        fraud_missed = fn * fraud_cost
        net_savings = fraud_prevented - investigation_costs - fraud_missed

        logger.info(f"Net savings: ${net_savings:,.2f}")
        return {
            'fraud_prevented_value': float(fraud_prevented),
            'investigation_costs': float(investigation_costs),
            'fraud_missed_value': float(fraud_missed),
            'net_savings': float(net_savings),
            'true_positives': int(tp),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_negatives': int(tn)
        }

    def save_report(self, metrics: dict, filename: str = "evaluation_report.json"):
        """Save evaluation report to reports/<filename>"""
        report_path = writable_path("reports")
        report_path.mkdir(exist_ok=True)
        filepath = report_path / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, default=float)
        logger.info(f"Saved evaluation report to {filepath}")
