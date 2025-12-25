// API Service for Fraud Detection Backend
// Location: frontend/src/services/fraudApi.js

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

class FraudDetectionAPI {
  /**
   * Check API health status
   */
  async checkHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return await response.json();
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  }

  /**
   * Get API configuration
   */
  async getConfig() {
    try {
      const response = await fetch(`${API_BASE_URL}/config`);
      return await response.json();
    } catch (error) {
      console.error('Config fetch failed:', error);
      throw error;
    }
  }

  /**
   * Predict fraud for a single transaction
   * @param {Object} transaction - Transaction data
   */
  async predictFraud(transaction) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(transaction),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Prediction failed:', error);
      throw error;
    }
  }

  /**
   * Predict fraud for multiple transactions
   * @param {Array} transactions - Array of transaction objects
   */
  async predictBatch(transactions) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/predict/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ transactions }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Batch prediction failed:', error);
      throw error;
    }
  }

  /**
   * Get fraud detection statistics
   */
  async getStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/stats`);
      return await response.json();
    } catch (error) {
      console.error('Stats fetch failed:', error);
      throw error;
    }
  }

  /**
   * Get model information
   */
  async getModelInfo() {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/model/info`);
      return await response.json();
    } catch (error) {
      console.error('Model info fetch failed:', error);
      throw error;
    }
  }
}

// Export singleton instance
const fraudAPI = new FraudDetectionAPI();
export default fraudAPI;

// Also export the class for testing
export { FraudDetectionAPI };