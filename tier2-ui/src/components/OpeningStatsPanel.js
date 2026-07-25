import React from 'react';
import useTheme from '../hooks/useTheme';

// Fixed across themes — semantic status colors, not chrome.
const STATUS_BADGE = {
  study: { backgroundColor: '#fef9c3', color: '#854d0e' },
  master: { backgroundColor: '#dcfce7', color: '#166534' },
  avoid: { backgroundColor: '#fee2e2', color: '#991b1b' },
};

const badgeStyle = { padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold' };

function StatCard({ label, value, color, bg, small }) {
  return (
    <div style={{ backgroundColor: bg, padding: '12px 16px', borderRadius: '8px', minWidth: '120px' }}>
      <div style={{ fontSize: small ? '14px' : '22px', fontWeight: 'bold', color }}>{value}</div>
      <div style={{ fontSize: '12px', color: '#6b7280' }}>{label}</div>
    </div>
  );
}

// All figures come straight from GET /api/openings/stats (database.py's
// get_analytics()/list_openings(), plus the mistake_count merged in by
// api_server.py). No fabricated columns — the prototype's mock "Avg Rating"
// column is dropped since nothing in this project tracks ratings.
export default function OpeningStatsPanel({ stats }) {
  const { colors } = useTheme();
  const thStyle = { padding: '8px 12px', textAlign: 'left', fontWeight: 'bold', color: colors.text };
  const tdStyle = { padding: '8px 12px', color: colors.text };

  if (!stats) {
    return (
      <div style={{ padding: '16px 24px' }} role="region" aria-label="Opening statistics">
        <h3 style={{ marginTop: 0, color: colors.text }}>Opening Statistics</h3>
        <p style={{ color: colors.textSecondary }}>Play a few moves to see stats here</p>
      </div>
    );
  }

  const { analytics, openings } = stats;

  return (
    <div style={{ padding: '16px 24px', overflowY: 'auto', height: '100%' }} role="region" aria-label="Opening statistics">
      <h2 style={{ fontSize: '20px', fontWeight: 'bold', marginTop: 0, marginBottom: '16px', color: colors.text }}>Opening Statistics</h2>

      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <StatCard label="Total Games" value={analytics.total_games} color={colors.accentBlue} bg={colors.infoBg} />
        <StatCard
          label="Win Rate"
          value={analytics.win_rate != null ? `${(analytics.win_rate * 100).toFixed(0)}%` : '-'}
          color={colors.accentGreen} bg={colors.successBg}
        />
        <StatCard
          label="Most Played"
          value={analytics.most_played_opening ? analytics.most_played_opening.name : '-'}
          color={colors.textSecondary} bg={colors.panelBg} small
        />
      </div>

      {openings.length === 0 ? (
        <p style={{ color: colors.textMuted, fontSize: '13px' }}>No openings recorded yet.</p>
      ) : (
        <div style={{ backgroundColor: colors.cardBg, borderRadius: '8px', border: `1px solid ${colors.border}`, overflow: 'hidden' }}>
          <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse' }}>
            <thead style={{ backgroundColor: colors.tableHeaderBg }}>
              <tr>
                <th scope="col" style={thStyle}>Opening</th>
                <th scope="col" style={{ ...thStyle, textAlign: 'center' }}>Record (W-L-D)</th>
                <th scope="col" style={{ ...thStyle, textAlign: 'center' }}>Games</th>
                <th scope="col" style={{ ...thStyle, textAlign: 'center' }}>Mistakes</th>
                <th scope="col" style={{ ...thStyle, textAlign: 'center' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {openings.map((o) => (
                <tr key={o.id} style={{ borderTop: `1px solid ${colors.borderLight}` }}>
                  <td style={tdStyle}>{o.name}{o.eco ? ` (${o.eco})` : ''}</td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', textAlign: 'center' }}>
                    {o.wins}-{o.losses}-{o.draws}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'center' }}>{o.games_played}</td>
                  <td style={{
                    ...tdStyle, textAlign: 'center',
                    color: o.mistake_count > 3 ? '#dc2626' : colors.text,
                    fontWeight: o.mistake_count > 3 ? 'bold' : 'normal',
                  }}>
                    {o.mistake_count}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'center' }}>
                    {o.favorite_status ? (
                      <span style={{ ...badgeStyle, ...STATUS_BADGE[o.favorite_status] }}>{o.favorite_status}</span>
                    ) : (
                      <span style={{ color: colors.textMuted }}>-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {analytics.weakest_opening_by_mistakes && (
        <div style={{ marginTop: '16px', backgroundColor: colors.warningBg, borderLeft: '4px solid #eab308', padding: '12px', borderRadius: '4px' }}>
          <strong style={{ color: colors.warningText }}>Study Recommendation</strong>
          <p style={{ fontSize: '13px', color: colors.warningText, margin: '4px 0 0' }}>
            Your weakest opening by mistakes is <strong>{analytics.weakest_opening_by_mistakes.eco}</strong> with{' '}
            {analytics.weakest_opening_by_mistakes.mistake_count} logged mistake
            {analytics.weakest_opening_by_mistakes.mistake_count === 1 ? '' : 's'}. Worth reviewing that line.
          </p>
        </div>
      )}
    </div>
  );
}
