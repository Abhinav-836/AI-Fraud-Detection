import React, { useState, useEffect, useRef, useCallback } from 'react';
import { FaPlug, FaPlay, FaStop, FaBell, FaShieldAlt } from 'react-icons/fa';
import { WS_URL } from '../services/fraudApi';
import { useSettings } from '../context/SettingsContext';
import DecisionBadge, { DriverList } from './DecisionBadge';
import './RealTimeMonitor.css';

const RECONNECT_MS = 3000;
const SIM_INTERVAL_S = 1.0;
const PARENT_REFRESH_MS = 2000; // don't hammer the REST API on every streamed transaction
const MAX_ROWS = 50;

// The simulation now runs on the server: a population of customers with
// stable habits (home country, usual merchants, typical amounts) shops on a
// simulated clock, and fraud episodes (account takeover, card testing, ...)
// are injected at random. The browser only says start/stop. Because the
// server knows which transactions were injected fraud, each row shows
// whether the engine caught it — a live scorecard, not just a feed.
const RealTimeMonitor = ({ onTransactionScored }) => {
  const { t, formatTime, formatCurrency, formatPercent, merchantName, countryName, scenarioName } = useSettings();
  const [isConnected, setIsConnected] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats] = useState({ total: 0, flagged: 0, fraud: 0, caught: 0, legit: 0, falseAlarms: 0 });
  const [lastError, setLastError] = useState(null);

  const wsRef = useRef(null);
  const reconnectRef = useRef(null);
  const unmountedRef = useRef(false);
  const lastParentRefresh = useRef(0);
  const onScoredRef = useRef(onTransactionScored);
  onScoredRef.current = onTransactionScored;

  const notifyParent = () => {
    const now = Date.now();
    if (onScoredRef.current && now - lastParentRefresh.current > PARENT_REFRESH_MS) {
      lastParentRefresh.current = now;
      onScoredRef.current();
    }
  };

  const handleMessage = useCallback((data) => {
    if (data.type === 'error') {
      setLastError(data.message);
      return;
    }
    if (data.type === 'simulation') {
      setIsSimulating(data.state === 'started');
      return;
    }
    if (data.type !== 'fraud_alert' && data.type !== 'transaction_processed') return;

    const p = data.prediction;
    const flagged = p.decision !== 'approve';
    const truth = data.truth || null;
    const tx = {
      key: `${p.prediction_id || data.transaction.transaction_id}-${data.timestamp}`,
      transactionId: data.transaction.transaction_id,
      cardId: data.transaction.card_id,
      amount: Number(data.transaction.amount) || 0,
      merchant: data.transaction.merchant_category,
      country: data.transaction.location_country,
      decision: p.decision,
      flagged,
      probability: p.fraud_probability,
      drivers: p.drivers || [],
      truth,
      timestamp: data.timestamp,
    };
    setTransactions((prev) => [tx, ...prev].slice(0, MAX_ROWS));
    setStats((prev) => {
      const next = { ...prev, total: prev.total + 1, flagged: prev.flagged + (flagged ? 1 : 0) };
      if (truth) {
        if (truth.is_fraud) {
          next.fraud += 1;
          next.caught += flagged ? 1 : 0;
        } else {
          next.legit += 1;
          next.falseAlarms += flagged ? 1 : 0;
        }
      }
      return next;
    });
    notifyParent();
  }, []);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setLastError(null);
    };
    ws.onmessage = (event) => {
      try {
        handleMessage(JSON.parse(event.data));
      } catch (e) {
        console.error('Bad WebSocket message', e);
      }
    };
    ws.onerror = () => setIsConnected(false);
    ws.onclose = () => {
      setIsConnected(false);
      setIsSimulating(false); // the server stops the simulation with the socket
      // Only reconnect if this is still the active socket of a mounted
      // component (avoids leaked duplicate sockets after unmount/StrictMode).
      if (!unmountedRef.current && wsRef.current === ws) {
        reconnectRef.current = setTimeout(connect, RECONNECT_MS);
      }
    };
  }, [handleMessage]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      clearTimeout(reconnectRef.current);
      if (wsRef.current) wsRef.current.close();
      wsRef.current = null;
    };
  }, [connect]);

  const send = (msg) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  };

  const toggleSimulation = () => {
    if (isSimulating) send({ action: 'stop_simulation' });
    else send({ action: 'start_simulation', interval: SIM_INTERVAL_S });
  };

  const ratio = (a, b) => (b ? `${a} / ${b} (${formatPercent(a / b, 0)})` : '—');

  return (
    <div className="realtime-monitor">
      <div className="monitor-header">
        <div className="monitor-title">
          <FaShieldAlt className="title-icon" />
          <h2>{t('monitor.title')}</h2>
          <div className={`connection-badge ${isConnected ? 'connected' : 'disconnected'}`}>
            <FaPlug />
            <span>{t(isConnected ? 'monitor.live' : 'monitor.offline')}</span>
          </div>
        </div>
        <button
          className={`simulate-btn ${isSimulating ? 'active' : ''}`}
          onClick={toggleSimulation}
          disabled={!isConnected}
        >
          {isSimulating ? <FaStop /> : <FaPlay />}
          {t(isSimulating ? 'monitor.stop' : 'monitor.start')}
        </button>
      </div>

      {lastError && <div className="monitor-error">{t('monitor.rejected', { message: lastError })}</div>}

      <div className="monitor-stats">
        <div className="stat-item">
          <span className="stat-label">{t('monitor.total')}</span>
          <span className="stat-number">{stats.total}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">{t('monitor.flagged')}</span>
          <span className="stat-number fraud">{stats.flagged}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">{t('monitor.caught')}</span>
          <span className="stat-number">{ratio(stats.caught, stats.fraud)}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">{t('monitor.falseAlarms')}</span>
          <span className="stat-number">{ratio(stats.falseAlarms, stats.legit)}</span>
        </div>
      </div>

      <div className="transactions-container">
        <div className="transactions-header">
          <h3>{t('monitor.stream')}</h3>
          {isSimulating && <div className="live-indicator">{t('monitor.liveBadge')}</div>}
        </div>

        <div className="transactions-list">
          {transactions.length === 0 ? (
            <div className="empty-state">
              <FaBell className="empty-icon" />
              <p>{t(isConnected ? 'monitor.empty' : 'monitor.connecting')}</p>
            </div>
          ) : (
            transactions.map((tx) => (
              <div key={tx.key} className={`transaction-card decision-${tx.decision}`}>
                <div className="tx-header">
                  <div className="tx-id">
                    {tx.cardId && <span className="mono">{tx.cardId}</span>} · {merchantName(tx.merchant)} · {countryName(tx.country)}
                  </div>
                  <div className="tx-time">{formatTime(tx.timestamp)}</div>
                </div>
                <div className="tx-body">
                  <div className="amount">{formatCurrency(tx.amount)}</div>
                  <DecisionBadge decision={tx.decision} />
                  <div className="probability">{t('monitor.probability', { p: formatPercent(tx.probability) })}</div>
                </div>
                {tx.truth && tx.truth.is_fraud && (
                  <div className={`truth-tag ${tx.flagged ? 'caught' : 'missed'}`}>
                    {t('monitor.truthFraud', { scenario: scenarioName(tx.truth.scenario) })} —{' '}
                    {t(tx.flagged ? 'monitor.truthCaught' : 'monitor.truthMissed')}
                  </div>
                )}
                {tx.truth && !tx.truth.is_fraud && tx.flagged && (
                  <div className="truth-tag false-alarm">{t('monitor.falseAlarm')}</div>
                )}
                {tx.flagged && <DriverList drivers={tx.drivers} max={3} className="fraud-factors" />}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default RealTimeMonitor;
