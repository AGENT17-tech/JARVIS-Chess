import React from 'react';
import useTheme from '../hooks/useTheme';

const VARIANTS = {
  error: (colors) => ({ bg: colors.errorBg, border: colors.errorBorder, text: colors.errorText, icon: '✕' }),
  success: (colors) => ({ bg: colors.successBg, border: colors.successBorder, text: colors.successText, icon: '✓' }),
  warning: (colors) => ({ bg: colors.warningBg, border: colors.warningBorder, text: colors.warningText, icon: '⚠' }),
  info: (colors) => ({ bg: colors.infoBg, border: colors.infoBorder, text: colors.infoText, icon: 'ℹ' }),
};

export default function Toast({ message, type = 'info', onDismiss }) {
  const { colors } = useTheme();
  const v = (VARIANTS[type] || VARIANTS.info)(colors);

  return (
    <div
      role={type === 'error' ? 'alert' : 'status'}
      style={{
        display: 'flex', alignItems: 'center', gap: '12px', minWidth: '260px', maxWidth: '400px',
        padding: '12px 16px', borderRadius: '8px', boxShadow: colors.shadow,
        backgroundColor: v.bg, borderLeft: `4px solid ${v.border}`, color: v.text,
      }}
    >
      <span aria-hidden="true" style={{ fontWeight: 'bold' }}>{v.icon}</span>
      <span style={{ fontSize: '13px', flex: 1 }}>{message}</span>
      <button
        onClick={onDismiss}
        aria-label="Dismiss notification"
        style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '14px', opacity: 0.7, padding: 0 }}
      >
        ✕
      </button>
    </div>
  );
}
