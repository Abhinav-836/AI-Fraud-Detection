"""
Data transformation and preprocessing utilities
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

class DataTransformer:
    """Transform and preprocess transaction data for fraud detection"""
    
    def __init__(self):
        self.feature_columns = []
        self.scaler = None
        self.encoder = None
        
    def transform_transaction(self, transaction: Dict[str, Any]) -> np.ndarray:
        """
        Transform a single transaction into feature vector
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Feature array
        """
        features = []
        
        # Extract and normalize amount
        amount = transaction.get('amount', 0)
        features.append(amount)
        
        # Card present flag
        card_present = 1 if transaction.get('card_present', True) else 0
        features.append(card_present)
        
        # Merchant category (simplified encoding)
        merchant_category = transaction.get('merchant_category', '0000')
        try:
            category_code = int(merchant_category)
        except:
            category_code = 0
        features.append(category_code)
        
        # Additional features can be added here
        
        return np.array(features).reshape(1, -1)
    
    def transform_batch(self, transactions: List[Dict[str, Any]]) -> np.ndarray:
        """
        Transform multiple transactions into feature matrix
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Feature matrix
        """
        feature_vectors = []
        for txn in transactions:
            features = self.transform_transaction(txn)
            feature_vectors.append(features[0])
        
        return np.array(feature_vectors)
    
    def fit_transform(self, data: pd.DataFrame) -> np.ndarray:
        """
        Fit transformer on training data and transform
        
        Args:
            data: Training dataframe
            
        Returns:
            Transformed feature array
        """
        # Placeholder for fitting logic
        # In a real implementation, you would fit scalers, encoders, etc.
        return data.values
    
    def inverse_transform(self, features: np.ndarray) -> Dict[str, Any]:
        """
        Convert feature vector back to transaction-like dictionary
        
        Args:
            features: Feature array
            
        Returns:
            Transaction dictionary
        """
        return {
            'amount': float(features[0]),
            'card_present': bool(features[1]),
            'merchant_category': str(int(features[2]))
        }