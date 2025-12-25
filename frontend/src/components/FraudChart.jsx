import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const FraudChart = () => {
  const data = [
    { date: 'Jan 1', fraudCases: 12, flagged: 45 },
    { date: 'Jan 2', fraudCases: 8, flagged: 38 },
    { date: 'Jan 3', fraudCases: 15, flagged: 52 },
    { date: 'Jan 4', fraudCases: 10, flagged: 42 },
    { date: 'Jan 5', fraudCases: 18, flagged: 60 },
    { date: 'Jan 6', fraudCases: 14, flagged: 48 },
    { date: 'Jan 7', fraudCases: 9, flagged: 35 },
  ];

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Fraud Trends</h2>
      </div>
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="fraudCases" stroke="#e74c3c" strokeWidth={2} />
            <Line type="monotone" dataKey="flagged" stroke="#3498db" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default FraudChart;