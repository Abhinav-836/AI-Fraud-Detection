from typing import Optional

from ..api.services.fraud_service import FraudDetectionService
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RealTimeDetector:
    """
    Real-time detection for the Kafka stream processor. A thin wrapper over
    FraudDetectionService, so streaming, REST and WebSocket share the same
    card history, model, decision policy and database.
    """

    def __init__(self, model_path: Optional[str] = None, require_model: bool = True,
                 service: Optional[FraudDetectionService] = None):
        self.service = service or FraudDetectionService()
        loaded = self.service.initialize(model_path)
        if require_model and not loaded:
            raise FileNotFoundError(
                "No trained model found. Run `python -m src.pipelines.training_pipeline` first "
                "or pass require_model=False to use rule-based scoring."
            )
        self.stats = {'total_processed': 0, 'flagged': 0, 'declined': 0, 'latency_sum_ms': 0.0}

    def detect(self, transaction: dict) -> dict:
        """Score one transaction. Errors are returned, not raised, so a bad message can't kill the consumer."""
        try:
            result = self.service.predict(transaction, source="stream")
        except Exception as e:
            logger.error(f"Error scoring {transaction.get('transaction_id')}: {e}")
            return {'transaction_id': transaction.get('transaction_id'), 'error': str(e)}

        self.stats['total_processed'] += 1
        self.stats['flagged'] += int(result['is_fraud'])
        self.stats['declined'] += int(result['decision'] == 'decline')
        self.stats['latency_sum_ms'] += result['processing_time_ms']
        if result['is_fraud']:
            logger.warning(f"{result['decision'].upper()} {result['transaction_id']} "
                           f"p={result['fraud_probability']:.3f}: {'; '.join(result['factors'][:2])}")
        return result

    def detect_batch(self, transactions: list) -> list:
        return [self.detect(tx) for tx in transactions]

    def get_statistics(self) -> dict:
        n = self.stats['total_processed']
        return {
            'total_processed': n,
            'fraud_detected': self.stats['flagged'],
            'declined': self.stats['declined'],
            'fraud_rate': self.stats['flagged'] / n if n else 0.0,
            'avg_processing_time_ms': self.stats['latency_sum_ms'] / n if n else 0.0,
            'model_type': self.service.model_type,
        }

    def reset_statistics(self):
        self.stats = {'total_processed': 0, 'flagged': 0, 'declined': 0, 'latency_sum_ms': 0.0}
