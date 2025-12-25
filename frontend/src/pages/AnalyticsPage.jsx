import React from 'react';
import { FaChartLine, FaChartBar, FaChartPie, FaDownload } from 'react-icons/fa';

const AnalyticsPage = () => {
  const analyticsData = {
    dailyStats: [
      { label: 'Total Transactions', value: '12,457', change: '+2.5%' },
      { label: 'Fraud Rate', value: '2.7%', change: '-0.3%' },
      { label: 'Avg. Transaction', value: '$245.67', change: '+1.8%' },
      { label: 'Response Time', value: '2.4s', change: '-12%' },
    ],
    topFraudPatterns: [
      { pattern: 'Unusual Location', count: 45, percent: 32 },
      { pattern: 'Velocity Spike', count: 38, percent: 27 },
      { pattern: 'Amount Anomaly', count: 29, percent: 21 },
      { pattern: 'Time Anomaly', count: 18, percent: 13 },
      { pattern: 'Device Change', count: 12, percent: 8 },
    ],
    regionalStats: [
      { region: 'North America', fraudRate: '3.2%', transactions: '5,432' },
      { region: 'Europe', fraudRate: '2.1%', transactions: '3,987' },
      { region: 'Asia', fraudRate: '1.8%', transactions: '2,543' },
      { region: 'Others', fraudRate: '4.1%', transactions: '495' },
    ],
  };

  return (
    <div className="analytics-page container">
      <div className="page-header">
        <h1>Analytics & Reports</h1>
        <button className="btn btn-primary">
          <FaDownload /> Export Report
        </button>
      </div>

      <div className="dashboard-grid">
        {analyticsData.dailyStats.map((stat, index) => (
          <div key={index} className="card">
            <div className="card-header">
              <h3 className="card-title">{stat.label}</h3>
              <FaChartLine className="stat-icon" />
            </div>
            <div className="stat-content">
              <p className="stat-value">{stat.value}</p>
              <p className={`stat-change ${stat.change.startsWith('+') ? 'positive' : 'negative'}`}>
                {stat.change} from yesterday
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="analytics-content">
        <div className="analytics-row">
          <div className="analytics-col">
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Top Fraud Patterns</h3>
                <FaChartBar className="stat-icon" />
              </div>
              <div className="patterns-list">
                {analyticsData.topFraudPatterns.map((pattern, index) => (
                  <div key={index} className="pattern-item">
                    <div className="pattern-header">
                      <span className="pattern-name">{pattern.pattern}</span>
                      <span className="pattern-count">{pattern.count} cases</span>
                    </div>
                    <div className="progress-bar">
                      <div 
                        className="progress-fill"
                        style={{ width: `${pattern.percent}%` }}
                      />
                    </div>
                    <div className="pattern-percent">{pattern.percent}%</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="analytics-col">
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Regional Fraud Analysis</h3>
                <FaChartPie className="stat-icon" />
              </div>
              <div className="regional-stats">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Region</th>
                      <th>Fraud Rate</th>
                      <th>Transactions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyticsData.regionalStats.map((region, index) => (
                      <tr key={index}>
                        <td>{region.region}</td>
                        <td>
                          <span className={`fraud-rate ${parseFloat(region.fraudRate) > 3 ? 'high' : 'low'}`}>
                            {region.fraudRate}
                          </span>
                        </td>
                        <td>{region.transactions}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <div className="analytics-row">
          <div className="card full-width">
            <div className="card-header">
              <h3 className="card-title">Performance Metrics</h3>
            </div>
            <div className="metrics-grid">
              <div className="metric">
                <h4>Detection Accuracy</h4>
                <p className="metric-value">94.7%</p>
                <p className="metric-desc">Correct fraud identification rate</p>
              </div>
              <div className="metric">
                <h4>False Positive Rate</h4>
                <p className="metric-value">1.2%</p>
                <p className="metric-desc">Legitimate transactions flagged as fraud</p>
              </div>
              <div className="metric">
                <h4>Avg. Investigation Time</h4>
                <p className="metric-value">18.4min</p>
                <p className="metric-desc">Time to investigate flagged transactions</p>
              </div>
              <div className="metric">
                <h4>Automated Resolution</h4>
                <p className="metric-value">68%</p>
                <p className="metric-desc">Cases resolved automatically</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .analytics-page {
          padding: 24px 0;
        }
        
        .page-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 32px;
        }
        
        .page-header h1 {
          font-size: 28px;
          color: #2c3e50;
        }
        
        .page-header button {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .stat-content {
          margin-top: 16px;
        }
        
        .stat-value {
          font-size: 32px;
          font-weight: 600;
          color: #2c3e50;
          margin-bottom: 8px;
        }
        
        .stat-change {
          font-size: 14px;
        }
        
        .stat-change.positive {
          color: #27ae60;
        }
        
        .stat-change.negative {
          color: #e74c3c;
        }
        
        .stat-icon {
          color: #3498db;
          font-size: 24px;
        }
        
        .analytics-content {
          margin-top: 32px;
        }
        
        .analytics-row {
          display: flex;
          gap: 24px;
          margin-bottom: 24px;
        }
        
        .analytics-col {
          flex: 1;
        }
        
        .full-width {
          flex: 100%;
        }
        
        .patterns-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        
        .pattern-item {
          padding: 12px;
          border-radius: 8px;
          background-color: #f8f9fa;
        }
        
        .pattern-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        
        .pattern-name {
          font-weight: 500;
          color: #2c3e50;
        }
        
        .pattern-count {
          font-size: 14px;
          color: #7f8c8d;
        }
        
        .progress-bar {
          height: 6px;
          background-color: #e9ecef;
          border-radius: 3px;
          margin: 8px 0;
          overflow: hidden;
        }
        
        .progress-fill {
          height: 100%;
          background-color: #3498db;
          border-radius: 3px;
        }
        
        .pattern-percent {
          font-size: 14px;
          color: #7f8c8d;
          text-align: right;
        }
        
        .regional-stats {
          margin-top: 16px;
        }
        
        .fraud-rate {
          padding: 4px 8px;
          border-radius: 4px;
          font-weight: 600;
        }
        
        .fraud-rate.high {
          background-color: rgba(231, 76, 60, 0.1);
          color: #e74c3c;
        }
        
        .fraud-rate.low {
          background-color: rgba(39, 174, 96, 0.1);
          color: #27ae60;
        }
        
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 24px;
          margin-top: 20px;
        }
        
        .metric {
          text-align: center;
          padding: 20px;
          border-radius: 8px;
          background-color: #f8f9fa;
        }
        
        .metric h4 {
          font-size: 16px;
          color: #7f8c8d;
          margin-bottom: 12px;
        }
        
        .metric-value {
          font-size: 32px;
          font-weight: 600;
          color: #2c3e50;
          margin-bottom: 8px;
        }
        
        .metric-desc {
          font-size: 14px;
          color: #95a5a6;
        }
        
        @media (max-width: 768px) {
          .analytics-row {
            flex-direction: column;
          }
          
          .page-header {
            flex-direction: column;
            gap: 16px;
            align-items: flex-start;
          }
          
          .metrics-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
};

export default AnalyticsPage;