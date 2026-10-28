"""
Central configuration and path helpers.

All paths resolve against the project root (or against FRAUD_DATA_DIR for
writable state), so the code behaves the same from pytest, uvicorn, Docker
and the packaged desktop app.
"""
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Union

import yaml

# In a PyInstaller bundle, read-only resources live in sys._MEIPASS
_BUNDLE_ROOT = getattr(sys, "_MEIPASS", None)
PROJECT_ROOT = Path(_BUNDLE_ROOT) if _BUNDLE_ROOT else Path(__file__).resolve().parents[2]


def resolve_path(path: Union[str, Path]) -> Path:
    """Absolute path; relative paths are anchored at the project root."""
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def data_dir() -> Path:
    """
    Writable directory for the database, logs, reports and trained models.
    Defaults to the project root; the desktop app points it at the user's
    AppData folder via FRAUD_DATA_DIR (the install folder is read-only).
    """
    base = os.getenv("FRAUD_DATA_DIR")
    path = Path(base) if base else PROJECT_ROOT
    path.mkdir(parents=True, exist_ok=True)
    return path


def writable_path(path: Union[str, Path]) -> Path:
    """Resolve a relative path inside the writable data directory."""
    p = Path(path)
    return p if p.is_absolute() else data_dir() / p


def load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    with open(resolve_path(path), "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=None)
def _cached_settings(path: str) -> Dict[str, Any]:
    return load_yaml(path)


def load_settings(path: Union[str, Path] = "config/settings.yaml") -> Dict[str, Any]:
    """
    Load settings.yaml and apply environment-variable overrides.

      KAFKA_BOOTSTRAP_SERVERS  comma-separated list
      MODEL_PATH               directory holding trained artifacts
      CORS_ORIGINS             comma-separated list
      HISTORY_BACKEND          memory | redis
      REDIS_URL                redis://host:6379/0
      FRAUD_DB_PATH            SQLite file for predictions + feedback
    """
    resolved = resolve_path(path)
    settings = dict(_cached_settings(str(resolved))) if resolved.exists() else {}

    for key in ("kafka", "model", "api", "history", "storage"):
        settings[key] = dict(settings.get(key) or {})

    env = os.environ
    if env.get("KAFKA_BOOTSTRAP_SERVERS"):
        settings["kafka"]["bootstrap_servers"] = [
            s.strip() for s in env["KAFKA_BOOTSTRAP_SERVERS"].split(",") if s.strip()
        ]
    if env.get("MODEL_PATH"):
        settings["model"]["model_path"] = env["MODEL_PATH"]
    if env.get("CORS_ORIGINS"):
        settings["api"]["cors_origins"] = [s.strip() for s in env["CORS_ORIGINS"].split(",") if s.strip()]
    if env.get("HISTORY_BACKEND"):
        settings["history"]["backend"] = env["HISTORY_BACKEND"]
    if env.get("REDIS_URL"):
        settings["history"]["redis_url"] = env["REDIS_URL"]
    if env.get("FRAUD_DB_PATH"):
        settings["storage"]["db_path"] = env["FRAUD_DB_PATH"]
    return settings


def load_model_config(path: Union[str, Path] = "config/model_config.yaml") -> Dict[str, Any]:
    return load_yaml(path)


def model_dir() -> Path:
    """Directory that holds trained model artifacts (writable)."""
    return writable_path(load_settings().get("model", {}).get("model_path", "models"))


def bundled_model_dir() -> Path:
    """Read-only models shipped inside the desktop bundle / Docker image, if any."""
    return resolve_path("models")


def db_path() -> Path:
    return writable_path(load_settings().get("storage", {}).get("db_path", "data/fraud.db"))
