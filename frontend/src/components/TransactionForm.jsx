import React, { useState } from 'react';
import { FaShieldAlt, FaSync, FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa';

const API_BASE_URL = 'http://127.0.0.1:8000';

const TransactionForm = ({ onPredictionComplete }) => {
  const [formData, setFormData] = useState({
    transaction_id: `TXN_${Date.now()}`,
    amount: 250.00,
    merchant_category: 'retail',
    device_type: 'web',
    location_country: 'US',
    hour_of_day: new Date().getHours(),
    day_of_week: new Date().getDay(),
  });
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'amount' ? parseFloat(value) || 0 : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setPrediction(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      
      if (!response.ok) throw new Error('Prediction failed');
      
      const result = await response.json();
      setPrediction(result);
      if (onPredictionComplete) onPredictionComplete(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      transaction_id: `TXN_${Date.now()}`,
      amount: 250.00,
      merchant_category: 'retail',
      device_type: 'web',
      location_country: 'US',
      hour_of_day: new Date().getHours(),
      day_of_week: new Date().getDay(),
    });
    setPrediction(null);
    setError(null);
  };

  return (
    <div className="transaction-form-card">
      <div className="card-header">
        <h3 className="card-title">
          <FaShieldAlt /> Test Transaction
        </h3>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label>Transaction ID</label>
            <input type="text" name="transaction_id" value={formData.transaction_id} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label>Amount ($)</label>
            <input type="number" name="amount" value={formData.amount} onChange={handleChange} step="0.01" required />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Merchant Category</label>
            <select name="merchant_category" value={formData.merchant_category} onChange={handleChange}>
              <option value="retail">Retail</option>
              <option value="food">Food</option>
              <option value="travel">Travel</option>
              <option value="electronics">Electronics</option>
              <option value="gambling">Gambling (High Risk)</option>
              <option value="money_transfer">Money Transfer (High Risk)</option>
              <option value="cryptocurrency">Cryptocurrency (High Risk)</option>
            </select>
          </div>
          <div className="form-group">
            <label>Device Type</label>
            <select name="device_type" value={formData.device_type} onChange={handleChange}>
              <option value="web">Web/Desktop</option>
              <option value="mobile">Mobile</option>
              <option value="tablet">Tablet</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Location</label>
            <select name="location_country" value={formData.location_country} onChange={handleChange}>
              <option value="US">United States</option>
              <option value="CA">Canada</option>
              <option value="UK">United Kingdom</option>
              <option value="AU">Australia</option>
              <option value="DE">Germany (International)</option>
              <option value="FR">France (International)</option>
              <option value="SG">Singapore (International)</option>
            </select>
          </div>
          <div className="form-group">
            <label>Hour of Day</label>
            <input type="number" name="hour_of_day" value={formData.hour_of_day} onChange={handleChange} min="0" max="23" />
          </div>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Analyzing...' : 'Analyze Transaction'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={resetForm}>
            <FaSync /> Reset
          </button>
        </div>
      </form>

      {error && (
        <div className="alert-danger-custom">
          <FaExclamationTriangle /> Error: {error}
        </div>
      )}

      {prediction && (
        <div className={`prediction-result ${prediction.is_fraud ? 'fraud' : 'safe'}`}>
          <div className="result-header">
            {prediction.is_fraud ? <FaExclamationTriangle /> : <FaCheckCircle />}
            <span>{prediction.is_fraud ? 'FRAUD DETECTED' : 'SAFE TRANSACTION'}</span>
          </div>
          <div className="result-details">
            <div>Probability: {(prediction.fraud_probability * 100).toFixed(1)}%</div>
            <div>Risk Level: <span className={`risk-${prediction.risk_level}`}>{prediction.risk_level.toUpperCase()}</span></div>
            <div>Confidence: {(prediction.confidence * 100).toFixed(1)}%</div>
          </div>
          <div className="result-factors">
            <strong>Risk Factors:</strong>
            <ul>{prediction.factors.map((f, i) => <li key={i}>{f}</li>)}</ul>
          </div>
        </div>
      )}

      <style jsx>{`
        .transaction-form-card {
          background: white;
          border-radius: 20px;
          padding: 24px;
          box-shadow: var(--card-shadow);
        }
        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-bottom: 16px;
        }
        .form-group {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .form-group label {
          font-size: 12px;
          font-weight: 600;
          color: var(--gray);
        }
        .form-group input, .form-group select {
          padding: 10px 12px;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          font-size: 14px;
        }
        .form-actions {
          display: flex;
          gap: 12px;
          margin-top: 20px;
        }
        .btn-secondary {
          background: #f1f5f9;
          color: var(--dark);
        }
        .prediction-result {
          margin-top: 20px;
          padding: 16px;
          border-radius: 16px;
        }
        .prediction-result.fraud {
          background: linear-gradient(135deg, #fef2f2, #fee2e2);
          border-left: 4px solid #ef4444;
        }
        .prediction-result.safe {
          background: linear-gradient(135deg, #f0fdf4, #dcfce7);
          border-left: 4px solid #10b981;
        }
        .result-header {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 700;
          margin-bottom: 12px;
        }
        .result-details {
          display: flex;
          gap: 20px;
          margin-bottom: 12px;
          flex-wrap: wrap;
        }
        .risk-high { color: #dc2626; font-weight: 600; }
        .risk-medium { color: #f59e0b; font-weight: 600; }
        .risk-low { color: #10b981; font-weight: 600; }
        .result-factors ul {
          margin-top: 8px;
          padding-left: 20px;
          color: var(--danger);
        }
        .alert-danger-custom {
          margin-top: 16px;
          padding: 12px;
          background: #fef2f2;
          border-radius: 12px;
          color: #dc2626;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        @media (max-width: 640px) {
          .form-row { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
};

export default TransactionForm;