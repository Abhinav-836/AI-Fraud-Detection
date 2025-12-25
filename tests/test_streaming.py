import pytest
from unittest.mock import Mock, patch, MagicMock
from src.streaming.kafka_producer import FraudKafkaProducer
from src.streaming.kafka_consumer import FraudKafkaConsumer
from src.streaming.stream_processor import StreamProcessor


class TestKafkaProducer:
    """Test cases for Kafka producer"""
    
    @pytest.fixture
    def mock_producer(self):
        """Create mock Kafka producer"""
        with patch('src.streaming.kafka_producer.KafkaProducer') as mock:
            producer = FraudKafkaProducer()
            producer.producer = mock
            yield producer
    
    def test_send_transaction(self, mock_producer):
        """Test sending transaction"""
        transaction = {
            'transaction_id': 'TXN_001',
            'amount': 100.0,
            'merchant_category': 'retail'
        }
        
        # Mock the send method
        mock_future = Mock()
        mock_future.get.return_value = Mock(topic='transactions', partition=0)
        mock_producer.producer.send.return_value = mock_future
        
        result = mock_producer.send_transaction(transaction)
        
        assert result is True
        mock_producer.producer.send.assert_called_once()
    
    def test_send_fraud_alert(self, mock_producer):
        """Test sending fraud alert"""
        alert = {
            'transaction_id': 'TXN_001',
            'fraud_probability': 0.95,
            'risk_level': 'high'
        }
        
        # Mock the send method
        mock_future = Mock()
        mock_future.get.return_value = Mock(topic='fraud_alerts', partition=0)
        mock_producer.producer.send.return_value = mock_future
        
        result = mock_producer.send_fraud_alert(alert)
        
        assert result is True
        mock_producer.producer.send.assert_called_once()
    
    def test_send_batch(self, mock_producer):
        """Test sending batch of transactions"""
        transactions = [
            {'transaction_id': 'TXN_001', 'amount': 100.0},
            {'transaction_id': 'TXN_002', 'amount': 200.0},
            {'transaction_id': 'TXN_003', 'amount': 300.0}
        ]
        
        # Mock the send method
        mock_future = Mock()
        mock_future.get.return_value = Mock(topic='transactions', partition=0)
        mock_producer.producer.send.return_value = mock_future
        
        results = mock_producer.send_batch(transactions)
        
        assert results['success'] == 3
        assert results['failed'] == 0
        assert mock_producer.producer.send.call_count == 3


class TestKafkaConsumer:
    """Test cases for Kafka consumer"""
    
    @pytest.fixture
    def mock_consumer(self):
        """Create mock Kafka consumer"""
        with patch('src.streaming.kafka_consumer.KafkaConsumer') as mock:
            consumer = FraudKafkaConsumer()
            consumer.consumer = mock
            yield consumer
    
    def test_connect(self):
        """Test consumer connection"""
        with patch('src.streaming.kafka_consumer.KafkaConsumer') as mock_kafka:
            consumer = FraudKafkaConsumer()
            consumer.connect()
            
            mock_kafka.assert_called_once()
            assert consumer.consumer is not None
    
    def test_consume_messages(self, mock_consumer):
        """Test consuming messages"""
        # Mock messages
        mock_messages = [
            Mock(value={'transaction_id': 'TXN_001', 'amount': 100.0}),
            Mock(value={'transaction_id': 'TXN_002', 'amount': 200.0})
        ]
        
        mock_consumer.consumer.__iter__ = Mock(return_value=iter(mock_messages))
        
        processed = []
        
        def callback(message):
            processed.append(message)
            if len(processed) >= 2:
                raise KeyboardInterrupt  # Stop after 2 messages
            return message
        
        mock_consumer.consume_messages(callback)
        
        assert len(processed) == 2


class TestStreamProcessor:
    """Test cases for stream processor"""
    
    @pytest.fixture
    def mock_processor(self):
        """Create mock stream processor"""
        with patch('src.streaming.stream_processor.FraudKafkaConsumer'), \
             patch('src.streaming.stream_processor.FraudKafkaProducer'), \
             patch('src.streaming.stream_processor.RealTimeDetector'):
            
            processor = StreamProcessor()
            yield processor
    
    def test_process_transaction_normal(self, mock_processor):
        """Test processing normal transaction"""
        transaction = {
            'transaction_id': 'TXN_001',
            'amount': 100.0,
            'merchant_category': 'retail',
            'device_type': 'mobile',
            'location_country': 'US'
        }
        
        # Mock detector result
        mock_processor.detector.detect = Mock(return_value={
            'transaction_id': 'TXN_001',
            'is_fraud': False,
            'fraud_probability': 0.1,
            'risk_level': 'low',
            'timestamp': '2024-01-01T00:00:00'
        })
        
        result = mock_processor.process_transaction(transaction)
        
        assert result['is_fraud'] is False
        mock_processor.detector.detect.assert_called_once()
    
    def test_process_transaction_fraud(self, mock_processor):
        """Test processing fraudulent transaction"""
        transaction = {
            'transaction_id': 'TXN_002',
            'amount': 5000.0,
            'merchant_category': 'electronics',
            'device_type': 'web',
            'location_country': 'US'
        }
        
        # Mock detector result
        mock_processor.detector.detect = Mock(return_value={
            'transaction_id': 'TXN_002',
            'is_fraud': True,
            'fraud_probability': 0.95,
            'risk_level': 'high',
            'timestamp': '2024-01-01T00:00:00'
        })
        
        # Mock producer
        mock_processor.producer.send_fraud_alert = Mock(return_value=True)
        
        result = mock_processor.process_transaction(transaction)
        
        assert result['is_fraud'] is True
        mock_processor.detector.detect.assert_called_once()
        mock_processor.producer.send_fraud_alert.assert_called_once()
    
    def test_get_stats(self, mock_processor):
        """Test getting processing statistics"""
        mock_processor.detector.get_statistics = Mock(return_value={
            'total_processed': 100,
            'fraud_detected': 5,
            'fraud_rate': 0.05
        })
        
        stats = mock_processor.get_stats()
        
        assert stats['total_processed'] == 100
        assert stats['fraud_detected'] == 5
        assert stats['fraud_rate'] == 0.05