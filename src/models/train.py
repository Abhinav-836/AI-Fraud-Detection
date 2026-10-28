import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from xgboost import XGBClassifier

from ..utils.config import load_model_config, model_dir, resolve_path
from ..utils.logger import get_logger

logger = get_logger(__name__)

MODEL_FILE = "model.pkl"
METADATA_FILE = "metadata.json"
_LR_DEPRECATED = ("penalty", "n_jobs")  # removed from LogisticRegression in scikit-learn 1.10


def _calibrate(model, X_val, y_val):
    """
    Isotonic calibration on validation data, so a score of 0.8 really means
    ~80% of such transactions are fraud. Class-weighted training inflates raw
    scores (a normal $250 purchase used to show 41% risk).
    """
    try:
        from sklearn.frozen import FrozenEstimator  # scikit-learn >= 1.6
        calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="isotonic")
    except ImportError:  # older scikit-learn
        calibrated = CalibratedClassifierCV(model, method="isotonic", cv="prefit")
    return calibrated.fit(X_val, y_val)


class FraudModelTrainer:
    """Train candidate models, pick the best on validation PR-AUC, calibrate it."""

    def __init__(self, config_path: str = "config/model_config.yaml"):
        self.config = load_model_config(config_path)
        self.candidates: Dict[str, Any] = {}
        self.scores: Dict[str, Dict[str, float]] = {}
        self.best_model: Optional[str] = None
        self.model = None  # calibrated best model

    @staticmethod
    def _dir(path: Optional[Union[str, Path]]) -> Path:
        return resolve_path(path) if path else model_dir()

    # ------------------------------------------------------------ training
    def train_xgboost(self, X_train, y_train, X_val, y_val) -> XGBClassifier:
        params = dict(self.config.get("xgboost", {}))
        if params.get("scale_pos_weight", "auto") in (1, None, "auto"):
            pos = max(int(np.sum(y_train)), 1)
            params["scale_pos_weight"] = (len(y_train) - pos) / pos
        params.setdefault("eval_metric", "aucpr")
        model = XGBClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        return model

    def train_random_forest(self, X_train, y_train) -> RandomForestClassifier:
        params = dict(self.config.get("random_forest", {}))
        params.setdefault("class_weight", "balanced_subsample")
        return RandomForestClassifier(**params).fit(X_train, y_train)

    def train_logistic_regression(self, X_train, y_train) -> LogisticRegression:
        params = {k: v for k, v in self.config.get("logistic_regression", {}).items() if k not in _LR_DEPRECATED}
        params.setdefault("class_weight", "balanced")
        return LogisticRegression(**params).fit(X_train, y_train)

    def train_all_models(self, X_train, y_train, X_val, y_val, models=("xgboost", "random_forest", "logistic_regression")):
        builders = {
            "xgboost": lambda: self.train_xgboost(X_train, y_train, X_val, y_val),
            "random_forest": lambda: self.train_random_forest(X_train, y_train),
            "logistic_regression": lambda: self.train_logistic_regression(X_train, y_train),
        }
        for name in models:
            logger.info(f"Training {name}")
            model = builders[name]()
            proba = model.predict_proba(X_val)[:, 1]
            self.candidates[name] = model
            self.scores[name] = {
                "val_pr_auc": float(average_precision_score(y_val, proba)),
                "val_roc_auc": float(roc_auc_score(y_val, proba)),
            }
            logger.info(f"{name}: PR-AUC {self.scores[name]['val_pr_auc']:.4f} ROC-AUC {self.scores[name]['val_roc_auc']:.4f}")

        # PR-AUC, not ROC-AUC: with ~1% fraud, ROC-AUC looks great even for
        # models that flag far too many good customers.
        self.best_model = max(self.scores, key=lambda n: self.scores[n]["val_pr_auc"])
        self.model = _calibrate(self.candidates[self.best_model], X_val, y_val)
        logger.info(f"Selected {self.best_model} (calibrated, isotonic)")
        return self.scores

    def predict_proba(self, X) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("No model trained or loaded")
        return self.model.predict_proba(X)[:, 1]

    # ------------------------------------------------------------ persistence
    def save(self, metadata: Dict[str, Any], path: Optional[Union[str, Path]] = None) -> Path:
        target = self._dir(path)
        target.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, target / MODEL_FILE)
        meta = {
            "model_type": self.best_model,
            "candidates": self.scores,
            "trained_at": datetime.now().astimezone().isoformat(),
            **metadata,
        }
        (target / METADATA_FILE).write_text(json.dumps(meta, indent=2, default=float), encoding="utf-8")
        logger.info(f"Saved model + metadata to {target}")
        return target

    @classmethod
    def read_metadata(cls, path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        target = cls._dir(path) / METADATA_FILE
        return json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}

    def load(self, path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        target = self._dir(path)
        model_file = target / MODEL_FILE
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_file}")
        self.model = joblib.load(model_file)
        meta = self.read_metadata(path)
        self.best_model = meta.get("model_type")
        logger.info(f"Loaded {self.best_model} from {model_file}")
        return meta
