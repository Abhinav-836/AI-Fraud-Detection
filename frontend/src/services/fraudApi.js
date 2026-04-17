const API_BASE_URL = 'http://127.0.0.1:8000';

class FraudDetectionAPI {
  async checkHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return await response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      return { status: 'unhealthy' };
    }
  }

  async getStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/stats`);
      return await response.json();
    } catch (error) {
      console.error('Stats fetch failed:', error);
      return { total_predictions: 0, fraud_detected: 0 };
    }
  }

  async predictFraud(transaction) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(transaction),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Prediction failed');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Prediction error:', error);
      throw error;
    }
  }

  async testConnection() {
    try {
      const health = await this.checkHealth();
      return health.status === 'healthy' || health.status === 'running';
    } catch {
      return false;
    }
  }
}

const fraudAPI = new FraudDetectionAPI();
export default fraudAPI;