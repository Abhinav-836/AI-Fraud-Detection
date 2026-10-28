"""
AI Fraud Detection — desktop app.

Runs the same FastAPI engine + React dashboard as the website, but locally
and in its own window: no Python, Node, Docker or browser setup needed
once packaged (see desktop/README.md).

  * data (database, logs, retrained models) -> %LOCALAPPDATA%\\AIFraudDetection
    (~/.local/share/AIFraudDetection on Linux, ~/Library/Application Support on macOS)
  * the API listens on 127.0.0.1 only, on a free port
  * window: pywebview (Edge WebView2 on Windows); if that is unavailable the
    dashboard opens in the default browser instead

Run from source:  python desktop/launcher.py [--browser] [--port 8765] [--no-open]
"""
import argparse
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "AI Fraud Detection"
APP_ID = "AIFraudDetection"


def user_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    path = base / APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


# Must happen before anything from src/ is imported: config, logging and the
# database location are resolved at import time.
DATA_DIR = Path(os.environ.setdefault("FRAUD_DATA_DIR", str(user_data_dir())))

# A windowed (no console) PyInstaller build has sys.stdout/stderr = None;
# uvicorn and logging would crash writing to them. Send them to a file.
if sys.stdout is None or sys.stderr is None:
    (DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
    _log = open(DATA_DIR / "logs" / "desktop.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or _log
    sys.stderr = sys.stderr or _log

# Running from source: make `src` importable
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402

from src.api.main import app  # noqa: E402  (direct import: PyInstaller can't follow "src.api.main:app" strings)
from src.api.services.fraud_service import fraud_service  # noqa: E402


def free_port(preferred: int = 0) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
        except OSError:
            s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_until_healthy(url: str, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except OSError:
            pass
        time.sleep(0.25)
    return False


def start_server(port: int) -> uvicorn.Server:
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_config=None,      # default config assumes a console
        log_level="warning",
        ws="auto",
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, name="api-server", daemon=True).start()
    return server


def ensure_model():
    """No trained model anywhere (e.g. a source checkout)? Train one in the
    background; the dashboard works on rules meanwhile and switches over
    automatically when training finishes (~30 s)."""
    if not fraud_service.model_loaded:
        print("No trained model found - training one in the background", flush=True)
        fraud_service.start_retrain()


def open_window(url: str) -> bool:
    """Native window. Returns False if pywebview / WebView2 is unavailable."""
    try:
        import webview
    except ImportError:
        return False
    try:
        webview.create_window(APP_NAME, url, width=1440, height=900, min_size=(1000, 680))
        webview.start()  # blocks until the window is closed
        return True
    except Exception as e:  # missing WebView2 runtime, no GUI backend, ...
        print(f"Native window unavailable ({e}); using the browser", flush=True)
        return False


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--browser", action="store_true", help="open in the default browser instead of a window")
    parser.add_argument("--no-open", action="store_true", help="only run the server (headless)")
    parser.add_argument("--port", type=int, default=0, help="port (default: a free one)")
    args = parser.parse_args()

    port = free_port(args.port)
    url = f"http://127.0.0.1:{port}"
    server = start_server(port)
    if not wait_until_healthy(url):
        print("The fraud detection engine did not start; see logs in", DATA_DIR / "logs", flush=True)
        sys.exit(1)
    ensure_model()
    print(f"{APP_NAME} running at {url}  (data: {DATA_DIR})", flush=True)

    try:
        if args.no_open:
            server_thread_wait(server)
        elif args.browser or not open_window(url):
            webbrowser.open(url)
            print("Close this window or press Ctrl+C to quit.", flush=True)
            server_thread_wait(server)
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True
        time.sleep(0.5)


def server_thread_wait(server: uvicorn.Server):
    while not server.should_exit:
        time.sleep(0.5)


if __name__ == "__main__":
    main()
