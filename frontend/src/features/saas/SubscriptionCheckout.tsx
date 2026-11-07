import { useEffect, useRef, useState, type FormEvent } from "react";
import { api, apiMessage } from "../../lib/api";
import { newRequestId } from "../../lib/requestId";
import { packagePrice } from "../../lib/subscription";
import type { DataRecord } from "../../types/api";

export { hostedPaymentUrl as subscriptionPaymentUrl } from "../../lib/hostedPayment";
import { hostedPaymentUrl as subscriptionPaymentUrl } from "../../lib/hostedPayment";

export function SubscriptionCheckout({ invoice, onClose, onRefresh }: { invoice: DataRecord; onClose: () => void; onRefresh: () => void }) {
  const [busy, setBusy] = useState(false), [error, setError] = useState(""), [url, setUrl] = useState<string | null>(null), [message, setMessage] = useState("");
  const [requestId, setRequestId] = useState(newRequestId);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    const body = Object.fromEntries(new FormData(event.currentTarget));
    await send("checkout", { ...body, request_id: requestId });
  }
  async function send(action: "checkout" | "resume" | "payment-status", body?: Record<string, unknown>) {
    if (busy) return; setBusy(true); setError(""); setMessage("");
    try {
      const requests = {
        checkout: () => api.post(`/subscription/invoices/${invoice.id}/checkout`, body),
        resume: () => api.post(`/subscription/invoices/${invoice.id}/resume`, body),
        "payment-status": () => api.post(`/subscription/invoices/${invoice.id}/payment-status`, body),
      };
      const response = await requests[action]();
      const data = response.data.data;
      if (data.checkout_url) {
        const validated = subscriptionPaymentUrl(data.checkout_url);
        if (!validated) throw new Error("Ödeme sayfası doğrulanamadı");
        setUrl(validated);
      } else if (data.status === "FAILED") {
        setRequestId(newRequestId()); setUrl(null); setMessage("Ödeme tamamlanmadı. Yeniden deneyebilirsiniz."); onRefresh();
      } else if (data.invoice?.status === "PAID") { onRefresh(); onClose(); }
      else { setMessage(data.status === "INITIALIZING" ? "Ödeme oturumu hazırlanıyor. Sonucu kontrol edin." : "Ödeme sonucu henüz kesinleşmedi. Sonucu kontrol edin."); onRefresh(); }
    } catch (reason) { setError(apiMessage(reason)); } finally { setBusy(false); }
  }
  return <section className="card card-pad" aria-label="Güvenli üyelik ödemesi" style={{ marginTop: 18 }}>
    <h2 ref={heading} tabIndex={-1}>Üyelik ödemesi · {String(invoice.package_name ?? "")}</h2>
    <p>{packagePrice(invoice.amount, invoice.currency)}</p>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {url ? <p><a className="btn btn-primary" href={url} referrerPolicy="no-referrer">Güvenli ödeme sayfasını aç</a></p>
      : invoice.can_resume ? <button className="btn btn-primary" disabled={busy} onClick={() => send("resume")}>Mevcut ödeme sayfasını getir</button>
      : <form onSubmit={submit} onChange={() => setRequestId(newRequestId())} aria-label="Üyelik ödeme bilgileri"><fieldset disabled={busy} style={{ display: "grid", gap: 12, border: 0, padding: 0 }}>
        <p>Fatura ve ödeme doğrulaması için bilgilerinizi girin. Kart bilgileri güvenli ödeme sayfasında alınır.</p>
        <label>Kimlik veya vergi numarası<input className="filter-select" name="identity_number" required maxLength={50} autoComplete="off" /></label>
        <label>Telefon<input className="filter-select" type="tel" name="phone" required minLength={5} maxLength={30} autoComplete="tel" /></label>
        <label>Fatura adresi<input className="filter-select" name="address" required minLength={5} maxLength={500} autoComplete="street-address" /></label>
        <label>Şehir<input className="filter-select" name="city" required maxLength={100} autoComplete="address-level2" /></label>
        <label>Ülke<input className="filter-select" name="country" required maxLength={100} autoComplete="country-name" /></label>
        <button className="btn btn-primary">Ödeme sayfasını hazırla</button>
      </fieldset></form>}
    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 12 }}>
      <button className="btn btn-secondary" disabled={busy} onClick={() => send("payment-status")}>Ödeme sonucunu kontrol et</button>
      <button className="btn btn-secondary" disabled={busy} onClick={onClose}>Kapat</button>
    </div>
  </section>;
}
