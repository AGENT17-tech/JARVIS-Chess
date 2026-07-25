import React from 'react';
import useTheme from '../hooks/useTheme';

const STATUS_LABELS = {
  connecting: 'Connecting to JARVIS backend...',
  disconnected: 'Disconnected from backend',
  playing: 'Game in progress',
  checkmate: 'Checkmate',
  stalemate: 'Stalemate',
  draw: 'Draw',
};

function HeaderButton({ onClick, bg, children, ...rest }) {
  return (
    <button
      onClick={onClick}
      style={{
        backgroundColor: bg, color: 'white', fontWeight: 'bold', fontSize: '13px',
        padding: '8px 16px', borderRadius: '6px', border: 'none', cursor: 'pointer',
      }}
      {...rest}
    >
      {children}
    </button>
  );
}

export default function Header({
  status, gameId, errorMsg, onImportClick, onNewGameClick, onHistoryClick, onPuzzleClick,
  onHelpClick, onSettingsClick, onThemeToggle, themeMode,
}) {
  const { colors } = useTheme();
  const statusLabel = STATUS_LABELS[status] || status;

  return (
    <header style={{
      background: colors.headerBg,
      color: colors.headerText,
      padding: '16px 24px',
      boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
    }} role="banner">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
          <h1 style={{ fontSize: '28px', fontWeight: 'bold', margin: 0 }}>{'♞'} JARVIS Chess</h1>
          <span style={{ fontSize: '13px', color: colors.headerTextMuted }}>Tier 2: Desktop UI</span>
        </div>

        <nav style={{ display: 'flex', alignItems: 'center', gap: '16px' }} aria-label="Main actions">
          <div style={{ textAlign: 'right' }} role="status" aria-live="polite">
            <div style={{ fontSize: '11px', color: colors.headerTextMuted }}>STATUS</div>
            <div style={{ fontWeight: 'bold' }}>
              {statusLabel}
              {gameId ? <span style={{ color: colors.headerTextMuted, fontWeight: 'normal' }}> ({gameId})</span> : null}
            </div>
          </div>

          {errorMsg && <div style={{ color: '#fca5a5', fontSize: '13px', maxWidth: '220px' }} role="alert">{errorMsg}</div>}

          <HeaderButton onClick={onImportClick} bg={colors.accentBlue}>Import Chess.com</HeaderButton>
          <HeaderButton onClick={onHistoryClick} bg={colors.accentPurple}>Game History</HeaderButton>
          <HeaderButton onClick={onPuzzleClick} bg={colors.accentCyan}>Puzzles</HeaderButton>
          <HeaderButton onClick={onNewGameClick} bg={colors.accentGreen}>New Game</HeaderButton>
          <button
            onClick={onSettingsClick}
            aria-label="Settings"
            title="Settings"
            style={{
              backgroundColor: 'transparent', color: colors.headerText, fontSize: '16px',
              padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.headerTextMuted}`, cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            ⚙
          </button>
          <button
            onClick={onHelpClick}
            aria-label="Keyboard shortcuts help"
            title="Keyboard shortcuts (?)"
            style={{
              backgroundColor: 'transparent', color: colors.headerText, fontSize: '14px', fontWeight: 'bold',
              padding: '6px 12px', borderRadius: '6px', border: `1px solid ${colors.headerTextMuted}`, cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            ?
          </button>
          <button
            onClick={onThemeToggle}
            aria-label={themeMode === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            title={themeMode === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            style={{
              backgroundColor: 'transparent', color: colors.headerText, fontSize: '18px',
              padding: '6px 10px', borderRadius: '6px', border: `1px solid ${colors.headerTextMuted}`, cursor: 'pointer',
              lineHeight: 1,
            }}
          >
            {themeMode === 'dark' ? '☀️' : '🌙'}
          </button>
        </nav>
      </div>
    </header>
  );
}
