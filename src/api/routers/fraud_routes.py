from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
except:
    import logging
    logger = logging.getLogger(__name__)

router = APIRouter()


class Transaction(BaseModel):
    """Transaction model"""
    transaction_id: str
    amount: float = Field(..., gt=0)
    merchant_category: Optional[str] = "unknown"
    device_type: Optional[str] = "web"
    location_country: Optional[str] = "US"
    hour_of_day: Optional[int] = Field(None, ge=0, le=23)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    timestamp: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN123456",
                "amount": 1500.50,
                "merchant_category": "retail",
                "device_type": "mobile",
                "location_country": "US",
                "hour_of_day": 14,
                "day_of_week": 3
            }
        }


class TransactionBatch(BaseModel):
    """Batch of transactions"""
    transactions: List[Transaction]


class FraudPrediction(BaseModel):
    """Fraud prediction response"""
    transaction_id: str
    is_fraud: bool
    fraud_probability: float
    risk_level: str
    confidence: float
    factors: List[str]
    timestamp: datetime


def calculate_fraud_score(transaction: Transaction) -> tuple:
    """
    Simple rule-based fraud detection
    
    Returns:
        (fraud_probability, risk_factors)
    """
    fraud_score = 0.0
    risk_factors = []
    
    # Rule 1: High amount transactions
    if transaction.amount > 1000:
        fraud_score += 0.25
        risk_factors.append("High transaction amount")
    
    if transaction.amount > 5000:
        fraud_score += 0.25
        risk_factors.append("Very high transaction amount")
    
    # Rule 2: Unusual hours
    if transaction.hour_of_day is not None:
        if transaction.hour_of_day < 6 or transaction.hour_of_day > 22:
            fraud_score += 0.15
            risk_factors.append("Unusual transaction time")
    
    # Rule 3: Weekend transactions
    if transaction.day_of_week is not None and transaction.day_of_week >= 5:
        fraud_score += 0.10
        risk_factors.append("Weekend transaction")
    
    # Rule 4: High-risk merchant categories
    high_risk_categories = ["gambling", "money_transfer", "pawn_shop"]
    if transaction.merchant_category in high_risk_categories:
        fraud_score += 0.30
        risk_factors.append("High-risk merchant category")
    
    # Rule 5: International transactions
    if transaction.location_country not in ["US", "CA", "UK", "AU"]:
        fraud_score += 0.15
        risk_factors.append("International transaction")
    
    return min(fraud_score, 0.95), risk_factors


@router.post("/predict", response_model=FraudPrediction)
async def predict_fraud(transaction: Transaction):
    """
    Predict fraud for a single transaction
    
    Args:
        transaction: Transaction data
        
    Returns:
        Fraud prediction result
    """
    try:
        logger.info(f"Processing prediction for transaction: {transaction.transaction_id}")
        
        # Calculate fraud score
        fraud_probability, risk_factors = calculate_fraud_score(transaction)
        
        is_fraud = fraud_probability > 0.5
        
        # Determine risk level
        if fraud_probability < 0.3:
            risk_level = "low"
        elif fraud_probability < 0.7:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        # Calculate confidence
        confidence = abs(fraud_probability - 0.5) * 2
        
        if not risk_factors:
            risk_factors = ["No significant risk factors detected"]
        
        result = FraudPrediction(
            transaction_id=transaction.transaction_id,
            is_fraud=is_fraud,
            fraud_probability=round(fraud_probability, 3),
            risk_level=risk_level,
            confidence=round(confidence, 3),
            factors=risk_factors,
            timestamp=datetime.now()
        )
        
        logger.info(
            f"Prediction complete - ID: {transaction.transaction_id}, "
            f"Fraud: {is_fraud}, Probability: {fraud_probability:.3f}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/batch")
async def predict_fraud_batch(batch: TransactionBatch):
    """
    Predict fraud for multiple transactions
    
    Args:
        batch: Batch of transactions
        
    Returns:
        List of fraud predictions
    """
    try:
        logger.info(f"Processing batch of {len(batch.transactions)} transactions")
        
        predictions = []
        fraud_count = 0
        
        for transaction in batch.transactions:
            prediction = await predict_fraud(transaction)
            predictions.append(prediction)
            if prediction.is_fraud:
                fraud_count += 1
        
        logger.info(
            f"Batch complete - Total: {len(predictions)}, "
            f"Fraud detected: {fraud_count}"
        )
        
        return {
            "total_transactions": len(predictions),
            "fraud_detected": fraud_count,
            "fraud_rate": fraud_count / len(predictions) if predictions else 0,
            "predictions": predictions
        }
        
    except Exception as e:
        logger.error(f"Batch prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics():
    """Get fraud detection statistics"""
    return {
        "total_predictions": 0,
        "fraud_detected": 0,
        "accuracy": 0.0,
        "model_type": "rule_based",
        "message": "Statistics tracking not yet implemented"
    }


@router.get("/model/info")
async def get_model_info():
    """Get information about the loaded model"""
    return {
        "model_type": "rule_based",
        "version": "1.0.0",
        "status": "active",
        "description": "Simple rule-based fraud detection system"
    }