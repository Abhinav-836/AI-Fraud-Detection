"""
Feed the Kafka `transactions` topic with realistic simulated card traffic,
so the full streaming path (producer -> Kafka -> stream processor -> DB ->
dashboard) can be exercised without a real payment feed.

    python -m src.streaming.simulate_to_kafka --rate 2

The ground truth (is_fraud / scenario) is NOT sent: a real feed doesn't have
it either. Use the dashboard's built-in simulation to see the scorecard.
"""
import argparse
import time

from ..ingestion.simulator import LiveSimulator
from ..utils.logger import get_logger
from .kafka_producer import FraudKafkaProducer

logger = get_logger(__name__)


def connect_with_retry(producer: FraudKafkaProducer, attempts: int = 30, wait: float = 2.0):
    """Kafka can take a while to accept connections after its container starts."""
    for i in range(attempts):
        try:
            producer.connect()
            return
        except Exception as e:  # NoBrokersAvailable and friends
            logger.info(f"Kafka not ready ({e}); retry {i + 1}/{attempts}")
            time.sleep(wait)
    raise RuntimeError("Could not connect to Kafka")


def main():
    parser = argparse.ArgumentParser(description="Send simulated transactions to Kafka")
    parser.add_argument("--rate", type=float, default=2.0, help="transactions per second")
    parser.add_argument("--count", type=int, default=0, help="stop after N transactions (0 = forever)")
    parser.add_argument("--fraud-probability", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--warmup-days", type=int, default=0,
                        help="first send N days of past normal traffic so cards have history "
                             "(these are scored and stored too)")
    args = parser.parse_args()

    sim = LiveSimulator(fraud_probability=args.fraud_probability, seed=args.seed)
    producer = FraudKafkaProducer()
    connect_with_retry(producer)

    # Optionally prime card histories through the same stream so velocity /
    # "new country" features have something to compare against.
    if args.warmup_days:
        warm = sim.warmup_history(days=args.warmup_days)
        for i, tx in enumerate(warm):
            tx, _ = LiveSimulator.split_truth(dict(tx))
            tx["timestamp"] = tx["timestamp"].isoformat()
            tx.setdefault("transaction_id", f"WARM_{i}")
            producer.send_transaction(tx)
        logger.info(f"Sent {len(warm)} warm-up transactions")
    logger.info(f"Streaming at {args.rate}/s")

    sent = 0
    try:
        while not args.count or sent < args.count:
            tx, _ = LiveSimulator.split_truth(sim.next_transaction())
            producer.send_transaction(tx)
            sent += 1
            time.sleep(1.0 / max(args.rate, 0.01))
    except KeyboardInterrupt:
        pass
    finally:
        producer.close()
        logger.info(f"Sent {sent} live transactions")


if __name__ == "__main__":
    main()
