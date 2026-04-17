from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import yaml
from pathlib import Path
import sys
import os
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import with proper error handling FIRST
try:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
except ImportError as e:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import custom logger: {e}")

# Global state
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Fraud Detection API")
    
    # Load configuration
    try:
        config_path = project_root / "config" / "settings.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            app_state['config'] = config
            logger.info("Configuration loaded successfully")
        else:
            logger.warning("Configuration file not found, using defaults")
            app_state['config'] = {
                'app': {
                    'name': 'Fraud Detection API',
                    'version': '1.0.0',
                    'environment': 'development'
                }
            }
    except Exception as e:
        logger.error(f"Failed to load config: {str(e)}")
        app_state['config'] = {}
    
    # Initialize model (optional - will use rule-based if not available)
    app_state['model'] = None
    app_state['transformer'] = None
    
    logger.info("API initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Fraud Detection API")


# Create FastAPI app
app = FastAPI(
    title="AI Fraud Detection API",
    description="Real-time fraud detection API using machine learning",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - FIXED for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Try to include routers (AFTER logger is defined)
try:
    from src.api.routers import fraud_routes
    app.include_router(fraud_routes.router, prefix="/api/v1", tags=["fraud"])
    logger.info("Fraud routes included successfully")
except ImportError as e:
    logger.warning(f"Could not import fraud_routes: {e}")
    logger.info("Using basic endpoints")

# Add WebSocket routes (AFTER logger is defined)
try:
    from src.api.routers import websocket_routes
    app.include_router(websocket_routes.router, tags=["websocket"])
    logger.info("WebSocket routes included successfully")
except ImportError as e:
    logger.warning(f"Could not import websocket_routes: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Fraud Detection API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "config": "/config",
            "predict": "/api/v1/predict",
            "websocket": "ws://localhost:8000/ws/live"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": app_state.get('model') is not None,
        "config_loaded": 'config' in app_state,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/config")
async def get_config():
    """Get API configuration (non-sensitive)"""
    config = app_state.get('config', {})
    
    return {
        "app_name": config.get('app', {}).get('name', 'Fraud Detection API'),
        "version": config.get('app', {}).get('version', '1.0.0'),
        "environment": config.get('app', {}).get('environment', 'development'),
        "timestamp": datetime.now().isoformat()
    }


def get_app():
    """Get FastAPI app instance"""
    return app


# For direct execution
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Starting AI Fraud Detection API")
    print("=" * 60)
    print("API Documentation: http://127.0.0.1:8000/docs")
    print("Health Check: http://127.0.0.1:8000/health")
    print("Predict Endpoint: POST http://127.0.0.1:8000/api/v1/predict")
    print("WebSocket Endpoint: ws://127.0.0.1:8000/ws/live")
    print("=" * 60)
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)