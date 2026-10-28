"""
Real-time channel.

Client -> server messages:
  {transaction JSON}                         score one transaction
  {"action": "start_simulation", "interval": 1.0}
                                             stream realistic simulated traffic
  {"action": "stop_simulation"}

Server -> client messages:
  {"type": "connection", ...}
  {"type": "transaction_processed" | "fraud_alert", "transaction", "prediction", "truth"?}
  {"type": "simulation", "state": "started" | "stopped"}
  {"type": "error", ...}

The sender gets every result; other dashboards receive only fraud alerts.
"""
import asyncio
import json
from datetime import datetime
from typing import Awaitable, Callable, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from ...features.feature_engineering import normalize_transaction
from ...ingestion.simulator import LiveSimulator
from ...utils.logger import get_logger
from ..security import websocket_authorized
from ..services.fraud_service import fraud_service
from .fraud_routes import Transaction

logger = get_logger(__name__)

router = APIRouter()


def _now() -> str:
    return datetime.now().astimezone().isoformat()


class ConnectionManager:
    def __init__(self):
        # websocket -> its serialised send function
        self.active_connections: Dict[WebSocket, Callable[[dict], Awaitable[None]]] = {}
        self.messages_processed = 0

    def register(self, websocket: WebSocket, send: Callable[[dict], Awaitable[None]]):
        self.active_connections[websocket] = send

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    async def broadcast(self, message: dict, exclude: WebSocket = None):
        for connection, send in list(self.active_connections.items()):
            if connection is exclude:
                continue
            try:
                await send(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


async def _score_and_send(websocket: WebSocket, send, tx: dict, source: str, truth: Optional[dict] = None):
    result = await run_in_threadpool(fraud_service.predict, tx, source, truth)
    manager.messages_processed += 1
    message = {
        "type": "fraud_alert" if result["is_fraud"] else "transaction_processed",
        "transaction": tx,
        "prediction": result,
        "truth": truth,
        "timestamp": _now(),
    }
    await send(message)
    if result["is_fraud"]:
        await manager.broadcast(message, exclude=websocket)


async def _run_simulation(websocket: WebSocket, send, interval: float):
    sim = LiveSimulator()

    def warmup():
        # A week of normal history so simulated cards behave like real ones
        for tx in sim.warmup_history(days=7):
            n = normalize_transaction(tx)
            fraud_service.history.score_and_update(n["card_id"], n["epoch"], n["amount"], n["location_country"],
                                                   n["merchant_category"], n["device_type"])

    await run_in_threadpool(warmup)
    await send({"type": "simulation", "state": "started", "timestamp": _now()})
    while True:
        tx, truth = LiveSimulator.split_truth(sim.next_transaction())
        await _score_and_send(websocket, send, tx, "simulation", truth)
        # Fraud episodes arrive in quick bursts, like the real thing
        await asyncio.sleep(interval / 3 if sim.queue else interval)


@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    if not websocket_authorized(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    simulation: Optional[asyncio.Task] = None
    # The simulation task, this loop and broadcasts from other clients all
    # write to the socket; serialise the sends
    send_lock = asyncio.Lock()

    async def send(message: dict):
        async with send_lock:
            await websocket.send_json(message)

    manager.register(websocket, send)

    try:
        await send({"type": "connection", "status": "connected",
                                   "model_type": fraud_service.model_type, "timestamp": _now()})
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as e:
                await send({"type": "error", "message": "Invalid JSON", "details": str(e), "timestamp": _now()})
                continue

            action = data.get("action") if isinstance(data, dict) else None
            if action == "start_simulation":
                if simulation is None or simulation.done():
                    interval = min(max(float(data.get("interval", 1.0)), 0.2), 5.0)
                    simulation = asyncio.create_task(_run_simulation(websocket, send, interval))
                continue
            if action == "stop_simulation":
                if simulation:
                    simulation.cancel()
                    simulation = None
                await send({"type": "simulation", "state": "stopped", "timestamp": _now()})
                continue

            try:
                tx = Transaction.model_validate(data).model_dump(mode="json")
            except ValidationError as e:
                await send({"type": "error", "message": "Invalid transaction",
                                           "details": e.errors(include_url=False), "timestamp": _now()})
                continue
            await _score_and_send(websocket, send, tx, "websocket")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
    finally:
        if simulation:
            simulation.cancel()
        manager.disconnect(websocket)


@router.get("/ws/stats")
def get_websocket_stats():
    return {
        "active_connections": len(manager.active_connections),
        "total_transactions_processed": manager.messages_processed,
        "timestamp": _now(),
    }
