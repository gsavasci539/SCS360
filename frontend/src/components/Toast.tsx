import { CheckCircle2, CircleAlert, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

type ToastType = "success" | "error";
interface ToastItem { id: number; title: string; message?: string; type: ToastType }
interface ToastContextValue { showToast: (title: string, message?: string, type?: ToastType) => void }

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);
  const timers = useRef(new Map<number, number>());
  const dismiss = useCallback((id: number) => {
    const timer = timers.current.get(id);
    if (timer) window.clearTimeout(timer);
    timers.current.delete(id);
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);
  const showToast = useCallback((title: string, message?: string, type: ToastType = "success") => {
    const id = ++nextId.current;
    setToasts((current) => [...current, { id, title, message, type }]);
    timers.current.set(id, window.setTimeout(() => dismiss(id), 4200));
  }, [dismiss]);
  useEffect(() => () => { timers.current.forEach((timer) => window.clearTimeout(timer)); timers.current.clear(); }, []);
  const value = useMemo(() => ({ showToast }), [showToast]);
  return <ToastContext.Provider value={value}>
    {children}
    <div className="toast-region" aria-live="polite">
      {toasts.map((toast) => <div className={`toast toast-${toast.type}`} key={toast.id} role={toast.type === "error" ? "alert" : "status"}>
        {toast.type === "success" ? <CheckCircle2 size={19} color="#2c8a6f" /> : <CircleAlert size={19} color="#c34b4b" />}
        <div style={{ flex: 1 }}><strong>{toast.title}</strong>{toast.message && <span>{toast.message}</span>}</div>
        <button className="btn btn-ghost btn-icon" onClick={() => dismiss(toast.id)} aria-label="Bildirimi kapat"><X size={15} /></button>
      </div>)}
    </div>
  </ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used inside ToastProvider");
  return context;
}
