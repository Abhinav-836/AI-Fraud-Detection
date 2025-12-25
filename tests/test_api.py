import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


class TestFraudAPI:
    """Test cases for Fraud Detection API"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns correct response"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_predict_single_transaction(self):
        """Test single transaction prediction"""
        transaction = {
            "transaction_id": "TEST_001",
            "amount": 150.50,
            "merchant_category": "retail",
            "device_type": "mobile",
            "location_country": "US",
            "hour_of_day": 14,
            "day_of_week": 3
        }
        
        response = client.post("/api/v1/predict", json=transaction)
        
        # May return 200 or 503 depending on model availability
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "transaction_id" in data
            assert "is_fraud" in data
            assert "fraud_probability" in data
            assert "risk_level" in data
            assert data["transaction_id"] == "TEST_001"
            assert data["risk_level"] in ["low", "medium", "high"]
    
    def test_predict_invalid_transaction(self):
        """Test prediction with invalid transaction data"""
        transaction = {
            "transaction_id": "TEST_002",
            "amount": -100,  # Invalid negative amount
            "merchant_category": "retail",
            "device_type": "mobile",
            "location_country": "US"
        }
        
        response = client.post("/api/v1/predict", json=transaction)
        assert response.status_code == 422  # Validation error
    
    def test_predict_batch(self):
        """Test batch prediction"""
        batch = {
            "transactions": [
                {
                    "transaction_id": "TEST_003",
                    "amount": 50.0,
                    "merchant_category": "food",
                    "device_type": "web",
                    "location_country": "UK"
                },
                {
                    "transaction_id": "TEST_004",
                    "amount": 500.0,
                    "merchant_category": "travel",
                    "device_type": "mobile",
                    "location_country": "US"
                }
            ]
        }
        
        response = client.post("/api/v1/predict/batch", json=batch)
        
        # May return 200 or 503 depending on model availability
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
    
    def test_get_statistics(self):
        """Test statistics endpoint"""
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_transactions" in data
        assert "fraud_detected" in data
    
    def test_get_model_info(self):
        """Test model info endpoint"""
        response = client.get("/api/v1/model/info")
        
        # May return 200 or 503 depending on model availability
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "model_type" in data
    
    def test_missing_required_fields(self):
        """Test prediction with missing required fields"""
        transaction = {
            "transaction_id": "TEST_005",
            "amount": 100.0
            # Missing other required fields
        }
        
        response = client.post("/api/v1/predict", json=transaction)
        assert response.status_code == 422