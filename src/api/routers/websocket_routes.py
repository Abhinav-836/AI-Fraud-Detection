from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from datetime import datetime
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.detection.real_time_detector import RealTimeDetector
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    # Create a simple RealTimeDetector mock if not available
    class RealTimeDetector:
        def __init__(self, *args, **kwargs):
            pass
        def detect(self, transaction):
            return rule_based_detection(transaction)

router = APIRouter()

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.transaction_history = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast: {e}")
                self.active_connections.discard(connection)

    async def send_personal(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

manager = ConnectionManager()

# Initialize real-time detector
try:
    realtime_detector = RealTimeDetector(model_path="models", threshold=0.5)
    logger.info("Real-time detector initialized")
except Exception as e:
    logger.warning(f"Real-time detector not available: {e}, using rule-based fallback")
    realtime_detector = None


def rule_based_detection(transaction: dict) -> dict:
    """Fallback rule-based detection"""
    fraud_score = 0.0
    risk_factors = []
    
    amount = transaction.get("amount", 0)
    if amount > 1000:
        fraud_score += 0.25
        risk_factors.append("High amount")
    if amount > 5000:
        fraud_score += 0.25
        risk_factors.append("Very high amount")
    
    hour = transaction.get("hour_of_day", 12)
    if hour < 6 or hour > 22:
        fraud_score += 0.15
        risk_factors.append("Unusual hour")
    
    merchant = transaction.get("merchant_category", "").lower()
    high_risk_merchants = ["gambling", "money_transfer", "cryptocurrency", "pawn_shop"]
    if merchant in high_risk_merchants:
        fraud_score += 0.30
        risk_factors.append("High-risk merchant")
    
    location = transaction.get("location_country", "US")
    if location not in ["US", "CA", "UK", "AU"]:
        fraud_score += 0.15
        risk_factors.append("International transaction")
    
    fraud_probability = min(fraud_score, 0.95)
    is_fraud = fraud_probability > 0.5
    
    return {
        "is_fraud": is_fraud,
        "fraud_probability": fraud_probability,
        "risk_level": "high" if fraud_probability > 0.7 else "medium" if fraud_probability > 0.3 else "low",
        "factors": risk_factors or ["No risk factors detected"],
        "processing_time_ms": 5.0,
        "timestamp": datetime.now().isoformat()
    }


@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time fraud detection"""
    await manager.connect(websocket)
    
    try:
        # Send initial connection confirmation
        await manager.send_personal({
            "type": "connection",
            "status": "connected",
            "message": "Connected to real-time fraud detection",
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        while True:
            # Receive transaction from WebSocket
            data = await websocket.receive_text()
            transaction = json.loads(data)
            
            logger.info(f"Received real-time transaction: {transaction.get('transaction_id')}")
            
            # Process with real-time detector or fallback
            if realtime_detector:
                try:
                    result = realtime_detector.detect(transaction)
                except Exception as e:
                    logger.error(f"Real-time detector error: {e}, using fallback")
                    result = rule_based_detection(transaction)
            else:
                result = rule_based_detection(transaction)
            
            # Ensure result has all required fields
            if 'processing_time_ms' not in result:
                result['processing_time_ms'] = 5.0
            if 'timestamp' not in result:
                result['timestamp'] = datetime.now().isoformat()
            
            # Add to history
            manager.transaction_history.append({
                "transaction": transaction,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Keep only last 1000 transactions
            if len(manager.transaction_history) > 1000:
                manager.transaction_history.pop(0)
            
            # Broadcast result to all connected clients
            await manager.broadcast({
                "type": "fraud_alert" if result.get("is_fraud") else "transaction_processed",
                "transaction": transaction,
                "prediction": result,
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "active_connections": len(manager.active_connections),
        "total_transactions_processed": len(manager.transaction_history),
        "timestamp": datetime.now().isoformat()
    }