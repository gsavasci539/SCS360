import { useState, type FormEvent } from "react";
import { api, apiMessage } from "../../lib/api";
import { newRequestId } from "../../lib/requestId";
import { packagePrice } from "../../lib/subscription";
import type { DataRecord } from "../../types/api";

export function PaymentReview({ invoice, onDone, onClose }: { invoice: DataRecord; onDone: () => void; onClose: () => void }) {
  const [action, setAction] = useState("APPLY"), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const [requestId, setRequestId] = useState(newRequestId);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const values = new FormData(event.currentTarget); setBusy(true); setError("");
    try {
      const body = action === "APPLY" ? { period_start: new Date(String(values.get("period_start"))).toISOString(), period_end: new Date(String(values.get("period_end"))).toISOString() }
        : { refund_reference: values.get("refund_reference") };
      await api.post(`/platform/invoices/${invoice.id}/review`, { ...body, action, reason: values.get("reason"), request_id: requestId }); onDone();
    } catch (reason) { setError(apiMessage(reason)); } finally { setBusy(false); }
  }
  return <section className="card card-pad" aria-label="Üyelik ödemesini uzlaştır" style={{ marginTop: 18 }}>
    <h2>Ödeme uzlaştırması</h2><p>{String(invoice.organization_name ?? "")} · {String(invoice.package_name ?? "")}</p>
    <p>Talep: {packagePrice(invoice.amount, invoice.currency)} · Sağlayıcı: {packagePrice(invoice.provider_paid_amount, invoice.provider_currency)} · İşlem: {String(invoice.provider_payment_id ?? "—")}</p>
    {error && <p role="alert">{error}</p>}
    <form onSubmit={submit} onChange={() => setRequestId(newRequestId())}><fieldset disabled={busy} style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
      <label>Uzlaştırma işlemi<select className="filter-select" value={action} onChange={(event) => setAction(event.target.value)}><option value="APPLY">Doğrulanan ödemeyi üyeliğe uygula</option><option value="REFUND_RECORDED">Dışarıda yapılan iadeyi kaydet</option></select></label>
      {action === "APPLY" ? <><label>Uzlaştırılan başlangıç<input className="filter-select" type="datetime-local" name="period_start" required /></label><label>Uzlaştırılan bitiş<input className="filter-select" type="datetime-local" name="period_end" required /></label></>
        : <><p>Önce bankada veya sağlayıcı panelinde yapılan iadeyi kontrol edin. Bu işlem para göndermez.</p><label>Doğrulanan iade referansı<input className="filter-select" name="refund_reference" required maxLength={240} /></label></>}
      <label>Kontrol açıklaması<textarea className="filter-select" name="reason" minLength={10} maxLength={1000} required /></label>
      <button className="btn btn-primary">Uzlaştırmayı kaydet</button><button className="btn btn-secondary" type="button" onClick={onClose}>Kapat</button>
    </fieldset></form>
  </section>;
}
