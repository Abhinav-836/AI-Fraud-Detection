from typing import Dict, Any
from .kafka_consumer import FraudKafkaConsumer
from .kafka_producer import FraudKafkaProducer
from ..detection.real_time_detector import RealTimeDetector
from ..utils.logger import get_logger

logger = get_logger(__name__)


class StreamProcessor:
    """Process streaming transactions and detect fraud in real-time"""
    
    def __init__(self):
        self.consumer = FraudKafkaConsumer()
        self.producer = FraudKafkaProducer()
        self.detector = RealTimeDetector()
        self.running = False
        
    def start(self):
        """Start the stream processor"""
        logger.info("Starting stream processor")
        
        # Connect consumer and producer
        self.consumer.connect()
        self.producer.connect()
        
        self.running = True
        
        # Start consuming messages
        logger.info("Stream processor started. Waiting for messages...")
        self.consumer.consume_messages(self.process_transaction)
    
    def process_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single transaction
        
        Args:
            transaction: Transaction data
            
        Returns:
            Processing result
        """
        try:
            # Detect fraud
            result = self.detector.detect(transaction)
            
            # If fraud detected, send alert
            if result.get('is_fraud'):
                alert = {
                    'transaction_id': transaction.get('transaction_id'),
                    'fraud_probability': result['fraud_probability'],
                    'risk_level': result['risk_level'],
                    'transaction_details': transaction,
                    'detection_timestamp': result['timestamp']
                }
                
                # Send fraud alert to Kafka
                self.producer.send_fraud_alert(alert)
                
                logger.warning(
                    f"FRAUD ALERT: Transaction {transaction.get('transaction_id')} "
                    f"flagged with probability {result['fraud_probability']:.4f}"
                )
            else:
                logger.debug(
                    f"Transaction {transaction.get('transaction_id')} verified as legitimate"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            return {'error': str(e)}
    
    def stop(self):
        """Stop the stream processor"""
        logger.info("Stopping stream processor")
        
        self.running = False
        
        # Close connections
        self.consumer.close()
        self.producer.close()
        
        # Log statistics
        stats = self.detector.get_statistics()
        logger.info(f"Final statistics: {stats}")
        
        logger.info("Stream processor stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return self.detector.get_statistics()


def main():
    """Main function to run stream processor"""
    processor = StreamProcessor()
    
    try:
        processor.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        processor.stop()
    except Exception as e:
        logger.error(f"Stream processor error: {str(e)}")
        processor.stop()
        raise


if __name__ == "__main__":
    main()