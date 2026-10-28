import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..utils.config import load_settings, resolve_path
from ..utils.logger import get_logger
from .routers import fraud_routes, websocket_routes
from .security import configured_key
from .services.fraud_service import fraud_service

logger = get_logger(__name__)

settings = load_settings()
APP_NAME = settings.get('app', {}).get('name', 'AI Fraud Detection System')
APP_VERSION = settings.get('app', {}).get('version', '2.0.0')

DEFAULT_ORIGINS = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:5173", "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Fraud Detection API")
    fraud_service.initialize()
    logger.info(f"Scoring with: {fraud_service.model_type}; API key {'required' if configured_key() else 'not set'}")
    yield
    logger.info("Shutting down Fraud Detection API")


app = FastAPI(
    title=APP_NAME,
    description="Real-time fraud detection: card-history features, calibrated ML model, "
                "approve/review/decline decisions with explanations, analyst feedback loop.",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get('api', {}).get('cors_origins') or DEFAULT_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(fraud_routes.router, prefix="/api/v1", tags=["fraud"])
app.include_router(websocket_routes.router, tags=["websocket"])


@app.get("/api")
def api_root():
    return {
        "message": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "timestamp": datetime.now().astimezone().isoformat(),
        "docs": "/docs",
        "auth": "X-API-Key header required" if configured_key() else "open (FRAUD_API_KEY not set)",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": fraud_service.model_loaded,
        "model_type": fraud_service.model_type,
        "timestamp": datetime.now().astimezone().isoformat(),
    }


# ---------------------------------------------------------------- frontend
# When the React build exists (frontend/dist, or FRONTEND_DIST), the API also
# serves the dashboard, so one process (Docker image, desktop app) is enough.
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST") or resolve_path("frontend/dist"))

if (FRONTEND_DIST / "index.html").exists():
    if (FRONTEND_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith(("api/", "ws/", "docs", "redoc", "openapi.json")):
            raise HTTPException(status_code=404)
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")  # client-side routes
else:
    @app.get("/", include_in_schema=False)
    def root():
        return api_root()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
