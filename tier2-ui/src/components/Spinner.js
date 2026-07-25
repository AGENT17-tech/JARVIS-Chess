import React from 'react';
import useTheme from '../hooks/useTheme';

const SIZES = { sm: 20, md: 32, lg: 48 };

export default function Spinner({ size = 'md', label }) {
  const { colors } = useTheme();
  const px = SIZES[size] || SIZES.md;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px', padding: '16px' }} role="status" aria-live="polite">
      <div
        style={{
          width: px, height: px, borderRadius: '50%',
          border: `3px solid ${colors.border}`, borderTopColor: colors.accentBlue,
          animation: 'jarvis-spin 0.8s linear infinite',
        }}
      />
      {label && <p style={{ color: colors.textSecondary, fontSize: '13px', margin: 0 }}>{label}</p>}
      <style>{'@keyframes jarvis-spin { to { transform: rotate(360deg); } }'}</style>
    </div>
  );
}
