import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { FaHome, FaChartBar, FaCog } from 'react-icons/fa';
import HomePage from './pages/HomePage';
import AnalyticsPage from './pages/AnalyticsPage';
import SettingsPage from './pages/SettingsPage';
import './index.css';

function App() {
  return (
    <Router>
      <div className="App">
        <nav className="sidebar">
          <div className="sidebar-header">
            <h2>Fraud Detection</h2>
          </div>
          <ul className="sidebar-menu">
            <li>
              <Link to="/">
                <FaHome /> Dashboard
              </Link>
            </li>
            <li>
              <Link to="/analytics">
                <FaChartBar /> Analytics
              </Link>
            </li>
            <li>
              <Link to="/settings">
                <FaCog /> Settings
              </Link>
            </li>
          </ul>
        </nav>
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;