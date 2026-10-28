from kafka import KafkaProducer
import json
from typing import Dict, Any
from datetime import datetime
from ..utils.config import load_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FraudKafkaProducer:
    """Kafka producer for sending transactions and fraud alerts"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)
        self.producer = None
        
    def _load_config(self, config_path: str) -> dict:
        """Load settings.yaml (project-root relative) with env overrides such as
        KAFKA_BOOTSTRAP_SERVERS — the Kubernetes manifest sets that variable,
        but the old code only ever read the YAML file, so pods dialled localhost."""
        return load_settings(config_path)
    
    def connect(self):
        """Connect to Kafka"""
        kafka_config = self.config['kafka']
        
        logger.info(f"Connecting to Kafka at {kafka_config['bootstrap_servers']}")
        
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_config['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=1
        )
        
        logger.info("Connected to Kafka producer")
    
    def send_transaction(self, transaction: Dict[str, Any]) -> bool:
        """
        Send a transaction to Kafka
        
        Args:
            transaction: Transaction data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.producer:
            raise RuntimeError("Producer not connected. Call connect() first.")
        
        try:
            topic = self.config['kafka']['topics']['transactions']
            
            # Copy before adding metadata: mutating the caller's dict leaked
            # 'produced_at' into objects the caller reused (e.g. send_batch input)
            transaction = {**transaction, 'produced_at': datetime.now().astimezone().isoformat()}
            
            # Send to Kafka
            future = self.producer.send(
                topic,
                key=transaction.get('transaction_id'),
                value=transaction
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            
            logger.debug(
                f"Sent transaction {transaction.get('transaction_id')} "
                f"to {record_metadata.topic} partition {record_metadata.partition}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending transaction: {str(e)}")
            return False
    
    def send_fraud_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Send a fraud alert to Kafka
        
        Args:
            alert: Fraud alert data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.producer:
            raise RuntimeError("Producer not connected. Call connect() first.")
        
        try:
            topic = self.config['kafka']['topics']['fraud_alerts']
            
            alert = {**alert, 'alert_generated_at': datetime.now().astimezone().isoformat()}
            
            # Send to Kafka
            future = self.producer.send(
                topic,
                key=alert.get('transaction_id'),
                value=alert
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Sent fraud alert for {alert.get('transaction_id')} "
                f"to {record_metadata.topic}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending fraud alert: {str(e)}")
            return False
    
    def send_batch(self, transactions: list) -> Dict[str, int]:
        """
        Send multiple transactions in batch
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Dictionary with success/failure counts
        """
        results = {'success': 0, 'failed': 0}
        
        for transaction in transactions:
            if self.send_transaction(transaction):
                results['success'] += 1
            else:
                results['failed'] += 1
        
        # Flush to ensure all messages are sent
        self.producer.flush()
        
        logger.info(
            f"Batch send complete - Success: {results['success']}, "
            f"Failed: {results['failed']}"
        )
        
        return results
    
    def close(self):
        """Close producer connection"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Producer closed")