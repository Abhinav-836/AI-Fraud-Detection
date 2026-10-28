import os
from typing import Tuple

import pandas as pd

from ..utils.config import load_settings, load_yaml, resolve_path, writable_path
from ..utils.logger import get_logger
from .kaggle_loader import load_kaggle_dataset
from .simulator import generate_dataset

logger = get_logger(__name__)

REQUIRED_COLUMNS = ["timestamp", "amount", "is_fraud"]


class DataLoader:
    """Load transaction data from the simulator, the Kaggle dataset, a CSV or Postgres."""

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = load_settings(config_path)

    # ------------------------------------------------------------ sources
    def load_synthetic_data(self, n_customers: int = 2000, days: int = 60, seed: int = 42) -> pd.DataFrame:
        logger.info(f"Simulating {n_customers} customers over {days} days")
        df = generate_dataset(n_customers=n_customers, days=days, seed=seed)
        logger.info(f"Simulated {len(df)} transactions ({df['is_fraud'].mean():.2%} fraud)")
        return df

    def load_kaggle(self, directory: str = "data/raw/kaggle") -> pd.DataFrame:
        return load_kaggle_dataset(directory)

    def load_csv(self, filename: str) -> pd.DataFrame:
        """
        CSV in this project's schema: timestamp, amount, is_fraud, and ideally
        card_id, merchant_category, device_type, location_country.
        """
        path = resolve_path(filename)
        if not path.exists():
            path = resolve_path("data/raw") / filename
        df = pd.read_csv(path)
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"{path.name} is missing required columns: {missing}")
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp", kind="stable").reset_index(drop=True)
        logger.info(f"Loaded {len(df)} records from {path.name}")
        return df

    def _database_url(self) -> str:
        if os.getenv("DATABASE_URL"):
            return os.environ["DATABASE_URL"]
        db = self.config.get('database', {})
        creds_path = resolve_path("config/credentials.yaml")
        creds = load_yaml(creds_path).get('database', {}) if creds_path.exists() else {}
        user, password = creds.get('username', ''), creds.get('password', '')
        auth = f"{user}:{password}@" if user else ""
        return f"postgresql://{auth}{db.get('host', 'localhost')}:{db.get('port', 5432)}/{db.get('name', 'fraud_detection')}"

    def load_from_database(self, query: str) -> pd.DataFrame:
        from sqlalchemy import create_engine, text  # optional dependency
        engine = create_engine(self._database_url())
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)

    # ------------------------------------------------------------ splitting
    @staticmethod
    def time_split(df: pd.DataFrame, val_size: float = 0.15, test_size: float = 0.15
                   ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Chronological split: train on the past, validate on the next period,
        test on the most recent. A random split leaks future card behaviour
        into training and overstates how well the model will do live.
        """
        df = df.sort_values("timestamp", kind="stable")
        n = len(df)
        train_end = int(n * (1 - val_size - test_size))
        val_end = int(n * (1 - test_size))
        train, val, test = df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]
        logger.info(f"Time split: train={len(train)} val={len(val)} test={len(test)} "
                    f"(fraud {train['is_fraud'].mean():.2%}/{val['is_fraud'].mean():.2%}/{test['is_fraud'].mean():.2%})")
        return train, val, test

    def save_processed_data(self, df: pd.DataFrame, filename: str):
        path = writable_path("data/processed") / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        logger.info(f"Saved {path}")
