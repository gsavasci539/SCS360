import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Brand } from "../../components/Brand";
import { Badge, ErrorState, LoadingState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { getHomePath } from "../../lib/home";
import { isOrganizationAccess, packagePrice } from "../../lib/subscription";
import { newRequestId } from "../../lib/requestId";
import { useAuthStore } from "../../stores/auth";
import type { DataRecord, OrganizationAccess } from "../../types/api";
import { SubscriptionCheckout } from "./SubscriptionCheckout";

interface Information { access: OrganizationAccess; can_manage: boolean; package?: DataRecord | null; usage?: Record<string, number>; online_payment_available?: boolean; payment_instructions?: string; support_email?: string }
const text = (value: unknown) => String(value ?? "");
const stamp = (value: unknown) => value ? new Date(text(value)).toLocaleString("tr-TR") : "—";
const labels: Record<string, string> = { PENDING_PAYMENT: "Üyeliğinizi başlatın", PLATFORM: "Platform yönetimi", LEGACY: "Mevcut kurum: paket tanımlanmamış", ACTIVE: "Üyelik etkin", GRACE: "Ödeme için ek süre", PAST_DUE: "Üyelik ödemesi bekleniyor", SUSPENDED: "Kurum hesabı kapalı", UNCONFIGURED: "Üyelik kurulumu bekleniyor", UNASSIGNED: "Kurum bağlantısı gerekli", REVIEW_REQUIRED: "Üyelik incelemede", NOT_STARTED: "Üyelik dönemi henüz başlamadı" };

export function SubscriptionPage() {
  const [query] = useSearchParams();
  const [info, setInfo] = useState<Information | null>(null), [plans, setPlans] = useState<DataRecord[]>([]), [invoices, setInvoices] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true), [error, setError] = useState(""), [revision, setRevision] = useState(0), [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false), [planId, setPlanId] = useState(() => query.get("paket") || ""), [requestId, setRequestId] = useState(() => newRequestId());
  const [checkoutId, setCheckoutId] = useState<string | null>(null);
  const user = useAuthStore((state) => state.user), refreshToken = useAuthStore((state) => state.refreshToken);
  const { showToast } = useToast(); const navigate = useNavigate();
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    (async () => {
      try {
        const current: Information = (await api.get("/subscription/access", { signal: controller.signal })).data.data;
        if (!isOrganizationAccess(current.access)) throw new Error("Üyelik bilgisi alınamadı");
        if (controller.signal.aborted) return;
        setInfo(current);
        const account = useAuthStore.getState().user;
        if (account) useAuthStore.getState().setUser({ ...account, organization_access: current.access });
        if (current.can_manage && current.access.status !== "PLATFORM") {
          const [catalog, history] = await Promise.all([api.get("/subscription/plans", { signal: controller.signal }),
            api.get("/subscription/invoices", { params: { limit: 21, offset: (page - 1) * 20 }, signal: controller.signal })]);
          if (controller.signal.aborted) return;
          setPlans(catalog.data.data || []); setInvoices(history.data.data || []);
        } else { setPlans([]); setInvoices([]); }
        setError("");
      } catch (reason) { if (!controller.signal.aborted) setError(apiMessage(reason)); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
  }, [revision, page]);
  const refresh = () => setRevision((value) => value + 1);
  async function logout() {
    try { if (refreshToken) await api.post("/auth/logout", { refresh_token: refreshToken }); } catch { /* Local logout remains available offline. */ } finally { useAuthStore.getState().clearSession(); navigate("/login", { replace: true }); }
  }
  async function requestInvoice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy || !planId) return; setBusy(true);
    try { await api.post("/subscription/invoices", { plan_id: planId, request_id: requestId }); setRequestId(newRequestId()); setPage(1); refresh(); showToast(firstPurchase ? "Üyelik ödeme talebi oluşturuldu" : "Yenileme talebi oluşturuldu"); }
    catch (reason) { showToast("Talep oluşturulamadı", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function cancel(row: DataRecord) {
    if (busy) return; setBusy(true);
    try { await api.post(`/subscription/invoices/${row.id}/cancel`); refresh(); showToast("Ödeme talebi iptal edildi"); }
    catch (reason) { showToast("Talep iptal edilemedi", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function paymentAction(row: DataRecord, action: "payment-status" | "activate-free") {
    if (busy) return; setBusy(true);
    try { const response = action === "payment-status" ? await api.post(`/subscription/invoices/${row.id}/payment-status`) : await api.post(`/subscription/invoices/${row.id}/activate-free`); refresh();
      showToast(response.data.data.invoice?.status === "PAID" ? "Üyelik ödemesi tamamlandı" : "Ödeme durumu güncellendi"); }
    catch (reason) { showToast("İşlem tamamlanamadı", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  const firstPurchase = info?.access.status === "PENDING_PAYMENT";
  const suspended = info && ["SUSPENDED", "UNASSIGNED", "REVIEW_REQUIRED", "NOT_STARTED"].includes(info.access.status);
  const checkoutInvoice = invoices.find((row) => row.id === checkoutId);
  return <main className="saas-workspace" style={{ maxWidth: 1040, margin: "32px auto", padding: "0 16px 50px" }}>
    <Brand subtitle="Kurumsal üyelik" /><div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap", marginTop: 24 }}><h1>Üyelik ve Ödeme</h1><button className="btn btn-secondary" onClick={refresh} disabled={busy || loading}>Üyelik durumunu yenile</button><button className="btn btn-secondary" onClick={logout} disabled={busy}>Oturumu kapat</button></div>
    {error && <ErrorState message={error} retry={refresh} />}{loading && !info && <LoadingState label="Üyelik bilgileri yükleniyor" />}
    {info && <>
      <section className="card card-pad" aria-label="Üyelik durumu"><h2>{labels[info.access.status] || info.access.status}</h2>
        {info.access.warning && <p role="alert">{info.access.warning}</p>}
        {info.access.period_end && <p>Üyelik bitişi: {stamp(info.access.period_end)} · Ek süre sonu: {stamp(info.access.grace_end)}</p>}
        {!info.access.restricted && user && <Link className="btn btn-primary" to={getHomePath({ ...user, organization_access: info.access })}>Çalışma alanına dön</Link>}
        {info.access.status === "PLATFORM" && <Link className="btn btn-primary" to="/platform">Kurum ve paket yönetimine git</Link>}
        {!info.can_manage && <p>Üyeliğinizin yenilenmesi için okul veya kurum sahibinizle iletişime geçin.</p>}
      </section>
      {info.can_manage && info.access.status !== "PLATFORM" && <>
        <section className="card card-pad" aria-label="Paket kullanımı" style={{ marginTop: 18 }}><h2>{text(info.package?.name) || "Paket tanımlanmamış"}</h2>
          {info.package && <p>{packagePrice(info.package.price, info.package.currency)} · {text(info.package.period_months)} aylık paket</p>}
          <p>Şube: {info.usage?.branch_limit ?? 0} / {text(info.package?.branch_limit) || "—"} · Öğrenci: {info.usage?.student_limit ?? 0} / {text(info.package?.student_limit) || "—"} · Kullanıcı: {info.usage?.user_limit ?? 0} / {text(info.package?.user_limit) || "—"}</p>
        </section>
        {!suspended && <section className="card card-pad" aria-label={firstPurchase ? "İlk üyelik ödemesi" : "Üyelik yenileme"} style={{ marginTop: 18 }}><h2>{firstPurchase ? "Üyeliği başlat" : "Üyeliği yenile"}</h2>
          <form onSubmit={requestInvoice}><fieldset disabled={busy || loading} style={{ border: 0, padding: 0, display: "grid", gap: 12 }}>
            <label>{firstPurchase ? "Üyelik paketi" : "Yenileme paketi"}<select className="filter-select" value={planId} onChange={(event) => { setPlanId(event.target.value); setRequestId(newRequestId()); }} required><option value="">Paket seçin</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{text(plan.name)} · {packagePrice(plan.price, plan.currency)} / {text(plan.period_months)} ay · {text(plan.branch_limit)} şube / {text(plan.student_limit)} öğrenci / {text(plan.user_limit)} kullanıcı</option>)}</select></label>
            <button className="btn btn-primary">{firstPurchase ? "Ödeme talebi oluştur" : "Yenileme talebi oluştur"}</button>
          </fieldset></form>
          {!info.online_payment_available && <p>Online ödeme şu anda açık değil. Ödeme için platform yöneticisiyle iletişime geçin.</p>}
          {info.payment_instructions && <p style={{ whiteSpace: "pre-wrap" }}>{info.payment_instructions}</p>}
          {info.support_email && <p>Üyelik desteği: {info.support_email}</p>}
        </section>}
        <section className="card card-pad" aria-label="Üyelik ödeme geçmişi" style={{ marginTop: 18 }}><h2>Yenileme ve ödeme talepleri</h2>
          {!invoices.length ? <p>Henüz ödeme talebi yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Paket</th><th>Tutar</th><th>Üyelik aralığı</th><th>Durum</th><th>İşlem</th></tr></thead><tbody>{invoices.slice(0, 20).map((row) => <tr key={row.id}><td>{text(row.package_name)}</td><td>{packagePrice(row.amount, row.currency)}</td><td>{stamp(row.period_start)} – {stamp(row.period_end)}</td><td><Badge value={row.status} />{row.paid_at && <p>{stamp(row.paid_at)}</p>}</td><td>
            {row.status === "PENDING" && <p>Talep geçerliliği: {stamp(row.valid_until)}</p>}
            {row.can_cancel !== false && row.status === "PENDING" && <button className="btn btn-secondary" disabled={busy || Boolean(suspended)} onClick={() => cancel(row)}>Talebi iptal et</button>}
            {!suspended && row.status === "PENDING" && row.can_cancel && Number(row.amount) === 0 && <button className="btn btn-primary" disabled={busy} onClick={() => paymentAction(row, "activate-free")}>Ücretsiz paketi etkinleştir</button>}
            {!suspended && info.online_payment_available && (row.can_checkout || row.can_resume) && <button className="btn btn-primary" disabled={busy} onClick={() => setCheckoutId(row.id)}>{row.can_resume ? "Ödemeye devam et" : "Kartla öde"}</button>}
            {["INITIALIZING", "PENDING", "REVIEW"].includes(text(row.checkout_status)) && <button className="btn btn-secondary" disabled={busy} onClick={() => paymentAction(row, "payment-status")}>Ödeme sonucunu kontrol et</button>}
            {row.status === "PAYMENT_REVIEW" && <p>Ödemeniz sağlayıcının incelemesinde.</p>}
            {row.status === "PAID_REVIEW" && <p>Ödeme alındı; platform yöneticisi üyeliğinizi kontrol ediyor.</p>}
          </td></tr>)}</tbody></table></div>}
          <nav aria-label="Üyelik ödeme sayfaları" style={{ display: "flex", gap: 12, marginTop: 12 }}><button className="btn btn-secondary" disabled={busy || loading || page === 1} onClick={() => setPage((value) => value - 1)}>Önceki</button><span>Sayfa {page}</span><button className="btn btn-secondary" disabled={busy || loading || invoices.length <= 20} onClick={() => setPage((value) => value + 1)}>Sonraki</button></nav>
        </section>
        {checkoutInvoice && !suspended && checkoutInvoice.status === "PENDING" && <SubscriptionCheckout key={checkoutInvoice.id} invoice={checkoutInvoice} onClose={() => setCheckoutId(null)} onRefresh={refresh} />}
      </>}
    </>}
  </main>;
}
