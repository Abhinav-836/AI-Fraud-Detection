"""
Optional API-key protection.

Set FRAUD_API_KEY to require the key on every /api/v1 request
(header `X-API-Key: <key>`) and on the WebSocket (`/ws/live?api_key=<key>`).
Left unset (local development, the desktop app) the API is open.
"""
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException, WebSocket, status


def configured_key() -> Optional[str]:
    return os.getenv("FRAUD_API_KEY") or None


def _matches(given: Optional[str], expected: str) -> bool:
    return bool(given) and hmac.compare_digest(given, expected)


async def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    expected = configured_key()
    if expected and not _matches(x_api_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


def websocket_authorized(websocket: WebSocket) -> bool:
    expected = configured_key()
    if not expected:
        return True
    given = websocket.query_params.get("api_key") or websocket.headers.get("x-api-key")
    return _matches(given, expected)
