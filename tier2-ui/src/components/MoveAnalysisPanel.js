import React, { useEffect, useState } from 'react';
import { CLASSIFICATION_COLORS } from './MoveHistoryPanel';
import useTheme from '../hooks/useTheme';

/**
 * All data here comes from the move record already broadcast over the
 * WebSocket (see game_engine.py's move()) except the opening's overall
 * record, which is fetched on demand only when a book move is selected.
 */
export default function MoveAnalysisPanel({ selectedMove, apiBase }) {
  const { colors } = useTheme();
  const [openingRecord, setOpeningRecord] = useState(null);

  useEffect(() => {
    setOpeningRecord(null);
    if (selectedMove && selectedMove.eco) {
      fetch(`${apiBase}/api/openings/${encodeURIComponent(selectedMove.eco)}/analysis`)
        .then((r) => r.json())
        .then(setOpeningRecord)
        .catch(() => {});
    }
  }, [selectedMove, apiBase]);

  if (!selectedMove) {
    return (
      <div
        style={{ width: '280px', backgroundColor: colors.panelBg, borderRight: `1px solid ${colors.border}`, padding: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        role="region"
        aria-label="Move analysis"
      >
        <p style={{ color: colors.textMuted, fontSize: '13px', textAlign: 'center' }}>Click a move to see analysis</p>
      </div>
    );
  }

  const badgeColor = CLASSIFICATION_COLORS[selectedMove.classification] || colors.textSecondary;

  return (
    <div
      style={{ width: '280px', backgroundColor: colors.panelBg, borderRight: `1px solid ${colors.border}`, padding: '16px', overflowY: 'auto' }}
      role="region"
      aria-label="Move analysis"
    >
      <h2 style={{ fontWeight: 'bold', fontSize: '18px', marginTop: 0, marginBottom: '16px', color: colors.text }}>Move Analysis</h2>

      <div style={{ backgroundColor: badgeColor, color: 'white', padding: '12px', borderRadius: '8px', marginBottom: '16px', textAlign: 'center', fontWeight: 'bold' }}>
        {selectedMove.san} - {selectedMove.classification}
      </div>

      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '11px', fontWeight: 'bold', color: colors.textSecondary, marginBottom: '4px' }}>EVALUATION</div>
        {selectedMove.eval != null ? (
          <>
            <div style={{ fontSize: '22px', fontFamily: 'monospace', fontWeight: 'bold', color: colors.text }}>
              {selectedMove.eval > 0 ? '+' : ''}{selectedMove.eval.toFixed(2)}
            </div>
            <div style={{ fontSize: '11px', color: colors.textSecondary }}>
              {selectedMove.eval > 0 ? 'White advantage' : selectedMove.eval < 0 ? 'Black advantage' : 'Equal'}
            </div>
          </>
        ) : selectedMove.eval_mate != null ? (
          <div style={{ fontSize: '22px', fontFamily: 'monospace', fontWeight: 'bold', color: colors.text }}>
            Mate in {Math.abs(selectedMove.eval_mate)}
          </div>
        ) : (
          <div style={{ fontSize: '13px', color: colors.textMuted }}>Not available - move fell outside the engine's top candidates</div>
        )}
      </div>

      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '11px', fontWeight: 'bold', color: colors.textSecondary, marginBottom: '6px' }}>TOP ALTERNATIVES</div>
        {selectedMove.alternatives && selectedMove.alternatives.length > 0 ? (
          <div>
            {selectedMove.alternatives.map((alt, idx) => (
              <div
                key={idx}
                style={{
                  backgroundColor: colors.cardBg, padding: '6px 8px', borderRadius: '4px', fontSize: '13px',
                  border: `1px solid ${colors.borderLight}`, marginBottom: '4px', display: 'flex', justifyContent: 'space-between',
                }}
              >
                <span style={{ fontFamily: 'monospace', fontWeight: 'bold', color: colors.text }}>{alt.san}</span>
                <span style={{ fontFamily: 'monospace', color: colors.textSecondary }}>
                  {alt.eval != null ? (alt.eval > 0 ? '+' : '') + alt.eval.toFixed(2) : '-'}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: '12px', color: colors.textMuted }}>No alternatives recorded for this move.</p>
        )}
      </div>

      {selectedMove.eco ? (
        <div style={{ backgroundColor: colors.cardBg, padding: '10px', borderRadius: '6px', border: `1px solid ${colors.borderLight}`, fontSize: '13px' }}>
          <div style={{ fontWeight: 'bold', marginBottom: '6px', color: colors.text }}>Opening Context</div>
          <span style={{ display: 'inline-block', backgroundColor: colors.infoBg, color: colors.infoText, padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold' }}>
            Book: {selectedMove.opening_name} ({selectedMove.eco})
          </span>
          {openingRecord && openingRecord.total_games > 0 && (
            <p style={{ fontSize: '12px', color: colors.textSecondary, marginTop: '8px', marginBottom: 0 }}>
              You've played this line {openingRecord.total_games} time{openingRecord.total_games === 1 ? '' : 's'}
              {openingRecord.win_rate != null ? `, ${(openingRecord.win_rate * 100).toFixed(0)}% win rate` : ''}.
            </p>
          )}
        </div>
      ) : (
        <div style={{ fontSize: '12px', color: colors.textMuted }}>Outside known opening theory.</div>
      )}
    </div>
  );
}
