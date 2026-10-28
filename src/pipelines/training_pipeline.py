"""
End-to-end training:

  load data (simulator / Kaggle / CSV)
  -> replay all transactions in time order to build card-history features
  -> chronological train / validation / test split
  -> + analyst-labelled transactions from the database (feedback loop)
  -> train XGBoost, Random Forest, Logistic Regression; pick best PR-AUC
  -> isotonic calibration on validation
  -> choose approve / review / decline thresholds on validation
  -> evaluate once on the untouched, most recent test period
  -> save model, transformer and metadata
"""
import argparse
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from ..features.feature_engineering import MODEL_COLUMNS, build_feature_frame
from ..ingestion.data_loader import DataLoader
from ..models.decision import derive_policy, sensitivity_presets, threshold_curve, tier_metrics
from ..models.evaluate import ModelEvaluator
from ..models.train import FraudModelTrainer
from ..preprocessing.transform import DataTransformer
from ..utils.config import load_model_config
from ..utils.logger import get_logger

logger = get_logger(__name__)

SCORE_BINS = np.linspace(0, 1, 11)


class TrainingPipeline:
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.loader = DataLoader(config_path)
        self.model_config = load_model_config()
        self.transformer = DataTransformer()
        self.trainer = FraudModelTrainer()
        self.evaluator = ModelEvaluator()

    def _load(self, source: str, **kw) -> pd.DataFrame:
        if source == "synthetic":
            return self.loader.load_synthetic_data(kw.get("n_customers", 2000), kw.get("days", 60), kw.get("seed", 42))
        if source == "kaggle":
            return self.loader.load_kaggle(kw.get("kaggle_dir", "data/raw/kaggle"))
        if source == "csv":
            return self.loader.load_csv(kw.get("csv_file", "transactions.csv"))
        raise ValueError(f"Unknown data source: {source}")

    def _feedback_frame(self) -> Optional[pd.DataFrame]:
        try:
            from ..storage.db import PredictionStore
            rows = PredictionStore().labeled_rows()
        except Exception as e:  # no DB yet is normal on first training
            logger.info(f"No feedback data used ({e})")
            return None
        if not rows:
            return None
        df = pd.DataFrame(rows)
        logger.info(f"Adding {len(df)} analyst-labelled transactions ({int(df['is_fraud'].sum())} fraud)")
        return df

    def run(
        self,
        source: str = "synthetic",
        save_artifacts: bool = True,
        model_path: Optional[str] = None,
        include_feedback: bool = True,
        models=("xgboost", "random_forest", "logistic_regression"),
        **source_kwargs,
    ) -> Dict[str, Any]:
        started = datetime.now()
        cfg_train = self.model_config.get("training", {})
        cfg_policy = self.model_config.get("decision", {})

        df = self._load(source, **source_kwargs)
        features = build_feature_frame(df)  # history built over the full timeline
        train_df, val_df, test_df = self.loader.time_split(
            df, cfg_train.get("val_size", 0.15), cfg_train.get("test_size", 0.15))

        X_train_feats = features.loc[train_df.index]
        y_train = train_df["is_fraud"].astype(int).to_numpy()

        feedback = self._feedback_frame() if include_feedback else None
        if feedback is not None:
            X_train_feats = pd.concat([X_train_feats, feedback[MODEL_COLUMNS]], ignore_index=True)
            y_train = np.concatenate([y_train, feedback["is_fraud"].astype(int).to_numpy()])

        X_train = self.transformer.fit_transform(X_train_feats)
        X_val = self.transformer.transform(features.loc[val_df.index])
        X_test = self.transformer.transform(features.loc[test_df.index])
        y_val = val_df["is_fraud"].astype(int).to_numpy()
        y_test = test_df["is_fraud"].astype(int).to_numpy()

        scores = self.trainer.train_all_models(X_train, y_train, X_val, y_val, models=models)

        val_proba = self.trainer.predict_proba(X_val)
        policy = derive_policy(y_val, val_proba,
                               target_recall=cfg_policy.get("target_recall", 0.90),
                               decline_precision=cfg_policy.get("decline_precision", 0.90))
        curve = threshold_curve(y_val, val_proba)

        test_proba = self.trainer.predict_proba(X_test)
        evaluation = self.evaluator.evaluate(y_test, test_proba, model_name=self.trainer.best_model)
        tiers = tier_metrics(y_test, test_proba, policy)
        hist, _ = np.histogram(val_proba, bins=SCORE_BINS)

        test_metrics = {k: evaluation[k] for k in ("auc_roc", "auc_pr", "brier")}
        test_metrics.update(tiers)
        results = {
            "data_source": source,
            "rows": len(df),
            "fraud_rate": float(df["is_fraud"].mean()),
            "train_rows": int(len(X_train_feats)),
            "feedback_rows": 0 if feedback is None else len(feedback),
            "best_model": self.trainer.best_model,
            "candidates": scores,
            "policy": policy.to_dict(),
            "test_metrics": test_metrics,
            "duration_seconds": (datetime.now() - started).total_seconds(),
        }

        if save_artifacts:
            self.transformer.save_transformers(f"{model_path}/transformers" if model_path else None)
            self.trainer.save({
                "data_source": source,
                "rows": results["rows"],
                "feedback_rows": results["feedback_rows"],
                "feature_names": self.transformer.feature_names,
                "policy": policy.to_dict(),
                "curve": curve,
                "presets": sensitivity_presets(curve, policy.decline_threshold),
                "test_metrics": test_metrics,
                "val_score_histogram": (hist / max(hist.sum(), 1)).tolist(),
            }, path=model_path)
            self.evaluator.save_report({**evaluation, "tiers": tiers, "policy": policy.to_dict()})

        logger.info(
            f"Training done in {results['duration_seconds']:.1f}s | {results['best_model']} | "
            f"test PR-AUC {test_metrics['auc_pr']:.3f} | catches {tiers['fraud_caught_rate']:.1%} of fraud | "
            f"review {tiers['review_rate']:.2%} / decline {tiers['decline_rate']:.2%} of traffic"
        )
        return results


def main():
    p = argparse.ArgumentParser(description="Train the fraud detection model")
    p.add_argument("--source", choices=["synthetic", "kaggle", "csv"], default="synthetic")
    p.add_argument("--customers", type=int, default=2000, help="simulated customers (synthetic)")
    p.add_argument("--days", type=int, default=60, help="simulated days (synthetic)")
    p.add_argument("--kaggle-dir", default="data/raw/kaggle")
    p.add_argument("--csv", default="transactions.csv")
    p.add_argument("--no-feedback", action="store_true", help="ignore analyst labels in the database")
    args = p.parse_args()

    r = TrainingPipeline().run(
        source=args.source, include_feedback=not args.no_feedback,
        n_customers=args.customers, days=args.days, kaggle_dir=args.kaggle_dir, csv_file=args.csv,
    )
    m, pol = r["test_metrics"], r["policy"]
    print(f"\nModel:            {r['best_model']}  (trained on {r['train_rows']:,} rows, {r['fraud_rate']:.2%} fraud)")
    print(f"Test PR-AUC:      {m['auc_pr']:.3f}   ROC-AUC: {m['auc_roc']:.3f}   Brier: {m['brier']:.4f}")
    print(f"Thresholds:       review >= {pol['review_threshold']:.2f}   decline >= {pol['decline_threshold']:.2f}")
    print(f"Fraud caught:     {m['fraud_caught_rate']:.1%}  (auto-declined {m['fraud_auto_declined_rate']:.1%})")
    print(f"Traffic:          {m['review_rate']:.2%} to review, {m['decline_rate']:.2%} declined, "
          f"decline precision {m['decline_precision']:.1%}")


if __name__ == "__main__":
    main()
