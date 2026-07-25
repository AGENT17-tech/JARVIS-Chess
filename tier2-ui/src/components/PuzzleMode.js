import React, { useEffect, useState } from 'react';
import { Chess } from 'chess.js';
import ChessBoard from './ChessBoard';
import Spinner from './Spinner';
import useTheme from '../hooks/useTheme';

/**
 * Pulls a random puzzle from lichess.org (via GET /api/puzzle/random —
 * api_server.py's _puzzle_from_lichess) and checks the player's first move
 * against `solution_move`. lichess puzzles can chain further forced moves
 * beyond that; this only checks the single key move, not the full
 * continuation — see the docstring on _puzzle_from_lichess for why.
 */
export default function PuzzleMode({ isOpen, onClose, apiBase }) {
  const { colors } = useTheme();
  const [chess] = useState(() => new Chess());
  const [puzzle, setPuzzle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null); // 'correct' | 'incorrect' | null
  const [error, setError] = useState(null);
  const [selectedSquare, setSelectedSquare] = useState(null);
  const [stats, setStats] = useState(null);

  const fetchStats = () => {
    fetch(`${apiBase}/api/puzzle/stats`).then((r) => r.json()).then(setStats).catch(() => {});
  };

  const fetchPuzzle = () => {
    setLoading(true);
    setFeedback(null);
    setError(null);
    setSelectedSquare(null);
    fetch(`${apiBase}/api/puzzle/random`)
      .then(async (r) => {
        if (!r.ok) {
          const body = await r.json().catch(() => ({}));
          throw new Error(body.detail || 'Failed to fetch a puzzle');
        }
        return r.json();
      })
      .then((data) => {
        chess.load(data.fen);
        setPuzzle(data);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (isOpen) {
      fetchPuzzle();
      fetchStats();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const handleMove = (uci) => {
    if (!puzzle || feedback === 'correct') return;
    const correct = uci === puzzle.solution_move;
    setFeedback(correct ? 'correct' : 'incorrect');
    setSelectedSquare(null);
    fetch(`${apiBase}/api/puzzle/solved`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ puzzle_id: puzzle.id, correct }),
    })
      .then(fetchStats)
      .catch(() => {});
  };

  const handleClose = () => {
    setPuzzle(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed', inset: 0, backgroundColor: colors.overlayBg,
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="puzzle-modal-title"
    >
      <div style={{
        backgroundColor: colors.cardBg, color: colors.text, borderRadius: '8px', padding: '24px', width: '440px',
        boxShadow: colors.shadowLg, textAlign: 'center',
      }}>
        <h2 id="puzzle-modal-title" style={{ fontSize: '22px', fontWeight: 'bold', marginTop: 0, marginBottom: '4px' }}>Puzzle Mode</h2>
        <p style={{ fontSize: '12px', color: colors.textSecondary, marginTop: 0, marginBottom: '16px' }}>
          Find the best move. Puzzles from lichess.org.
        </p>

        {stats && stats.total > 0 && (
          <p style={{ fontSize: '12px', color: colors.text, marginBottom: '16px' }}>
            {stats.correct}/{stats.total} solved ({(stats.accuracy * 100).toFixed(0)}% accuracy)
          </p>
        )}

        {error && (
          <div style={{ backgroundColor: colors.errorBg, borderLeft: `4px solid ${colors.errorBorder}`, padding: '12px', marginBottom: '16px', borderRadius: '4px', textAlign: 'left' }} role="alert">
            <p style={{ fontSize: '13px', color: colors.errorText, margin: 0 }}>{error}</p>
          </div>
        )}

        {loading ? (
          <Spinner label="Loading puzzle..." />
        ) : puzzle ? (
          <>
            <p style={{ fontSize: '12px', color: colors.textSecondary }}>
              Rating {puzzle.rating}
              {puzzle.themes && puzzle.themes.length > 0 ? ` · ${puzzle.themes.join(', ')}` : ''}
            </p>

            <div style={{ display: 'flex', justifyContent: 'center', margin: '12px 0' }}>
              <ChessBoard
                chess={chess}
                position={chess.fen()}
                selectedSquare={selectedSquare}
                onSelectSquare={setSelectedSquare}
                onMove={handleMove}
                disabled={feedback === 'correct'}
              />
            </div>

            {feedback === 'correct' && (
              <div style={{ backgroundColor: colors.successBg, borderLeft: `4px solid ${colors.successBorder}`, padding: '12px', marginBottom: '12px', borderRadius: '4px' }} role="status">
                <p style={{ fontWeight: 'bold', color: colors.successText, margin: 0 }}>Correct! ✓</p>
              </div>
            )}
            {feedback === 'incorrect' && (
              <div style={{ backgroundColor: colors.errorBg, borderLeft: `4px solid ${colors.errorBorder}`, padding: '12px', marginBottom: '12px', borderRadius: '4px' }} role="status">
                <p style={{ fontWeight: 'bold', color: colors.errorText, margin: 0 }}>Not quite — try again.</p>
              </div>
            )}
          </>
        ) : null}

        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
          <button
            onClick={fetchPuzzle}
            style={{ flex: 1, backgroundColor: colors.accentBlue, color: 'white', fontWeight: 'bold', padding: '10px', borderRadius: '8px', border: 'none', cursor: 'pointer' }}
          >
            {feedback === 'correct' ? 'Next Puzzle' : 'Skip Puzzle'}
          </button>
          <button
            onClick={handleClose}
            style={{ flex: 1, backgroundColor: colors.accentGray, color: 'white', fontWeight: 'bold', padding: '10px', borderRadius: '8px', border: 'none', cursor: 'pointer' }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
