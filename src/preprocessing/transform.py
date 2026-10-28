"""
Engineered feature frame -> numeric matrix.

The fitted transformer (scaler + one-hot encoder + exact column order) is
saved next to the model so inference uses the training-time mapping.
Input must already contain MODEL_COLUMNS (see feature_engineering.py).
"""
from pathlib import Path
from typing import List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, RobustScaler, StandardScaler

from ..features.feature_engineering import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from ..utils.config import load_model_config, model_dir, resolve_path
from ..utils.logger import get_logger

logger = get_logger(__name__)

TRANSFORMER_FILE = "transformer.pkl"
_SCALERS = {"standard": StandardScaler, "minmax": MinMaxScaler, "robust": RobustScaler}


class DataTransformer:
    """Scale numeric features and one-hot encode categorical ones."""

    def __init__(self, scaler: Optional[str] = None):
        if scaler is None:
            try:
                scaler = load_model_config().get("preprocessing", {}).get("scaler", "standard")
            except FileNotFoundError:
                scaler = "standard"
        if scaler not in _SCALERS:
            raise ValueError(f"Unknown scaler '{scaler}'. Use one of {list(_SCALERS)}")
        self.scaler_name = scaler
        self.numeric_features: List[str] = list(NUMERIC_FEATURES)
        self.categorical_features: List[str] = list(CATEGORICAL_FEATURES)
        self.column_transformer: Optional[ColumnTransformer] = None
        self.feature_names: List[str] = []

    @property
    def is_fitted(self) -> bool:
        return self.column_transformer is not None

    def _build(self) -> ColumnTransformer:
        return ColumnTransformer(
            transformers=[
                ("num", _SCALERS[self.scaler_name](), self.numeric_features),
                # Unseen categories at inference become all-zeros instead of raising
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), self.categorical_features),
            ],
            remainder="drop",
        )

    def fit(self, features: pd.DataFrame) -> "DataTransformer":
        self.column_transformer = self._build().fit(features[self.numeric_features + self.categorical_features])
        self.feature_names = [n.split("__", 1)[-1] for n in self.column_transformer.get_feature_names_out()]
        logger.info(f"Transformer fitted with {len(self.feature_names)} model inputs")
        return self

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("DataTransformer is not fitted. Call fit() or load_transformers().")
        cols = features[self.numeric_features + self.categorical_features]
        return np.asarray(self.column_transformer.transform(cols), dtype=np.float64)

    def fit_transform(self, features: pd.DataFrame) -> np.ndarray:
        return self.fit(features).transform(features)

    def transform_one(self, feature_row: dict) -> np.ndarray:
        return self.transform(pd.DataFrame([feature_row]))

    def source_feature_of(self, model_input: str) -> str:
        """Map a model input name (e.g. 'merchant_category_gambling') back to its source feature."""
        for cat in self.categorical_features:
            if model_input.startswith(cat + "_"):
                return cat
        return model_input

    # -------------------------------------------------------- persistence
    @staticmethod
    def _artifact_path(path: Optional[Union[str, Path]]) -> Path:
        base = resolve_path(path) if path else model_dir() / "transformers"
        return base / TRANSFORMER_FILE

    def save_transformers(self, path: Optional[Union[str, Path]] = None) -> Path:
        if not self.is_fitted:
            raise RuntimeError("Nothing to save: transformer is not fitted")
        target = self._artifact_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "column_transformer": self.column_transformer,
            "feature_names": self.feature_names,
            "numeric_features": self.numeric_features,
            "categorical_features": self.categorical_features,
            "scaler_name": self.scaler_name,
        }, target)
        logger.info(f"Saved transformer to {target}")
        return target

    def load_transformers(self, path: Optional[Union[str, Path]] = None) -> "DataTransformer":
        source = self._artifact_path(path)
        if not source.exists():
            raise FileNotFoundError(f"Transformer artifact not found: {source}")
        state = joblib.load(source)
        if state["numeric_features"] != list(NUMERIC_FEATURES):
            raise ValueError("Saved transformer was trained with a different feature set; retrain the model.")
        self.column_transformer = state["column_transformer"]
        self.feature_names = state["feature_names"]
        self.numeric_features = state["numeric_features"]
        self.categorical_features = state["categorical_features"]
        self.scaler_name = state["scaler_name"]
        logger.info(f"Loaded transformer from {source}")
        return self
