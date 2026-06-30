'use client';

/**
 * Shared UI primitives for the Reup Vietsub web/admin dashboard.
 * Dependency-free (no Tailwind / no component lib) — styled via globals.css.
 */

import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';

/* ----------------------------------------------------------- StatusBadge -- */

const NODE_STATUS_CLASS: Record<string, string> = {
  IDLE: 'status-idle',
  BUSY: 'status-busy',
  OFFLINE: 'status-offline',
  DISABLED: 'status-disabled',
  ERROR: 'status-error',
  PROVISIONING: 'status-provisioning',
};

const JOB_STATUS_CLASS: Record<string, string> = {
  DONE: 'status-done',
  FAILED: 'status-failed',
  CANCELLED: 'status-failed',
  EXPIRED: 'status-offline',
  WAITING_UPLOAD: 'status-waiting',
  CREATED: 'status-waiting',
  ASSIGNED_NODE: 'status-waiting',
  UPLOADING: 'status-processing',
  UPLOADED: 'status-processing',
  EXTRACTING_AUDIO: 'status-processing',
  CHUNKING_AUDIO: 'status-processing',
  TRANSCRIBING: 'status-processing',
  TRANSLATING: 'status-processing',
  GENERATING_SRT: 'status-processing',
  RENDERING: 'status-processing',
};

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const cls =
    NODE_STATUS_CLASS[status] || JOB_STATUS_CLASS[status] || 'status-neutral';
  const pulse = ['BUSY', 'UPLOADING', 'EXTRACTING_AUDIO', 'CHUNKING_AUDIO', 'TRANSCRIBING', 'TRANSLATING', 'GENERATING_SRT', 'RENDERING'].includes(status);
  return (
    <span className={`status-badge ${cls}`}>
      <span className={`dot ${pulse ? 'pulse' : ''}`} />
      {label || status}
    </span>
  );
}

/* ------------------------------------------------------------- Skeleton --- */

export function Skeleton({ className = '', style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={`skeleton ${className}`} style={style} />;
}

export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton skeleton-stat" />
      ))}
    </div>
  );
}

/* --------------------------------------------------------------- Empty ---- */

export function EmptyState({
  icon = '📭',
  title,
  hint,
  action,
}: {
  icon?: string;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      <div className="empty-title">{title}</div>
      {hint && <div className="text-sm">{hint}</div>}
      {action && <div className="mt-16">{action}</div>}
    </div>
  );
}

/* ------------------------------------------------------------ CopyButton -- */

export function CopyButton({
  value,
  label = 'Copy',
  copiedLabel = 'Đã copy ✓',
  className = 'btn btn-secondary btn-sm',
}: {
  value: string;
  label?: string;
  copiedLabel?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);
  const onCopy = useCallback(() => {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [value]);
  return (
    <button type="button" className={className} onClick={onCopy}>
      {copied ? copiedLabel : label}
    </button>
  );
}

/* ------------------------------------------------------------- Modal ------ */

export function Modal({
  title,
  children,
  onClose,
  width = 480,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  width?: number;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: width }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-title">{title}</div>
        {children}
      </div>
    </div>
  );
}

export function ConfirmModal({
  title,
  message,
  confirmLabel = 'Xác nhận',
  danger = false,
  onConfirm,
  onCancel,
  loading = false,
}: {
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}) {
  return (
    <Modal title={title} onClose={onCancel}>
      <div className="modal-body">{message}</div>
      <div className="modal-actions">
        <button className="btn btn-secondary" onClick={onCancel} disabled={loading}>
          Hủy
        </button>
        <button
          className={`btn ${danger ? 'btn-danger' : 'btn-primary'}`}
          onClick={onConfirm}
          disabled={loading}
        >
          {loading ? <span className="spinner" /> : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}

/* --------------------------------------------------------------- Toasts --- */

type Toast = { id: number; message: string; type: 'success' | 'error' | 'info' };
type ToastCtx = { push: (message: string, type?: Toast['type']) => void };

const ToastContext = createContext<ToastCtx>({ push: () => {} });

/** Returns a callable that shows a toast: `toast('message', 'success')`. */
export function useToast() {
  const { push } = useContext(ToastContext);
  return push;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ------------------------------------------------------------ helpers ----- */

export function timeAgo(timestamp: string | null): { text: string; stale: boolean } {
  if (!timestamp) return { text: 'Chưa có', stale: true };
  const diffMs = Date.now() - new Date(timestamp).getTime();
  const s = Math.floor(diffMs / 1000);
  const stale = s > 90; // > heartbeat stale window-ish
  if (s < 60) return { text: `${s}s trước`, stale };
  const m = Math.floor(s / 60);
  if (m < 60) return { text: `${stale ? 'stale ' : ''}${m}m trước`, stale };
  const h = Math.floor(m / 60);
  return { text: `${stale ? 'stale ' : ''}${h}h trước`, stale };
}

export function formatBytes(bytes: number | null): string {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB'];
  let v = bytes / 1024;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(1)} ${units[i]}`;
}
