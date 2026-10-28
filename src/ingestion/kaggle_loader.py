"""
Loader for the Kaggle "Credit Card Transactions Fraud Detection Dataset"
(kartik2112/fraud-detection): fraudTrain.csv + fraudTest.csv, ~1.85M rows.

Download it yourself (Kaggle needs a login), unzip the two CSVs into
data/raw/kaggle/, then train with:

    python -m src.pipelines.training_pipeline --source kaggle

Column mapping to this project's schema:
    cc_num                -> card_id
    trans_date_trans_time -> timestamp
    amt                   -> amount
    category              -> merchant_category   (e.g. grocery_pos, shopping_net)
    *_net categories      -> device_type "web", everything else "pos"
    (all US)              -> location_country "US"
    trans_num             -> transaction_id
    is_fraud              -> is_fraud
"""
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ..utils.config import resolve_path
from ..utils.logger import get_logger

logger = get_logger(__name__)

KAGGLE_FILES = ("fraudTrain.csv", "fraudTest.csv")
REQUIRED = ["cc_num", "trans_date_trans_time", "amt", "category", "trans_num", "is_fraud"]


def map_kaggle_frame(raw: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        raise ValueError(f"Not the Kaggle card-transactions format; missing columns: {missing}")
    category = raw["category"].astype(str).str.lower()
    df = pd.DataFrame({
        "transaction_id": raw["trans_num"].astype(str),
        "card_id": raw["cc_num"].astype(str),
        "timestamp": pd.to_datetime(raw["trans_date_trans_time"]),
        "amount": raw["amt"].astype(float),
        "merchant_category": category,
        "device_type": category.str.endswith("_net").map({True: "web", False: "pos"}),
        "location_country": "US",
        "is_fraud": raw["is_fraud"].astype(int),
    })
    return df.sort_values("timestamp", kind="stable").reset_index(drop=True)


def load_kaggle_dataset(directory: Union[str, Path] = "data/raw/kaggle", nrows: Optional[int] = None) -> pd.DataFrame:
    """Read and map fraudTrain.csv / fraudTest.csv (whichever exist)."""
    folder = resolve_path(directory)
    frames = []
    for name in KAGGLE_FILES:
        path = folder / name
        if path.exists():
            logger.info(f"Reading {path}")
            frames.append(pd.read_csv(path, usecols=REQUIRED, nrows=nrows))
    if not frames:
        raise FileNotFoundError(
            f"No Kaggle files found in {folder}. Download 'kartik2112/fraud-detection' from Kaggle "
            f"and place {' / '.join(KAGGLE_FILES)} there."
        )
    df = map_kaggle_frame(pd.concat(frames, ignore_index=True))
    logger.info(f"Loaded {len(df)} Kaggle transactions ({df['is_fraud'].mean():.2%} fraud)")
    return df
