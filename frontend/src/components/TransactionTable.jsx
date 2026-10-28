import React, { useState } from 'react';
import { useSettings } from '../context/SettingsContext';
import DecisionBadge from './DecisionBadge';

const MAX_ROWS = 25;
const FILTERS = {
  all: () => true,
  flagged: (p) => p.decision !== 'approve',
  approved: (p) => p.decision === 'approve',
};

// Read-only history of what the engine decided. Analyst verdicts are given
// in the Review Queue and shown here in the "Analyst label" column (they
// come from the database, so they survive refreshes and restarts).
const TransactionTable = ({ predictions = [] }) => {
  const { t, formatCurrency, formatDateTime, formatPercent, merchantName } = useSettings();
  const [filter, setFilter] = useState('all');

  const rows = predictions.filter(FILTERS[filter]).slice(0, MAX_ROWS);

  const labelCell = (label) => {
    if (label === true) return <span className="label-chip label-fraud">{t('label.fraud')}</span>;
    if (label === false) return <span className="label-chip label-legit">{t('label.legit')}</span>;
    return <span className="muted">{t('label.none')}</span>;
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">{t('table.title')}</h2>
        <div className="filter-buttons">
          {Object.keys(FILTERS).map((f) => (
            <button key={f} className={`filter-btn ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
              {t(`table.${f}`)}
            </button>
          ))}
        </div>
      </div>

      {rows.length === 0 ? (
        <p className="muted-empty">{t('table.empty')}</p>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>{t('table.card')}</th><th>{t('table.merchant')}</th><th>{t('table.amount')}</th>
                <th>{t('table.time')}</th><th>{t('table.probability')}</th><th>{t('table.decision')}</th>
                <th>{t('table.label')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((tx) => (
                <tr key={tx.id} className={tx.decision !== 'approve' ? 'flagged-row' : ''}>
                  <td className="mono">{tx.card_id || '—'}</td>
                  <td>{merchantName(tx.merchant_category)}</td>
                  <td>{formatCurrency(tx.amount)}</td>
                  <td className="nowrap">{formatDateTime(tx.timestamp)}</td>
                  <td>{formatPercent(tx.probability)}</td>
                  <td><DecisionBadge decision={tx.decision} /></td>
                  <td>{labelCell(tx.label)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default TransactionTable;
