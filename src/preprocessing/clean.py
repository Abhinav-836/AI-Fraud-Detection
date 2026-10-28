from typing import List, Optional

import numpy as np
import pandas as pd

from ..utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """Clean and prepare transaction data"""

    def __init__(self):
        self.cleaning_report = {}

    def clean(self, df: pd.DataFrame, cap_outliers: bool = False) -> pd.DataFrame:
        """
        Apply all cleaning steps to the dataframe

        Args:
            df: Input DataFrame
            cap_outliers: Clip extreme amounts. Off by default: inference
                never clips, so clipping only at training time creates
                train/serve skew and erases the high-amount signal.

        Returns:
            Cleaned DataFrame
        """
        logger.info("Starting data cleaning")

        df = df.copy()
        original_shape = df.shape

        df = self.fix_data_types(df)
        df = self.handle_missing_values(df)
        df = self.remove_duplicates(df)
        if cap_outliers:
            df = self.handle_outliers(df)
        df = self.validate_ranges(df)

        final_shape = df.shape
        self.cleaning_report = {
            'original_rows': original_shape[0],
            'final_rows': final_shape[0],
            'rows_removed': original_shape[0] - final_shape[0],
        }
        logger.info(f"Cleaning complete: {original_shape} -> {final_shape}")
        return df

    def handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values in the dataset"""
        missing_before = int(df.isnull().sum().sum())

        for col in df.columns:
            if not df[col].isnull().any():
                continue
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue  # timestamps are resolved during feature engineering
            if pd.api.types.is_numeric_dtype(df[col]):
                # Assign back: `df[col].fillna(..., inplace=True)` is chained
                # assignment and is a silent no-op under pandas Copy-on-Write.
                df[col] = df[col].fillna(df[col].median())
            else:
                mode = df[col].mode()
                df[col] = df[col].fillna(mode.iloc[0] if len(mode) else 'unknown')

        missing_after = int(df.isnull().sum().sum())
        logger.info(f"Filled {missing_before - missing_after} missing values")
        return df

    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate transactions"""
        if 'transaction_id' not in df.columns:
            return df.drop_duplicates()
        before = len(df)
        df = df.drop_duplicates(subset=['transaction_id'], keep='first')
        logger.info(f"Removed {before - len(df)} duplicate transactions")
        return df

    def handle_outliers(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        method: str = 'iqr'
    ) -> pd.DataFrame:
        """Cap (iqr) or drop (zscore) outliers in numerical columns"""
        columns = columns or ['amount']
        for col in columns:
            if col not in df.columns:
                continue
            if method == 'iqr':
                q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
                iqr = q3 - q1
                df[col] = df[col].clip(lower=q1 - 3 * iqr, upper=q3 + 3 * iqr)
            elif method == 'zscore':
                std = df[col].std()
                if std and std > 0:
                    df = df[np.abs((df[col] - df[col].mean()) / std) < 3]
            else:
                raise ValueError(f"Unknown outlier method: {method}")
        return df

    def fix_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure correct data types for all columns"""
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        for col in ['hour_of_day', 'day_of_week']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        for col in ['merchant_category', 'device_type', 'location_country']:
            if col in df.columns:
                df[col] = df[col].where(df[col].isna(), df[col].astype(str))
        if 'is_fraud' in df.columns:
            df['is_fraud'] = pd.to_numeric(df['is_fraud'], errors='coerce')
        return df

    def validate_ranges(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop rows whose values are outside valid ranges"""
        before = len(df)
        if 'amount' in df.columns:
            df = df[df['amount'] > 0]
        if 'hour_of_day' in df.columns:
            df = df[df['hour_of_day'].between(0, 23)]
        if 'day_of_week' in df.columns:
            df = df[df['day_of_week'].between(0, 6)]
        if 'is_fraud' in df.columns:
            df = df[df['is_fraud'].isin([0, 1])]
            df = df.assign(is_fraud=df['is_fraud'].astype(int))
        removed = before - len(df)
        if removed:
            logger.info(f"Removed {removed} records with invalid ranges")
        return df

    def get_data_quality_report(self, df: pd.DataFrame) -> dict:
        """Generate a data quality report"""
        numeric = df.select_dtypes(include=[np.number])
        return {
            'total_records': len(df),
            'total_features': len(df.columns),
            'missing_values': df.isnull().sum().to_dict(),
            'duplicate_count': int(df.duplicated().sum()),
            'data_types': df.dtypes.astype(str).to_dict(),
            'numeric_summary': numeric.describe().to_dict() if not numeric.empty else {}
        }