import pandas as pd
import numpy as np
from typing import List, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """Clean and prepare transaction data"""
    
    def __init__(self):
        self.cleaning_report = {}
    
    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all cleaning steps to the dataframe
        
        Args:
            df: Input DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        logger.info("Starting data cleaning")
        
        df = df.copy()
        
        # Store original shape
        original_shape = df.shape
        
        # Apply cleaning steps
        df = self.handle_missing_values(df)
        df = self.remove_duplicates(df)
        df = self.handle_outliers(df)
        df = self.fix_data_types(df)
        df = self.validate_ranges(df)
        
        # Log cleaning report
        final_shape = df.shape
        logger.info(f"Cleaning complete: {original_shape} -> {final_shape}")
        logger.info(f"Removed {original_shape[0] - final_shape[0]} rows")
        
        return df
    
    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataset"""
        logger.info("Handling missing values")
        
        missing_before = df.isnull().sum().sum()
        
        # Strategy for different column types
        for col in df.columns:
            if df[col].isnull().sum() > 0:
                if df[col].dtype in ['float64', 'int64']:
                    # Fill numerical columns with median
                    df[col].fillna(df[col].median(), inplace=True)
                else:
                    # Fill categorical columns with mode
                    df[col].fillna(df[col].mode()[0] if len(df[col].mode()) > 0 else 'unknown', inplace=True)
        
        missing_after = df.isnull().sum().sum()
        logger.info(f"Filled {missing_before - missing_after} missing values")
        
        return df
    
    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate transactions"""
        logger.info("Removing duplicates")
        
        before_count = len(df)
        
        # Keep first occurrence of duplicates
        df = df.drop_duplicates(subset=['transaction_id'], keep='first')
        
        removed_count = before_count - len(df)
        logger.info(f"Removed {removed_count} duplicate transactions")
        
        return df
    
    def handle_outliers(
        self, 
        df: pd.DataFrame, 
        columns: Optional[List[str]] = None,
        method: str = 'iqr'
    ) -> pd.DataFrame:
        """
        Handle outliers in numerical columns
        
        Args:
            df: Input DataFrame
            columns: List of columns to check for outliers
            method: Method to use ('iqr' or 'zscore')
            
        Returns:
            DataFrame with outliers handled
        """
        logger.info(f"Handling outliers using {method} method")
        
        if columns is None:
            columns = ['amount']
        
        before_count = len(df)
        
        for col in columns:
            if col not in df.columns:
                continue
                
            if method == 'iqr':
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 3 * IQR
                upper_bound = Q3 + 3 * IQR
                
                # Cap outliers instead of removing
                df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
            
            elif method == 'zscore':
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                df = df[z_scores < 3]
        
        removed_count = before_count - len(df)
        if removed_count > 0:
            logger.info(f"Handled {removed_count} outlier records")
        
        return df
    
    def fix_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure correct data types for all columns"""
        logger.info("Fixing data types")
        
        # Convert timestamp if present
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Ensure amount is float
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # Ensure categorical columns are strings
        categorical_cols = ['merchant_category', 'device_type', 'location_country']
        for col in categorical_cols:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        # Ensure target is integer
        if 'is_fraud' in df.columns:
            df['is_fraud'] = df['is_fraud'].astype(int)
        
        return df
    
    def validate_ranges(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate that values are within expected ranges"""
        logger.info("Validating value ranges")
        
        before_count = len(df)
        
        # Amount should be positive
        if 'amount' in df.columns:
            df = df[df['amount'] > 0]
        
        # Hour should be 0-23
        if 'hour_of_day' in df.columns:
            df = df[(df['hour_of_day'] >= 0) & (df['hour_of_day'] <= 23)]
        
        # Day of week should be 0-6
        if 'day_of_week' in df.columns:
            df = df[(df['day_of_week'] >= 0) & (df['day_of_week'] <= 6)]
        
        removed_count = before_count - len(df)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} records with invalid ranges")
        
        return df
    
    def get_data_quality_report(self, df: pd.DataFrame) -> dict:
        """Generate a data quality report"""
        report = {
            'total_records': len(df),
            'total_features': len(df.columns),
            'missing_values': df.isnull().sum().to_dict(),
            'duplicate_count': df.duplicated().sum(),
            'data_types': df.dtypes.astype(str).to_dict(),
            'numeric_summary': df.describe().to_dict() if len(df.select_dtypes(include=[np.number]).columns) > 0 else {}
        }
        
        return report