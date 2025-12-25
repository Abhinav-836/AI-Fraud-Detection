import React, { useState, useEffect } from 'react';
import { FaFlag, FaCheckCircle, FaTimesCircle } from 'react-icons/fa';
import { formatCurrency, formatDate, calculateRiskColor } from '../utils/helpers';
const TransactionTable = () => {
  const [transactions, setTransactions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setTransactions([
        {
          id: 1,
          transactionId: 'TX001234',
          amount: 1250.00,
          currency: 'USD',
          date: '2024-01-15T14:30:22Z',
          merchant: 'TechStore Inc.',
          category: 'electronics',
          status: 'completed',
          riskScore: 0.85,
          riskLevel: 'high',
          flagged: true,
        },
        {
          id: 2,
          transactionId: 'TX001235',
          amount: 45.50,
          currency: 'USD',
          date: '2024-01-15T13:45:10Z',
          merchant: 'Coffee Shop',
          category: 'food',
          status: 'completed',
          riskScore: 0.15,
          riskLevel: 'low',
          flagged: false,
        },
        {
          id: 3,
          transactionId: 'TX001236',
          amount: 1200.00,
          currency: 'USD',
          date: '2024-01-15T12:20:45Z',
          merchant: 'Online Retailer',
          category: 'shopping',
          status: 'pending',
          riskScore: 0.65,
          riskLevel: 'medium',
          flagged: true,
        },
      ]);
      setIsLoading(false);
    }, 1000);
  }, []);

  const handleFlagTransaction = (id) => {
    setTransactions(transactions.map(tx =>
      tx.id === id ? { ...tx, flagged: !tx.flagged } : tx
    ));
  };

  if (isLoading) {
    return <div className="loading">Loading transactions...</div>;
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Recent Transactions</h2>
      </div>
      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Transaction ID</th>
              <th>Merchant</th>
              <th>Amount</th>
              <th>Date</th>
              <th>Risk Level</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((transaction) => (
              <tr key={transaction.id}>
                <td>{transaction.transactionId}</td>
                <td>{transaction.merchant}</td>
                <td>{formatCurrency(transaction.amount, transaction.currency)}</td>
                <td>{formatDate(transaction.date)}</td>
                <td>
                  <span 
                    className="risk-badge" 
                    style={{ 
                      backgroundColor: calculateRiskColor(transaction.riskScore),
                      color: 'white',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      fontSize: '12px'
                    }}
                  >
                    {transaction.riskLevel.toUpperCase()}
                  </span>
                </td>
                <td>
                  <span className={`status-badge status-${transaction.status}`}>
                    {transaction.status}
                  </span>
                </td>
                <td>
                  <button 
                    className={`btn btn-sm ${transaction.flagged ? 'btn-danger' : 'btn-primary'}`}
                    onClick={() => handleFlagTransaction(transaction.id)}
                  >
                    {transaction.flagged ? <FaCheckCircle /> : <FaFlag />}
                    {transaction.flagged ? ' Unflag' : ' Flag'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TransactionTable;