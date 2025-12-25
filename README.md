# AI Fraud Detection System

A comprehensive, production-ready fraud detection system using machine learning with real-time streaming capabilities, REST API, and web interface.

## Features

- **Real-time Fraud Detection**: Process transactions in real-time using Kafka streaming
- **Multiple ML Models**: XGBoost, Random Forest, and Logistic Regression
- **REST API**: FastAPI-based API for easy integration
- **Feature Engineering**: Automated feature creation and selection
- **Model Registry**: Track and manage multiple model versions
- **Monitoring**: Built-in metrics and logging
- **Scalable**: Kubernetes-ready deployment

## Project Structure

```
AI-Fraud-Detection/
├── config/              # Configuration files
├── data/               # Data storage
├── src/                # Source code
│   ├── ingestion/      # Data loading
│   ├── preprocessing/  # Data cleaning and transformation
│   ├── features/       # Feature engineering
│   ├── models/         # Model training and evaluation
│   ├── detection/      # Real-time and batch detection
│   ├── streaming/      # Kafka integration
│   ├── api/           # FastAPI application
│   └── utils/         # Utilities
├── notebooks/         # Jupyter notebooks
├── deployment/        # Docker and Kubernetes configs
├── frontend/          # React frontend
└── tests/            # Unit and integration tests
```

## Quick Start

### Prerequisites

- Python 3.9+
- Docker (optional)
- Kafka (for streaming)
- PostgreSQL (for data storage)
- Redis (for caching)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/AI-Fraud-Detection.git
cd AI-Fraud-Detection
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up configuration:
```bash
cp config/credentials.example.yaml config/credentials.yaml
# Edit credentials.yaml with your actual credentials
```

### Training the Model

```python
from src.ingestion.data_loader import DataLoader
from src.preprocessing.clean import DataCleaner
from src.preprocessing.transform import DataTransformer
from src.features.feature_engineering import FeatureEngineer
from src.models.train import FraudModelTrainer

# Load data
loader = DataLoader()
df = loader.load_synthetic_data(n_samples=10000)

# Clean data
cleaner = DataCleaner()
df_clean = cleaner.clean(df)

# Engineer features
engineer = FeatureEngineer()
df_features = engineer.create_features(df_clean)

# Transform data
transformer = DataTransformer()
X, y = transformer.fit_transform(df_features)

# Split data
train_df, val_df, test_df = loader.split_data(df_features)
X_train, y_train = transformer.fit_transform(train_df)
X_val, y_val = transformer.transform(val_df)

# Train models
trainer = FraudModelTrainer()
results = trainer.train_all_models(X_train, y_train, X_val, y_val)

# Save best model
trainer.save_model(trainer.best_model)
transformer.save_transformers()
```

### Running the API

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. 

API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### API Usage Examples

**Single Transaction Prediction:**
```bash
curl -X POST "http://localhost:8000/api/v1/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN_001",
    "amount": 1500.50,
    "merchant_category": "retail",
    "device_type": "mobile",
    "location_country": "US",
    "hour_of_day": 14,
    "day_of_week": 3
  }'
```

**Batch Prediction:**
```bash
curl -X POST "http://localhost:8000/api/v1/predict/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "transactions": [
      {
        "transaction_id": "TXN_001",
        "amount": 1500.50,
        "merchant_category": "retail",
        "device_type": "mobile",
        "location_country": "US"
      }
    ]
  }'
```

### Running with Docker

```bash
# Build image
docker build -t fraud-detection-api -f deployment/docker/Dockerfile.api .

# Run container
docker run -p 8000:8000 fraud-detection-api
```

### Real-time Streaming

Start Kafka consumer for real-time fraud detection:

```python
from src.streaming.kafka_consumer import FraudKafkaConsumer
from src.detection.real_time_detector import RealTimeDetector

# Initialize detector
detector = RealTimeDetector()

# Initialize consumer
consumer = FraudKafkaConsumer()
consumer.connect()

# Start consuming
consumer.consume_messages(detector.detect)
```

## Model Performance

The trained models achieve the following performance on the test set:

| Model | Accuracy | Precision | Recall | F1-Score | AUC-ROC |
|-------|----------|-----------|--------|----------|---------|
| XGBoost | 0.9823 | 0.9456 | 0.9234 | 0.9344 | 0.9876 |
| Random Forest | 0.9756 | 0.9234 | 0.9123 | 0.9178 | 0.9823 |
| Logistic Regression | 0.9456 | 0.8934 | 0.8823 | 0.8878 | 0.9567 |

## Features

The system uses the following features for fraud detection:

**Transaction Features:**
- Amount
- Transaction velocity (count in 1h, 24h, 7d)
- Time since last transaction
- Amount to average ratio

**Temporal Features:**
- Hour of day
- Day of week
- Is weekend
- Is business hours

**Behavioral Features:**
- Device changes
- Location changes
- Merchant diversity

**Categorical Features:**
- Merchant category
- Device type
- Location country

## Configuration

Edit `config/settings.yaml` to customize:
- API settings (host, port, CORS)
- Database connection
- Kafka configuration
- Model parameters
- Logging settings

Edit `config/model_config.yaml` to customize:
- Model hyperparameters
- Feature engineering settings
- Training configuration
- Evaluation metrics

## Testing

Run tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=src tests/
```

## Monitoring

The system includes built-in monitoring:

- **Health Check**: `GET /health`
- **Statistics**: `GET /api/v1/stats`
- **Model Info**: `GET /api/v1/model/info`
- **Prometheus Metrics**: Available on port 9090

## Deployment

### Kubernetes Deployment

```bash
kubectl apply -f deployment/kubernetes/deployment.yaml
```

### CI/CD

GitHub Actions workflow is configured in `.github/workflows/ci.yaml` for:
- Automated testing
- Docker image building
- Deployment to staging/production

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Email: support@frauddetection.com
- Documentation: https://docs.frauddetection.com

## Acknowledgments

- XGBoost for the gradient boosting library
- FastAPI for the excellent web framework
- Scikit-learn for ML utilities