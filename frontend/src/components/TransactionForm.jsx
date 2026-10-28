import React, { useState } from 'react';
import { FaShieldAlt, FaSync, FaCheckCircle, FaExclamationTriangle, FaBan } from 'react-icons/fa';
import fraudAPI, { apiDayOfWeek } from '../services/fraudApi';
import { useSettings } from '../context/SettingsContext';
import { DriverList } from './DecisionBadge';

// Same categories the simulator / model use
const MERCHANTS = [
  'grocery', 'restaurants', 'retail', 'fuel', 'utilities', 'entertainment', 'travel', 'health',
  'online_shopping', 'electronics', 'gift_cards', 'gambling', 'money_transfer', 'cryptocurrency',
];
const HIGH_RISK = new Set(['gift_cards', 'gambling', 'money_transfer', 'cryptocurrency']);
const DEVICES = ['pos', 'mobile', 'web', 'tablet'];
const COUNTRIES = ['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'IN', 'SG', 'BR', 'NG'];
const INT_FIELDS = new Set(['hour_of_day', 'day_of_week']);

const freshForm = (cardId = 'CARD_DEMO_001') => {
  const now = new Date();
  return {
    transaction_id: `TXN_${Date.now()}`,
    card_id: cardId,
    amount: 45.0,
    merchant_category: 'grocery',
    device_type: 'pos',
    location_country: 'US',
    hour_of_day: now.getHours(),
    day_of_week: apiDayOfWeek(now),
  };
};

const RESULT_ICON = {
  approve: <FaCheckCircle />,
  review: <FaExclamationTriangle />,
  decline: <FaBan />,
};

const TransactionForm = ({ onPredictionComplete }) => {
  const { t, weekdayName, countryName, merchantName, deviceName, formatPercent, modelName } = useSettings();
  const [formData, setFormData] = useState(() => freshForm());
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'amount' ? value : INT_FIELDS.has(name) ? (value === '' ? '' : parseInt(value, 10)) : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setPrediction(null);

    const payload = {
      ...formData,
      card_id: formData.card_id.trim() || null,
      amount: parseFloat(formData.amount),
      hour_of_day: formData.hour_of_day === '' ? null : formData.hour_of_day,
    };

    try {
      const result = await fraudAPI.predictFraud(payload);
      setPrediction(result);
      if (onPredictionComplete) onPredictionComplete(result);
      setFormData((prev) => ({ ...prev, transaction_id: `TXN_${Date.now()}` }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData(freshForm(formData.card_id));
    setPrediction(null);
    setError(null);
  };

  return (
    <div className="transaction-form-card card">
      <div className="card-header">
        <h3 className="card-title">
          <FaShieldAlt /> {t('form.title')}
        </h3>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label htmlFor="card_id">{t('form.card')}</label>
            <input id="card_id" type="text" name="card_id" value={formData.card_id} onChange={handleChange} maxLength={64} />
          </div>
          <div className="form-group">
            <label htmlFor="amount">{t('form.amount')}</label>
            <input id="amount" type="number" name="amount" value={formData.amount} onChange={handleChange} step="0.01" min="0.01" required />
          </div>
        </div>
        <p className="form-hint">{t('form.cardHint')}</p>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="merchant_category">{t('form.merchant')}</label>
            <select id="merchant_category" name="merchant_category" value={formData.merchant_category} onChange={handleChange}>
              {MERCHANTS.map((m) => (
                <option key={m} value={m}>
                  {merchantName(m)}{HIGH_RISK.has(m) ? ` (${t('form.highRisk')})` : ''}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="device_type">{t('form.device')}</label>
            <select id="device_type" name="device_type" value={formData.device_type} onChange={handleChange}>
              {DEVICES.map((d) => <option key={d} value={d}>{deviceName(d)}</option>)}
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="location_country">{t('form.location')}</label>
            <select id="location_country" name="location_country" value={formData.location_country} onChange={handleChange}>
              {COUNTRIES.map((c) => <option key={c} value={c}>{countryName(c)}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="hour_of_day">{t('form.hour')}</label>
            <input id="hour_of_day" type="number" name="hour_of_day" value={formData.hour_of_day} onChange={handleChange} min="0" max="23" step="1" />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="day_of_week">{t('form.day')}</label>
            <select id="day_of_week" name="day_of_week" value={formData.day_of_week} onChange={handleChange}>
              {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                <option key={i} value={i}>{weekdayName(i)}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="transaction_id">{t('form.id')}</label>
            <input id="transaction_id" type="text" name="transaction_id" value={formData.transaction_id} onChange={handleChange} required />
          </div>
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? t('form.analyzing') : t('form.analyze')}
          </button>
          <button type="button" className="btn btn-secondary" onClick={resetForm}>
            <FaSync /> {t('form.reset')}
          </button>
        </div>
      </form>

      {error && (
        <div className="alert-danger-custom">
          <FaExclamationTriangle /> {error}
        </div>
      )}

      {prediction && (
        <div className={`prediction-result decision-${prediction.decision}`}>
          <div className="result-header">
            {RESULT_ICON[prediction.decision]}
            <span>{t(`form.result.${prediction.decision}`)}</span>
          </div>
          <div className="result-details">
            <div>{t('form.probability')}: <strong>{formatPercent(prediction.fraud_probability)}</strong></div>
            <div>{t('form.model')}: {modelName(prediction.model_type)}</div>
          </div>
          <div className="result-factors">
            <strong>{t('form.reasons')}</strong>
            {prediction.decision !== 'approve' && prediction.drivers && prediction.drivers.length
              ? <DriverList drivers={prediction.drivers} />
              : <p className="muted">{t('form.noReasons')}</p>}
          </div>
        </div>
      )}
    </div>
  );
};

export default TransactionForm;
