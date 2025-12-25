from pathlib import Path
from datetime import datetime
from ..ingestion.data_loader import DataLoader
from ..preprocessing.clean import DataCleaner
from ..preprocessing.transform import DataTransformer
from ..features.feature_engineering import FeatureEngineer
from ..models.train import FraudModelTrainer
from ..models.evaluate import ModelEvaluator
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TrainingPipeline:
    """End-to-end training pipeline for fraud detection"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = config_path
        self.loader = DataLoader(config_path)
        self.cleaner = DataCleaner()
        self.transformer = DataTransformer()
        self.engineer = FeatureEngineer()
        self.trainer = FraudModelTrainer()
        self.evaluator = ModelEvaluator()
        
    def run(
        self, 
        data_source: str = "synthetic",
        n_samples: int = 10000,
        save_artifacts: bool = True
    ) -> dict:
        """
        Run the complete training pipeline
        
        Args:
            data_source: Source of data ('synthetic', 'csv', 'database')
            n_samples: Number of samples (for synthetic data)
            save_artifacts: Whether to save trained models and transformers
            
        Returns:
            Dictionary with pipeline results
        """
        logger.info("=" * 80)
        logger.info("STARTING TRAINING PIPELINE")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        results = {}
        
        # Step 1: Load Data
        logger.info("Step 1: Loading data")
        if data_source == "synthetic":
            df = self.loader.load_synthetic_data(n_samples=n_samples)
        elif data_source == "csv":
            df = self.loader.load_csv("transactions.csv")
        else:
            raise ValueError(f"Unknown data source: {data_source}")
        
        results['data_loaded'] = len(df)
        logger.info(f"Loaded {len(df)} records")
        
        # Step 2: Clean Data
        logger.info("Step 2: Cleaning data")
        df_clean = self.cleaner.clean(df)
        results['data_cleaned'] = len(df_clean)
        results['records_removed'] = len(df) - len(df_clean)
        
        # Step 3: Feature Engineering
        logger.info("Step 3: Engineering features")
        df_features = self.engineer.create_features(df_clean)
        results['features_created'] = len(df_features.columns)
        
        # Step 4: Split Data
        logger.info("Step 4: Splitting data")
        train_df, val_df, test_df = self.loader.split_data(df_features)
        results['train_size'] = len(train_df)
        results['val_size'] = len(val_df)
        results['test_size'] = len(test_df)
        
        # Step 5: Transform Data
        logger.info("Step 5: Transforming data")
        X_train, y_train = self.transformer.fit_transform(train_df)
        X_val, y_val = self.transformer.transform(val_df), val_df['is_fraud'].values
        X_test, y_test = self.transformer.transform(test_df), test_df['is_fraud'].values
        
        # Step 6: Train Models
        logger.info("Step 6: Training models")
        training_results = self.trainer.train_all_models(X_train, y_train, X_val, y_val)
        results['model_scores'] = training_results
        results['best_model'] = self.trainer.best_model
        results['best_score'] = float(self.trainer.best_score)
        
        # Step 7: Evaluate on Test Set
        logger.info("Step 7: Evaluating on test set")
        test_predictions = self.trainer.get_predictions(self.trainer.best_model, X_test)
        
        evaluation = self.evaluator.evaluate(
            y_test, 
            test_predictions,
            model_name=self.trainer.best_model
        )
        results['test_evaluation'] = evaluation
        
        # Step 8: Save Artifacts
        if save_artifacts:
            logger.info("Step 8: Saving artifacts")
            
            # Save models
            self.trainer.save_all_models()
            
            # Save transformers
            self.transformer.save_transformers()
            
            # Save data splits
            self.loader.save_processed_data(train_df, "train.csv")
            self.loader.save_processed_data(val_df, "val.csv")
            self.loader.save_processed_data(test_df, "test.csv")
            
            # Save evaluation report
            self.evaluator.save_report(evaluation, "evaluation_report.json")
            
            logger.info("Artifacts saved successfully")
        
        # Pipeline Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        results['pipeline_duration_seconds'] = duration
        results['timestamp'] = end_time.isoformat()
        
        logger.info("=" * 80)
        logger.info("TRAINING PIPELINE COMPLETED")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Best Model: {results['best_model']}")
        logger.info(f"Best Score: {results['best_score']:.4f}")
        logger.info(f"Test Accuracy: {evaluation['accuracy']:.4f}")
        logger.info(f"Test AUC-ROC: {evaluation['auc_roc']:.4f}")
        logger.info("=" * 80)
        
        return results
    
    def run_incremental_training(self, new_data_path: str) -> dict:
        """
        Run incremental training with new data
        
        Args:
            new_data_path: Path to new data
            
        Returns:
            Training results
        """
        logger.info("Starting incremental training")
        
        # Load new data
        new_df = self.loader.load_csv(new_data_path)
        
        # Clean and engineer features
        new_df = self.cleaner.clean(new_df)
        new_df = self.engineer.create_features(new_df)
        
        # Transform
        X_new, y_new = self.transformer.fit_transform(new_df)
        
        # Load existing model
        self.trainer.load_model(self.trainer.best_model)
        
        # Retrain (warm start if supported)
        # For now, we'll just evaluate on new data
        new_predictions = self.trainer.get_predictions(self.trainer.best_model, X_new)
        new_evaluation = self.evaluator.evaluate(y_new, new_predictions)
        
        logger.info(f"Incremental evaluation - Accuracy: {new_evaluation['accuracy']:.4f}")
        
        return new_evaluation


if __name__ == "__main__":
    # Run training pipeline
    pipeline = TrainingPipeline()
    results = pipeline.run(data_source="synthetic", n_samples=20000)
    
    print("\nPipeline Results:")
    print(f"Best Model: {results['best_model']}")
    print(f"Test Accuracy: {results['test_evaluation']['accuracy']:.4f}")
    print(f"Test AUC-ROC: {results['test_evaluation']['auc_roc']:.4f}")