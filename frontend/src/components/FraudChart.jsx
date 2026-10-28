import React, { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useSettings } from '../context/SettingsContext';

// Bucket the API's recent predictions per minute (flagged = review + decline).
const bucketByMinute = (predictions) => {
  const buckets = new Map();
  predictions.forEach((p) => {
    const t = new Date(p.timestamp);
    if (Number.isNaN(t.getTime())) return;
    t.setSeconds(0, 0);
    const key = t.getTime();
    const b = buckets.get(key) || { time: key, scored: 0, flagged: 0 };
    b.scored += 1;
    b.flagged += p.decision && p.decision !== 'approve' ? 1 : 0;
    buckets.set(key, b);
  });
  return [...buckets.values()].sort((a, b) => a.time - b.time);
};

const FraudChart = ({ predictions = [] }) => {
  const { t, settings, resolvedTheme } = useSettings();
  const tz = settings.timezone === 'local' ? undefined : settings.timezone;

  const data = useMemo(
    () => bucketByMinute(predictions).map((b) => ({
      ...b,
      label: new Date(b.time).toLocaleTimeString(settings.language, { hour: '2-digit', minute: '2-digit', timeZone: tz }),
    })),
    [predictions, settings.language, tz]
  );

  // SVG chart colours don't come from CSS, so pick them per theme
  const dark = resolvedTheme === 'dark';
  const axis = dark ? '#9ca3af' : '#64748b';
  const grid = dark ? 'rgba(255,255,255,0.08)' : '#e2e8f0';
  const tooltipStyle = dark
    ? { background: '#111827', border: '1px solid #374151', color: '#e5e7eb' }
    : { background: '#ffffff', border: '1px solid #e2e8f0', color: '#0f172a' };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">{t('chart.title')}</h2>
      </div>
      {data.length === 0 ? (
        <p className="muted-empty">{t('chart.empty')}</p>
      ) : (
        <div style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke={grid} />
              <XAxis dataKey="label" stroke={axis} />
              <YAxis allowDecimals={false} stroke={axis} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              <Line type="monotone" dataKey="scored" name={t('chart.scored')} stroke="#3b82f6" strokeWidth={2} />
              <Line type="monotone" dataKey="flagged" name={t('chart.flagged')} stroke="#ef4444" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default FraudChart;
