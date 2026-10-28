import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FaChartLine, FaChartBar, FaGlobe, FaDownload, FaBrain, FaHeartbeat, FaRedo } from 'react-icons/fa';
import fraudAPI from '../services/fraudApi';
import { useSettings } from '../context/SettingsContext';
import './pages.css';

const SAMPLE = 1000;
const RETRAIN_POLL_MS = 3000;

const csvEscape = (v) => {
  const s = v === null || v === undefined ? '' : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

const downloadCsv = (rows) => {
  const cols = ['id', 'transaction_id', 'card_id', 'timestamp', 'amount', 'merchant_category', 'device_type',
    'location_country', 'probability', 'decision', 'label', 'drivers', 'source', 'model_type'];
  const value = (r, c) => (c === 'drivers' ? (r.drivers || []).map((d) => d.text).join('; ') : r[c]);
  const csv = [cols.join(','), ...rows.map((r) => cols.map((c) => csvEscape(value(r, c))).join(','))].join('\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = `fraud-predictions-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

const Metric = ({ label, value, hint }) => (
  <div className="metric">
    <h4>{label}</h4>
    <p className="metric-value">{value}</p>
    {hint && <p className="metric-hint">{hint}</p>}
  </div>
);

// Everything here comes from the API: stored predictions, the trained
// model's held-out test metrics, live monitoring and the feedback loop.
const AnalyticsPage = () => {
  const {
    t, formatNumber, formatPercent, formatCurrency, countryName, driverText, modelName,
  } = useSettings();
  const [predictions, setPredictions] = useState([]);
  const [stats, setStats] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [error, setError] = useState(false);
  const pollRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const [recent, s, info, mon] = await Promise.all([
        fraudAPI.getRecent({ limit: SAMPLE }),
        fraudAPI.getStats(),
        fraudAPI.getModelInfo(),
        fraudAPI.getMonitoring(),
      ]);
      setPredictions(recent);
      setStats(s);
      setModelInfo(info);
      setMonitoring(mon);
      setError(false);
      return mon;
    } catch {
      setError(true);
      return null;
    }
  }, []);

  useEffect(() => {
    load();
    return () => clearInterval(pollRef.current);
  }, [load]);

  const retrainState = monitoring && monitoring.retrain ? monitoring.retrain.state : 'idle';

  // While a retrain runs, poll until it finishes, then reload the new model's metrics
  useEffect(() => {
    clearInterval(pollRef.current);
    if (retrainState !== 'running') return undefined;
    pollRef.current = setInterval(async () => {
      const mon = await load();
      if (mon && mon.retrain && mon.retrain.state !== 'running') clearInterval(pollRef.current);
    }, RETRAIN_POLL_MS);
    return () => clearInterval(pollRef.current);
  }, [retrainState, load]);

  const startRetrain = async () => {
    try {
      await fraudAPI.retrain();
    } finally {
      load();
    }
  };

  const summary = useMemo(() => {
    const flagged = predictions.filter((p) => p.decision !== 'approve');
    const amounts = predictions.map((p) => Number(p.amount) || 0);
    const total = amounts.reduce((a, b) => a + b, 0);

    // Top drivers among flagged transactions, grouped by driver type
    const driverCounts = {};
    flagged.forEach((p) => (p.drivers || []).forEach((d) => {
      const key = d.feature || d.key;
      driverCounts[key] = driverCounts[key] || { count: 0, example: d };
      driverCounts[key].count += 1;
    }));
    const drivers = Object.entries(driverCounts)
      .sort((a, b) => b[1].count - a[1].count)
      .slice(0, 6)
      .map(([feature, v]) => ({ feature, count: v.count, example: v.example, share: v.count / flagged.length }));

    const byCountry = {};
    predictions.forEach((p) => {
      const c = p.location_country || '—';
      byCountry[c] = byCountry[c] || { total: 0, flagged: 0 };
      byCountry[c].total += 1;
      byCountry[c].flagged += p.decision !== 'approve' ? 1 : 0;
    });
    const countries = Object.entries(byCountry)
      .map(([code, v]) => ({ code, ...v, rate: v.flagged / v.total }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 8);

    return {
      n: predictions.length,
      flagRate: predictions.length ? flagged.length / predictions.length : 0,
      avgAmount: predictions.length ? total / predictions.length : 0,
      flaggedAmount: flagged.reduce((a, p) => a + (Number(p.amount) || 0), 0),
      drivers,
      countries,
    };
  }, [predictions]);

  const metrics = modelInfo && modelInfo.test_metrics;
  const n3 = (v) => formatNumber(v, { maximumFractionDigits: 3, minimumFractionDigits: 3 });
  const ms = (v) => (v === null || v === undefined ? '—' : `${formatNumber(v, { maximumFractionDigits: 1 })} ms`);

  // Generic label for a group of drivers ("Several transactions within an hour"),
  // falling back to the first example's text for unknown driver types
  const driverLabel = (d) => {
    const key = `driverGroup.${d.feature}`;
    const label = t(key);
    return label === key ? driverText(d.example) : label;
  };

  const scorecard = monitoring && monitoring.simulation_scorecard;
  const latency = monitoring && monitoring.latency_ms;
  const retrain = monitoring && monitoring.retrain;

  return (
    <div className="page container">
      <div className="page-header">
        <div>
          <h1>{t('analytics.title')}</h1>
          <p className="page-subtitle">
            {error ? t('analytics.apiOffline') : summary.n ? t('analytics.basedOn', { n: formatNumber(summary.n) }) : t('analytics.empty')}
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => downloadCsv(predictions)} disabled={!summary.n}>
          <FaDownload /> {t('analytics.export')}
        </button>
      </div>

      <div className="kpi-grid">
        {[
          ['dash.scored', formatNumber(stats ? stats.total_predictions : summary.n)],
          ['analytics.flagRate', formatPercent(summary.flagRate)],
          ['analytics.avgAmount', formatCurrency(summary.avgAmount)],
          ['analytics.flaggedAmount', formatCurrency(summary.flaggedAmount)],
        ].map(([key, value]) => (
          <div key={key} className="card kpi">
            <div className="kpi-label"><FaChartLine /> {t(key)}</div>
            <div className="kpi-value">{value}</div>
          </div>
        ))}
      </div>

      <div className="analytics-row">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FaChartBar /> {t('analytics.drivers')}</h3>
          </div>
          {summary.drivers.length === 0 ? (
            <p className="muted-empty">{t('queue.empty')}</p>
          ) : (
            <div className="patterns-list">
              {summary.drivers.map((d) => (
                <div key={d.feature} className="pattern-item">
                  <div className="pattern-header">
                    <span className="pattern-name">{driverLabel(d)}</span>
                    <span className="pattern-count">{t('analytics.cases', { n: formatNumber(d.count) })}</span>
                  </div>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${Math.round(d.share * 100)}%` }} />
                  </div>
                  <div className="pattern-percent">{formatPercent(d.share, 0)}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FaGlobe /> {t('analytics.regional')}</h3>
          </div>
          {summary.countries.length === 0 ? (
            <p className="muted-empty">{t('analytics.empty')}</p>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr><th>{t('analytics.country')}</th><th>{t('analytics.rate')}</th><th>{t('analytics.transactions')}</th></tr>
                </thead>
                <tbody>
                  {summary.countries.map((c) => (
                    <tr key={c.code}>
                      <td>{countryName(c.code)}</td>
                      <td><span className={`fraud-rate ${c.rate > 0.2 ? 'high' : 'low'}`}>{formatPercent(c.rate)}</span></td>
                      <td>{formatNumber(c.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title"><FaBrain /> {t('analytics.performance')}</h3>
        </div>
        {metrics ? (
          <>
            <p className="page-subtitle muted">
              {t('analytics.testSet', {
                model: modelName(modelInfo.model_type),
                rows: formatNumber(modelInfo.training_rows),
                source: modelInfo.data_source,
              })}
            </p>
            <div className="metrics-grid">
              <Metric label={t('analytics.prauc')} value={n3(metrics.auc_pr)} />
              <Metric label={t('analytics.rocauc')} value={n3(metrics.auc_roc)} />
              <Metric label={t('analytics.brier')} value={formatNumber(metrics.brier, { maximumFractionDigits: 4 })} />
              <Metric label={t('analytics.caught')} value={formatPercent(metrics.fraud_caught_rate)} />
              <Metric label={t('analytics.autoDeclined')} value={formatPercent(metrics.fraud_auto_declined_rate)} />
              <Metric label={t('analytics.declinePrecision')} value={formatPercent(metrics.decline_precision)} />
              <Metric label={t('analytics.reviewRate')} value={formatPercent(metrics.review_rate, 2)} />
            </div>
            {modelInfo.candidates && (
              <div className="candidates">
                <h4>{t('analytics.candidates')}</h4>
                <ul>
                  {Object.entries(modelInfo.candidates)
                    .sort((a, b) => b[1].val_pr_auc - a[1].val_pr_auc)
                    .map(([name, c]) => (
                      <li key={name} className={name === modelInfo.model_type ? 'chosen' : ''}>
                        <span>{modelName(name)}</span>
                        <span className="mono">{n3(c.val_pr_auc)}</span>
                      </li>
                    ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          <p className="muted-empty">{error ? t('analytics.apiOffline') : t('analytics.noModel')}</p>
        )}
      </div>

      <div className="analytics-row">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FaHeartbeat /> {t('analytics.monitoring')}</h3>
          </div>
          {monitoring ? (
            <div className="metrics-grid compact">
              <Metric
                label={t('analytics.latency')}
                value={latency && latency.p50 !== null ? `${ms(latency.p50)} / ${ms(latency.p95)} / ${ms(latency.p99)}` : '—'}
              />
              <Metric
                label={t('analytics.drift')}
                value={monitoring.score_drift_psi === null ? '—' : formatNumber(monitoring.score_drift_psi, { maximumFractionDigits: 3 })}
                hint={t(`analytics.drift.${monitoring.drift_status || 'none'}`)}
              />
              {scorecard && scorecard.fraud_total + scorecard.legit_total > 0 && (
                <Metric
                  label={t('analytics.scorecard')}
                  value={formatPercent(scorecard.fraud_total ? scorecard.fraud_caught / scorecard.fraud_total : 0, 0)}
                  hint={t('analytics.scorecardText', {
                    caught: formatNumber(scorecard.fraud_caught),
                    total: formatNumber(scorecard.fraud_total),
                    fp: formatNumber(scorecard.legit_flagged),
                    legit: formatNumber(scorecard.legit_total),
                  })}
                />
              )}
            </div>
          ) : (
            <p className="muted-empty">{t('analytics.apiOffline')}</p>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h3 className="card-title"><FaRedo /> {t('analytics.feedback')}</h3>
          </div>
          <div className="metrics-grid compact">
            <Metric label={t('analytics.labeledFraud')} value={formatNumber(stats ? stats.labeled_fraud : 0)} />
            <Metric label={t('analytics.labeledLegit')} value={formatNumber(stats ? stats.labeled_legit : 0)} />
          </div>
          <p className="muted queue-hint">{t('queue.hint')}</p>
          <button className="btn btn-primary" onClick={startRetrain} disabled={error || retrainState === 'running'}>
            <FaRedo /> {t('analytics.retrain')}
          </button>
          {retrainState === 'running' && <p className="setting-status">{t('analytics.retraining')}</p>}
          {retrainState === 'done' && retrain && (
            <p className="setting-status ok">
              {t('analytics.retrainDone', {
                model: modelName(retrain.model_type),
                prauc: n3(retrain.test_pr_auc),
                rows: formatNumber(retrain.feedback_rows),
              })}
            </p>
          )}
          {retrainState === 'failed' && retrain && (
            <p className="setting-status error">{t('analytics.retrainFailed', { error: retrain.error })}</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;
