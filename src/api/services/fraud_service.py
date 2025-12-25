import pandas as pd
from typing import Dict, List, Any
from datetime import datetime
from ...models.train import FraudModelTrainer
from ...preprocessing.transform import DataTransformer
from ...features.feature_engineering import FeatureEngineer
from ...models.model_registry import ModelRegistry
from ...utils.logger import get_logger

logger = get_logger(__name__)


class FraudDetectionService:
    """Service layer for fraud detection operations"""
    
    def __init__(self):
        self.model = None
        self.transformer = None
        self.engineer = None
        self.registry = ModelRegistry()
        self.threshold = 0.5
        
        # Statistics
        self.stats = {
            'total_predictions': 0,
            'fraud_detected': 0,
            'last_prediction_time': None
        }
    
    def initialize(self, model_version: str = None):
        """
        Initialize service components
        
        Args:
            model_version: Specific model version to load (optional)
        """
        logger.info("Initializing Fraud Detection Service")
        
        try:
            # Load model from registry
            if model_version:
                model_obj = self.registry.load_model(model_version)
                logger.info(f"Loaded model version: {model_version}")
            else:
                active_model = self.registry.get_active_model()
                if active_model:
                    model_obj = self.registry.load_model(active_model['version'])
                    logger.info(f"Loaded active model: {active_model['version']}")
                else:
                    # Fallback to default loading
                    self.model = FraudModelTrainer()
                    self.model.load_model('xgboost')
                    logger.info("Loaded default XGBoost model")
            
            # Load transformer
            self.transformer = DataTransformer()
            self.transformer.load_transformers()
            
            # Initialize feature engineer
            self.engineer = FeatureEngineer()
            
            logger.info("Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize service: {str(e)}")
            raise
    
    def predict_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict fraud for a single transaction
        
        Args:
            transaction: Transaction data
            
        Returns:
            Prediction result
        """
        start_time = datetime.now()
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame([transaction])
            
            # Add timestamp if missing
            if 'timestamp' not in df.columns or pd.isna(df['timestamp'].iloc[0]):
                df['timestamp'] = datetime.now()
            
            # Engineer features
            df = self.engineer.create_features(df)
            
            # Transform
            X = self.transformer.transform(df)
            
            # Predict
            fraud_prob = self.model.get_predictions('xgboost', X)[0]
            is_fraud = fraud_prob > self.threshold
            
            # Determine risk level
            risk_level = self._calculate_risk_level(fraud_prob)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_stats(is_fraud)
            
            result = {
                'transaction_id': transaction.get('transaction_id'),
                'is_fraud': bool(is_fraud),
                'fraud_probability': float(fraud_prob),
                'risk_level': risk_level,
                'confidence': self._calculate_confidence(fraud_prob),
                'processing_time_ms': processing_time,
                'timestamp': datetime.now().isoformat(),
                'model_version': self.registry.get_active_model()['version'] if self.registry.get_active_model() else 'default'
            }
            
            logger.info(
                f"Prediction: {transaction.get('transaction_id')} - "
                f"Fraud: {is_fraud}, Probability: {fraud_prob:.4f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            raise
    
    def predict_batch(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict fraud for multiple transactions
        
        Args:
            transactions: List of transactions
            
        Returns:
            List of prediction results
        """
        logger.info(f"Processing batch of {len(transactions)} transactions")
        
        results = []
        for transaction in transactions:
            try:
                result = self.predict_transaction(transaction)
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing transaction {transaction.get('transaction_id')}: {str(e)}")
                results.append({
                    'transaction_id': transaction.get('transaction_id'),
                    'error': str(e)
                })
        
        return results
    
    def _calculate_risk_level(self, probability: float) -> str:
        """Calculate risk level from probability"""
        if probability < 0.3:
            return "low"
        elif probability < 0.7:
            return "medium"
        else:
            return "high"
    
    def _calculate_confidence(self, probability: float) -> float:
        """Calculate prediction confidence"""
        # Distance from decision boundary (0.5)
        distance = abs(probability - 0.5)
        confidence = (distance * 2) * 100  # Scale to 0-100
        return round(confidence, 2)
    
    def _update_stats(self, is_fraud: bool):
        """Update service statistics"""
        self.stats['total_predictions'] += 1
        if is_fraud:
            self.stats['fraud_detected'] += 1
        self.stats['last_prediction_time'] = datetime.now().isoformat()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = self.stats.copy()
        
        if stats['total_predictions'] > 0:
            stats['fraud_rate'] = stats['fraud_detected'] / stats['total_predictions']
        else:
            stats['fraud_rate'] = 0
        
        return stats
    
    def validate_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate transaction data
        
        Args:
            transaction: Transaction to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['transaction_id', 'amount', 'merchant_category', 'device_type', 'location_country']
        for field in required_fields:
            if field not in transaction:
                errors.append(f"Missing required field: {field}")
        
        # Validate amount
        if 'amount' in transaction:
            if transaction['amount'] <= 0:
                errors.append("Amount must be positive")
            elif transaction['amount'] > 100000:
                warnings.append("Unusually large amount detected")
        
        # Validate hour_of_day
        if 'hour_of_day' in transaction:
            if not 0 <= transaction['hour_of_day'] <= 23:
                errors.append("hour_of_day must be between 0 and 23")
        
        # Validate day_of_week
        if 'day_of_week' in transaction:
            if not 0 <= transaction['day_of_week'] <= 6:
                errors.append("day_of_week must be between 0 and 6")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def explain_prediction(self, transaction: Dict[str, Any], prediction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide explanation for a prediction
        
        Args:
            transaction: Original transaction
            prediction: Prediction result
            
        Returns:
            Explanation dictionary
        """
        explanation = {
            'transaction_id': transaction.get('transaction_id'),
            'prediction': prediction['is_fraud'],
            'probability': prediction['fraud_probability'],
            'factors': []
        }
        
        # Analyze key factors
        if transaction.get('amount', 0) > 1000:
            explanation['factors'].append({
                'factor': 'high_amount',
                'description': 'Transaction amount is unusually high',
                'impact': 'increases_risk'
            })
        
        if transaction.get('hour_of_day', 12) in [0, 1, 2, 3, 4]:
            explanation['factors'].append({
                'factor': 'unusual_time',
                'description': 'Transaction occurred during unusual hours',
                'impact': 'increases_risk'
            })
        
        if prediction['risk_level'] == 'high':
            explanation['factors'].append({
                'factor': 'high_risk_score',
                'description': 'Multiple risk indicators detected',
                'impact': 'increases_risk'
            })
        
        return explanation
    
    def set_threshold(self, threshold: float):
        """Set prediction threshold"""
        if not 0 <= threshold <= 1:
            raise ValueError("Threshold must be between 0 and 1")
        
        self.threshold = threshold
        logger.info(f"Threshold updated to {threshold}")
    
    def reload_model(self, version: str = None):
        """Reload model from registry"""
        logger.info("Reloading model")
        self.initialize(model_version=version)