import React from 'react';
import useTheme from '../hooks/useTheme';

const SHORTCUTS = [
  ['Ctrl+N', 'New game'],
  ['Ctrl+I', 'Import from Chess.com'],
  ['Ctrl+H', 'Game history'],
  ['Ctrl+P', 'Puzzle mode'],
  ['← / →', 'Previous / next move (while replaying a game)'],
  ['Esc', 'Close the open dialog'],
  ['?', 'Show this help'],
];

export default function HelpModal({ isOpen, onClose }) {
  const { colors } = useTheme();
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed', inset: 0, backgroundColor: colors.overlayBg,
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="help-modal-title"
    >
      <div style={{ backgroundColor: colors.cardBg, color: colors.text, borderRadius: '8px', padding: '24px', width: '400px', boxShadow: colors.shadowLg }}>
        <h2 id="help-modal-title" style={{ fontSize: '20px', fontWeight: 'bold', marginTop: 0, marginBottom: '16px' }}>Keyboard Shortcuts</h2>
        <div>
          {SHORTCUTS.map(([key, desc]) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: `1px solid ${colors.borderLight}` }}>
              <kbd style={{
                fontFamily: 'monospace', backgroundColor: colors.panelBg, border: `1px solid ${colors.border}`,
                borderRadius: '4px', padding: '2px 8px', fontSize: '12px', fontWeight: 'bold',
              }}>
                {key}
              </kbd>
              <span style={{ fontSize: '13px', color: colors.textSecondary, textAlign: 'right' }}>{desc}</span>
            </div>
          ))}
        </div>
        <button
          onClick={onClose}
          style={{ width: '100%', marginTop: '16px', backgroundColor: colors.accentGray, color: 'white', fontWeight: 'bold', padding: '10px', borderRadius: '8px', border: 'none', cursor: 'pointer' }}
        >
          Close
        </button>
      </div>
    </div>
  );
}
