# AI Fraud Detection System

Real-time card-fraud detection: every transaction is scored against **that card's own history**, a calibrated ML model turns it into a fraud probability, and a decision policy answers **approve / review / decline** with the reasons. Analysts confirm or clear flagged transactions, and those verdicts are used the next time the model is retrained.

It runs three ways from the same code:

| | What you get | Needs |
|---|---|---|
| **Desktop app** | Windows installer → opens in its own window, works offline | nothing (Python/Node are bundled) |
| **Website** | API + dashboard on one URL (`http://localhost:8000`) | Python 3.10+, Node 20+ (to build the dashboard) |
| **Docker** | API + dashboard + Redis, optional Kafka streaming stack | Docker |

## How it works

```
transaction ─► card history (velocity, usual amount, known countries/devices)
            ─► features ─► calibrated model (XGBoost / RF / LR) ─► probability
            ─► policy: approve  < review threshold ≤ review <  decline threshold ≤ decline
            ─► reasons (TreeSHAP)  ─► stored in SQLite ─► dashboard / review queue
                                                         └─► analyst label ─► retraining
```

**Features** (identical at training and serving time):

- *Card history:* transactions on the card in the last hour / 24 h, amount spent in 24 h, minutes since the previous transaction, amount ÷ the card's usual amount, first time from this country / category / device, how much history the card has
- *Transaction:* amount, hour, weekday, weekend, night, merchant category, device, country

History lives in memory (single process) or Redis (`HISTORY_BACKEND=redis`) so several processes see the same cards. After a restart the last 7 days are replayed from the database.

**Model selection & thresholds.** Data is split by time (train → validation → most recent period as test, never shuffled). XGBoost, Random Forest and Logistic Regression are trained; the best validation PR-AUC wins and is isotonically calibrated, so a 0.30 score really means ~30 %. The review threshold is set to catch a target share of fraud, the decline threshold to keep auto-declines ≥ 90 % precise. Low / Medium / High sensitivity presets (catch ~70 / 80 / 90 % of fraud) are computed from validation data and shown in Settings with their expected review load.

**Explanations.** Each decision lists its top drivers, e.g. *"4 transactions on this card in the last hour"*, *"8.3× this card's usual amount"*, *"First transaction from Nigeria on this card"* — exact TreeSHAP contributions for XGBoost, translated in the dashboard.

## Data

- **Built-in behavioural simulator (default).** Customers with stable habits (home country, favourite merchants, spend level, device, daily rhythm). Fraud is injected the way it happens: account takeover bursts, card testing, single high-value fraud, new-card fraud and *stealth* fraud that mimics the customer. Legitimate look-alikes (trips abroad, big purchases, shopping sprees, micro-payments, late nights, new customers) keep the task honest.
- **Kaggle credit-card transactions** ([kartik2112/fraud-detection](https://www.kaggle.com/datasets/kartik2112/fraud-detection), 1.85 M real-format rows). Download `fraudTrain.csv` and `fraudTest.csv` into `data/raw/kaggle/`, then:
  ```bash
  python -m src.pipelines.training_pipeline --source kaggle
  ```
- **Your own CSV** with at least `timestamp, amount, is_fraud` (plus `card_id, merchant_category, device_type, location_country` for full features): `--source csv --csv data/raw/yours.csv`.

### Results on the simulator (default run, test = last 15 % of time)

| Metric | Value |
|---|---|
| PR-AUC / ROC-AUC | ≈ 0.63 / 0.95 |
| Fraud caught (review + decline) | ≈ 80 % |
| Sent to review / auto-declined | ≈ 2 % / 0.5 % of traffic |
| Decline precision | ≈ 80 % |
| Scoring latency | p50 ≈ 10 ms |

Live simulation scorecard (5,000 streamed transactions): ~77 % of injected fraud flagged, ~3 % of legitimate customers flagged. The stealth scenario is designed to be mostly undetectable, so 100 % is not achievable — as in real life. Exact numbers for your run are printed after training and stored in `models/metadata.json`.

## Run as a website (from source)

```bash
git clone https://github.com/Abhinav-836/AI-Fraud-Detection.git
cd AI-Fraud-Detection
python -m venv venv
venv\Scripts\activate                 # macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt

python -m src.pipelines.training_pipeline          # ~30 s, writes models/

cd frontend && npm ci && npm run build && cd ..    # dashboard -> frontend/dist
uvicorn src.api.main:app --port 8000               # open http://localhost:8000
```

Dashboard development with hot reload: run `uvicorn` as above and `npm run dev` in `frontend/` (http://localhost:3000, talks to the API on port 8000).

Without a trained model the API still works on a transparent rule engine (`/health` → `"model_type": "rule_based"`).

## Desktop app

**Run from source** (opens a native window; falls back to the browser):

```bash
pip install -r requirements.txt pywebview
python desktop/launcher.py               # --browser to use the default browser
```

**Build the Windows installer** (Python 3.10–3.12 64-bit + Node 20 on PATH; [Inno Setup 6](https://jrsoftware.org/isdl.php) for the setup .exe):

```powershell
powershell -ExecutionPolicy Bypass -File desktop\build_desktop.ps1
```

Produces `dist\AIFraudDetection-Setup-2.0.0.exe` (installer, no admin rights needed), `dist\AIFraudDetection\AIFraudDetection.exe` (portable) and `dist\AIFraudDetection-portable.zip`. The app listens on `127.0.0.1` only and keeps its database, logs and retrained models in `%LOCALAPPDATA%\AIFraudDetection` (kept on uninstall). The window uses Microsoft Edge WebView2, which ships with Windows 10/11; if it is missing the dashboard opens in the default browser.

## Docker

```bash
docker compose up --build                          # API + dashboard + Redis  → http://localhost:8000
docker compose --profile streaming up --build      # + Kafka, traffic simulator, stream processor
```

With the streaming profile, `traffic-simulator` publishes transactions to Kafka, `stream-processor` scores them with the same engine (shared Redis history, shared database volume), and they appear on the dashboard. Single container: `docker build -f deployment/docker/Dockerfile.api -t fraud-detection . && docker run -p 8000:8000 -v fraud-data:/data fraud-detection`.

## Dashboard

- **Dashboard:** approve / review / decline counts, live simulation (start/stop; each row shows the decision, reasons, and whether an injected fraud was caught or missed), transaction tester, **review queue** (Confirm fraud / Legitimate → saved as labels), activity chart, recent transactions with analyst labels.
- **Analytics:** flag rate, amounts, top reasons, flag rate by country, model test metrics (PR-AUC, ROC-AUC, Brier, fraud caught, decline precision, review rate) and candidate models, live monitoring (latency p50/p95/p99, score drift PSI, simulation scorecard), feedback counts and **Retrain** (runs in the background; the new model is hot-swapped). CSV export.
- **Settings:** sensitivity presets or custom review/decline thresholds; theme (light/dark/system), language (English, Español, Français, Deutsch), time zone, date format.

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness + active model |
| POST | `/api/v1/predict` | Score one transaction |
| POST | `/api/v1/predict/batch` | Score up to 1000 (processed in time order) |
| GET | `/api/v1/stats` | Totals by decision, labels |
| GET | `/api/v1/predictions/recent` | `?limit=&flagged_only=&unlabeled_only=` |
| POST | `/api/v1/predictions/{id}/feedback` | `{"is_fraud": true|false}` analyst label |
| GET | `/api/v1/model/info` | Model, training data, test metrics, candidates |
| POST / GET | `/api/v1/model/retrain` | Start / poll background retraining |
| GET / PUT | `/api/v1/settings/decision` | Policy, presets / set `review_threshold`, `decline_threshold` |
| GET | `/api/v1/monitoring` | Latency, drift, simulation scorecard, retrain status |
| WS | `/ws/live` | Send a transaction → scored result; `{"action":"start_simulation","interval":1}` / `stop_simulation` |

Docs: `http://localhost:8000/docs`.

```bash
curl -X POST http://localhost:8000/api/v1/predict -H "Content-Type: application/json" \
  -d '{"transaction_id":"TXN_001","card_id":"CARD_42","amount":1500.50,"merchant_category":"electronics",
       "device_type":"web","location_country":"US","timestamp":"2026-10-28T14:05:00+05:30"}'
```

`transaction_id` and `amount` are required; send `card_id` to enable history features. Without `timestamp` the current time is used.

## Batch scoring

```bash
python -m src.pipelines.detection_pipeline --input data/raw/new.csv --output data/processed/scored.csv
```

Adds `fraud_probability`, `decision` and `predicted_fraud`; rows are replayed in time order so history features work. If the file has `is_fraud`, precision/recall are reported.

## Configuration

`config/settings.yaml`, `config/model_config.yaml`, plus environment variables:

| Variable | Purpose |
|---|---|
| `FRAUD_DATA_DIR` | Writable folder for database, logs, retrained models (default: project folder) |
| `FRAUD_DB_PATH` | SQLite file (default `data/fraud.db` inside the data folder) |
| `MODEL_PATH` | Model directory (default `models`) |
| `HISTORY_BACKEND` / `REDIS_URL` | `memory` (default) or `redis` + its URL |
| `FRAUD_API_KEY` | If set, `/api/v1/*` and `/ws/live` require `X-API-Key` (or `?api_key=` for WebSocket) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka brokers |
| `LOG_LEVEL` | Logging level |
| `VITE_API_URL`, `VITE_API_KEY` | Build-time: dashboard served from another origin / with an API key |

## Tests

```bash
pytest            # 37 tests
```

CI runs them on Python 3.10–3.13, a training smoke test, the dashboard build with `npm audit`, and the Docker build.

## Limitations

- The simulator is realistic in structure but synthetic; validate on your own labelled data before relying on the thresholds.
- Predictions are stored in SQLite: fine for one machine (the desktop app, one container); use one API replica or move storage to a shared database for horizontal scaling.
- Policy changes from the dashboard last until restart; retraining sets new defaults.

## License

MIT — see `LICENSE.txt`.
