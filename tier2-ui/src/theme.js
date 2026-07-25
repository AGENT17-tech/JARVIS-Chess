// Color tokens for the two supported themes. Consumed via useTheme()'s
// `colors` object in each component's inline styles — this codebase has no
// CSS files, so theming is plain JS objects rather than CSS variables.
//
// Deliberately NOT themed: the chess board's square colors (traditional
// beige/brown, already high-contrast in both themes) and move-classification
// badge colors in MoveHistoryPanel.js/MoveAnalysisPanel.js (semantic
// meaning — Blunder is red, Book is gray — independent of app theme).

export const lightTheme = {
  name: 'light',
  bg: '#f5f5f5',
  panelBg: '#fafafa',
  cardBg: '#ffffff',
  border: '#d1d5db',
  borderLight: '#e5e7eb',
  text: '#1f2937',
  textSecondary: '#6b7280',
  textMuted: '#9ca3af',
  headerBg: 'linear-gradient(to right, #1f2937, #111827)',
  headerText: '#ffffff',
  headerTextMuted: '#9ca3af',
  overlayBg: 'rgba(0,0,0,0.5)',
  accentBlue: '#2563eb',
  accentBlueHover: '#1d4ed8',
  accentGreen: '#16a34a',
  accentPurple: '#7c3aed',
  accentCyan: '#0891b2',
  accentGray: '#4b5563',
  accentGrayHover: '#374151',
  inputBg: '#ffffff',
  tableHeaderBg: '#f3f4f6',
  errorBg: '#fef2f2', errorBorder: '#dc2626', errorText: '#991b1b',
  successBg: '#f0fdf4', successBorder: '#22c55e', successText: '#166534',
  warningBg: '#fefce8', warningBorder: '#eab308', warningText: '#854d0e',
  infoBg: '#eff6ff', infoBorder: '#2563eb', infoText: '#1e40af',
  shadow: '0 4px 12px rgba(0,0,0,0.15)',
  shadowLg: '0 20px 40px rgba(0,0,0,0.3)',
};

export const darkTheme = {
  name: 'dark',
  bg: '#0f172a',
  panelBg: '#1e293b',
  cardBg: '#1e293b',
  border: '#334155',
  borderLight: '#2d3b4e',
  text: '#e5e7eb',
  textSecondary: '#9ca3af',
  textMuted: '#6b7280',
  headerBg: 'linear-gradient(to right, #060a14, #0a0f1c)',
  headerText: '#f3f4f6',
  headerTextMuted: '#94a3b8',
  overlayBg: 'rgba(0,0,0,0.7)',
  accentBlue: '#3b82f6',
  accentBlueHover: '#60a5fa',
  accentGreen: '#22c55e',
  accentPurple: '#a78bfa',
  accentCyan: '#22d3ee',
  accentGray: '#64748b',
  accentGrayHover: '#94a3b8',
  inputBg: '#0f172a',
  tableHeaderBg: '#273449',
  errorBg: '#3f1d1d', errorBorder: '#f87171', errorText: '#fca5a5',
  successBg: '#14291c', successBorder: '#4ade80', successText: '#86efac',
  warningBg: '#3a2f0f', warningBorder: '#facc15', warningText: '#fde68a',
  infoBg: '#1e3a5f', infoBorder: '#3b82f6', infoText: '#93c5fd',
  shadow: '0 4px 12px rgba(0,0,0,0.5)',
  shadowLg: '0 20px 40px rgba(0,0,0,0.6)',
};
