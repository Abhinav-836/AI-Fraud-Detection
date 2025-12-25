from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from ..detection.batch_detector import BatchDetector
from ..detection.real_time_detector import RealTimeDetector
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DetectionPipeline:
    """End-to-end detection pipeline for fraud detection"""
    
    def __init__(self, model_path: str = "models"):
        self.model_path = model_path
        self.batch_detector = None
        self.realtime_detector = None
        
    def initialize_batch_detector(self, threshold: float = 0.5):
        """Initialize batch detector"""
        logger.info("Initializing batch detector")
        self.batch_detector = BatchDetector(
            model_path=self.model_path,
            threshold=threshold
        )
        logger.info("Batch detector initialized")
    
    def initialize_realtime_detector(self, threshold: float = 0.5):
        """Initialize real-time detector"""
        logger.info("Initializing real-time detector")
        self.realtime_detector = RealTimeDetector(
            model_path=self.model_path,
            threshold=threshold
        )
        logger.info("Real-time detector initialized")
    
    def run_batch_detection(
        self,
        input_file: str,
        output_file: str = None,
        generate_report: bool = True
    ) -> Dict[str, Any]:
        """
        Run batch fraud detection on a file
        
        Args:
            input_file: Path to input CSV file
            output_file: Path to output file (optional)
            generate_report: Whether to generate detection report
            
        Returns:
            Detection results and report
        """
        logger.info("=" * 80)
        logger.info("STARTING BATCH DETECTION PIPELINE")
        logger.info("=" * 80)
        
        start_time = datetime.now()
        
        # Initialize batch detector if not already done
        if not self.batch_detector:
            self.initialize_batch_detector()
        
        # Run detection
        logger.info(f"Processing file: {input_file}")
        results_df = self.batch_detector.detect_from_file(
            input_file=input_file,
            output_file=output_file
        )
        
        # Generate report
        report = None
        if generate_report:
            report = self.batch_detector.generate_report(results_df)
            self._save_report(report, "batch_detection_report.json")
        
        # Get high-risk transactions
        high_risk = self.batch_detector.flag_high_risk_transactions(results_df)
        
        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()
        
        # Summary
        summary = {
            'total_transactions': len(results_df),
            'fraud_detected': int(results_df['is_fraud'].sum()),
            'fraud_rate': float(results_df['is_fraud'].mean()),
            'high_risk_count': len(high_risk),
            'processing_duration_seconds': duration,
            'transactions_per_second': len(results_df) / duration if duration > 0 else 0,
            'report': report,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info("=" * 80)
        logger.info("BATCH DETECTION COMPLETED")
        logger.info(f"Total Transactions: {summary['total_transactions']}")
        logger.info(f"Fraud Detected: {summary['fraud_detected']}")
        logger.info(f"Fraud Rate: {summary['fraud_rate']:.2%}")
        logger.info(f"High Risk: {summary['high_risk_count']}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Throughput: {summary['transactions_per_second']:.2f} txn/s")
        logger.info("=" * 80)
        
        return summary
    
    def run_realtime_detection(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Run real-time detection on a list of transactions
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of detection results
        """
        logger.info("=" * 80)
        logger.info("STARTING REAL-TIME DETECTION")
        logger.info("=" * 80)
        
        # Initialize real-time detector if not already done
        if not self.realtime_detector:
            self.initialize_realtime_detector()
        
        # Process transactions
        results = self.realtime_detector.detect_batch(transactions)
        
        # Log statistics
        stats = self.realtime_detector.get_statistics()
        
        logger.info("=" * 80)
        logger.info("REAL-TIME DETECTION COMPLETED")
        logger.info(f"Processed: {stats['total_processed']}")
        logger.info(f"Fraud Detected: {stats['fraud_detected']}")
        logger.info(f"Avg Processing Time: {stats.get('avg_processing_time_ms', 0):.2f}ms")
        logger.info("=" * 80)
        
        return results
    
    def run_continuous_monitoring(
        self,
        input_file: str,
        check_interval: int = 60,
        alert_threshold: float = 0.8
    ):
        """
        Run continuous monitoring on incoming transactions
        
        Args:
            input_file: File to monitor for new transactions
            check_interval: Check interval in seconds
            alert_threshold: Threshold for fraud alerts
        """
        logger.info("Starting continuous monitoring")
        logger.info(f"Monitoring file: {input_file}")
        logger.info(f"Check interval: {check_interval}s")
        logger.info(f"Alert threshold: {alert_threshold}")
        
        # Initialize detector
        if not self.realtime_detector:
            self.initialize_realtime_detector(threshold=alert_threshold)
        
        # This would be implemented with a file watcher or streaming system
        # For now, we'll just document the pattern
        logger.info("Continuous monitoring mode - press Ctrl+C to stop")
        
        try:
            import time
            while True:
                # Check for new transactions
                # Process them
                # Send alerts if needed
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("Stopping continuous monitoring")
    
    def _save_report(self, report: Dict[str, Any], filename: str):
        """Save detection report"""
        import json
        
        report_path = Path("reports")
        report_path.mkdir(exist_ok=True)
        
        filepath = report_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved to {filepath}")
    
    def compare_detections(
        self,
        predictions1: pd.DataFrame,
        predictions2: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Compare two sets of predictions (e.g., different models or thresholds)
        
        Args:
            predictions1: First set of predictions
            predictions2: Second set of predictions
            
        Returns:
            Comparison results
        """
        comparison = {
            'agreement_rate': float((predictions1['is_fraud'] == predictions2['is_fraud']).mean()),
            'both_fraud': int((predictions1['is_fraud'] == 1) & (predictions2['is_fraud'] == 1)).sum(),
            'only_first_fraud': int((predictions1['is_fraud'] == 1) & (predictions2['is_fraud'] == 0)).sum(),
            'only_second_fraud': int((predictions1['is_fraud'] == 0) & (predictions2['is_fraud'] == 1)).sum(),
            'both_legitimate': int((predictions1['is_fraud'] == 0) & (predictions2['is_fraud'] == 0)).sum()
        }
        
        return comparison


def main():
    """Main function for detection pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fraud Detection Pipeline")
    parser.add_argument('--mode', choices=['batch', 'realtime'], required=True, help='Detection mode')
    parser.add_argument('--input', type=str, help='Input file path')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--threshold', type=float, default=0.5, help='Detection threshold')
    
    args = parser.parse_args()
    
    pipeline = DetectionPipeline()
    
    if args.mode == 'batch':
        if not args.input:
            print("Error: --input is required for batch mode")
            return
        
        results = pipeline.run_batch_detection(
            input_file=args.input,
            output_file=args.output
        )
        
        print("\nBatch Detection Results:")
        print(f"Total Transactions: {results['total_transactions']}")
        print(f"Fraud Detected: {results['fraud_detected']}")
        print(f"Fraud Rate: {results['fraud_rate']:.2%}")
        
    elif args.mode == 'realtime':
        # For real-time mode, you would set up streaming
        print("Real-time mode - set up streaming connection")


if __name__ == "__main__":
    main()