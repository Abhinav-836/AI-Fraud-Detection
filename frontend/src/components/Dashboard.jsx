import React from 'react';
import AlertPanel from './AlertPanel';
import FraudChart from './FraudChart';
import TransactionTable from './TransactionTable';

const Dashboard = () => {
  const stats = {
    totalTransactions: 12457,
    flaggedTransactions: 342,
    fraudRate: 2.7,
    resolvedCases: 289,
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Fraud Detection Dashboard</h1>
        <div className="stats-overview">
          <div className="stat-card">
            <h3>Total Transactions</h3>
            <p className="stat-value">{stats.totalTransactions.toLocaleString()}</p>
          </div>
          <div className="stat-card">
            <h3>Flagged Transactions</h3>
            <p className="stat-value warning">{stats.flaggedTransactions.toLocaleString()}</p>
          </div>
          <div className="stat-card">
            <h3>Fraud Rate</h3>
            <p className="stat-value danger">{stats.fraudRate}%</p>
          </div>
          <div className="stat-card">
            <h3>Resolved Cases</h3>
            <p className="stat-value success">{stats.resolvedCases.toLocaleString()}</p>
          </div>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="dashboard-row">
          <div className="dashboard-col">
            <AlertPanel />
          </div>
          <div className="dashboard-col">
            <FraudChart />
          </div>
        </div>
        <div className="dashboard-row">
          <div className="dashboard-col full-width">
            <TransactionTable />
          </div>
        </div>
      </div>

      <style jsx>{`
        .dashboard {
          padding: 24px;
        }
        
        .dashboard-header {
          margin-bottom: 32px;
        }
        
        .dashboard-header h1 {
          font-size: 28px;
          color: #2c3e50;
          margin-bottom: 24px;
        }
        
        .stats-overview {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 20px;
        }
        
        .stat-card {
          background: white;
          padding: 20px;
          border-radius: 12px;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
        }
        
        .stat-card h3 {
          font-size: 14px;
          color: #7f8c8d;
          margin-bottom: 8px;
          font-weight: 500;
        }
        
        .stat-value {
          font-size: 28px;
          font-weight: 600;
          color: #2c3e50;
        }
        
        .stat-value.warning {
          color: #f39c12;
        }
        
        .stat-value.danger {
          color: #e74c3c;
        }
        
        .stat-value.success {
          color: #27ae60;
        }
        
        .dashboard-content {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        
        .dashboard-row {
          display: flex;
          gap: 24px;
        }
        
        .dashboard-col {
          flex: 1;
        }
        
        .dashboard-col.full-width {
          flex: 100%;
        }
        
        @media (max-width: 768px) {
          .dashboard-row {
            flex-direction: column;
          }
          
          .stats-overview {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        
        @media (max-width: 480px) {
          .stats-overview {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default Dashboard;