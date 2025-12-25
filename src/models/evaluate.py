import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import json
from pathlib import Path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ModelEvaluator:
    """Evaluate fraud detection models"""
    
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
    
    def evaluate(
        self, 
        y_true: np.ndarray, 
        y_pred_proba: np.ndarray,
        model_name: str = "model"
    ) -> dict:
        """
        Evaluate model predictions
        
        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities
            model_name: Name of the model
            
        Returns:
            Dictionary with evaluation metrics
        """
        logger.info(f"Evaluating {model_name}")
        
        # Convert probabilities to binary predictions
        y_pred = (y_pred_proba >= self.threshold).astype(int)
        
        # Calculate metrics
        metrics = {
            'model_name': model_name,
            'threshold': self.threshold,
            'accuracy': float(accuracy_score(y_true, y_pred)),
            'precision': float(precision_score(y_true, y_pred)),
            'recall': float(recall_score(y_true, y_pred)),
            'f1_score': float(f1_score(y_true, y_pred)),
            'auc_roc': float(roc_auc_score(y_true, y_pred_proba)),
            'confusion_matrix': confusion_matrix(y_true, y_pred).tolist()
        }
        
        # Classification report
        report = classification_report(y_true, y_pred, output_dict=True)
        metrics['classification_report'] = report
        
        # Log metrics
        logger.info(f"Accuracy: {metrics['accuracy']:.4f}")
        logger.info(f"Precision: {metrics['precision']:.4f}")
        logger.info(f"Recall: {metrics['recall']:.4f}")
        logger.info(f"F1 Score: {metrics['f1_score']:.4f}")
        logger.info(f"AUC-ROC: {metrics['auc_roc']:.4f}")
        
        return metrics
    
    def evaluate_at_thresholds(
        self, 
        y_true: np.ndarray, 
        y_pred_proba: np.ndarray,
        thresholds: list = None
    ) -> dict:
        """
        Evaluate model at different thresholds
        
        Args:
            y_true: True labels
            y_pred_proba: Predicted probabilities
            thresholds: List of thresholds to evaluate
            
        Returns:
            Dictionary with metrics at each threshold
        """
        if thresholds is None:
            thresholds = [0.3, 0.4, 0.5, 0.6, 0.7]
        
        logger.info(f"Evaluating at {len(thresholds)} thresholds")
        
        results = {}
        
        for threshold in thresholds:
            self.threshold = threshold
            y_pred = (y_pred_proba >= threshold).astype(int)
            
            results[str(threshold)] = {
                'accuracy': float(accuracy_score(y_true, y_pred)),
                'precision': float(precision_score(y_true, y_pred)),
                'recall': float(recall_score(y_true, y_pred)),
                'f1_score': float(f1_score(y_true, y_pred))
            }
        
        return results
    
    def calculate_cost_savings(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        fraud_cost: float = 100.0,
        investigation_cost: float = 5.0
    ) -> dict:
        """
        Calculate cost savings from fraud detection
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            fraud_cost: Average cost of a fraud transaction
            investigation_cost: Cost to investigate a transaction
            
        Returns:
            Dictionary with cost analysis
        """
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()
        
        # Calculate costs
        fraud_prevented = tp * fraud_cost
        investigation_costs = (tp + fp) * investigation_cost
        fraud_missed = fn * fraud_cost
        
        net_savings = fraud_prevented - investigation_costs - fraud_missed
        
        cost_analysis = {
            'fraud_prevented_value': float(fraud_prevented),
            'investigation_costs': float(investigation_costs),
            'fraud_missed_value': float(fraud_missed),
            'net_savings': float(net_savings),
            'true_positives': int(tp),
            'false_positives': int(fp),
            'false_negatives': int(fn),
            'true_negatives': int(tn)
        }
        
        logger.info(f"Net savings: ${net_savings:,.2f}")
        
        return cost_analysis
    
    def save_report(self, metrics: dict, filename: str = "evaluation_report.json"):
        """
        Save evaluation report to file
        
        Args:
            metrics: Evaluation metrics
            filename: Output filename
        """
        report_path = Path("reports")
        report_path.mkdir(exist_ok=True)
        
        filepath = report_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Saved evaluation report to {filepath}")