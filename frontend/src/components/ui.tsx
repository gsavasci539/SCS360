import { AlertCircle, Inbox, LoaderCircle, Plus, X } from "lucide-react";
import { cloneElement, isValidElement, useEffect, useId, useRef, type ReactElement, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { statusLabels, statusTone } from "../lib/format";

export function PageHeader({ eyebrow, title, description, children }: { eyebrow?: string; title: string; description?: string; children?: ReactNode }) {
  return <header className="page-head"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{children && <div className="head-actions">{children}</div>}</header>;
}

export function AddButton({ to, label }: { to: string; label: string }) { return <Link className="btn btn-primary" to={to}><Plus size={16} />{label}</Link>; }

export function Badge({ value }: { value: unknown }) {
  const raw = String(value || "");
  return <span className={`badge badge-${statusTone(raw)}`}>{statusLabels[raw] || raw || "Belirsiz"}</span>;
}

export function LoadingState({ label = "Veriler hazırlanıyor" }: { label?: string }) { return <div className="state"><div><div className="spinner" style={{ margin: "auto" }} /><h3>{label}</h3><p>Bu işlem yalnızca birkaç saniye sürmeli.</p></div></div>; }
export function EmptyState({ title = "Henüz kayıt yok", description = "İlk kaydı eklediğinizde burada görünecek.", action }: { title?: string; description?: string; action?: ReactNode }) { return <div className="state"><div><div className="state-icon" style={{ margin: "auto" }}><Inbox size={23} /></div><h3>{title}</h3><p>{description}</p>{action && <div style={{ marginTop: 16 }}>{action}</div>}</div></div>; }
export function ErrorState({ message, retry }: { message: string; retry?: () => void }) { return <div className="state"><div><div className="state-icon" style={{ margin: "auto", color: "#c34b4b", background: "#fff0ef" }}><AlertCircle size={23} /></div><h3>Veriler yüklenemedi</h3><p>{message}</p>{retry && <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={retry}>Tekrar dene</button>}</div></div>; }

export function Modal({ open, title, description, onClose, children, actions }: { open: boolean; title: string; description?: string; onClose: () => void; children: ReactNode; actions?: ReactNode }) {
  const modalRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    const focusableSelector = "button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";
    const frame = window.requestAnimationFrame(() => {
      const first = modalRef.current?.querySelector<HTMLElement>(focusableSelector);
      (first || modalRef.current)?.focus();
    });
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !modalRef.current) return;
      const focusable = Array.from(modalRef.current.querySelectorAll<HTMLElement>(focusableSelector));
      if (!focusable.length) { event.preventDefault(); modalRef.current.focus(); return; }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", handler); document.body.style.overflow = "hidden";
    return () => { window.cancelAnimationFrame(frame); document.removeEventListener("keydown", handler); document.body.style.overflow = previousOverflow; previouslyFocused?.focus(); };
  }, [open, onClose]);
  if (!open) return null;
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><div ref={modalRef} className="modal" role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
    <div className="modal-head"><div><h2 id={titleId}>{title}</h2>{description && <p>{description}</p>}</div><button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Pencereyi kapat"><X size={18} /></button></div>
    <div className="modal-body">{children}</div>{actions && <div className="modal-actions">{actions}</div>}
  </div></div>;
}

export function ConfirmDialog({ open, title = "Kaydı kaldırmak istiyor musunuz?", description = "Bu işlem kaydı pasife alır ve listeden kaldırır.", busy, onCancel, onConfirm }: { open: boolean; title?: string; description?: string; busy?: boolean; onCancel: () => void; onConfirm: () => void }) {
  return <Modal open={open} title={title} description={description} onClose={onCancel} actions={<><button className="btn btn-secondary" onClick={onCancel}>Vazgeç</button><button className="btn btn-danger" disabled={busy} onClick={onConfirm}>{busy && <LoaderCircle size={15} />}Onayla</button></>}><p style={{ margin: 0, color: "#5e6c6d", fontSize: 13, lineHeight: 1.6 }}>Silinen finansal kayıtlar güvenlik gereği kalıcı olarak yok edilmez; işlem geçmişinde izlenebilir kalır.</p></Modal>;
}

export function Field({ label, error, required, children, full }: { label: string; error?: string; required?: boolean; children: ReactNode; full?: boolean }) {
  const generatedId = useId();
  const errorId = `${generatedId}-error`;
  const nativeControl = isValidElement(children) && typeof children.type === "string" && ["input", "select", "textarea"].includes(children.type);
  const control = nativeControl
    ? cloneElement(children as ReactElement<{ id?: string; "aria-describedby"?: string; "aria-invalid"?: boolean }>, {
      id: (children.props as { id?: string }).id || generatedId,
      "aria-describedby": error ? errorId : undefined,
      "aria-invalid": Boolean(error),
    })
    : children;
  const controlId = nativeControl ? ((control as ReactElement<{ id?: string }>).props.id || generatedId) : undefined;
  return <div className={`field${full ? " field-full" : ""}`}><label htmlFor={controlId}>{label}{required && <span> *</span>}</label>{control}{error && <div className="field-error" id={errorId} role="alert">{error}</div>}</div>;
}

export function StatCard({ icon, label, value, change, meta, color = "green" }: { icon: ReactNode; label: string; value: string | number; change?: string; meta?: string; color?: "green" | "blue" | "orange" | "red" }) {
  const palette = { green: ["#e6f3ef", "#176b5b"], blue: ["#e8f1f5", "#397c92"], orange: ["#fff2df", "#ad7020"], red: ["#fff0ef", "#b14545"] }[color];
  return <div className="card stat-card" style={{ "--stat-bg": palette[0], "--stat-ink": palette[1], "--stat-color": palette[0] } as React.CSSProperties}><div className="stat-top"><div className="stat-icon">{icon}</div>{change && <span className="stat-change">{change}</span>}</div><div className="stat-label">{label}</div><div className="stat-value">{value}</div>{meta && <div className="stat-meta">{meta}</div>}</div>;
}

export function Tabs({ activeTab, onTabChange, tabs }: { activeTab: string; onTabChange: (tab: string) => void; tabs: Array<{ id: string; label: string }> }) {
  return <div className="tabs">{tabs.map((tab) => (
    <button
      key={tab.id}
      className={`tab ${activeTab === tab.id ? "active" : ""}`}
      onClick={() => onTabChange(tab.id)}
    >
      {tab.label}
    </button>
  ))}</div>;
}
