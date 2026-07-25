import React from 'react';
import useTheme from '../hooks/useTheme';

// Keys match moveanalyzer.py's exact label strings (LABEL_* constants).
// Fixed across themes — these are semantic severity indicators, not chrome.
export const CLASSIFICATION_COLORS = {
  Brilliant: '#059669',
  Excellent: '#22c55e',
  Good: '#3b82f6',
  Book: '#6b7280',
  Inaccuracy: '#ca8a04',
  Mistake: '#ea580c',
  Blunder: '#dc2626',
  MissedWin: '#b91c1c',
};

const CLASSIFICATION_ICONS = {
  Brilliant: '!!',
  Excellent: '!',
  Good: '✓',
  Book: '[B]',
  Inaccuracy: '?!',
  Mistake: '??',
  Blunder: 'X',
  MissedWin: '/!\\',
};

export default function MoveHistoryPanel({ moves, selectedMove, onSelectMove }) {
  const { colors } = useTheme();
  const rounds = [];
  for (let i = 0; i < moves.length; i += 2) {
    rounds.push({ white: moves[i], black: moves[i + 1] });
  }

  const renderMove = (move) => {
    const color = CLASSIFICATION_COLORS[move.classification] || colors.textSecondary;
    const isSelected = selectedMove && selectedMove.ply === move.ply;
    return (
      <div
        role="button"
        tabIndex={0}
        aria-label={`Move ${move.ply}: ${move.san}, ${move.classification}`}
        aria-pressed={isSelected}
        onClick={() => onSelectMove(move)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onSelectMove(move);
          }
        }}
        style={{
          cursor: 'pointer', padding: '4px 6px', borderRadius: '4px',
          backgroundColor: isSelected ? '#fef9c3' : 'transparent',
          color: isSelected ? '#1f2937' : 'inherit',
        }}
      >
        <span style={{ fontFamily: 'monospace', color: isSelected ? '#1f2937' : colors.text }}>{move.san}</span>
        <span style={{ marginLeft: '8px', fontSize: '11px', color, fontWeight: 'bold' }}>
          {CLASSIFICATION_ICONS[move.classification] || ''} {move.classification}
        </span>
      </div>
    );
  };

  return (
    <div
      style={{ width: '260px', backgroundColor: colors.panelBg, borderLeft: `1px solid ${colors.border}`, padding: '16px', overflowY: 'auto' }}
      role="region"
      aria-label="Move history"
    >
      <h2 style={{ fontWeight: 'bold', fontSize: '18px', marginTop: 0, marginBottom: '16px', color: colors.text }}>Move History</h2>
      {moves.length === 0 ? (
        <p style={{ color: colors.textMuted, fontSize: '12px' }}>No moves yet</p>
      ) : (
        <div>
          {rounds.map((round, idx) => (
            <div key={idx} style={{ fontSize: '14px', borderBottom: `1px solid ${colors.borderLight}`, paddingBottom: '6px', marginBottom: '6px' }}>
              <div style={{ fontWeight: 'bold', color: colors.textSecondary }}>{idx + 1}.</div>
              {round.white && renderMove(round.white)}
              {round.black && <div style={{ marginLeft: '16px' }}>{renderMove(round.black)}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
