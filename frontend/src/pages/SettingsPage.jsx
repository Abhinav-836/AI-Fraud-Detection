import React, { useState } from 'react';
import { FaSave, FaBell, FaShieldAlt, FaCog, FaToggleOn, FaToggleOff } from 'react-icons/fa';

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    notifications: {
      emailAlerts: true,
      pushNotifications: true,
      smsAlerts: false,
      highRiskOnly: true,
    },
    detection: {
      sensitivity: 'medium',
      autoBlockHighRisk: true,
      reviewMediumRisk: true,
      monitorNewAccounts: true,
      checkVelocity: true,
    },
    security: {
      twoFactorAuth: true,
      sessionTimeout: 30,
      ipWhitelist: ['192.168.1.1', '10.0.0.1'],
      apiRateLimit: 100,
    },
    preferences: {
      timezone: 'UTC',
      dateFormat: 'YYYY-MM-DD',
      language: 'en',
      theme: 'light',
    },
  });

  const [newIp, setNewIp] = useState('');

  const handleToggle = (category, field) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [field]: !prev[category][field]
      }
    }));
  };

  const handleInputChange = (category, field, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [field]: value
      }
    }));
  };

  const handleAddIp = () => {
    if (newIp && !settings.security.ipWhitelist.includes(newIp)) {
      setSettings(prev => ({
        ...prev,
        security: {
          ...prev.security,
          ipWhitelist: [...prev.security.ipWhitelist, newIp]
        }
      }));
      setNewIp('');
    }
  };

  const handleRemoveIp = (ip) => {
    setSettings(prev => ({
      ...prev,
      security: {
        ...prev.security,
        ipWhitelist: prev.security.ipWhitelist.filter(i => i !== ip)
      }
    }));
  };

  const handleSaveSettings = () => {
    alert('Settings saved successfully!');
    // In a real app, you would make an API call here
  };

  const ToggleButton = ({ enabled, onToggle }) => (
    <button 
      className="toggle-btn"
      onClick={onToggle}
      aria-label={enabled ? 'Disable' : 'Enable'}
    >
      {enabled ? <FaToggleOn className="toggle-icon enabled" /> : <FaToggleOff className="toggle-icon" />}
    </button>
  );

  return (
    <div className="settings-page container">
      <div className="page-header">
        <h1>Settings</h1>
        <button className="btn btn-primary" onClick={handleSaveSettings}>
          <FaSave /> Save Changes
        </button>
      </div>

      <div className="settings-sections">
        {/* Notifications Settings */}
        <div className="settings-section card">
          <div className="section-header">
            <FaBell className="section-icon" />
            <h2>Notifications</h2>
          </div>
          <div className="settings-grid">
            <div className="setting-item">
              <div className="setting-info">
                <h3>Email Alerts</h3>
                <p>Receive fraud alerts via email</p>
              </div>
              <ToggleButton 
                enabled={settings.notifications.emailAlerts}
                onToggle={() => handleToggle('notifications', 'emailAlerts')}
              />
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>Push Notifications</h3>
                <p>Real-time notifications on dashboard</p>
              </div>
              <ToggleButton 
                enabled={settings.notifications.pushNotifications}
                onToggle={() => handleToggle('notifications', 'pushNotifications')}
              />
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>SMS Alerts</h3>
                <p>Critical alerts via SMS</p>
              </div>
              <ToggleButton 
                enabled={settings.notifications.smsAlerts}
                onToggle={() => handleToggle('notifications', 'smsAlerts')}
              />
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>High Risk Only</h3>
                <p>Only notify for high-risk transactions</p>
              </div>
              <ToggleButton 
                enabled={settings.notifications.highRiskOnly}
                onToggle={() => handleToggle('notifications', 'highRiskOnly')}
              />
            </div>
          </div>
        </div>

        {/* Detection Settings */}
        <div className="settings-section card">
          <div className="section-header">
            <FaShieldAlt className="section-icon" />
            <h2>Fraud Detection</h2>
          </div>
          <div className="settings-grid">
            <div className="setting-item">
              <div className="setting-info">
                <h3>Sensitivity Level</h3>
                <p>Adjust fraud detection sensitivity</p>
              </div>
              <select 
                value={settings.detection.sensitivity}
                onChange={(e) => handleInputChange('detection', 'sensitivity', e.target.value)}
                className="setting-select"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>Auto-block High Risk</h3>
                <p>Automatically block high-risk transactions</p>
              </div>
              <ToggleButton 
                enabled={settings.detection.autoBlockHighRisk}
                onToggle={() => handleToggle('detection', 'autoBlockHighRisk')}
              />
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>Review Medium Risk</h3>
                <p>Flag medium-risk for manual review</p>
              </div>
              <ToggleButton 
                enabled={settings.detection.reviewMediumRisk}
                onToggle={() => handleToggle('detection', 'reviewMediumRisk')}
              />
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>Monitor New Accounts</h3>
                <p>Enhanced monitoring for new accounts</p>
              </div>
              <ToggleButton 
                enabled={settings.detection.monitorNewAccounts}
                onToggle={() => handleToggle('detection', 'monitorNewAccounts')}
              />
            </div>
          </div>
        </div>

        {/* Security Settings */}
        <div className="settings-section card">
          <div className="section-header">
            <FaCog className="section-icon" />
            <h2>Security</h2>
          </div>
          <div className="settings-grid">
            <div className="setting-item">
              <div className="setting-info">
                <h3>Two-Factor Authentication</h3>
                <p>Require 2FA for admin access</p>
              </div>
              <ToggleButton 
                enabled={settings.security.twoFactorAuth}
                onToggle={() => handleToggle('security', 'twoFactorAuth')}
              />
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>Session Timeout (minutes)</h3>
                <p>Auto-logout after inactivity</p>
              </div>
              <input 
                type="number"
                min="1"
                max="120"
                value={settings.security.sessionTimeout}
                onChange={(e) => handleInputChange('security', 'sessionTimeout', parseInt(e.target.value))}
                className="setting-input"
              />
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>API Rate Limit</h3>
                <p>Requests per minute</p>
              </div>
              <input 
                type="number"
                min="10"
                max="1000"
                value={settings.security.apiRateLimit}
                onChange={(e) => handleInputChange('security', 'apiRateLimit', parseInt(e.target.value))}
                className="setting-input"
              />
            </div>
            <div className="setting-item full-width">
              <div className="setting-info">
                <h3>IP Whitelist</h3>
                <p>Allowed IP addresses for admin access</p>
              </div>
              <div className="ip-list">
                <div className="ip-input-group">
                  <input 
                    type="text"
                    value={newIp}
                    onChange={(e) => setNewIp(e.target.value)}
                    placeholder="Enter IP address"
                    className="ip-input"
                  />
                  <button className="btn btn-primary" onClick={handleAddIp}>
                    Add IP
                  </button>
                </div>
                <div className="ip-tags">
                  {settings.security.ipWhitelist.map((ip, index) => (
                    <div key={index} className="ip-tag">
                      {ip}
                      <button 
                        className="ip-remove"
                        onClick={() => handleRemoveIp(ip)}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Preferences */}
        <div className="settings-section card">
          <div className="section-header">
            <FaCog className="section-icon" />
            <h2>Preferences</h2>
          </div>
          <div className="settings-grid">
            <div className="setting-item">
              <div className="setting-info">
                <h3>Timezone</h3>
                <p>Display times in your local timezone</p>
              </div>
              <select 
                value={settings.preferences.timezone}
                onChange={(e) => handleInputChange('preferences', 'timezone', e.target.value)}
                className="setting-select"
              >
                <option value="UTC">UTC</option>
                <option value="EST">EST</option>
                <option value="PST">PST</option>
                <option value="GMT">GMT</option>
              </select>
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>Date Format</h3>
                <p>Preferred date display format</p>
              </div>
              <select 
                value={settings.preferences.dateFormat}
                onChange={(e) => handleInputChange('preferences', 'dateFormat', e.target.value)}
                className="setting-select"
              >
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
              </select>
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>Language</h3>
                <p>Interface language</p>
              </div>
              <select 
                value={settings.preferences.language}
                onChange={(e) => handleInputChange('preferences', 'language', e.target.value)}
                className="setting-select"
              >
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </div>
            <div className="setting-item">
              <div className="setting-info">
                <h3>Theme</h3>
                <p>Color scheme</p>
              </div>
              <select 
                value={settings.preferences.theme}
                onChange={(e) => handleInputChange('preferences', 'theme', e.target.value)}
                className="setting-select"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .settings-page {
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
        
        .settings-sections {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        
        .settings-section {
          padding: 24px;
        }
        
        .section-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 24px;
          padding-bottom: 16px;
          border-bottom: 2px solid #f8f9fa;
        }
        
        .section-icon {
          color: #3498db;
          font-size: 24px;
        }
        
        .section-header h2 {
          font-size: 20px;
          color: #2c3e50;
          margin: 0;
        }
        
        .settings-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 20px;
        }
        
        .setting-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          border-radius: 8px;
          background-color: #f8f9fa;
          transition: background-color 0.2s;
        }
        
        .setting-item:hover {
          background-color: #e9ecef;
        }
        
        .setting-item.full-width {
          grid-column: 1 / -1;
          flex-direction: column;
          align-items: stretch;
          gap: 12px;
        }
        
        .setting-info h3 {
          font-size: 16px;
          color: #2c3e50;
          margin-bottom: 4px;
        }
        
        .setting-info p {
          font-size: 14px;
          color: #7f8c8d;
        }
        
        .toggle-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 8px;
          border-radius: 4px;
          transition: background-color 0.2s;
        }
        
        .toggle-btn:hover {
          background-color: rgba(0, 0, 0, 0.05);
        }
        
        .toggle-icon {
          font-size: 32px;
          color: #95a5a6;
        }
        
        .toggle-icon.enabled {
          color: #27ae60;
        }
        
        .setting-select,
        .setting-input {
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 14px;
          background: white;
          min-width: 120px;
        }
        
        .setting-input {
          width: 100px;
        }
        
        .ip-list {
          width: 100%;
        }
        
        .ip-input-group {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
        }
        
        .ip-input {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 14px;
        }
        
        .ip-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        
        .ip-tag {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 12px;
          background-color: #3498db;
          color: white;
          border-radius: 16px;
          font-size: 14px;
        }
        
        .ip-remove {
          background: none;
          border: none;
          color: white;
          cursor: pointer;
          font-size: 18px;
          padding: 0;
          width: 20px;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          transition: background-color 0.2s;
        }
        
        .ip-remove:hover {
          background-color: rgba(255, 255, 255, 0.2);
        }
        
        @media (max-width: 768px) {
          .settings-grid {
            grid-template-columns: 1fr;
          }
          
          .page-header {
            flex-direction: column;
            gap: 16px;
            align-items: flex-start;
          }
        }
      `}</style>
    </div>
  );
};

export default SettingsPage;