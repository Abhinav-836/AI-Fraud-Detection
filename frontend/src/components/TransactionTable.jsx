import React, { useState, useEffect } from 'react';
import { FaFlag, FaCheckCircle } from 'react-icons/fa';

const formatCurrency = (amount, currency = 'USD') => {
  if (amount === null || amount === undefined) return 'N/A';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, minimumFractionDigits: 2 }).format(amount);
};

const formatDate = (date) => {
  if (!date) return 'N/A';
  return new Date(date).toLocaleString();
};

const calculateRiskColor = (riskScore) => {
  if (riskScore >= 0.7) return '#ef4444';
  if (riskScore >= 0.4) return '#f59e0b';
  return '#10b981';
};

const TransactionTable = ({ predictions = [] }) => {
  const [transactions, setTransactions] = useState([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const sampleTransactions = [
      { id: 1, transactionId: 'TX001234', amount: 1250.00, currency: 'USD', date: new Date().toISOString(), merchant: 'TechStore Inc.', status: 'completed', riskScore: 0.85, riskLevel: 'high', flagged: true },
      { id: 2, transactionId: 'TX001235', amount: 45.50, currency: 'USD', date: new Date().toISOString(), merchant: 'Coffee Shop', status: 'completed', riskScore: 0.15, riskLevel: 'low', flagged: false },
      { id: 3, transactionId: 'TX001236', amount: 1200.00, currency: 'USD', date: new Date().toISOString(), merchant: 'Online Retailer', status: 'pending', riskScore: 0.65, riskLevel: 'medium', flagged: true },
    ];

    const predictionTransactions = predictions.map((pred, idx) => ({
      id: 100 + idx,
      transactionId: pred.transaction_id,
      amount: 0,
      currency: 'USD',
      date: pred.timestamp,
      merchant: 'API Transaction',
      status: pred.is_fraud ? 'flagged' : 'completed',
      riskScore: pred.fraud_probability,
      riskLevel: pred.risk_level,
      flagged: pred.is_fraud,
    }));

    setTransactions([...predictionTransactions, ...sampleTransactions]);
  }, [predictions]);

  const handleFlagTransaction = (id) => {
    setTransactions(transactions.map(tx => tx.id === id ? { ...tx, flagged: !tx.flagged } : tx));
  };

  const filteredTransactions = transactions.filter(tx => {
    if (filter === 'flagged') return tx.flagged;
    if (filter === 'safe') return !tx.flagged;
    return true;
  });

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Recent Transactions</h2>
        <div className="filter-buttons">
          <button className={`filter-btn ${filter === 'all' ? 'active' : ''}`} onClick={() => setFilter('all')}>All</button>
          <button className={`filter-btn ${filter === 'flagged' ? 'active' : ''}`} onClick={() => setFilter('flagged')}>Flagged</button>
          <button className={`filter-btn ${filter === 'safe' ? 'active' : ''}`} onClick={() => setFilter('safe')}>Safe</button>
        </div>
      </div>
      <div className="table-container">
        <table className="table">
          <thead><tr><th>ID</th><th>Merchant</th><th>Amount</th><th>Date</th><th>Risk</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            {filteredTransactions.map(tx => (
              <tr key={tx.id} className={tx.flagged ? 'flagged-row' : ''}>
                <td>{tx.transactionId}</td><td>{tx.merchant}</td><td>{formatCurrency(tx.amount)}</td><td>{formatDate(tx.date)}</td>
                <td><span className="risk-badge" style={{ backgroundColor: calculateRiskColor(tx.riskScore), color: 'white', padding: '4px 8px', borderRadius: '20px', fontSize: '11px' }}>{tx.riskLevel.toUpperCase()}</span></td>
                <td><span className={`status-badge status-${tx.status}`}>{tx.status}</span></td>
                <td><button className={`btn btn-sm ${tx.flagged ? 'btn-danger' : 'btn-primary'}`} onClick={() => handleFlagTransaction(tx.id)}>{tx.flagged ? <FaCheckCircle /> : <FaFlag />} {tx.flagged ? ' Unflag' : ' Flag'}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TransactionTable;