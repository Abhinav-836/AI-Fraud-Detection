from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from ...utils.logger import get_logger
from ..security import require_api_key
from ..services.fraud_service import fraud_service

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(require_api_key)])


class Transaction(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "transaction_id": "TXN123456",
            "card_id": "CARD_000123",
            "amount": 1500.50,
            "merchant_category": "electronics",
            "device_type": "mobile",
            "location_country": "US",
            "timestamp": "2026-10-28T14:05:00+05:30",
        }
    })

    transaction_id: str = Field(..., min_length=1, max_length=128)
    card_id: Optional[str] = Field(None, max_length=64, description="Card / account identifier; enables history features")
    amount: float = Field(..., gt=0, le=10_000_000)
    merchant_category: str = Field("unknown", max_length=64)
    device_type: str = Field("unknown", max_length=32)
    location_country: str = Field("US", min_length=2, max_length=3)
    hour_of_day: Optional[int] = Field(None, ge=0, le=23)
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="0 = Monday ... 6 = Sunday")
    timestamp: Optional[datetime] = Field(None, description="Defaults to now")


class TransactionBatch(BaseModel):
    transactions: List[Transaction] = Field(..., min_length=1, max_length=1000)


class Driver(BaseModel):
    feature: str
    impact: float
    key: str
    params: Dict[str, Any]
    text: str


class FraudPrediction(BaseModel):
    prediction_id: Optional[int]
    transaction_id: str
    card_id: Optional[str]
    decision: str = Field(..., description="approve | review | decline")
    is_fraud: bool = Field(..., description="True when the decision is review or decline")
    fraud_probability: float = Field(..., description="Calibrated probability that the transaction is fraud")
    risk_level: str
    drivers: List[Driver]
    factors: List[str]
    model_type: str
    processing_time_ms: float
    timestamp: datetime


class BatchPredictionResponse(BaseModel):
    total_transactions: int
    approved: int
    in_review: int
    declined: int
    predictions: List[FraudPrediction]


class Feedback(BaseModel):
    is_fraud: bool = Field(..., description="Analyst verdict: true = confirmed fraud, false = legitimate")


class PolicyUpdate(BaseModel):
    review_threshold: float = Field(..., gt=0, lt=1)
    decline_threshold: float = Field(..., gt=0, lt=1)


def _payload(tx: Transaction) -> dict:
    data = tx.model_dump()
    if data.get("timestamp") is not None:
        data["timestamp"] = data["timestamp"].isoformat()
    return data


@router.post("/predict", response_model=FraudPrediction)
def predict_fraud(transaction: Transaction):
    """Score one transaction: approve, review or decline, with the reasons."""
    try:
        return fraud_service.predict(_payload(transaction), source="api")
    except Exception as e:
        logger.exception(f"Prediction error for {transaction.transaction_id}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")


@router.post("/predict/batch", response_model=BatchPredictionResponse)
def predict_fraud_batch(batch: TransactionBatch):
    """Score many transactions (in time order, so later ones see earlier ones in card history)."""
    try:
        preds = fraud_service.predict_batch([_payload(t) for t in batch.transactions], source="batch")
    except Exception as e:
        logger.exception("Batch prediction error")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {e}")
    count = lambda d: sum(p["decision"] == d for p in preds)  # noqa: E731
    return {"total_transactions": len(preds), "approved": count("approve"), "in_review": count("review"),
            "declined": count("decline"), "predictions": preds}


@router.get("/stats")
def get_statistics():
    """All-time counts (persisted in the database)."""
    return fraud_service.get_statistics()


@router.get("/predictions/recent")
def get_recent_predictions(
    limit: int = Query(50, ge=1, le=1000),
    flagged_only: bool = False,
    unlabeled_only: bool = False,
):
    """Most recent predictions from every channel. flagged_only = the review / decline queue."""
    return fraud_service.get_recent(limit=limit, flagged_only=flagged_only, unlabeled_only=unlabeled_only)


@router.post("/predictions/{prediction_id}/feedback")
def submit_feedback(prediction_id: int, feedback: Feedback):
    """Analyst verdict on a prediction. Labels are used the next time the model is retrained."""
    row = fraud_service.label(prediction_id, feedback.is_fraud)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Prediction {prediction_id} not found")
    return row


@router.get("/model/info")
def get_model_info():
    return fraud_service.get_model_info()


@router.post("/model/retrain", status_code=status.HTTP_202_ACCEPTED)
def retrain_model():
    """Retrain in the background with all analyst feedback, then hot-swap the model."""
    return fraud_service.start_retrain()


@router.get("/model/retrain")
def retrain_status():
    return fraud_service.retrain_status


@router.get("/settings/decision")
def get_decision_policy():
    """Current approve/review/decline thresholds, plus presets derived from validation data."""
    return fraud_service.get_policy()


@router.put("/settings/decision")
def set_decision_policy(update: PolicyUpdate):
    """
    Change the thresholds for this API process. In-memory: resets to the
    trained policy on restart (retrain to change the default).
    """
    try:
        return fraud_service.set_policy(update.review_threshold, update.decline_threshold)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/monitoring")
def get_monitoring():
    """Latency percentiles, decision mix, score drift vs training, simulation scorecard."""
    return fraud_service.get_monitoring()
