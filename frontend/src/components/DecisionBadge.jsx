import React from 'react';
import { useSettings } from '../context/SettingsContext';

// approve / review / decline — the three outcomes of the decision policy
const DecisionBadge = ({ decision }) => {
  const { t } = useSettings();
  const d = decision || 'approve';
  return <span className={`decision-badge decision-${d}`}>{t(`decision.${d}`)}</span>;
};

export const DriverList = ({ drivers = [], max = 4, className = '' }) => {
  const { driverText } = useSettings();
  if (!drivers.length) return null;
  return (
    <ul className={`driver-list ${className}`}>
      {drivers.slice(0, max).map((d) => (
        <li key={d.feature || d.key || d.text}>{driverText(d)}</li>
      ))}
    </ul>
  );
};

export default DecisionBadge;
