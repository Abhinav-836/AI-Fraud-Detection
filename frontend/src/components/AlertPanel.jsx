import React, { useState, useEffect } from 'react';
import { FaExclamationTriangle, FaCheckCircle, FaClock } from 'react-icons/fa';
import './AlertPanel.css';

const AlertPanel = () => {
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate API call
    setTimeout(() => {
      setAlerts([
        {
          id: 1,
          type: 'high',
          message: 'Unusual transaction pattern detected',
          timestamp: '2024-01-15 14:30:22',
          status: 'pending'
        },
        {
          id: 2,
          type: 'medium',
          message: 'Multiple failed login attempts',
          timestamp: '2024-01-15 13:45:10',
          status: 'investigating'
        },
        {
          id: 3,
          type: 'low',
          message: 'New device login detected',
          timestamp: '2024-01-15 12:20:45',
          status: 'resolved'
        },
        {
          id: 4,
          type: 'high',
          message: 'Suspicious withdrawal request',
          timestamp: '2024-01-15 11:15:33',
          status: 'pending'
        },
      ]);
      setIsLoading(false);
    }, 1000);
  }, []);

  const getAlertIcon = (type) => {
    switch (type) {
      case 'high':
        return <FaExclamationTriangle className="alert-icon high" />;
      case 'medium':
        return <FaExclamationTriangle className="alert-icon medium" />;
      case 'low':
        return <FaExclamationTriangle className="alert-icon low" />;
      default:
        return <FaExclamationTriangle className="alert-icon" />;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'resolved':
        return <FaCheckCircle className="status-icon resolved" />;
      case 'investigating':
        return <FaClock className="status-icon investigating" />;
      default:
        return <FaClock className="status-icon pending" />;
    }
  };

  const handleResolveAlert = (id) => {
    setAlerts(alerts.map(alert => 
      alert.id === id ? { ...alert, status: 'resolved' } : alert
    ));
  };

  if (isLoading) {
    return <div className="loading">Loading alerts...</div>;
  }

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
                <button 
                  className="btn btn-primary btn-sm"
                  onClick={() => handleResolveAlert(alert.id)}
                >
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

// AlertPanel.css
const styles = `
.alert-panel {
  height: 100%;
}

.alert-count {
  background-color: #e74c3c;
  color: white;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.alert-item {
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #ddd;
}

.alert-item.alert-high {
  border-left-color: #e74c3c;
  background-color: rgba(231, 76, 60, 0.05);
}

.alert-item.alert-medium {
  border-left-color: #f39c12;
  background-color: rgba(243, 156, 18, 0.05);
}

.alert-item.alert-low {
  border-left-color: #3498db;
  background-color: rgba(52, 152, 219, 0.05);
}

.alert-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.alert-icon {
  font-size: 20px;
  margin-top: 2px;
}

.alert-icon.high {
  color: #e74c3c;
}

.alert-icon.medium {
  color: #f39c12;
}

.alert-icon.low {
  color: #3498db;
}

.alert-info h4 {
  font-size: 16px;
  font-weight: 500;
  color: #2c3e50;
  margin-bottom: 4px;
}

.alert-time {
  font-size: 12px;
  color: #7f8c8d;
}

.alert-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-icon {
  font-size: 16px;
}

.status-icon.resolved {
  color: #27ae60;
}

.status-icon.investigating {
  color: #f39c12;
}

.status-icon.pending {
  color: #e74c3c;
}

.status-text {
  font-size: 14px;
  font-weight: 500;
}

.status-resolved {
  color: #27ae60;
}

.status-investigating {
  color: #f39c12;
}

.status-pending {
  color: #e74c3c;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 14px;
}
`;
