import React, { useEffect, useState } from 'react';
import { FaShieldAlt, FaCog, FaUndo } from 'react-icons/fa';
import fraudAPI from '../services/fraudApi';
import { DATE_FORMATS, TIMEZONES, useSettings } from '../context/SettingsContext';
import { LANGUAGES } from '../i18n/translations';
import './pages.css';

const PRESETS = ['low', 'medium', 'high'];
const near = (a, b) => Math.abs(a - b) < 1e-6;

// Decision policy: approve below the review threshold, hold for an analyst
// between the two, decline above the decline threshold. The presets are
// computed from validation data at training time, so "High" means "catch
// ~90% of fraud" for THIS model, not an arbitrary 0.3 cut-off.
const SettingsPage = () => {
  const { settings, updateSetting, resetSettings, t, formatPercent, formatDateTime } = useSettings();
  const [policy, setPolicy] = useState(null);
  const [review, setReview] = useState('');
  const [decline, setDecline] = useState('');
  const [status, setStatus] = useState({ type: 'idle', message: '' });

  const applyResponse = (res) => {
    setPolicy(res);
    setReview(String(res.review_threshold));
    setDecline(String(res.decline_threshold));
  };

  useEffect(() => {
    let cancelled = false;
    fraudAPI.getPolicy()
      .then((res) => !cancelled && applyResponse(res))
      .catch(() => !cancelled && setStatus({ type: 'error', message: t('settings.apiOffline') }));
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const save = async (r, d) => {
    try {
      applyResponse(await fraudAPI.setPolicy(r, d));
      setStatus({ type: 'ok', message: t('settings.saved') });
    } catch (err) {
      setStatus({ type: 'error', message: err.message || t('settings.apiOffline') });
    }
  };

  const presets = (policy && policy.presets) || {};
  const level = policy
    ? PRESETS.find((k) => presets[k]
        && near(presets[k].review_threshold, policy.review_threshold)
        && near(presets[k].decline_threshold, policy.decline_threshold)) || 'custom'
    : '';

  const choosePreset = (k) => {
    if (presets[k]) save(presets[k].review_threshold, presets[k].decline_threshold);
  };

  const active = presets[level];

  return (
    <div className="page container">
      <div className="page-header">
        <div>
          <h1>{t('settings.title')}</h1>
          <p className="page-subtitle">{t('settings.autosave')}</p>
        </div>
        <button className="btn btn-secondary" onClick={resetSettings}>
          <FaUndo /> {t('settings.resetDefaults')}
        </button>
      </div>

      <div className="settings-sections">
        <section className="settings-section card">
          <div className="section-header">
            <FaShieldAlt className="section-icon" />
            <h2>{t('settings.detection')}</h2>
          </div>
          <div className="settings-grid">
            <div className="setting-item">
              <div className="setting-info">
                <h3>{t('settings.sensitivity')}</h3>
                <p>{t('settings.sensitivityDesc')}</p>
                {active && (
                  <p className="setting-preview">
                    {t('settings.presetInfo', {
                      recall: formatPercent(active.expected_recall, 0),
                      rate: formatPercent(active.expected_flag_rate, 1),
                    })}
                  </p>
                )}
              </div>
              <select
                className="setting-select"
                value={level}
                disabled={!policy || !Object.keys(presets).length}
                onChange={(e) => choosePreset(e.target.value)}
                aria-label={t('settings.sensitivity')}
              >
                {level === 'custom' && <option value="custom">{t('settings.sens.custom')}</option>}
                {level === '' && <option value="">—</option>}
                {PRESETS.filter((k) => presets[k]).map((k) => (
                  <option key={k} value={k}>{t(`settings.sens.${k}`)}</option>
                ))}
              </select>
            </div>

            <form
              className="setting-item threshold-form"
              onSubmit={(e) => { e.preventDefault(); save(parseFloat(review), parseFloat(decline)); }}
            >
              <div className="setting-info">
                <p>{t('settings.thresholdsDesc')}</p>
              </div>
              <div className="threshold-inputs">
                <label>
                  {t('settings.reviewThreshold')}
                  <input type="number" min="0" max="1" step="0.001" value={review}
                    disabled={!policy} onChange={(e) => setReview(e.target.value)} required />
                </label>
                <label>
                  {t('settings.declineThreshold')}
                  <input type="number" min="0" max="1" step="0.001" value={decline}
                    disabled={!policy} onChange={(e) => setDecline(e.target.value)} required />
                </label>
                <button type="submit" className="btn btn-primary" disabled={!policy}>{t('settings.apply')}</button>
              </div>
            </form>
          </div>
          <p className={`setting-status ${status.type}`}>
            {status.message || t('settings.thresholdNote')}
          </p>
        </section>

        <section className="settings-section card">
          <div className="section-header">
            <FaCog className="section-icon" />
            <h2>{t('settings.preferences')}</h2>
          </div>
          <div className="settings-grid">
            <div className="setting-item">
              <div className="setting-info">
                <h3>{t('settings.theme')}</h3>
                <p>{t('settings.themeDesc')}</p>
              </div>
              <select
                className="setting-select"
                value={settings.theme}
                onChange={(e) => updateSetting('theme', e.target.value)}
                aria-label={t('settings.theme')}
              >
                {['light', 'dark', 'auto'].map((v) => (
                  <option key={v} value={v}>{t(`settings.theme.${v}`)}</option>
                ))}
              </select>
            </div>

            <div className="setting-item">
              <div className="setting-info">
                <h3>{t('settings.language')}</h3>
                <p>{t('settings.languageDesc')}</p>
              </div>
              <select
                className="setting-select"
                value={settings.language}
                onChange={(e) => updateSetting('language', e.target.value)}
                aria-label={t('settings.language')}
              >
                {Object.entries(LANGUAGES).map(([code, name]) => (
                  <option key={code} value={code}>{name}</option>
                ))}
              </select>
            </div>

            <div className="setting-item">
              <div className="setting-info">
                <h3>{t('settings.timezone')}</h3>
                <p>{t('settings.timezoneDesc')}</p>
              </div>
              <select
                className="setting-select"
                value={settings.timezone}
                onChange={(e) => updateSetting('timezone', e.target.value)}
                aria-label={t('settings.timezone')}
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz === 'local' ? t('settings.timezone.local') : tz.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>

            <div className="setting-item">
              <div className="setting-info">
                <h3>{t('settings.dateFormat')}</h3>
                <p>{t('settings.dateFormatDesc')}</p>
                <p className="setting-preview">{formatDateTime(new Date())}</p>
              </div>
              <select
                className="setting-select"
                value={settings.dateFormat}
                onChange={(e) => updateSetting('dateFormat', e.target.value)}
                aria-label={t('settings.dateFormat')}
              >
                {DATE_FORMATS.map((f) => (
                  <option key={f} value={f}>{f === 'locale' ? t('settings.dateFormat.locale') : f}</option>
                ))}
              </select>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default SettingsPage;
