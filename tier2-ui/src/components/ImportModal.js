import React, { useState } from 'react';
import useTheme from '../hooks/useTheme';

export default function ImportModal({ isOpen, onClose, apiBase, onImported }) {
  const { colors } = useTheme();
  const [username, setUsername] = useState('');
  const [step, setStep] = useState('input'); // 'input' | 'loading' | 'complete' | 'error'
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleImport = async () => {
    setStep('loading');
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/import/chesscom/${encodeURIComponent(username)}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Import failed');
      }
      setResult(data);
      setStep('complete');
      if (onImported) onImported();
    } catch (e) {
      setError(e.message || String(e));
      setStep('error');
    }
  };

  const handleClose = () => {
    setStep('input');
    setUsername('');
    setResult(null);
    setError(null);
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
      aria-labelledby="import-modal-title"
    >
      <div style={{ backgroundColor: colors.cardBg, borderRadius: '8px', padding: '32px', width: '384px', boxShadow: colors.shadowLg }}>
        <h2 id="import-modal-title" style={{ fontSize: '22px', fontWeight: 'bold', marginTop: 0, marginBottom: '16px', color: colors.text }}>Import from Chess.com</h2>

        {step === 'input' && (
          <>
            <p style={{ color: colors.textSecondary, marginBottom: '16px', fontSize: '14px' }}>
              Enter a Chess.com username to import their public game history.
            </p>
            <label htmlFor="chesscom-username" style={{ position: 'absolute', width: '1px', height: '1px', overflow: 'hidden', clip: 'rect(0,0,0,0)' }}>
              Chess.com username
            </label>
            <input
              type="text"
              id="chesscom-username"
              name="chesscom-username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. hikaru"
              style={{
                width: '100%', padding: '8px 12px', border: `1px solid ${colors.border}`, borderRadius: '8px',
                marginBottom: '16px', boxSizing: 'border-box', backgroundColor: colors.inputBg, color: colors.text,
              }}
            />
            <button
              onClick={handleImport}
              disabled={!username}
              style={{
                width: '100%', backgroundColor: username ? colors.accentBlue : colors.textMuted, color: 'white', fontWeight: 'bold',
                padding: '10px', borderRadius: '8px', border: 'none', cursor: username ? 'pointer' : 'default',
              }}
            >
              Import Games
            </button>
          </>
        )}

        {step === 'loading' && (
          <div style={{ textAlign: 'center', padding: '16px 0' }} role="status" aria-live="polite">
            <p style={{ color: colors.textSecondary }}>Fetching games from Chess.com for "{username}"...</p>
            <p style={{ color: colors.textMuted, fontSize: '12px' }}>This can take a few seconds for accounts with many games.</p>
          </div>
        )}

        {step === 'complete' && result && (
          <>
            <div style={{ backgroundColor: colors.successBg, borderLeft: `4px solid ${colors.successBorder}`, padding: '12px', marginBottom: '16px', borderRadius: '4px' }} role="status">
              <p style={{ fontWeight: 'bold', color: colors.successText, margin: 0 }}>Import complete</p>
              <p style={{ fontSize: '13px', color: colors.successText, marginTop: '8px', marginBottom: 0 }}>
                Imported <strong>{result.imported}</strong> game{result.imported === 1 ? '' : 's'} for "{username}"
                {result.skipped ? ` (${result.skipped} already stored)` : ''}.
              </p>
            </div>
            {result.errors > 0 && (
              <p style={{ fontSize: '12px', color: colors.errorText }}>{result.errors} game(s) failed to import.</p>
            )}
            <button
              onClick={handleClose}
              style={{ width: '100%', backgroundColor: colors.accentGray, color: 'white', fontWeight: 'bold', padding: '10px', borderRadius: '8px', border: 'none', cursor: 'pointer' }}
            >
              Done
            </button>
          </>
        )}

        {step === 'error' && (
          <>
            <div style={{ backgroundColor: colors.errorBg, borderLeft: `4px solid ${colors.errorBorder}`, padding: '12px', marginBottom: '16px', borderRadius: '4px' }} role="alert">
              <p style={{ fontWeight: 'bold', color: colors.errorText, margin: 0 }}>Import failed</p>
              <p style={{ fontSize: '13px', color: colors.errorText, marginTop: '8px', marginBottom: 0 }}>{error}</p>
            </div>
            <button
              onClick={() => setStep('input')}
              style={{ width: '100%', backgroundColor: colors.accentBlue, color: 'white', fontWeight: 'bold', padding: '10px', borderRadius: '8px', border: 'none', cursor: 'pointer' }}
            >
              Try Again
            </button>
          </>
        )}
      </div>
    </div>
  );
}
