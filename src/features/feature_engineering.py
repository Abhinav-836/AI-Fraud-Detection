import pandas as pd
import numpy as np
from typing import List
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FeatureEngineer:
    """Engineer features for fraud detection"""
    
    def __init__(self):
        self.feature_history = {}
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create all engineered features
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with engineered features
        """
        logger.info("Creating engineered features")
        
        df = df.copy()
        
        # Time-based features
        df = self.create_time_features(df)
        
        # Transaction velocity features
        df = self.create_velocity_features(df)
        
        # Amount-based features
        df = self.create_amount_features(df)
        
        # Behavioral features
        df = self.create_behavioral_features(df)
        
        # Interaction features
        df = self.create_interaction_features(df)
        
        logger.info(f"Created features. Total columns: {len(df.columns)}")
        
        return df
    
    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features"""
        logger.info("Creating time features")
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Extract time components
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['day_of_month'] = df['timestamp'].dt.day
            df['month'] = df['timestamp'].dt.month
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
            
            # Time of day categories
            df['time_of_day'] = pd.cut(
                df['hour'], 
                bins=[0, 6, 12, 18, 24], 
                labels=['night', 'morning', 'afternoon', 'evening'],
                include_lowest=True
            )
            
            # Business hours
            df['is_business_hours'] = ((df['hour'] >= 9) & (df['hour'] <= 17)).astype(int)
        
        return df
    
    def create_velocity_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create transaction velocity features"""
        logger.info("Creating velocity features")
        
        if 'timestamp' in df.columns and 'transaction_id' in df.columns:
            df = df.sort_values('timestamp')
            
            # Time since last transaction (in minutes)
            df['time_since_last_txn'] = df.groupby('transaction_id')['timestamp'].diff().dt.total_seconds() / 60
            df['time_since_last_txn'].fillna(0, inplace=True)
            
            # Transaction count in time windows
            df['txn_count_1h'] = self._count_in_window(df, window='1H')
            df['txn_count_24h'] = self._count_in_window(df, window='24H')
            df['txn_count_7d'] = self._count_in_window(df, window='7D')
            
            # Transaction frequency
            df['txn_frequency'] = df['txn_count_24h'] / 24
        
        return df
    
    def create_amount_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create amount-based features"""
        logger.info("Creating amount features")
        
        if 'amount' in df.columns:
            # Log transform
            df['amount_log'] = np.log1p(df['amount'])
            
            # Rolling statistics
            df['amount_mean_7d'] = df.groupby('transaction_id')['amount'].transform(
                lambda x: x.rolling(window=7, min_periods=1).mean()
            )
            df['amount_std_7d'] = df.groupby('transaction_id')['amount'].transform(
                lambda x: x.rolling(window=7, min_periods=1).std()
            ).fillna(0)
            
            # Ratio to average
            df['amount_to_avg_ratio'] = df['amount'] / (df['amount_mean_7d'] + 1)
            
            # Amount categories
            df['amount_category'] = pd.cut(
                df['amount'],
                bins=[0, 50, 200, 500, float('inf')],
                labels=['small', 'medium', 'large', 'very_large']
            )
            
            # Z-score of amount
            mean_amount = df['amount'].mean()
            std_amount = df['amount'].std()
            df['amount_zscore'] = (df['amount'] - mean_amount) / (std_amount + 1e-10)
        
        return df
    
    def create_behavioral_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create behavioral pattern features"""
        logger.info("Creating behavioral features")
        
        # Device consistency
        if 'device_type' in df.columns:
            df['device_changes'] = (df.groupby('transaction_id')['device_type']
                                   .transform(lambda x: (x != x.shift()).cumsum()))
        
        # Location consistency
        if 'location_country' in df.columns:
            df['location_changes'] = (df.groupby('transaction_id')['location_country']
                                     .transform(lambda x: (x != x.shift()).cumsum()))
        
        # Merchant diversity
        if 'merchant_category' in df.columns:
            df['unique_merchants_7d'] = (df.groupby('transaction_id')['merchant_category']
                                        .transform(lambda x: x.rolling(window=7, min_periods=1)
                                                 .apply(lambda y: len(set(y)))))
        
        return df
    
    def create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create interaction features between existing features"""
        logger.info("Creating interaction features")
        
        # Amount and time interactions
        if 'amount' in df.columns and 'hour' in df.columns:
            df['amount_hour_interaction'] = df['amount'] * df['hour']
        
        # Amount and weekend interaction
        if 'amount' in df.columns and 'is_weekend' in df.columns:
            df['amount_weekend_ratio'] = df['amount'] * df['is_weekend']
        
        # Velocity and amount interaction
        if 'txn_count_24h' in df.columns and 'amount' in df.columns:
            df['velocity_amount_interaction'] = df['txn_count_24h'] * df['amount']
        
        return df
    
    def _count_in_window(self, df: pd.DataFrame, window: str) -> pd.Series:
        """Count transactions in a rolling time window"""
        df = df.sort_values('timestamp')
        df = df.set_index('timestamp')
        
        counts = df.groupby('transaction_id').rolling(window=window).size()
        
        df = df.reset_index()
        
        return counts.reset_index(level=0, drop=True)
    
    def select_top_features(
        self, 
        X: np.ndarray, 
        y: np.ndarray, 
        feature_names: List[str],
        k: int = 20
    ) -> List[str]:
        """
        Select top k features using feature importance
        
        Args:
            X: Feature matrix
            y: Target vector
            feature_names: List of feature names
            k: Number of features to select
            
        Returns:
            List of selected feature names
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.feature_selection import SelectKBest, f_classif
        
        logger.info(f"Selecting top {k} features")
        
        # Use Random Forest for feature importance
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X, y)
        
        # Get feature importances
        importances = rf.feature_importances_
        indices = np.argsort(importances)[::-1][:k]
        
        selected_features = [feature_names[i] for i in indices]
        
        logger.info(f"Selected features: {selected_features}")
        
        return selected_features
    
    def get_feature_importance(self, feature_names: List[str], importances: np.ndarray) -> pd.DataFrame:
        """Get feature importance dataframe"""
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        return importance_df