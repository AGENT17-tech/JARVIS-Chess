import React from 'react';
import useTheme from '../hooks/useTheme';

const THEME_OPTIONS = [
  ['system', 'Match system'],
  ['light', 'Light'],
  ['dark', 'Dark'],
];

const DEPTH_OPTIONS = [
  [5, 'Weakest'],
  [8, 'Easy'],
  [10, 'Balanced'],
  [12, 'Strong'],
  [15, 'Very strong'],
  [18, 'Expert'],
  [20, 'Strongest (slow)'],
];

export default function SettingsModal({ isOpen, onClose, settings, onUpdate }) {
  const { colors, mode, setMode } = useTheme();
  if (!isOpen) return null;

  const segmentedBtn = (active) => ({
    flex: 1, padding: '8px 12px', fontSize: '13px', fontWeight: 'bold', border: `1px solid ${colors.border}`,
    backgroundColor: active ? colors.accentBlue : colors.panelBg, color: active ? 'white' : colors.text,
    cursor: 'pointer',
  });

  return (
    <div
      style={{
        position: 'fixed', inset: 0, backgroundColor: colors.overlayBg,
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-modal-title"
    >
      <div style={{ backgroundColor: colors.cardBg, color: colors.text, borderRadius: '8px', padding: '24px', width: '420px', boxShadow: colors.shadowLg }}>
        <h2 id="settings-modal-title" style={{ fontSize: '20px', fontWeight: 'bold', marginTop: 0, marginBottom: '20px' }}>Settings</h2>

        <div style={{ marginBottom: '20px' }}>
          <h3 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', color: colors.textSecondary, marginBottom: '8px' }}>
            Appearance
          </h3>
          <div role="radiogroup" aria-label="Theme" style={{ display: 'flex', gap: '8px' }}>
            {THEME_OPTIONS.map(([value, label]) => (
              <button
                key={value}
                role="radio"
                aria-checked={mode === value}
                onClick={() => setMode(value)}
                style={{ ...segmentedBtn(mode === value), borderRadius: '6px' }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', color: colors.textSecondary, marginBottom: '8px' }}>
            New Game
          </h3>
          <label htmlFor="default-depth" style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
            Default engine depth
          </label>
          <select
            id="default-depth"
            value={settings.defaultDepth}
            onChange={(e) => onUpdate({ defaultDepth: Number(e.target.value) })}
            style={{
              width: '100%', padding: '8px 12px', border: `1px solid ${colors.border}`, borderRadius: '6px',
              backgroundColor: colors.inputBg, color: colors.text, fontSize: '13px', boxSizing: 'border-box',
            }}
          >
            {DEPTH_OPTIONS.map(([d, label]) => (
              <option key={d} value={d}>{d} — {label}</option>
            ))}
          </select>
          <p style={{ fontSize: '11px', color: colors.textMuted, marginTop: '6px', marginBottom: 0 }}>
            Applies the next time you start a new game. You can still adjust depth mid-game with the slider below the board.
          </p>
        </div>

        <button
          onClick={onClose}
          style={{ width: '100%', backgroundColor: colors.accentGray, color: 'white', fontWeight: 'bold', padding: '10px', borderRadius: '8px', border: 'none', cursor: 'pointer' }}
        >
          Close
        </button>
      </div>
    </div>
  );
}
