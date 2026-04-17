import React, { useState, useEffect } from 'react';
import { FaExclamationTriangle, FaCheckCircle, FaClock } from 'react-icons/fa';
import './AlertPanel.css';

const AlertPanel = () => {
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setTimeout(() => {
      setAlerts([
        { id: 1, type: 'high', message: 'Unusual transaction pattern detected', timestamp: new Date().toLocaleString(), status: 'pending' },
        { id: 2, type: 'medium', message: 'Multiple failed login attempts', timestamp: new Date().toLocaleString(), status: 'investigating' },
        { id: 3, type: 'low', message: 'New device login detected', timestamp: new Date().toLocaleString(), status: 'resolved' },
        { id: 4, type: 'high', message: 'Suspicious withdrawal request', timestamp: new Date().toLocaleString(), status: 'pending' },
      ]);
      setIsLoading(false);
    }, 1000);
  }, []);

  const getAlertIcon = (type) => {
    switch (type) {
      case 'high': return <FaExclamationTriangle className="alert-icon high" />;
      case 'medium': return <FaExclamationTriangle className="alert-icon medium" />;
      default: return <FaExclamationTriangle className="alert-icon low" />;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'resolved': return <FaCheckCircle className="status-icon resolved" />;
      case 'investigating': return <FaClock className="status-icon investigating" />;
      default: return <FaClock className="status-icon pending" />;
    }
  };

  const handleResolveAlert = (id) => {
    setAlerts(alerts.map(alert => alert.id === id ? { ...alert, status: 'resolved' } : alert));
  };

  if (isLoading) return <div className="loading">Loading alerts...</div>;

  return (
    <div className="alert-panel card">
      <div className="card-header">
        <h2 className="card-title">Recent Alerts</h2>
        <span className="alert-count">{alerts.length} alerts</span>
      </div>
      <div className="alerts-list">
        {alerts.map((alert) => (
          <div key={alert.id} className={`alert-item alert-${alert.type}`}>
            <div className="alert-header">
              {getAlertIcon(alert.type)}
              <div className="alert-info">
                <h4>{alert.message}</h4>
                <span className="alert-time">{alert.timestamp}</span>
              </div>
            </div>
            <div className="alert-footer">
              <div className="alert-status">
                {getStatusIcon(alert.status)}
                <span className={`status-text status-${alert.status}`}>
                  {alert.status.charAt(0).toUpperCase() + alert.status.slice(1)}
                </span>
              </div>
              {alert.status !== 'resolved' && (
                <button className="btn btn-primary btn-sm" onClick={() => handleResolveAlert(alert.id)}>
                  Resolve
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AlertPanel;