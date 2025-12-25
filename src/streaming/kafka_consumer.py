from kafka import KafkaConsumer
import json
import yaml
from typing import Callable
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FraudKafkaConsumer:
    """Kafka consumer for fraud detection"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)
        self.consumer = None
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def connect(self):
        """Connect to Kafka"""
        kafka_config = self.config['kafka']
        
        logger.info(f"Connecting to Kafka at {kafka_config['bootstrap_servers']}")
        
        self.consumer = KafkaConsumer(
            kafka_config['topics']['transactions'],
            bootstrap_servers=kafka_config['bootstrap_servers'],
            group_id=kafka_config['consumer_group'],
            auto_offset_reset=kafka_config['auto_offset_reset'],
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        logger.info("Connected to Kafka")
    
    def consume_messages(self, callback: Callable):
        """
        Consume messages and process with callback
        
        Args:
            callback: Function to process each message
        """
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        logger.info("Starting message consumption")
        
        try:
            for message in self.consumer:
                logger.debug(f"Received message: {message.value}")
                
                try:
                    # Process message with callback
                    result = callback(message.value)
                    
                    if result:
                        logger.info(f"Processed transaction: {result}")
                        
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    
        except KeyboardInterrupt:
            logger.info("Stopping consumer")
        finally:
            self.close()
    
    def close(self):
        """Close consumer connection"""
        if self.consumer:
            self.consumer.close()
            logger.info("Consumer closed")