import React, { useState, useEffect } from 'react';
import { FaShieldAlt, FaChartLine, FaExclamationTriangle, FaCheckCircle, FaDatabase } from 'react-icons/fa';
import AlertPanel from './AlertPanel';
import FraudChart from './FraudChart';
import TransactionTable from './TransactionTable';
import TransactionForm from './TransactionForm';
import RealTimeMonitor from './RealTimeMonitor';
import fraudAPI from '../services/fraudApi';

const Dashboard = () => {
  const [stats, setStats] = useState({
    totalTransactions: 12457,
    flaggedTransactions: 342,
    fraudRate: 2.7,
    resolvedCases: 289,
    accuracy: 98.5,
  });
  const [apiStatus, setApiStatus] = useState('checking');
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    checkApiStatus();
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkApiStatus = async () => {
    try {
      const health = await fraudAPI.checkHealth();
      setApiStatus(health.status === 'healthy' || health.status === 'running' ? 'connected' : 'disconnected');
    } catch (error) {
      setApiStatus('disconnected');
    }
  };

  const fetchStats = async () => {
    try {
      const apiStats = await fraudAPI.getStats();
      setStats(prev => ({ ...prev, ...apiStats }));
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handlePredictionComplete = (prediction) => {
    setRecentPredictions(prev => [prediction, ...prev].slice(0, 10));
    fetchStats();
  };

  const statCards = [
    { title: 'Total Transactions', value: stats.totalTransactions.toLocaleString(), icon: <FaDatabase />, color: 'primary', change: '+12.5%', trend: 'up' },
    { title: 'Fraud Detected', value: stats.flaggedTransactions.toLocaleString(), icon: <FaExclamationTriangle />, color: 'danger', change: '-5.2%', trend: 'down' },
    { title: 'Fraud Rate', value: `${stats.fraudRate}%`, icon: <FaChartLine />, color: 'warning', change: '-0.3%', trend: 'down' },
    { title: 'Detection Accuracy', value: `${stats.accuracy}%`, icon: <FaShieldAlt />, color: 'success', change: '+1.8%', trend: 'up' },
    { title: 'Resolved Cases', value: stats.resolvedCases.toLocaleString(), icon: <FaCheckCircle />, color: 'success', change: '+8.3%', trend: 'up' },
  ];

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">Fraud Detection Dashboard</h1>
          <p className="dashboard-subtitle">Real-time monitoring and analytics for transaction security</p>
        </div>
        <div className="api-status-badge">
          <span className={`status-dot ${apiStatus === 'connected' ? 'connected' : 'disconnected'}`}></span>
          {apiStatus === 'connected' ? 'API Connected' : 'API Disconnected'}
        </div>
      </div>

      <div className="stats-grid">
        {statCards.map((stat, index) => (
          <div key={index} className={`stat-card stat-card-${stat.color}`}>
            <div className="stat-icon">{stat.icon}</div>
            <div className="stat-info">
              <h3>{stat.title}</h3>
              <p className="stat-number">{stat.value}</p>
              <span className={`stat-change ${stat.trend}`}>{stat.change}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="dashboard-section">
        <RealTimeMonitor />
      </div>

      <div className="dashboard-row">
        <div className="dashboard-col">
          <TransactionForm onPredictionComplete={handlePredictionComplete} />
        </div>
        <div className="dashboard-col">
          <FraudChart />
        </div>
      </div>

      <div className="dashboard-row">
        <div className="dashboard-col">
          <AlertPanel />
        </div>
        <div className="dashboard-col full-width">
          <TransactionTable predictions={recentPredictions} />
        </div>
      </div>

      <div className="last-update">Last updated: {lastUpdate.toLocaleTimeString()}</div>
    </div>
  );
};

export default Dashboard;