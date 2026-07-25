import React from 'react';
import Toast from './Toast';
import useToast from '../hooks/useToast';

export default function ToastContainer() {
  const { toasts, dismiss } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed', top: '20px', right: '20px', zIndex: 9999,
        display: 'flex', flexDirection: 'column', gap: '10px',
      }}
      aria-live="polite"
    >
      {toasts.map((t) => (
        <Toast key={t.id} message={t.message} type={t.type} onDismiss={() => dismiss(t.id)} />
      ))}
    </div>
  );
}
