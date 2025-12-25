import pandas as pd
import numpy as np
from datetime import datetime
from ..models.train import FraudModelTrainer
from ..preprocessing.transform import DataTransformer
from ..features.feature_engineering import FeatureEngineer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RealTimeDetector:
    """Real-time fraud detection for streaming transactions"""
    
    def __init__(self, model_path: str = "models", threshold: float = 0.5):
        self.threshold = threshold
        self.model = None
        self.transformer = None
        self.engineer = None
        self.load_components(model_path)
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'fraud_detected': 0,
            'processing_times': []
        }
    
    def load_components(self, model_path: str):
        """Load model and preprocessing components"""
        logger.info("Loading detection components")
        
        try:
            # Load model
            self.model = FraudModelTrainer()
            self.model.load_model('xgboost', model_path)
            
            # Load transformer
            self.transformer = DataTransformer()
            self.transformer.load_transformers(f"{model_path}/transformers")
            
            # Initialize feature engineer
            self.engineer = FeatureEngineer()
            
            logger.info("Components loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading components: {str(e)}")
            raise
    
    def detect(self, transaction: dict) -> dict:
        """
        Detect fraud in a single transaction
        
        Args:
            transaction: Transaction data dictionary
            
        Returns:
            Detection result with fraud score and metadata
        """
        start_time = datetime.now()
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame([transaction])
            
            # Engineer features
            df = self.engineer.create_features(df)
            
            # Transform
            X = self.transformer.transform(df)
            
            # Predict
            fraud_prob = self.model.get_predictions('xgboost', X)[0]
            is_fraud = fraud_prob > self.threshold
            
            # Determine risk level
            if fraud_prob < 0.3:
                risk_level = "low"
            elif fraud_prob < 0.7:
                risk_level = "medium"
            else:
                risk_level = "high"
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update statistics
            self.stats['total_processed'] += 1
            if is_fraud:
                self.stats['fraud_detected'] += 1
            self.stats['processing_times'].append(processing_time)
            
            result = {
                'transaction_id': transaction.get('transaction_id'),
                'is_fraud': bool(is_fraud),
                'fraud_probability': float(fraud_prob),
                'risk_level': risk_level,
                'processing_time_ms': processing_time,
                'timestamp': datetime.now().isoformat()
            }
            
            if is_fraud:
                logger.warning(
                    f"FRAUD DETECTED - ID: {transaction.get('transaction_id')}, "
                    f"Probability: {fraud_prob:.4f}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting fraud: {str(e)}")
            return {
                'transaction_id': transaction.get('transaction_id'),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def detect_batch(self, transactions: list) -> list:
        """
        Detect fraud in a batch of transactions
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of detection results
        """
        logger.info(f"Processing batch of {len(transactions)} transactions")
        
        results = []
        for transaction in transactions:
            result = self.detect(transaction)
            results.append(result)
        
        return results
    
    def get_statistics(self) -> dict:
        """Get detection statistics"""
        stats = self.stats.copy()
        
        if stats['processing_times']:
            stats['avg_processing_time_ms'] = np.mean(stats['processing_times'])
            stats['max_processing_time_ms'] = np.max(stats['processing_times'])
            stats['min_processing_time_ms'] = np.min(stats['processing_times'])
        
        if stats['total_processed'] > 0:
            stats['fraud_rate'] = stats['fraud_detected'] / stats['total_processed']
        
        return stats
    
    def reset_statistics(self):
        """Reset detection statistics"""
        self.stats = {
            'total_processed': 0,
            'fraud_detected': 0,
            'processing_times': []
        }
        logger.info("Statistics reset")