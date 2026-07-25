import { useEffect } from 'react';

// Ignores keystrokes while focused in a text input, so shortcuts don't fire
// while e.g. typing a chess.com username into ImportModal.
function isTypingTarget(target) {
  if (!target) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable;
}

/**
 * `shortcuts` keys look like "ctrl+n", "?", "escape" (lowercase, '+'-joined
 * modifiers before the key). Pass a useMemo'd object so the listener isn't
 * torn down and rebuilt every render.
 */
export default function useKeyboardShortcuts(shortcuts) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (isTypingTarget(e.target)) return;
      for (const [combo, callback] of Object.entries(shortcuts)) {
        const parts = combo.split('+');
        const key = parts[parts.length - 1];
        const needsCtrl = parts.includes('ctrl');
        if (e.key.toLowerCase() === key.toLowerCase() && e.ctrlKey === needsCtrl) {
          e.preventDefault();
          callback();
          return;
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}
