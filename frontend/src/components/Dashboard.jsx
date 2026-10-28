import React, { useCallback, useEffect, useState } from 'react';
import { FaShieldAlt, FaCheckCircle, FaSearch, FaBan, FaDatabase } from 'react-icons/fa';
import AlertPanel from './AlertPanel';
import FraudChart from './FraudChart';
import TransactionTable from './TransactionTable';
import TransactionForm from './TransactionForm';
import RealTimeMonitor from './RealTimeMonitor';
import fraudAPI from '../services/fraudApi';
import { useSettings } from '../context/SettingsContext';

const POLL_MS = 5000;

const EMPTY_STATS = { total_predictions: 0, approved: 0, in_review: 0, declined: 0, model_type: null };

const Dashboard = () => {
  const { t, formatNumber, formatPercent, formatTime, modelName } = useSettings();
  const [stats, setStats] = useState(EMPTY_STATS);
  const [recent, setRecent] = useState([]);
  const [queue, setQueue] = useState([]);
  const [apiStatus, setApiStatus] = useState('checking');
  const [lastUpdate, setLastUpdate] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [apiStats, recentPredictions, reviewQueue] = await Promise.all([
        fraudAPI.getStats(),
        fraudAPI.getRecent({ limit: 200 }),
        fraudAPI.getRecent({ limit: 20, flaggedOnly: true, unlabeledOnly: true }),
      ]);
      setStats(apiStats);
      setRecent(recentPredictions);
      setQueue(reviewQueue);
      setApiStatus('connected');
      setLastUpdate(new Date());
    } catch {
      setApiStatus('disconnected');
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  const total = stats.total_predictions || 0;
  const share = (n) => (total ? formatPercent(n / total) : '');

  const statCards = [
    { key: 'scored', title: t('dash.scored'), value: formatNumber(total), icon: <FaDatabase />, color: 'primary' },
    { key: 'approved', title: t('dash.approved'), value: formatNumber(stats.approved), sub: share(stats.approved), icon: <FaCheckCircle />, color: 'success' },
    { key: 'review', title: t('dash.review'), value: formatNumber(stats.in_review), sub: share(stats.in_review), icon: <FaSearch />, color: 'warning' },
    { key: 'declined', title: t('dash.declined'), value: formatNumber(stats.declined), sub: share(stats.declined), icon: <FaBan />, color: 'danger' },
    { key: 'model', title: t('dash.model'), value: stats.model_type ? modelName(stats.model_type) : '—', icon: <FaShieldAlt />, color: 'info' },
  ];

  const statusLabel = apiStatus === 'checking'
    ? t('dash.apiChecking')
    : apiStatus === 'connected' ? t('dash.apiConnected') : t('dash.apiDisconnected');

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">{t('dash.title')}</h1>
          <p className="dashboard-subtitle">{t('dash.subtitle')}</p>
        </div>
        <div className="api-status-badge">
          <span className={`status-dot ${apiStatus === 'connected' ? 'connected' : 'disconnected'}`}></span>
          {statusLabel}
        </div>
      </div>

      <div className="stats-grid">
        {statCards.map((stat) => (
          <div key={stat.key} className={`stat-card stat-card-${stat.color}`}>
            <div className="stat-icon">{stat.icon}</div>
            <div className="stat-info">
              <h3>{stat.title}</h3>
              <p className="stat-number">{stat.value}</p>
              {stat.sub && <p className="stat-sub">{stat.sub}</p>}
            </div>
          </div>
        ))}
      </div>

      <div className="dashboard-section">
        <RealTimeMonitor onTransactionScored={refresh} />
      </div>

      <div className="dashboard-row">
        <div className="dashboard-col">
          <TransactionForm onPredictionComplete={refresh} />
        </div>
        <div className="dashboard-col">
          <AlertPanel queue={queue} onLabeled={refresh} />
        </div>
      </div>

      <div className="dashboard-section">
        <FraudChart predictions={recent} />
      </div>

      <div className="dashboard-section">
        <TransactionTable predictions={recent} />
      </div>

      <div className="last-update">
        {lastUpdate ? t('dash.lastUpdated', { time: formatTime(lastUpdate) }) : t('dash.waiting')}
      </div>
    </div>
  );
};

export default Dashboard;
