import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'jarvis-settings';

// Kept intentionally small: every field here must actually change backend
// behavior (see App.js's startGame, which passes defaultDepth to
// POST /api/games/new - api_server.py already accepts that query param).
// Theme lives in useTheme/ThemeProvider, not here, since it already persists
// itself; SettingsModal just exposes useTheme's setMode alongside these.
const DEFAULTS = {
  defaultDepth: 10, // matches /api/games/new's own default
};

export default function useSettings() {
  const [settings, setSettings] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      return { ...DEFAULTS, ...saved };
    } catch {
      return DEFAULTS;
    }
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  const updateSettings = useCallback((patch) => {
    setSettings((s) => ({ ...s, ...patch }));
  }, []);

  return { settings, updateSettings };
}
