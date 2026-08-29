'use client';

import { useEffect } from 'react';

export type ToastKind = 'info' | 'success' | 'error' | 'warning';

interface Props {
  message: string;
  kind?: ToastKind;
  onClose: () => void;
  durationMs?: number;
}

const STYLES: Record<ToastKind, string> = {
  info: 'border-sky-700/60 bg-sky-950/90 text-sky-100',
  success: 'border-emerald-700/60 bg-emerald-950/90 text-emerald-100',
  error: 'border-red-700/60 bg-red-950/90 text-red-100',
  warning: 'border-amber-700/60 bg-amber-950/90 text-amber-100',
};

const ICONS: Record<ToastKind, string> = {
  info: 'ℹ',
  success: '✓',
  error: '!',
  warning: '⚠',
};

export default function Toast({
  message,
  kind = 'info',
  onClose,
  durationMs = 4500,
}: Props) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, durationMs);
    return () => clearTimeout(t);
  }, [message, durationMs, onClose]);

  if (!message) return null;

  return (
    <div className="fixed bottom-5 right-5 z-[100] max-w-sm w-[min(100vw-2rem,24rem)] toast-enter">
      <div
        className={`flex items-start gap-3 rounded-xl border px-4 py-3 shadow-card backdrop-blur-md ${STYLES[kind]}`}
        role="status"
      >
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-bold">
          {ICONS[kind]}
        </span>
        <p className="flex-1 text-sm leading-snug pt-0.5">{message}</p>
        <button
          type="button"
          onClick={onClose}
          className="shrink-0 text-white/50 hover:text-white text-lg leading-none px-1"
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
    </div>
  );
}

export function toastKindFromMessage(msg: string): ToastKind {
  const m = msg.toLowerCase();
  if (m.includes('fail') || m.includes('error') || m.includes('cannot') || m.includes('❌')) {
    return 'error';
  }
  if (m.includes('scheduled') || m.includes('created') || m.includes('success') || m.includes('✅')) {
    return 'success';
  }
  if (m.includes('offline') || m.includes('warn')) return 'warning';
  return 'info';
}
