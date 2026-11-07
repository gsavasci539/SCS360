import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Badge, ErrorState, Field, LoadingState, Modal, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { shortDate } from "../../lib/format";
import { newRequestId } from "../../lib/requestId";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import { checkoutIdentifier, checkoutScope } from "./schoolCheckoutAttempt";

type Event = { request_id: string; action: string; result_status: string; created_at: string };
type Review = { id: string; debt_id: string; student_id: string | null; student_name: string | null;
  amount: string; currency: string; paid_amount: string | null; paid_currency: string | null; status: string;
  review_reason: string | null; provider_payment_id: string | null; provider_transaction_id: string | null;
  verified_at: string | null; created_at: string; remaining_amount: string | null; revision: string;
  can_apply: boolean; can_refund: boolean; environment: string | null; payment_id: string | null; receipt_id: string | null; review_events: Event[] };
type Page = { items: Review[]; page: number; page_size: number; total: number; total_pages: number };
type Command = { request_id: string; expected_revision: string; action: "APPLY" | "REFUND_RECORDED"; reason: string;
  refund_reference?: string; refund_amount?: string; refund_currency?: string; refunded_at?: string };
const base = "/payments/iyzico";
const moneyPattern = /^(?:0|[1-9]\d{0,9})\.\d{2}$/;
function amount(value: unknown): value is string { return typeof value === "string" && moneyPattern.test(value); }
function currency(value: unknown): value is string { return typeof value === "string" && /^[A-Z]{3}$/.test(value); }
function validReview(value: unknown): value is Review {
  if (!value || typeof value !== "object") return false;
  const row = value as Review;
  return Boolean(checkoutIdentifier(row.id)) && Boolean(checkoutIdentifier(row.debt_id)) && amount(row.amount) && currency(row.currency)
    && (row.paid_amount === null || amount(row.paid_amount)) && (row.paid_currency === null || currency(row.paid_currency))
    && (row.remaining_amount === null || amount(row.remaining_amount)) && typeof row.status === "string"
    && typeof row.revision === "string" && /^[0-9a-f]{64}$/i.test(row.revision)
    && typeof row.can_apply === "boolean" && typeof row.can_refund === "boolean" && Array.isArray(row.review_events)
    && row.review_events.every((event) => event && checkoutIdentifier(event.request_id) && typeof event.action === "string"
      && typeof event.result_status === "string" && typeof event.created_at === "string");
}
function cash(value: unknown, unit: unknown) { return amount(value) && currency(unit) ? `${value} ${unit}` : "—"; }
const reviewReasonLabels: Record<string, string> = {
  PROVIDER_INITIALIZE_REJECTED: "Ödeme başlangıcı sağlayıcı tarafından reddedildi",
  DEBT_UNAVAILABLE: "Borç kaydı kullanılamıyor",
  BALANCE_CHANGED: "Borç bakiyesi değişti",
  STUDENT_BALANCE_INVALID: "Öğrencinin bakiye kaydı kontrol edilmeli",
  VERIFIED_PROVIDER_FAILURE: "Ödeme başarısız olarak doğrulandı",
  PROVIDER_REVIEW: "Ödeme sağlayıcı incelemesinde",
  PROOF_MISMATCH: "Doğrulanan ödeme bilgileri işlemle eşleşmiyor",
  EXTERNAL_REFUND_RECORDED: "Dışarıda gerçekleşen iade kaydedildi",
};
function reviewReason(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return typeof value === "string" && Object.hasOwn(reviewReasonLabels, value)
    ? reviewReasonLabels[value] : "İnceleme nedeni için kayıt kontrol edilmeli";
}
function unavailableAction(status: string, canWrite: boolean) {
  if (status === "COMPLETED") return "Ödeme borca işlendi. Bu kayıt için ek mutabakat işlemi bulunmuyor.";
  if (status === "REFUNDED") return "Dışarıda gerçekleşen iade kaydı tamamlandı. Bu kayıt için ek mutabakat işlemi bulunmuyor.";
  return canWrite ? "Bu kayıt için uygulanabilir bir mutabakat işlemi bulunmuyor."
    : "Görüntüleme yetkisi işlem yapma yetkisi vermez.";
}

export function SchoolPaymentReviewPage() {
  const user = useAuthStore((state) => state.user), sessionVersion = useAuthStore((state) => state.sessionVersion);
  const workspace = usePlatformWorkspace((state) => state.workspace), scope = checkoutScope(user, workspace, "staff");
  const canRead = hasPermission(user, "finance.read") || hasPermission(user, "finance.write");
  if (!canRead || !scope) return <ErrorState message="Online ödeme incelemesi için finans yetkisi ve kurum çalışma alanı gerekir." />;
  return <ScopedReviewPage key={JSON.stringify([scope, sessionVersion, [...(user?.permissions || [])].sort()])}
    canWrite={hasPermission(user, "finance.write")} canReceipt={hasPermission(user, "receipt.read")} canReadPayments={hasPermission(user, "finance.read")} />;
}
function ScopedReviewPage({ canWrite, canReceipt, canReadPayments }: { canWrite: boolean; canReceipt: boolean; canReadPayments: boolean }) {
  const [search, setSearch] = useSearchParams(), selected = search.get("checkout");
  const [page, setPage] = useState(1), [revision, setRevision] = useState(0), [data, setData] = useState<Page | null>(null);
  const [loading, setLoading] = useState(true), [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    api.get(`${base}/reviews`, { params: { page, page_size: 20 }, signal: controller.signal }).then((response) => {
      if (controller.signal.aborted) return;
      const value = response.data.data as Page;
      if (!value || !Array.isArray(value.items) || !value.items.every(validReview)
        || ![value.page, value.page_size, value.total, value.total_pages].every((entry) => Number.isInteger(entry) && entry >= 0)) throw new Error("Online ödeme listesi doğrulanamadı.");
      setData(value); if (value.total_pages > 0 && page > value.total_pages) setPage(value.total_pages);
    }).catch((reason) => { if (!controller.signal.aborted) { setData(null); setError(apiMessage(reason)); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, revision]);
  function select(id: string | null) { const next = new URLSearchParams(search); if (id) next.set("checkout", id); else next.delete("checkout"); setSearch(next); }
  return <>
    <PageHeader eyebrow="Finans" title="Online ödeme incelemesi" description="Ödeme alınmış ancak borca işlenmesi için inceleme bekleyen öğrenci ödemeleri.">
      <button className="btn btn-secondary" disabled={loading} onClick={() => setRevision((value) => value + 1)}>Listeyi yenile</button>
      {canReadPayments ? <Link className="btn btn-secondary" to="/finance/payments">Tahsilatlara dön</Link>
        : <Link className="btn btn-secondary" to="/finance/payments/new">Yeni tahsilata git</Link>}
    </PageHeader>
    <p>Bu kuyruk yalnız uzlaştırma bekleyen kayıtları gösterir. Bir kaydı açmak veya sayfayı yenilemek işlem göndermez.</p>
    {error && <ErrorState message={error} retry={() => setRevision((value) => value + 1)} />}
    {loading && <LoadingState />}
    {!loading && data && <section className="card card-pad" aria-label="Uzlaştırma bekleyen online ödemeler">
      {data.items.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Öğrenci</th><th>İşlem tutarı</th><th>Durum</th><th>Ortam</th><th>Tarih</th><th>İşlem</th></tr></thead>
        <tbody>{data.items.map((row) => <tr key={row.id}><td>{row.student_name || "Öğrenci kaydı incelenmeli"}</td><td>{cash(row.amount, row.currency)}</td>
          <td><Badge value={row.status} /></td><td>{row.environment?.toUpperCase() === "SANDBOX" ? "Sandbox / test" : row.environment?.toUpperCase() === "LIVE" ? "Canlı" : "—"}</td>
          <td>{shortDate(row.created_at)}</td><td><button className="btn btn-secondary" onClick={() => select(row.id)}>İncele</button></td></tr>)}</tbody>
      </table></div> : <p>Uzlaştırma bekleyen online ödeme bulunmuyor.</p>}
      <div className="pagination"><span>Toplam {data.total} kayıt · Sayfa {page}/{Math.max(1, data.total_pages)}</span>
        <button className="btn btn-secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Önceki sayfa</button>
        <button className="btn btn-secondary" disabled={page >= data.total_pages} onClick={() => setPage((value) => value + 1)}>Sonraki sayfa</button></div>
    </section>}
    {selected !== null && (checkoutIdentifier(selected) ? <ReviewDialog key={selected} id={selected} canWrite={canWrite} canReceipt={canReceipt}
      onClose={() => select(null)} onChanged={() => setRevision((value) => value + 1)} />
      : <ErrorState message="Online ödeme kimliği geçersiz." />)}
  </>;
}
function ReviewDialog({ id, canWrite, canReceipt, onClose, onChanged }: { id: string; canWrite: boolean; canReceipt: boolean; onClose: () => void; onChanged: () => void }) {
  const [row, setRow] = useState<Review | null>(null), [loading, setLoading] = useState(true), [error, setError] = useState("");
  const [revision, setRevision] = useState(0), [action, setAction] = useState<Command["action"]>("APPLY");
  const [reason, setReason] = useState(""), [reference, setReference] = useState(""), [refundAmount, setRefundAmount] = useState("");
  const [refundCurrency, setRefundCurrency] = useState(""), [refundedAt, setRefundedAt] = useState("");
  const [pending, setPending] = useState<Command | null>(null), [busy, setBusy] = useState(false), [stale, setStale] = useState(false), [acknowledge, setAcknowledge] = useState(false), [message, setMessage] = useState("");
  const operation = useRef(new AbortController()), lock = useRef(false);
  useEffect(() => { const controller = new AbortController(); operation.current = controller; return () => controller.abort(); }, []);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    api.get(`${base}/checkouts/${id}/review`, { signal: controller.signal }).then((response) => {
      if (controller.signal.aborted) return;
      const value: unknown = response.data.data;
      if (!validReview(value) || value.id !== id) throw new Error("Online ödeme detayı doğrulanamadı.");
      setRow(value);
      if (pending && value.review_events.some((event) => event.request_id === pending.request_id)) {
        setPending(null); setStale(false); setAcknowledge(false); setMessage("Bu isteğin sonucu işlem geçmişinde doğrulandı."); onChanged();
      } else {
        if (value.status !== "PAID_REVIEW") onChanged();
        if (stale) setAcknowledge(true);
      }
      if (!pending) {
        setAction(value.can_apply ? "APPLY" : "REFUND_RECORDED");
        setRefundAmount(value.paid_amount || ""); setRefundCurrency(value.paid_currency || "");
      }
    }).catch((failure) => { if (!controller.signal.aborted) { setRow(null); setError(apiMessage(failure)); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [id, revision]);
  async function send(command: Command) {
    if (lock.current || operation.current.signal.aborted) return;
    lock.current = true; setBusy(true); setError(""); setMessage("");
    try {
      const response = await api.post(`${base}/checkouts/${id}/review`, command, { signal: operation.current.signal });
      if (operation.current.signal.aborted) return;
      const value: unknown = response.data.data;
      if (!validReview(value) || value.id !== id || !value.review_events.some((event) => event.request_id === command.request_id)) throw new Error("Mutabakat isteğinin sonucu doğrulanamadı. Aynı isteği tekrar kontrol edin.");
      setRow(value); setPending(null); setStale(false); setAcknowledge(false); setReason(""); setReference("");
      setMessage(command.action === "REFUND_RECORDED" ? "Dışarıda yapılan iade kaydı doğrulandı. Bu ekran para göndermez." : "Mutabakat isteğinin sonucu kaydedildi."); onChanged();
    } catch (failure) {
      if (operation.current.signal.aborted) return;
      setError(apiMessage(failure));
      const status = (failure as { response?: { status?: number } })?.response?.status;
      if (status === 422) setPending(null);
      if (status === 409 || status === 403) { if (status === 403) setPending(null); setStale(true); setAcknowledge(false); setRevision((value) => value + 1); }
    } finally { if (!operation.current.signal.aborted) { lock.current = false; setBusy(false); } }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!row || !canWrite || pending || busy || loading || stale) return;
    if (reason.trim().length < 10 || reason.trim().length > 1000) { setError("Kontrol açıklaması 10–1000 karakter olmalı."); return; }
    if (action === "APPLY" && !row.can_apply || action === "REFUND_RECORDED" && !row.can_refund) return;
    const command: Command = { request_id: newRequestId(), expected_revision: row.revision, action, reason: reason.trim() };
    if (action === "REFUND_RECORDED") {
      const instant = new Date(refundedAt);
      if (refundAmount !== row.paid_amount || refundCurrency !== row.paid_currency) { setError("İade tutarı ve para birimi doğrulanmış sağlayıcı kaydıyla aynı olmalı."); return; }
      if (!reference.trim() || reference.trim().length > 240 || !amount(refundAmount) || Number(refundAmount) <= 0 || !currency(refundCurrency)
        || !Number.isFinite(instant.getTime()) || instant.getTime() > Date.now()) { setError("İade referansını, tam tutarı (25.00), para birimini ve geçmiş iade tarihini kontrol edin."); return; }
      Object.assign(command, { refund_reference: reference.trim(), refund_amount: refundAmount, refund_currency: refundCurrency, refunded_at: instant.toISOString() });
    }
    setPending(command); await send(command);
  }
  const writable = canWrite && row && (row.can_apply || row.can_refund);
  return <Modal open title="Online ödeme incelemesi" description="Doğrulanmış ödeme ve borç bakiyesini karşılaştırın." onClose={onClose}>
    {loading && <LoadingState />}{error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    {row && <>
      <p><strong>{row.student_name || "Öğrenci kaydı incelenmeli"}</strong> · <Badge value={row.status} /></p>
      <dl className="detail-list"><div><dt>İşlem tutarı</dt><dd>{cash(row.amount, row.currency)}</dd></div>
        <div><dt>Sağlayıcıda doğrulanan</dt><dd>{cash(row.paid_amount, row.paid_currency)}</dd></div>
        <div><dt>Güncel kalan borç</dt><dd>{cash(row.remaining_amount, row.currency)}</dd></div>
        <div><dt>İnceleme nedeni</dt><dd>{reviewReason(row.review_reason)}</dd></div>
        <div><dt>Sağlayıcı işlem referansı</dt><dd style={{ overflowWrap: "anywhere" }}>{row.provider_payment_id || "—"}</dd></div>
        <div><dt>Doğrulama tarihi</dt><dd>{shortDate(row.verified_at)}</dd></div></dl>
      {row.receipt_id && canReceipt && <p><Link className="btn btn-secondary" to={`/finance/receipts/${row.receipt_id}`}>Makbuzu aç</Link></p>}
      {row.review_events.length > 0 && <section aria-label="Mutabakat işlem geçmişi"><h3>Mutabakat işlem geçmişi</h3>
        {row.review_events.map((event) => <p key={event.request_id}>{event.action === "APPLY" ? "Borca işleme" : "Dış iade kaydı"} · <Badge value={event.result_status} /> · {shortDate(event.created_at)}</p>)}
      </section>}
      {!writable && !pending && <p>{unavailableAction(row.status, canWrite)}</p>}
      {pending && <p>İstek kimliği bu pencere açıkken korunur. Sonuç belirsizken bilgileri değiştirmeyin veya ikinci işlem oluşturmayın.</p>}
      {pending && !stale && <button className="btn btn-primary" disabled={busy || loading} onClick={() => send(pending)}>Aynı mutabakat isteğini tekrar dene</button>}
      {stale && <p role="status">Kayıt değişmiş veya bu istek mevcut kayıtla çakışıyor. Güncel bilgileri yeniden inceleyin.</p>}
      {acknowledge && <button className="btn btn-secondary" disabled={busy || loading} onClick={() => { setPending(null); setStale(false); setAcknowledge(false); setReason(""); setAction(row.can_apply ? "APPLY" : "REFUND_RECORDED"); setRefundAmount(row.paid_amount || ""); setRefundCurrency(row.paid_currency || ""); setMessage("Güncel kayıt açıldı. İşlem göndermek için bilgileri yeniden inceleyip açıkça kaydedin."); }}>Güncel kaydı inceledim</button>}
      {writable && !pending && !stale && <form aria-label="Okul ödemesi mutabakatı" onSubmit={submit}><fieldset disabled={busy || loading} style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
        <Field label="Mutabakat işlemi"><select value={action} onChange={(event) => setAction(event.target.value as Command["action"])}>
          {row.can_apply && <option value="APPLY">Doğrulanan ödemeyi borca işle</option>}{row.can_refund && <option value="REFUND_RECORDED">Dışarıda yapılan iadeyi kaydet</option>}
        </select></Field>
        {action === "REFUND_RECORDED" && <><p>Önce banka veya sağlayıcı panelinde gerçekleşmiş tam iadeyi doğrulayın. Bu düğme para göndermez ve sağlayıcıya iade isteği yapmaz.</p>
          <Field label="Dış iade referansı"><input value={reference} maxLength={240} required onChange={(event) => setReference(event.target.value)} /></Field>
          <Field label="Tam iade tutarı"><input inputMode="decimal" value={refundAmount} required placeholder="25.00" onChange={(event) => setRefundAmount(event.target.value)} /></Field>
          <Field label="İade para birimi"><input value={refundCurrency} maxLength={3} required onChange={(event) => setRefundCurrency(event.target.value.toUpperCase())} /></Field>
          <Field label="Gerçekleşen iade tarihi"><input type="datetime-local" value={refundedAt} required onChange={(event) => setRefundedAt(event.target.value)} /></Field></>}
        <Field label="Kontrol açıklaması"><textarea value={reason} minLength={10} maxLength={1000} required onChange={(event) => setReason(event.target.value)} /></Field>
        <button className="btn btn-primary">{action === "APPLY" ? "Doğrulanan ödemeyi borca işle" : "Dış iade kaydını kaydet"}</button>
      </fieldset></form>}
    </>}
    <p className="cell-sub">Sayfa yenilendiğinde güncel detay ve işlem geçmişi yüklenir; yeni istek kendiliğinden gönderilmez. Açıklama ve iade referansı tarayıcı depolamasına kaydedilmez.</p>
    <button className="btn btn-secondary" disabled={busy || loading} onClick={() => setRevision((value) => value + 1)}>Güncel kaydı yükle</button>
  </Modal>;
}
