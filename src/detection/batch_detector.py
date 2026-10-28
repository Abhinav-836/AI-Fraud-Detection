from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from ..features.feature_engineering import build_feature_frame
from ..models.decision import DecisionPolicy
from ..models.train import FraudModelTrainer
from ..preprocessing.transform import DataTransformer
from ..utils.config import bundled_model_dir, model_dir, resolve_path, writable_path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BatchDetector:
    """Score a whole file of transactions (history features built within the file)."""

    def __init__(self, model_path: Optional[str] = None):
        # Same search order as the API: retrained model in the data folder
        # first, then the model bundled with the app / image.
        candidates = [resolve_path(model_path)] if model_path else [model_dir(), bundled_model_dir()]
        directory = next((d for d in candidates if (d / "model.pkl").exists()), candidates[0])
        self.trainer = FraudModelTrainer()
        meta = self.trainer.load(directory)
        self.transformer = DataTransformer().load_transformers(directory / "transformers")
        pol = meta.get("policy") or {}
        self.policy = DecisionPolicy(pol.get("review_threshold", 0.3), pol.get("decline_threshold", 0.8))
        self.model_type = meta.get("model_type")

    def detect_from_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        started = datetime.now()
        result = df.copy()
        if "timestamp" not in result.columns:
            result["timestamp"] = datetime.now()
        features = build_feature_frame(result)
        proba = self.trainer.predict_proba(self.transformer.transform(features))

        result["fraud_probability"] = proba
        result["decision"] = [self.policy.decide(p) for p in proba]
        # Separate column: a ground-truth `is_fraud` in the input is kept intact
        result["predicted_fraud"] = (result["decision"] != "approve").astype(int)
        result["detection_timestamp"] = datetime.now().astimezone().isoformat()
        logger.info(f"Scored {len(result)} transactions in {(datetime.now() - started).total_seconds():.1f}s: "
                    f"{result['decision'].value_counts().to_dict()}")
        return result

    def detect_from_file(self, input_file: str, output_file: Optional[str] = None) -> pd.DataFrame:
        path = resolve_path(input_file)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        results = self.detect_from_dataframe(pd.read_csv(path))
        if output_file:
            out = writable_path(output_file)
            out.parent.mkdir(parents=True, exist_ok=True)
            results.to_csv(out, index=False)
            logger.info(f"Results saved to {out}")
        return results

    def generate_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        flagged = df["predicted_fraud"] == 1
        report = {
            "total_transactions": len(df),
            "approved": int((df["decision"] == "approve").sum()),
            "in_review": int((df["decision"] == "review").sum()),
            "declined": int((df["decision"] == "decline").sum()),
            "flagged_amount": float(df.loc[flagged, "amount"].sum()) if "amount" in df.columns else None,
            "model_type": self.model_type,
            "policy": self.policy.to_dict(),
            "timestamp": datetime.now().astimezone().isoformat(),
        }
        if "is_fraud" in df.columns:
            truth = df["is_fraud"].astype(int) == 1
            report["fraud_caught_rate"] = float((truth & flagged).sum() / max(int(truth.sum()), 1))
            report["flag_precision"] = float((truth & flagged).sum() / max(int(flagged.sum()), 1))
        return report


if __name__ == "__main__":
    from ..ingestion.simulator import generate_dataset

    sample = generate_dataset(n_customers=300, days=20, seed=7)
    detector = BatchDetector()
    print(detector.generate_report(detector.detect_from_dataframe(sample)))
