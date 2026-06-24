'use client';

import { useEffect, useState } from 'react';

export type ToastType = 'success' | 'error' | 'info';

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

interface ToastProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export default function Toast({ toasts, onDismiss }: ToastProps) {
  return (
    <div className="fixed bottom-4 right-4 space-y-2 z-50">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function ToastItem({ toast, onDismiss }: { toast: ToastMessage; onDismiss: (id: string) => void }) {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (!toast.duration) return;

    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(() => onDismiss(toast.id), 300);
    }, toast.duration);

    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, onDismiss]);

  const bgColor =
    toast.type === 'success'
      ? 'bg-green-900/90 border-green-700'
      : toast.type === 'error'
        ? 'bg-red-900/90 border-red-700'
        : 'bg-blue-900/90 border-blue-700';

  const textColor =
    toast.type === 'success'
      ? 'text-green-100'
      : toast.type === 'error'
        ? 'text-red-100'
        : 'text-blue-100';

  const icon =
    toast.type === 'success'
      ? '✓'
      : toast.type === 'error'
        ? '✕'
        : 'ℹ';

  return (
    <div
      className={`notification-enter flex items-center gap-3 px-4 py-3 rounded-lg border ${bgColor} ${textColor} max-w-sm backdrop-blur-sm ${
        isExiting ? 'notification-exit' : ''
      }`}
    >
      <span className="text-lg font-bold">{icon}</span>
      <span className="text-sm">{toast.message}</span>
      <button
        onClick={() => onDismiss(toast.id)}
        className="ml-auto text-lg hover:opacity-70 transition"
      >
        ×
      </button>
    </div>
  );
}

/**
 * Hook for managing toasts
 */
export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const add = (message: string, type: ToastType = 'info', duration = 3000) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, message, type, duration }]);
    return id;
  };

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return {
    toasts,
    add,
    dismiss,
    success: (msg: string) => add(msg, 'success'),
    error: (msg: string) => add(msg, 'error'),
    info: (msg: string) => add(msg, 'info'),
  };
}
