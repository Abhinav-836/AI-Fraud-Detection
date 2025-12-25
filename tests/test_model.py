import pytest
import numpy as np
import pandas as pd
from src.models.train import FraudModelTrainer
from src.models.evaluate import ModelEvaluator
from src.preprocessing.transform import DataTransformer
from src.features.feature_engineering import FeatureEngineer


class TestFraudModel:
    """Test cases for fraud detection models"""
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample data for testing"""
        np.random.seed(42)
        n_samples = 1000
        
        data = {
            'transaction_id': [f'TXN_{i:06d}' for i in range(n_samples)],
            'amount': np.random.lognormal(3, 1, n_samples),
            'merchant_category': np.random.choice(['retail', 'food', 'travel'], n_samples),
            'device_type': np.random.choice(['mobile', 'web', 'pos'], n_samples),
            'location_country': np.random.choice(['US', 'UK', 'CA'], n_samples),
            'hour_of_day': np.random.randint(0, 24, n_samples),
            'day_of_week': np.random.randint(0, 7, n_samples),
            'is_fraud': np.random.choice([0, 1], n_samples, p=[0.9, 0.1])
        }
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def trained_model(self, sample_data):
        """Train a model for testing"""
        # Add timestamp
        sample_data['timestamp'] = pd.date_range(start='2024-01-01', periods=len(sample_data), freq='5min')
        
        # Feature engineering
        engineer = FeatureEngineer()
        df_features = engineer.create_features(sample_data)
        
        # Transform
        transformer = DataTransformer()
        X_train, y_train = transformer.fit_transform(df_features)
        
        # Split for validation
        split_idx = int(len(X_train) * 0.8)
        X_train_split = X_train[:split_idx]
        y_train_split = y_train[:split_idx]
        X_val = X_train[split_idx:]
        y_val = y_train[split_idx:]
        
        # Train
        trainer = FraudModelTrainer()
        trainer.train_xgboost(X_train_split, y_train_split, X_val, y_val)
        
        return trainer, transformer
    
    def test_model_training(self, sample_data):
        """Test model training"""
        sample_data['timestamp'] = pd.date_range(start='2024-01-01', periods=len(sample_data), freq='5min')
        
        engineer = FeatureEngineer()
        df_features = engineer.create_features(sample_data)
        
        transformer = DataTransformer()
        X, y = transformer.fit_transform(df_features)
        
        # Split data
        split_idx = int(len(X) * 0.8)
        X_train = X[:split_idx]
        y_train = y[:split_idx]
        X_val = X[split_idx:]
        y_val = y[split_idx:]
        
        trainer = FraudModelTrainer()
        model = trainer.train_xgboost(X_train, y_train, X_val, y_val)
        
        assert model is not None
        assert hasattr(model, 'predict')
        assert hasattr(model, 'predict_proba')
    
    def test_model_prediction(self, trained_model, sample_data):
        """Test model prediction"""
        trainer, transformer = trained_model
        
        # Prepare test data
        sample_data['timestamp'] = pd.date_range(start='2024-01-01', periods=len(sample_data), freq='5min')
        engineer = FeatureEngineer()
        df_features = engineer.create_features(sample_data)
        
        X_test = transformer.transform(df_features)
        
        predictions = trainer.get_predictions('xgboost', X_test)
        
        assert len(predictions) == len(sample_data)
        assert all(0 <= p <= 1 for p in predictions)
    
    def test_model_evaluation(self, trained_model, sample_data):
        """Test model evaluation"""
        trainer, transformer = trained_model
        
        # Prepare test data
        sample_data['timestamp'] = pd.date_range(start='2024-01-01', periods=len(sample_data), freq='5min')
        engineer = FeatureEngineer()
        df_features = engineer.create_features(sample_data)
        
        X_test = transformer.transform(df_features)
        y_test = sample_data['is_fraud'].values
        
        predictions = trainer.get_predictions('xgboost', X_test)
        
        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate(y_test, predictions)
        
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'auc_roc' in metrics
        
        # Check metric ranges
        assert 0 <= metrics['accuracy'] <= 1
        assert 0 <= metrics['precision'] <= 1
        assert 0 <= metrics['recall'] <= 1
        assert 0 <= metrics['auc_roc'] <= 1
    
    def test_feature_engineering(self, sample_data):
        """Test feature engineering"""
        sample_data['timestamp'] = pd.date_range(start='2024-01-01', periods=len(sample_data), freq='5min')
        
        engineer = FeatureEngineer()
        df_features = engineer.create_features(sample_data)
        
        # Check new features created
        assert 'hour' in df_features.columns
        assert 'day_of_week' in df_features.columns
        assert 'is_weekend' in df_features.columns
        assert len(df_features.columns) > len(sample_data.columns)
    
    def test_data_transformation(self, sample_data):
        """Test data transformation"""
        transformer = DataTransformer()
        
        X, y = transformer.fit_transform(sample_data)
        
        assert X.shape[0] == len(sample_data)
        assert y.shape[0] == len(sample_data)
        assert len(transformer.feature_names) > 0
    
    def test_model_save_load(self, trained_model, tmp_path):
        """Test model save and load"""
        trainer, _ = trained_model
        
        # Save model
        save_path = str(tmp_path)
        trainer.save_model('xgboost', save_path)
        
        # Load model
        new_trainer = FraudModelTrainer()
        new_trainer.load_model('xgboost', save_path)
        
        assert 'xgboost' in new_trainer.models
    
    def test_threshold_impact(self, trained_model, sample_data):
        """Test different thresholds"""
        trainer, transformer = trained_model
        
        sample_data['timestamp'] = pd.date_range(start='2024-01-01', periods=len(sample_data), freq='5min')
        engineer = FeatureEngineer()
        df_features = engineer.create_features(sample_data)
        
        X_test = transformer.transform(df_features)
        y_test = sample_data['is_fraud'].values
        
        predictions = trainer.get_predictions('xgboost', X_test)
        
        evaluator = ModelEvaluator()
        
        # Test multiple thresholds
        results = evaluator.evaluate_at_thresholds(y_test, predictions, [0.3, 0.5, 0.7])
        
        assert len(results) == 3
        assert '0.3' in results
        assert '0.5' in results
        assert '0.7' in results
    
    def test_batch_prediction_consistency(self, trained_model, sample_data):
        """Test that batch predictions are consistent"""
        trainer, transformer = trained_model
        
        sample_data['timestamp'] = pd.date_range(start='2024-01-01', periods=len(sample_data), freq='5min')
        engineer = FeatureEngineer()
        df_features = engineer.create_features(sample_data)
        
        X_test = transformer.transform(df_features)
        
        # Get predictions twice
        predictions1 = trainer.get_predictions('xgboost', X_test)
        predictions2 = trainer.get_predictions('xgboost', X_test)
        
        # Should be identical
        np.testing.assert_array_almost_equal(predictions1, predictions2)