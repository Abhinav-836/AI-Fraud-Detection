import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from ..models.train import FraudModelTrainer
from ..preprocessing.transform import DataTransformer
from ..features.feature_engineering import FeatureEngineer
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BatchDetector:
    """Batch fraud detection for large datasets"""
    
    def __init__(self, model_path: str = "models", threshold: float = 0.5):
        self.threshold = threshold
        self.model = None
        self.transformer = None
        self.engineer = None
        self.load_components(model_path)
    
    def load_components(self, model_path: str):
        """Load model and preprocessing components"""
        logger.info("Loading batch detection components")
        
        try:
            # Load model
            self.model = FraudModelTrainer()
            self.model.load_model('xgboost', model_path)
            
            # Load transformer
            self.transformer = DataTransformer()
            self.transformer.load_transformers(f"{model_path}/transformers")
            
            # Initialize feature engineer
            self.engineer = FeatureEngineer()
            
            logger.info("Components loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading components: {str(e)}")
            raise
    
    def detect_from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect fraud in a DataFrame of transactions
        
        Args:
            df: DataFrame with transaction data
            
        Returns:
            DataFrame with fraud predictions added
        """
        logger.info(f"Processing batch of {len(df)} transactions")
        
        start_time = datetime.now()
        
        try:
            # Store original data
            original_df = df.copy()
            
            # Engineer features
            df_features = self.engineer.create_features(df)
            
            # Transform
            X = self.transformer.transform(df_features)
            
            # Predict
            fraud_probs = self.model.get_predictions('xgboost', X)
            
            # Add predictions to original dataframe
            original_df['fraud_probability'] = fraud_probs
            original_df['is_fraud'] = (fraud_probs > self.threshold).astype(int)
            
            # Add risk levels
            original_df['risk_level'] = pd.cut(
                fraud_probs,
                bins=[0, 0.3, 0.7, 1.0],
                labels=['low', 'medium', 'high']
            )
            
            # Add processing timestamp
            original_df['detection_timestamp'] = datetime.now()
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            fraud_count = original_df['is_fraud'].sum()
            fraud_rate = fraud_count / len(original_df)
            
            logger.info(
                f"Batch processing complete - "
                f"Total: {len(original_df)}, "
                f"Fraud: {fraud_count} ({fraud_rate:.2%}), "
                f"Time: {processing_time:.2f}s"
            )
            
            return original_df
            
        except Exception as e:
            logger.error(f"Error in batch detection: {str(e)}")
            raise
    
    def detect_from_file(
        self, 
        input_file: str, 
        output_file: str = None,
        chunk_size: int = 10000
    ) -> pd.DataFrame:
        """
        Detect fraud from a CSV file
        
        Args:
            input_file: Path to input CSV file
            output_file: Path to output CSV file (optional)
            chunk_size: Process data in chunks
            
        Returns:
            DataFrame with predictions
        """
        logger.info(f"Processing file: {input_file}")
        
        # Read file in chunks if large
        file_path = Path(input_file)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Get file size to determine if chunking is needed
        file_size = file_path.stat().st_size
        
        if file_size > 100_000_000:  # 100MB
            logger.info("Large file detected. Processing in chunks...")
            return self._process_large_file(input_file, output_file, chunk_size)
        else:
            # Read entire file
            df = pd.read_csv(input_file)
            results = self.detect_from_dataframe(df)
            
            # Save results if output file specified
            if output_file:
                results.to_csv(output_file, index=False)
                logger.info(f"Results saved to {output_file}")
            
            return results
    
    def _process_large_file(
        self, 
        input_file: str, 
        output_file: str,
        chunk_size: int
    ) -> pd.DataFrame:
        """Process large files in chunks"""
        
        chunks_processed = 0
        all_results = []
        
        for chunk in pd.read_csv(input_file, chunksize=chunk_size):
            logger.info(f"Processing chunk {chunks_processed + 1}")
            
            chunk_results = self.detect_from_dataframe(chunk)
            all_results.append(chunk_results)
            
            chunks_processed += 1
        
        # Combine all chunks
        results = pd.concat(all_results, ignore_index=True)
        
        # Save results
        if output_file:
            results.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
        
        logger.info(f"Processed {chunks_processed} chunks")
        
        return results
    
    def generate_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate a fraud detection report
        
        Args:
            df: DataFrame with predictions
            
        Returns:
            Dictionary with report statistics
        """
        report = {
            'total_transactions': len(df),
            'fraud_detected': int(df['is_fraud'].sum()),
            'fraud_rate': float(df['is_fraud'].mean()),
            'risk_distribution': df['risk_level'].value_counts().to_dict(),
            'avg_fraud_probability': float(df[df['is_fraud'] == 1]['fraud_probability'].mean()) if df['is_fraud'].sum() > 0 else 0,
            'total_amount': float(df['amount'].sum()) if 'amount' in df.columns else None,
            'fraud_amount': float(df[df['is_fraud'] == 1]['amount'].sum()) if 'amount' in df.columns and df['is_fraud'].sum() > 0 else 0,
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def flag_high_risk_transactions(
        self, 
        df: pd.DataFrame,
        threshold: float = 0.8
    ) -> pd.DataFrame:
        """
        Flag only high-risk transactions
        
        Args:
            df: DataFrame with predictions
            threshold: Probability threshold for high risk
            
        Returns:
            DataFrame with only high-risk transactions
        """
        high_risk = df[df['fraud_probability'] >= threshold].copy()
        
        logger.info(f"Found {len(high_risk)} high-risk transactions")
        
        return high_risk.sort_values('fraud_probability', ascending=False)


if __name__ == "__main__":
    # Example usage
    detector = BatchDetector()
    
    # Create sample data
    from ..ingestion.data_loader import DataLoader
    loader = DataLoader()
    df = loader.load_synthetic_data(n_samples=1000)
    
    # Detect fraud
    results = detector.detect_from_dataframe(df)
    
    # Generate report
    report = detector.generate_report(results)
    print("\nBatch Detection Report:")
    print(f"Total Transactions: {report['total_transactions']}")
    print(f"Fraud Detected: {report['fraud_detected']}")
    print(f"Fraud Rate: {report['fraud_rate']:.2%}")
    
    # Get high-risk transactions
    high_risk = detector.flag_high_risk_transactions(results)
    print(f"\nHigh-Risk Transactions: {len(high_risk)}")