import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { LANGUAGES, TRANSLATIONS } from '../i18n/translations';

// App-wide preferences. The old Settings page kept theme/language in its own
// useState: nothing else in the app read those values, nothing applied them
// to the page, and they vanished on navigation. They now live here, are
// applied to <html>, and persist in localStorage.

export const STORAGE_KEY = 'fraud-dashboard-settings';

export const DEFAULT_SETTINGS = {
  theme: 'light',        // light | dark | auto
  language: 'en',        // key of LANGUAGES
  timezone: 'local',     // 'local' or an IANA zone
  dateFormat: 'locale',  // locale | YYYY-MM-DD | MM/DD/YYYY | DD/MM/YYYY
};

export const TIMEZONES = ['local', 'UTC', 'America/New_York', 'America/Los_Angeles', 'Europe/London', 'Europe/Berlin', 'Asia/Kolkata', 'Asia/Singapore'];
export const DATE_FORMATS = ['locale', 'YYYY-MM-DD', 'MM/DD/YYYY', 'DD/MM/YYYY'];

const readStored = () => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw);
    const merged = { ...DEFAULT_SETTINGS, ...parsed };
    if (!LANGUAGES[merged.language]) merged.language = 'en';
    if (!['light', 'dark', 'auto'].includes(merged.theme)) merged.theme = 'light';
    return merged;
  } catch {
    return DEFAULT_SETTINGS; // private mode / blocked storage
  }
};

const prefersDark = () =>
  typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;

const SettingsContext = createContext(null);

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(readStored);
  const [systemDark, setSystemDark] = useState(prefersDark);

  // Follow OS changes while "auto" is selected
  useEffect(() => {
    if (!window.matchMedia) return undefined;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = (e) => setSystemDark(e.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  const resolvedTheme = settings.theme === 'auto' ? (systemDark ? 'dark' : 'light') : settings.theme;

  // Apply to <html> so plain CSS ([data-theme="dark"] ...) can react
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', resolvedTheme);
    root.style.colorScheme = resolvedTheme; // native inputs, scrollbars, <select> menus
    root.setAttribute('lang', settings.language);
  }, [resolvedTheme, settings.language]);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // storage unavailable: settings still work for this session
    }
  }, [settings]);

  const updateSetting = useCallback((key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetSettings = useCallback(() => setSettings(DEFAULT_SETTINGS), []);

  const value = useMemo(() => {
    const lang = settings.language;
    const dict = TRANSLATIONS[lang] || TRANSLATIONS.en;
    const tz = settings.timezone === 'local' ? undefined : settings.timezone;

    const t = (key, vars) => {
      let text = dict[key] ?? TRANSLATIONS.en[key] ?? key;
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          text = text.split(`{${k}}`).join(String(v));
        });
      }
      return text;
    };

    const toDate = (input) => {
      const d = input instanceof Date ? input : new Date(input);
      return Number.isNaN(d.getTime()) ? null : d;
    };

    const formatTime = (input) => {
      const d = toDate(input);
      return d ? d.toLocaleTimeString(lang, { timeZone: tz }) : '—';
    };

    const formatDateTime = (input) => {
      const d = toDate(input);
      if (!d) return '—';
      if (settings.dateFormat === 'locale') return d.toLocaleString(lang, { timeZone: tz });

      const parts = Object.fromEntries(
        new Intl.DateTimeFormat('en-US', {
          timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit',
        }).formatToParts(d).map((p) => [p.type, p.value])
      );
      const date = settings.dateFormat
        .replace('YYYY', parts.year)
        .replace('MM', parts.month)
        .replace('DD', parts.day);
      return `${date} ${formatTime(d)}`;
    };

    const formatNumber = (n, options) =>
      n === null || n === undefined || Number.isNaN(Number(n)) ? '—' : Number(n).toLocaleString(lang, options);

    const formatCurrency = (n) => formatNumber(n, { style: 'currency', currency: 'USD' });

    const formatPercent = (ratio, digits = 1) =>
      formatNumber(ratio, { style: 'percent', minimumFractionDigits: digits, maximumFractionDigits: digits });

    const weekdayName = (apiDay) => {
      // API weekday: 0 = Monday. 2024-01-01 was a Monday.
      const d = new Date(Date.UTC(2024, 0, 1 + apiDay, 12));
      return d.toLocaleDateString(lang, { weekday: 'long', timeZone: 'UTC' });
    };

    let regionNames = null;
    try {
      regionNames = new Intl.DisplayNames([lang], { type: 'region' });
    } catch {
      regionNames = null;
    }
    const countryName = (code) => {
      if (!code) return '—';
      const iso = code === 'UK' ? 'GB' : code; // the API uses "UK"; ISO is "GB"
      try {
        return (regionNames && regionNames.of(iso)) || code;
      } catch {
        return code;
      }
    };

    const merchantName = (m) => {
      const key = `merchant.${m || 'unknown'}`;
      const out = t(key);
      return out === key ? m : out;
    };
    const lookup = (prefix, value, fallback) => {
      const key = `${prefix}.${value}`;
      const out = t(key);
      return out === key ? fallback : out;
    };
    const deviceName = (d) => lookup('device', d || 'unknown', d);
    const scenarioName = (s) => lookup('scenario', s, String(s || '').replace(/_/g, ' '));

    // Drivers come from the API as {key, params, text}. Render them in the
    // chosen language, localising the parameters (country, money, category).
    const driverText = (driver) => {
      if (!driver) return '';
      if (typeof driver === 'string') return driver;
      const p = driver.params || {};
      const vars = {
        ...p,
        amount: p.amount !== undefined ? formatCurrency(p.amount) : undefined,
        country: p.country ? countryName(p.country) : undefined,
        category: p.category ? merchantName(p.category) : undefined,
        device: p.device ? deviceName(p.device) : undefined,
        ratio: p.ratio !== undefined ? formatNumber(p.ratio, { maximumFractionDigits: 1 }) : undefined,
        minutes: p.minutes !== undefined ? formatNumber(p.minutes, { maximumFractionDigits: 1 }) : undefined,
      };
      Object.keys(vars).forEach((k) => vars[k] === undefined && delete vars[k]);
      const key = `driver.${driver.key || driver.feature}`;
      const out = t(key, vars);
      return out === key ? driver.text || driver.feature : out;
    };
    const modelName = (m) => {
      const key = `model.${m}`;
      const out = t(key);
      return out === key ? String(m || '—').replace(/_/g, ' ') : out;
    };

    return {
      settings,
      resolvedTheme,
      updateSetting,
      resetSettings,
      t,
      formatTime,
      formatDateTime,
      formatNumber,
      formatCurrency,
      formatPercent,
      weekdayName,
      countryName,
      merchantName,
      deviceName,
      scenarioName,
      driverText,
      modelName,
    };
  }, [settings, resolvedTheme, updateSetting, resetSettings]);

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error('useSettings must be used inside <SettingsProvider>');
  return ctx;
}
