import React, { useEffect, useState, useCallback } from 'react';
import { Chess } from 'chess.js';
import ChessBoard from './ChessBoard';
import EvaluationChart from './EvaluationChart';
import { CLASSIFICATION_COLORS } from './MoveHistoryPanel';
import useTheme from '../hooks/useTheme';
import useToast from '../hooks/useToast';
import Spinner from './Spinner';

const STARTING_FEN = new Chess().fen();
const emptyChess = new Chess(); // ChessBoard needs a chess.js instance to compute legal-move highlights; replay is read-only so it's never queried.

export default function GameHistoryModal({ isOpen, onClose, apiBase }) {
  const { colors } = useTheme();
  const toast = useToast();
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(false);
  const [replay, setReplay] = useState(null); // { ...game, moves } from /replay
  const [moveIndex, setMoveIndex] = useState(-1); // -1 = starting position

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetch(`${apiBase}/api/games/history`)
      .then((r) => r.json())
      .then((data) => setGames(data.games || []))
      .catch(() => toast.error('Could not load game history — check your connection.'))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, apiBase]);

  const openReplay = (gameId) => {
    fetch(`${apiBase}/api/games/history/${gameId}/replay`)
      .then((r) => r.json())
      .then((data) => {
        setReplay(data);
        setMoveIndex(-1);
      })
      .catch(() => toast.error('Could not load that game for replay.'));
  };

  const stepMove = useCallback((delta) => {
    setMoveIndex((i) => {
      if (!replay) return i;
      return Math.max(-1, Math.min(replay.moves.length - 1, i + delta));
    });
  }, [replay]);

  // Matches the shortcut HelpModal documents ("← / → Previous / next move
  // while replaying a game") - only active while a replay is actually open,
  // so it doesn't steal arrow keys from the game-list view or the rest of the app.
  useEffect(() => {
    if (!isOpen || !replay) return undefined;
    const onKeyDown = (e) => {
      if (e.key === 'ArrowLeft') { e.preventDefault(); stepMove(-1); }
      else if (e.key === 'ArrowRight') { e.preventDefault(); stepMove(1); }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, replay, stepMove]);

  const backToList = () => {
    setReplay(null);
    setMoveIndex(-1);
  };

  const handleClose = () => {
    setReplay(null);
    setMoveIndex(-1);
    onClose();
  };

  if (!isOpen) return null;

  const currentMove = replay && moveIndex >= 0 ? replay.moves[moveIndex] : null;
  const currentFen = currentMove ? currentMove.fen : STARTING_FEN;
  const navBtnStyle = (disabled) => ({
    backgroundColor: colors.panelBg, color: disabled ? colors.textMuted : colors.text, fontSize: '12px', fontWeight: 'bold',
    padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.border}`, cursor: disabled ? 'default' : 'pointer',
  });

  return (
    <div
      style={{
        position: 'fixed', inset: 0, backgroundColor: colors.overlayBg,
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="history-modal-title"
    >
      <div style={{
        backgroundColor: colors.cardBg, color: colors.text, borderRadius: '8px', padding: '24px', width: replay ? '640px' : '520px',
        maxHeight: '85vh', overflowY: 'auto', boxShadow: colors.shadowLg,
      }}>
        {!replay ? (
          <>
            <h2 id="history-modal-title" style={{ fontSize: '22px', fontWeight: 'bold', marginTop: 0, marginBottom: '16px' }}>Game History</h2>
            {loading ? (
              <Spinner label="Loading games..." />
            ) : games.length === 0 ? (
              <p style={{ color: colors.textMuted, fontSize: '13px' }}>No games stored yet — play a game or import from Chess.com.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {games.map((g) => (
                  <div
                    key={g.id}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 12px',
                      border: `1px solid ${colors.borderLight}`, borderRadius: '6px', fontSize: '13px',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 'bold' }}>{g.white} vs {g.black}</div>
                      <div style={{ color: colors.textSecondary, fontSize: '11px' }}>
                        {g.result || '*'} · {g.opening_name || 'Unknown opening'} · {g.source}
                        {g.date ? ` · ${g.date}` : ''}
                      </div>
                    </div>
                    <button
                      onClick={() => openReplay(g.id)}
                      aria-label={`Replay ${g.white} vs ${g.black}`}
                      style={{
                        backgroundColor: colors.accentBlue, color: 'white', fontWeight: 'bold', fontSize: '12px',
                        padding: '6px 12px', borderRadius: '6px', border: 'none', cursor: 'pointer',
                      }}
                    >
                      Replay
                    </button>
                  </div>
                ))}
              </div>
            )}
            <button
              onClick={handleClose}
              style={{
                width: '100%', marginTop: '16px', backgroundColor: colors.accentGray, color: 'white', fontWeight: 'bold',
                padding: '10px', borderRadius: '8px', border: 'none', cursor: 'pointer',
              }}
            >
              Close
            </button>
          </>
        ) : (
          <>
            <h2 style={{ fontSize: '18px', fontWeight: 'bold', marginTop: 0, marginBottom: '4px' }}>
              {replay.white} vs {replay.black}
            </h2>
            <p style={{ fontSize: '12px', color: colors.textSecondary, marginTop: 0, marginBottom: '16px' }}>
              {replay.result || '*'} · {replay.opening_name || 'Unknown opening'}
            </p>

            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '12px' }}>
              <ChessBoard chess={emptyChess} position={currentFen} selectedSquare={null} onSelectSquare={() => {}} onMove={() => {}} disabled />
            </div>

            <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginBottom: '12px' }} role="group" aria-label="Replay controls">
              <button onClick={() => setMoveIndex(-1)} disabled={moveIndex === -1} style={navBtnStyle(moveIndex === -1)}>⏮ Start</button>
              <button onClick={() => setMoveIndex((i) => Math.max(-1, i - 1))} disabled={moveIndex === -1} style={navBtnStyle(moveIndex === -1)}>◀ Prev</button>
              <span style={{ fontSize: '13px', alignSelf: 'center', color: colors.text }}>
                {moveIndex + 1} / {replay.moves.length}
              </span>
              <button
                onClick={() => setMoveIndex((i) => Math.min(replay.moves.length - 1, i + 1))}
                disabled={moveIndex >= replay.moves.length - 1}
                style={navBtnStyle(moveIndex >= replay.moves.length - 1)}
              >
                Next ▶
              </button>
              <button
                onClick={() => setMoveIndex(replay.moves.length - 1)}
                disabled={moveIndex >= replay.moves.length - 1}
                style={navBtnStyle(moveIndex >= replay.moves.length - 1)}
              >
                End ⏭
              </button>
            </div>

            {currentMove && (
              <div style={{ textAlign: 'center', marginBottom: '12px', fontSize: '13px' }}>
                <span style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>{currentMove.san}</span>
                {currentMove.classification && (
                  <span style={{ marginLeft: '8px', color: CLASSIFICATION_COLORS[currentMove.classification] || colors.textSecondary, fontWeight: 'bold' }}>
                    {currentMove.classification}
                  </span>
                )}
                {currentMove.eval != null && (
                  <span style={{ marginLeft: '8px', color: colors.textSecondary, fontFamily: 'monospace' }}>
                    {currentMove.eval > 0 ? '+' : ''}{currentMove.eval.toFixed(2)}
                  </span>
                )}
              </div>
            )}

            <EvaluationChart moves={replay.moves} analyzed={replay.analyzed} />

            <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
              <button
                onClick={backToList}
                style={{ flex: 1, backgroundColor: colors.panelBg, color: colors.text, fontWeight: 'bold', padding: '10px', borderRadius: '8px', border: `1px solid ${colors.border}`, cursor: 'pointer' }}
              >
                Back to List
              </button>
              <button
                onClick={handleClose}
                style={{ flex: 1, backgroundColor: colors.accentGray, color: 'white', fontWeight: 'bold', padding: '10px', borderRadius: '8px', border: 'none', cursor: 'pointer' }}
              >
                Close
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
