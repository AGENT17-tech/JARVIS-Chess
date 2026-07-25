import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts';
import useTheme from '../hooks/useTheme';

/**
 * Eval-over-time curve for a game's moves. `moves` entries need `ply` and
 * `eval` (White-positive, in pawns — see api_server.py's /replay and the
 * live WebSocket's move records, both already convert eval_cp/100.0).
 * `analyzed` distinguishes "no data because nothing was ever engine-
 * analyzed" (chess.com imports — see games_history_replay in api_server.py)
 * from "no moves yet".
 */
export default function EvaluationChart({ moves, analyzed = true }) {
  const { colors } = useTheme();

  if (!moves || moves.length === 0) {
    return <p style={{ fontSize: '12px', color: colors.textMuted }}>No moves to display.</p>;
  }

  const data = moves.map((m) => ({
    ply: m.ply,
    san: m.san,
    eval: m.eval != null ? m.eval : (m.eval_mate != null ? (m.eval_mate > 0 ? 10 : -10) : null),
  }));
  const hasAnyEval = data.some((d) => d.eval != null);

  if (!analyzed || !hasAnyEval) {
    return (
      <p style={{ fontSize: '12px', color: colors.textMuted }}>
        No evaluation data for this game — it was never analyzed by the engine (only games played in
        this app are; chess.com imports keep just the raw moves).
      </p>
    );
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.borderLight} />
          <XAxis dataKey="ply" tick={{ fontSize: 11, fill: colors.textSecondary }} stroke={colors.border}
            label={{ value: 'Ply', position: 'insideBottom', offset: -4, fontSize: 11, fill: colors.textSecondary }} />
          <YAxis tick={{ fontSize: 11, fill: colors.textSecondary }} stroke={colors.border} domain={[-5, 5]} width={32} />
          <ReferenceLine y={0} stroke={colors.textMuted} />
          <Tooltip
            contentStyle={{ backgroundColor: colors.cardBg, border: `1px solid ${colors.border}`, color: colors.text, fontSize: '12px' }}
            formatter={(value) => (value == null ? 'n/a' : (value > 0 ? '+' : '') + value.toFixed(2))}
            labelFormatter={(ply) => {
              const point = data.find((d) => d.ply === ply);
              return point ? `Ply ${ply}: ${point.san}` : `Ply ${ply}`;
            }}
          />
          <Line type="monotone" dataKey="eval" stroke={colors.accentBlue} dot={false} isAnimationActive={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: colors.textSecondary }}>
        <span>White winning</span>
        <span>Black winning</span>
      </div>
    </div>
  );
}
