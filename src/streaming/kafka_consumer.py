from kafka import KafkaConsumer
import json
from typing import Callable
from ..utils.config import load_settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FraudKafkaConsumer:
    """Kafka consumer for fraud detection"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)
        self.consumer = None
        
    def _load_config(self, config_path: str) -> dict:
        """Load settings.yaml (project-root relative) with env overrides such as
        KAFKA_BOOTSTRAP_SERVERS — the Kubernetes manifest sets that variable,
        but the old code only ever read the YAML file, so pods dialled localhost."""
        return load_settings(config_path)
    
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