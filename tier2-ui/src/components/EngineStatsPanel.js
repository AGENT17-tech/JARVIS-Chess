import React, { useEffect, useState } from 'react';
import useTheme from '../hooks/useTheme';

// Fetches GET /api/games/{gameId}/engine-stats after every move (`moves`
// changing is the refresh trigger) — see GameEngine.get_engine_stats() for
// why there's no nodes/sec here: the python-stockfish wrapper this project
// uses doesn't expose UCI node counts.
export default function EngineStatsPanel({ apiBase, gameId, moves }) {
  const { colors } = useTheme();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    if (!gameId) return;
    fetch(`${apiBase}/api/games/${gameId}/engine-stats`)
      .then((r) => r.json())
      .then(setStats)
      .catch(() => {});
  }, [apiBase, gameId, moves]);

  if (!stats || !stats.total_moves) {
    return null;
  }

  return (
    <div
      style={{
        display: 'flex', gap: '16px', backgroundColor: colors.panelBg, border: `1px solid ${colors.border}`,
        borderRadius: '8px', padding: '8px 16px', fontSize: '12px', color: colors.text,
      }}
      role="group"
      aria-label="Engine performance stats"
    >
      <span><strong>{stats.total_moves}</strong> move{stats.total_moves === 1 ? '' : 's'} thought about</span>
      <span>avg <strong>{stats.avg_time_ms.toFixed(0)}ms</strong></span>
      <span>min <strong>{stats.min_time_ms.toFixed(0)}ms</strong></span>
      <span>max <strong>{stats.max_time_ms.toFixed(0)}ms</strong></span>
      <span>avg depth <strong>{stats.avg_depth.toFixed(1)}</strong></span>
    </div>
  );
}
