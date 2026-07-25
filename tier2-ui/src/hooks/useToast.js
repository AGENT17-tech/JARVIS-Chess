import React, { createContext, useCallback, useContext, useState } from 'react';

const ToastContext = createContext(null);
let nextId = 1;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((message, type = 'info', duration = 3000) => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);
    if (duration) setTimeout(() => dismiss(id), duration);
    return id;
  }, [dismiss]);

  const value = {
    toasts,
    dismiss,
    success: useCallback((msg) => show(msg, 'success', 3000), [show]),
    error: useCallback((msg, duration = 5000) => show(msg, 'error', duration), [show]),
    warning: useCallback((msg) => show(msg, 'warning', 4000), [show]),
    info: useCallback((msg) => show(msg, 'info', 3000), [show]),
  };

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export default function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}
