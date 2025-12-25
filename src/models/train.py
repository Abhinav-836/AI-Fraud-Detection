import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, roc_auc_score
import joblib
import yaml
from pathlib import Path
from typing import Dict, Any
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FraudModelTrainer:
    """Train fraud detection models"""
    
    def __init__(self, config_path: str = "config/model_config.yaml"):
        self.config = self._load_config(config_path)
        self.models = {}
        self.best_model = None
        self.best_score = 0
        
    def _load_config(self, config_path: str) -> dict:
        """Load model configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def train_xgboost(self, X_train, y_train, X_val, y_val) -> XGBClassifier:
        """Train XGBoost model"""
        logger.info("Training XGBoost model")
        
        params = self.config['xgboost']
        
        model = XGBClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        return model
    
    def train_random_forest(self, X_train, y_train) -> RandomForestClassifier:
        """Train Random Forest model"""
        logger.info("Training Random Forest model")
        
        params = self.config['random_forest']
        
        model = RandomForestClassifier(**params)
        model.fit(X_train, y_train)
        
        return model
    
    def train_logistic_regression(self, X_train, y_train) -> LogisticRegression:
        """Train Logistic Regression model"""
        logger.info("Training Logistic Regression model")
        
        params = self.config['logistic_regression']
        
        model = LogisticRegression(**params)
        model.fit(X_train, y_train)
        
        return model
    
    def train_all_models(self, X_train, y_train, X_val, y_val) -> Dict[str, Any]:
        """Train all configured models"""
        logger.info("Training all models")
        
        # Train XGBoost
        self.models['xgboost'] = self.train_xgboost(X_train, y_train, X_val, y_val)
        
        # Train Random Forest
        self.models['random_forest'] = self.train_random_forest(X_train, y_train)
        
        # Train Logistic Regression
        self.models['logistic_regression'] = self.train_logistic_regression(X_train, y_train)
        
        # Evaluate all models on validation set
        results = {}
        for name, model in self.models.items():
            score = self._evaluate_model(model, X_val, y_val)
            results[name] = score
            
            logger.info(f"{name} - AUC: {score:.4f}")
            
            # Track best model
            if score > self.best_score:
                self.best_score = score
                self.best_model = name
        
        logger.info(f"Best model: {self.best_model} (AUC: {self.best_score:.4f})")
        
        return results
    
    def _evaluate_model(self, model, X, y) -> float:
        """Evaluate model and return AUC score"""
        y_pred_proba = model.predict_proba(X)[:, 1]
        return roc_auc_score(y, y_pred_proba)
    
    def get_predictions(self, model_name: str, X) -> np.ndarray:
        """Get predictions from a specific model"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        
        model = self.models[model_name]
        return model.predict_proba(X)[:, 1]
    
    def save_model(self, model_name: str, path: str = "models"):
        """Save a trained model"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        model_path = path / f"{model_name}.pkl"
        joblib.dump(self.models[model_name], model_path)
        
        logger.info(f"Saved {model_name} to {model_path}")
    
    def save_all_models(self, path: str = "models"):
        """Save all trained models"""
        for model_name in self.models.keys():
            self.save_model(model_name, path)
    
    def load_model(self, model_name: str, path: str = "models"):
        """Load a trained model"""
        path = Path(path)
        model_path = path / f"{model_name}.pkl"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        self.models[model_name] = joblib.load(model_path)
        logger.info(f"Loaded {model_name} from {model_path}")
    
    def get_feature_importance(self, model_name: str, feature_names: list) -> pd.DataFrame:
        """Get feature importance from a model"""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")
        
        model = self.models[model_name]
        
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        elif hasattr(model, 'coef_'):
            importances = np.abs(model.coef_[0])
        else:
            raise ValueError(f"Model {model_name} does not support feature importance")
        
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        return importance_df