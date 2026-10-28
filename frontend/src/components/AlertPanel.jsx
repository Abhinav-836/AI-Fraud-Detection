import React, { useState } from 'react';
import { FaCheck, FaTimes } from 'react-icons/fa';
import fraudAPI from '../services/fraudApi';
import { useSettings } from '../context/SettingsContext';
import DecisionBadge, { DriverList } from './DecisionBadge';
import './AlertPanel.css';

// Review queue: flagged transactions without an analyst verdict yet.
// The old "Resolve" button only changed local state; now each verdict is
// stored by the API (POST /predictions/{id}/feedback) and used as a
// training label the next time the model is retrained.
const AlertPanel = ({ queue = [], onLabeled }) => {
  const { t, formatCurrency, formatDateTime, merchantName, countryName, formatPercent } = useSettings();
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [done, setDone] = useState({}); // hide immediately, before the next poll

  const label = async (id, isFraud) => {
    setBusy(id);
    setError(null);
    try {
      await fraudAPI.sendFeedback(id, isFraud);
      setDone((prev) => ({ ...prev, [id]: true }));
      if (onLabeled) onLabeled();
    } catch (err) {
      setError(t('queue.error', { message: err.message }));
    } finally {
      setBusy(null);
    }
  };

  const items = queue.filter((p) => !done[p.id]);

  return (
    <div className="alert-panel card">
      <div className="card-header">
        <h2 className="card-title">{t('queue.title')}</h2>
        <span className="alert-count">{t('queue.waiting', { n: items.length })}</span>
      </div>
      <p className="queue-hint">{t('queue.hint')}</p>
      {error && <div className="alert-danger-custom">{error}</div>}

      {items.length === 0 ? (
        <p className="muted-empty">{t('queue.empty')}</p>
      ) : (
        <div className="alerts-list">
          {items.map((p) => (
            <div key={p.id} className={`alert-item decision-${p.decision}`}>
              <div className="alert-header">
                <div className="alert-info">
                  <h4>
                    {formatCurrency(p.amount)} · {merchantName(p.merchant_category)} · {countryName(p.location_country)}
                  </h4>
                  <span className="alert-time">
                    {p.card_id && <span className="mono">{p.card_id}</span>} · {formatDateTime(p.timestamp)}
                  </span>
                </div>
                <div className="alert-score">
                  <DecisionBadge decision={p.decision} />
                  <span className="alert-prob">{formatPercent(p.probability)}</span>
                </div>
              </div>
              <DriverList drivers={p.drivers} max={3} className="alert-drivers" />
              <div className="alert-footer">
                <button className="btn btn-danger btn-sm" disabled={busy === p.id} onClick={() => label(p.id, true)}>
                  <FaTimes /> {t('queue.confirm')}
                </button>
                <button className="btn btn-success btn-sm" disabled={busy === p.id} onClick={() => label(p.id, false)}>
                  <FaCheck /> {t('queue.legit')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AlertPanel;
