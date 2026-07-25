import React, { createContext, useContext, useEffect, useState } from 'react';
import { lightTheme, darkTheme } from '../theme';

const STORAGE_KEY = 'jarvis-theme'; // 'light' | 'dark' | 'system'

const ThemeContext = createContext(null);

function resolveMode(mode) {
  if (mode === 'system') {
    if (typeof window.matchMedia !== 'function') return 'light'; // e.g. jsdom in tests
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return mode;
}

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => localStorage.getItem(STORAGE_KEY) || 'system');
  const [resolvedMode, setResolvedMode] = useState(() => resolveMode(mode));

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
    setResolvedMode(resolveMode(mode));

    if (mode !== 'system' || typeof window.matchMedia !== 'function') return undefined;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setResolvedMode(resolveMode('system'));
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [mode]);

  const colors = resolvedMode === 'dark' ? darkTheme : lightTheme;
  const toggle = () => setMode(resolvedMode === 'dark' ? 'light' : 'dark');

  return (
    <ThemeContext.Provider value={{ mode, resolvedMode, colors, setMode, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export default function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
  return ctx;
}
