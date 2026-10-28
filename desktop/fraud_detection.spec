# PyInstaller spec for the desktop app. Build with desktop/build_desktop.ps1
# (Windows) or:  pyinstaller desktop/fraud_detection.spec --noconfirm
#
# Output: dist/AIFraudDetection/AIFraudDetection(.exe)  (one-folder build:
# starts much faster than --onefile, and Inno Setup packages the folder).
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent  # repository root
ICON = ROOT / "desktop" / "assets" / "app.ico"

for required in ("frontend/dist/index.html", "models/model.pkl", "models/transformers/transformer.pkl"):
    if not (ROOT / required).exists():
        raise SystemExit(f"Missing {required}: build the dashboard and train a model first (see build_desktop.ps1)")

datas = [
    (str(ROOT / "config"), "config"),
    (str(ROOT / "frontend" / "dist"), "frontend/dist"),
    (str(ROOT / "models"), "models"),   # bundled default model (read-only)
]
binaries = []
# Skip test suites and optional integrations: importing them needs pytest,
# hypothesis, dask, spark... which are not installed (and not needed).
SKIP = (".tests", ".testing", ".conftest", ".dask", ".spark", ".plotting")


def wanted(name):
    return not any(part in name for part in SKIP)


hiddenimports = (
    collect_submodules("src")
    + collect_submodules("uvicorn")
    + collect_submodules("sklearn", filter=wanted, on_error="ignore")
    + ["websockets", "websockets.legacy", "websockets.legacy.server", "h11", "httptools", "anyio._backends._asyncio"]
)

# xgboost ships its native library + VERSION file as package data.
# pywebview (and pythonnet on Windows) are covered by the hooks in
# pyinstaller-hooks-contrib, installed together with PyInstaller.
d, b, h = collect_all("xgboost", filter_submodules=wanted, on_error="ignore")
datas += d
binaries += b
hiddenimports += h + ["webview"]

a = Analysis(
    [str(ROOT / "desktop" / "launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "tkinter", "matplotlib", "IPython", "jupyter", "notebook", "pytest",
        "kafka", "psycopg2", "sqlalchemy",   # server-only extras, not used by the desktop app
    ],
    noarchive=False,
)
# xgboost's Linux wheel pulls in NVIDIA NCCL (~300 MB) for multi-GPU training;
# CPU inference never needs it.
a.binaries = [b for b in a.binaries if "nvidia" not in b[0].lower() and "nccl" not in b[0].lower()]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AIFraudDetection",
    console=False,          # no black console window behind the app
    icon=str(ICON) if ICON.exists() else None,
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="AIFraudDetection")
