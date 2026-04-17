import React, { useState, useEffect, useRef } from 'react';
import { FaPlug, FaPlay, FaStop, FaBell, FaShieldAlt } from 'react-icons/fa';
import './RealTimeMonitor.css';

const RealTimeMonitor = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats] = useState({ total: 0, fraud: 0 });
  const [isSimulating, setIsSimulating] = useState(false);
  const wsRef = useRef(null);
  const simulationInterval = useRef(null);

  const connectWebSocket = () => {
    const wsUrl = process.env.REACT_APP_WS_URL || 'ws://127.0.0.1:8000/ws/live';
    wsRef.current = new WebSocket(wsUrl);

    wsRef.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };

    wsRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    wsRef.current.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      setTimeout(connectWebSocket, 3000);
    };
  };

  const handleWebSocketMessage = (data) => {
    if (data.type === 'fraud_alert' || data.type === 'transaction_processed') {
      const newTransaction = {
        id: Date.now(),
        transactionId: data.transaction.transaction_id,
        amount: data.transaction.amount,
        isFraud: data.prediction.is_fraud,
        probability: data.prediction.fraud_probability,
        riskLevel: data.prediction.risk_level,
        factors: data.prediction.factors || [],
        timestamp: data.timestamp,
      };
      
      setTransactions(prev => [newTransaction, ...prev].slice(0, 50));
      setStats(prev => ({
        total: prev.total + 1,
        fraud: prev.fraud + (data.prediction.is_fraud ? 1 : 0)
      }));
    }
  };

  const startSimulation = () => {
    setIsSimulating(true);
    simulationInterval.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        const transaction = generateRandomTransaction();
        wsRef.current.send(JSON.stringify(transaction));
      }
    }, 2000);
  };

  const stopSimulation = () => {
    setIsSimulating(false);
    if (simulationInterval.current) {
      clearInterval(simulationInterval.current);
    }
  };

  const generateRandomTransaction = () => {
    const merchants = ['retail', 'food', 'travel', 'electronics', 'gambling', 'money_transfer', 'cryptocurrency'];
    const devices = ['web', 'mobile', 'tablet'];
    const locations = ['US', 'CA', 'UK', 'DE', 'FR', 'SG', 'JP'];
    const isHighRisk = Math.random() < 0.25;
    
    return {
      transaction_id: `RT_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`,
      amount: isHighRisk ? Math.random() * 8000 + 2000 : Math.random() * 800 + 20,
      merchant_category: merchants[Math.floor(Math.random() * merchants.length)],
      device_type: devices[Math.floor(Math.random() * devices.length)],
      location_country: locations[Math.floor(Math.random() * locations.length)],
      hour_of_day: new Date().getHours(),
      day_of_week: new Date().getDay(),
    };
  };

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (simulationInterval.current) clearInterval(simulationInterval.current);
    };
  }, []);

  const getRiskGradient = (riskLevel) => {
    switch(riskLevel) {
      case 'high': return 'linear-gradient(135deg, #ef4444, #dc2626)';
      case 'medium': return 'linear-gradient(135deg, #f59e0b, #d97706)';
      default: return 'linear-gradient(135deg, #10b981, #059669)';
    }
  };

  return (
    <div className="realtime-monitor">
      <div className="monitor-header">
        <div className="monitor-title">
          <FaShieldAlt className="title-icon" />
          <h2>Real-Time Fraud Monitor</h2>
          <div className={`connection-badge ${isConnected ? 'connected' : 'disconnected'}`}>
            <FaPlug />
            <span>{isConnected ? 'Live' : 'Offline'}</span>
          </div>
        </div>
        <button 
          className={`simulate-btn ${isSimulating ? 'active' : ''}`}
          onClick={isSimulating ? stopSimulation : startSimulation}
        >
          {isSimulating ? <FaStop /> : <FaPlay />}
          {isSimulating ? 'Stop Simulation' : 'Start Simulation'}
        </button>
      </div>

      <div className="monitor-stats">
        <div className="stat-item">
          <span className="stat-label">Total Processed</span>
          <span className="stat-number">{stats.total}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Fraud Detected</span>
          <span className="stat-number fraud">{stats.fraud}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Fraud Rate</span>
          <span className="stat-number">
            {stats.total > 0 ? ((stats.fraud / stats.total) * 100).toFixed(1) : 0}%
          </span>
        </div>
      </div>

      <div className="transactions-container">
        <div className="transactions-header">
          <h3>Live Transaction Stream</h3>
          {isSimulating && <div className="live-indicator">🔴 LIVE</div>}
        </div>
        
        <div className="transactions-list">
          {transactions.length === 0 ? (
            <div className="empty-state">
              <FaBell className="empty-icon" />
              <p>No transactions yet. Start simulation to see real-time data!</p>
            </div>
          ) : (
            transactions.map(tx => (
              <div key={tx.id} className={`transaction-card ${tx.isFraud ? 'fraud' : 'safe'}`}>
                <div className="card-header">
                  <div className="tx-id">{tx.transactionId}</div>
                  <div className="tx-time">{new Date(tx.timestamp).toLocaleTimeString()}</div>
                </div>
                <div className="card-body">
                  <div className="amount">${tx.amount.toFixed(2)}</div>
                  <div className="risk-badge" style={{ background: getRiskGradient(tx.riskLevel) }}>
                    {tx.riskLevel.toUpperCase()}
                  </div>
                  <div className="probability">{Math.round(tx.probability * 100)}% confidence</div>
                </div>
                {tx.isFraud && (
                  <div className="fraud-factors">
                    <strong>Risk Indicators:</strong>
                    <ul>
                      {tx.factors.map((factor, i) => (
                        <li key={i}>{factor}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default RealTimeMonitor;