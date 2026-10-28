"""
Batch scoring from the command line:

    python -m src.pipelines.detection_pipeline --input data/raw/new.csv --output data/processed/scored.csv
"""
import argparse
import json
from typing import Any, Dict, Optional

import pandas as pd

from ..detection.batch_detector import BatchDetector
from ..utils.config import writable_path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DetectionPipeline:
    def __init__(self, model_path: Optional[str] = None):
        self.detector = BatchDetector(model_path)

    def run_batch_detection(self, input_file: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        results = self.detector.detect_from_file(input_file, output_file)
        report = self.detector.generate_report(results)
        path = writable_path("reports") / "batch_detection_report.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        logger.info(f"Report saved to {path}")
        return report

    @staticmethod
    def compare_detections(a: pd.DataFrame, b: pd.DataFrame, column: str = "decision") -> Dict[str, Any]:
        """Compare two scorings of the same transactions (e.g. two models or policies)."""
        x, y = a[column].to_numpy(), b[column].to_numpy()
        return {
            "agreement_rate": float((x == y).mean()),
            "changed": int((x != y).sum()),
            "matrix": pd.crosstab(pd.Series(x, name="first"), pd.Series(y, name="second")).to_dict(),
        }


def main():
    parser = argparse.ArgumentParser(description="Score a CSV of transactions")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = DetectionPipeline().run_batch_detection(args.input, args.output)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
