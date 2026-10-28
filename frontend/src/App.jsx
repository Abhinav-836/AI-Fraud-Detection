import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, NavLink } from 'react-router-dom';
import { FaHome, FaChartBar, FaCog } from 'react-icons/fa';
import HomePage from './pages/HomePage';
import AnalyticsPage from './pages/AnalyticsPage';
import SettingsPage from './pages/SettingsPage';
import { useSettings } from './context/SettingsContext';
import './index.css';

// NavLink (not Link) so the `.sidebar-menu a.active` style actually applies,
// and labels wrapped in <span> so the 768px media query that hides
// `.sidebar-menu a span` can collapse the sidebar to icons.
const NAV = [
  { to: '/', labelKey: 'nav.dashboard', icon: <FaHome />, end: true },
  { to: '/analytics', labelKey: 'nav.analytics', icon: <FaChartBar /> },
  { to: '/settings', labelKey: 'nav.settings', icon: <FaCog /> },
];

function App() {
  const { t } = useSettings();

  return (
    <Router>
      <div className="App">
        <nav className="sidebar">
          <div className="sidebar-header">
            <h2>{t('app.title')}</h2>
          </div>
          <ul className="sidebar-menu">
            {NAV.map(({ to, labelKey, icon, end }) => (
              <li key={to}>
                <NavLink to={to} end={end}>
                  {icon} <span>{t(labelKey)}</span>
                </NavLink>
              </li>
            ))}
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