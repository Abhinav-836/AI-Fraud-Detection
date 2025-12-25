import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import yaml
from sqlalchemy import create_engine
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DataLoader:
    """Load data from various sources for fraud detection"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)
        self.data_path = Path("data")
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_csv(self, filename: str, data_type: str = "raw") -> pd.DataFrame:
        """
        Load data from CSV file
        
        Args:
            filename: Name of CSV file
            data_type: Type of data (raw, processed, external)
            
        Returns:
            DataFrame with loaded data
        """
        filepath = self.data_path / data_type / filename
        logger.info(f"Loading data from {filepath}")
        
        try:
            df = pd.read_csv(filepath)
            logger.info(f"Loaded {len(df)} records from {filename}")
            return df
        except Exception as e:
            logger.error(f"Error loading {filename}: {str(e)}")
            raise
    
    def load_from_database(self, query: str) -> pd.DataFrame:
        """
        Load data from database
        
        Args:
            query: SQL query to execute
            
        Returns:
            DataFrame with query results
        """
        db_config = self.config['database']
        connection_string = (
            f"postgresql://{db_config['host']}:{db_config['port']}/{db_config['name']}"
        )
        
        logger.info("Loading data from database")
        
        try:
            engine = create_engine(connection_string)
            df = pd.read_sql(query, engine)
            logger.info(f"Loaded {len(df)} records from database")
            return df
        except Exception as e:
            logger.error(f"Error loading from database: {str(e)}")
            raise
    
    def load_synthetic_data(self, n_samples: int = 10000, fraud_ratio: float = 0.1) -> pd.DataFrame:
        """
        Generate synthetic transaction data for testing
        
        Args:
            n_samples: Number of samples to generate
            fraud_ratio: Proportion of fraudulent transactions
            
        Returns:
            DataFrame with synthetic data
        """
        logger.info(f"Generating {n_samples} synthetic transactions")
        
        np.random.seed(42)
        
        # Generate normal transactions
        n_fraud = int(n_samples * fraud_ratio)
        n_normal = n_samples - n_fraud
        
        data = {
            'transaction_id': [f'TXN_{i:08d}' for i in range(n_samples)],
            'amount': np.concatenate([
                np.random.lognormal(3, 1, n_normal),  # Normal transactions
                np.random.lognormal(5, 1.5, n_fraud)  # Fraudulent transactions
            ]),
            'merchant_category': np.random.choice(
                ['retail', 'food', 'travel', 'entertainment', 'utilities'], 
                n_samples
            ),
            'device_type': np.random.choice(
                ['mobile', 'web', 'pos'], 
                n_samples, 
                p=[0.5, 0.3, 0.2]
            ),
            'location_country': np.random.choice(
                ['US', 'UK', 'CA', 'DE', 'FR'], 
                n_samples
            ),
            'hour_of_day': np.random.randint(0, 24, n_samples),
            'day_of_week': np.random.randint(0, 7, n_samples),
            'is_fraud': np.concatenate([
                np.zeros(n_normal, dtype=int),
                np.ones(n_fraud, dtype=int)
            ])
        }
        
        df = pd.DataFrame(data)
        
        # Shuffle the dataframe
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)
        
        # Add timestamp
        df['timestamp'] = pd.date_range(
            start='2024-01-01', 
            periods=n_samples, 
            freq='5min'
        )
        
        logger.info(f"Generated {n_samples} synthetic transactions ({n_fraud} fraudulent)")
        return df
    
    def save_processed_data(self, df: pd.DataFrame, filename: str):
        """
        Save processed data to CSV
        
        Args:
            df: DataFrame to save
            filename: Output filename
        """
        filepath = self.data_path / "processed" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(filepath, index=False)
        logger.info(f"Saved processed data to {filepath}")
    
    def split_data(
        self, 
        df: pd.DataFrame, 
        target_col: str = 'is_fraud',
        test_size: float = 0.2,
        val_size: float = 0.1
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split data into train, validation, and test sets
        
        Args:
            df: Input DataFrame
            target_col: Name of target column
            test_size: Proportion of test data
            val_size: Proportion of validation data
            
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        from sklearn.model_selection import train_test_split
        
        # First split: train+val and test
        train_val_df, test_df = train_test_split(
            df, 
            test_size=test_size,
            stratify=df[target_col],
            random_state=42
        )
        
        # Second split: train and validation
        val_ratio = val_size / (1 - test_size)
        train_df, val_df = train_test_split(
            train_val_df,
            test_size=val_ratio,
            stratify=train_val_df[target_col],
            random_state=42
        )
        
        logger.info(f"Split data: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")
        
        return train_df, val_df, test_df