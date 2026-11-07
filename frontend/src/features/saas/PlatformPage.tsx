import { useEffect, useState, type FormEvent } from "react";
import { PageHeader, Badge, ErrorState, LoadingState } from "../../components/ui";
import { useToast } from "../../components/Toast";
import { api, apiMessage } from "../../lib/api";
import { packagePrice } from "../../lib/subscription";
import { newRequestId } from "../../lib/requestId";
import type { DataRecord, OrganizationAccess } from "../../types/api";
import { useNavigate } from "react-router-dom";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import { useAuthStore } from "../../stores/auth";
import { PaymentReview } from "./PaymentReview";
import { PaymentReadinessPanel } from "./PaymentReadinessPanel";

interface Tenant { id: string; name: string; is_active: boolean; access: OrganizationAccess; package: DataRecord | null; usage: Record<string, number>; owner_user_id: string | null; period_start: string | null }
interface Person { id: string; name: string; email: string }
const text = (value: unknown) => String(value ?? "");
const stamp = (value: unknown) => value ? new Date(text(value)).toLocaleString("tr-TR") : "—";
const inputTime = (value: unknown) => {
  if (!value) return ""; const instant = new Date(text(value));
  return new Date(instant.getTime() - instant.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const group = { border: 0, padding: 0, display: "grid", gap: 12 };

export function PlatformPage() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<DataRecord[]>([]), [tenants, setTenants] = useState<Tenant[]>([]), [invoices, setInvoices] = useState<DataRecord[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({}), [people, setPeople] = useState<Person[]>([]);
  const [billingOwner, setBillingOwner] = useState("");
  const [loading, setLoading] = useState(true), [error, setError] = useState(""), [busy, setBusy] = useState(false), [revision, setRevision] = useState(0);
  const [search, setSearch] = useState(""), [page, setPage] = useState(1), [invoicePage, setInvoicePage] = useState(1);
  const [editingPlan, setEditingPlan] = useState<DataRecord | null>(null), [selected, setSelected] = useState<Tenant | null>(null), [receipt, setReceipt] = useState<DataRecord | null>(null);
  const [review, setReview] = useState<DataRecord | null>(null);
  const [requestId, setRequestId] = useState(() => newRequestId()), [clock] = useState(() => inputTime(new Date().toISOString()));
  const { showToast } = useToast(); const refresh = () => setRevision((value) => value + 1);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    Promise.all([api.get("/platform/plans", { signal: controller.signal }), api.get("/platform/summary", { signal: controller.signal }),
      api.get("/platform/tenants", { params: { search, limit: 21, offset: (page - 1) * 20 }, signal: controller.signal }),
      api.get("/platform/invoices", { params: { limit: 21, offset: (invoicePage - 1) * 20 }, signal: controller.signal })])
      .then(([catalog, totals, schools, payments]) => {
        if (controller.signal.aborted) return; setPlans(catalog.data.data || []); setSummary(totals.data.data || {});
        setTenants(schools.data.data || []); setInvoices(payments.data.data || []); setError("");
        setSelected((current) => current ? schools.data.data.find((row: Tenant) => row.id === current.id) || current : null);
      }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [search, page, invoicePage, revision]);
  useEffect(() => {
    const controller = new AbortController(); setPeople([]);
    setBillingOwner(selected?.owner_user_id || "");
    if (selected) api.get(`/platform/tenants/${selected.id}/users`, { signal: controller.signal }).then((response) => {
      if (!controller.signal.aborted) setPeople(response.data.data || []);
    }).catch((reason) => { if (!controller.signal.aborted) showToast("Kurum kullanıcıları alınamadı", apiMessage(reason), "error"); });
    return () => controller.abort();
  }, [selected?.id, selected?.owner_user_id, revision, showToast]);

  async function savePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; const form = event.currentTarget, data = new FormData(form); setBusy(true);
    const body = { code: data.get("code"), name: data.get("name"), branch_limit: Number(data.get("branch_limit")), student_limit: Number(data.get("student_limit")),
      user_limit: Number(data.get("user_limit")), price: data.get("price"), currency: data.get("currency"), period_months: Number(data.get("period_months")), is_active: data.get("is_active") === "true" };
    try { if (editingPlan) await api.put(`/platform/plans/${editingPlan.id}`, body); else await api.post("/platform/plans", body); setEditingPlan(null); form.reset(); refresh(); showToast("Paket kaydedildi"); }
    catch (reason) { showToast("Paket kaydedilemedi", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function provision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return; const form = event.currentTarget, data = new FormData(form); setBusy(true);
    const body: Record<string, unknown> = Object.fromEntries(data); body.request_id = requestId;
    try { for (const key of ["period_start", "period_end"]) { const value = text(body[key]); if (value) body[key] = new Date(value).toISOString(); else delete body[key]; }
      const response = await api.post("/platform/tenants", body); form.reset(); setRequestId(newRequestId()); setPage(1); refresh(); showToast("Kurum ve sahibi hesabı oluşturuldu", response.data.data.owner_email); }
    catch (reason) { showToast("Kurum oluşturulamadı", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function membership(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy || !selected) return; const data = new FormData(event.currentTarget); setBusy(true);
    try { await api.put(`/platform/tenants/${selected.id}/subscription`, { plan_id: data.get("plan_id"),
      period_start: new Date(text(data.get("period_start"))).toISOString(), period_end: new Date(text(data.get("period_end"))).toISOString(),
      admin_status: data.get("admin_status"), owner_user_id: data.get("owner_user_id") || null }); refresh(); showToast("Kurum üyeliği güncellendi"); }
    catch (reason) { showToast("Üyelik güncellenemedi", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function toggle(row: Tenant) {
    if (busy) return; setBusy(true);
    try { await api.patch(`/platform/tenants/${row.id}/status`, { is_active: !row.is_active }); refresh(); showToast(row.is_active ? "Kurum hesabı kapatıldı" : "Kurum hesabı açıldı"); }
    catch (reason) { showToast("Hesap durumu değiştirilemedi", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function openWorkspace(row: Tenant) {
    if (busy) return; setBusy(true);
    try { const response = await api.get(`/platform/tenants/${row.id}/workspace`); const operator = useAuthStore.getState().user;
      if (!operator?.is_super_admin) throw new Error("Platform oturumu gerekli");
      usePlatformWorkspace.getState().select({ ...response.data.data, operatorId: operator.id }); navigate("/dashboard");
    } catch (reason) { showToast("Kurum çalışma alanı açılamadı", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function verifyReceipt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy || !receipt) return; const data = new FormData(event.currentTarget); setBusy(true);
    try { await api.post(`/platform/invoices/${receipt.id}/settle`, { payment_reference: data.get("payment_reference"), amount: data.get("amount"),
      currency: data.get("currency"), ...(data.get("paid_at") ? { paid_at: new Date(text(data.get("paid_at"))).toISOString() } : {}) });
      setReceipt(null); refresh(); showToast("Doğrulanan ödeme kaydedildi"); }
    catch (reason) { showToast("Ödeme doğrulanamadı", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  async function paymentStatus(row: DataRecord) {
    if (busy) return; setBusy(true);
    try { await api.post(`/platform/invoices/${row.id}/payment-status`); refresh(); showToast("Ödeme durumu güncellendi"); }
    catch (reason) { showToast("Ödeme durumu alınamadı", apiMessage(reason), "error"); } finally { setBusy(false); }
  }
  function field(label: string, name: string, value: unknown, max: number, type = "text", required = false) {
    return <label>{label}<input className="filter-select" name={name} defaultValue={text(value)} type={type} maxLength={max} required={required} /></label>;
  }
  function pager(label: string, current: number, length: number, set: (value: number) => void) {
    return <nav aria-label={label} style={{ display: "flex", gap: 12, marginTop: 14 }}><button className="btn btn-secondary" disabled={busy || loading || current === 1} onClick={() => set(current - 1)}>Önceki</button><span>Sayfa {current}</span><button className="btn btn-secondary" disabled={busy || loading || length <= 20} onClick={() => set(current + 1)}>Sonraki</button></nav>;
  }
  return <div className="saas-workspace">
    <PageHeader eyebrow="SCS360 Platform" title="Kurumlar ve Üyelikler" description="Okul hesapları, paket sınırları ve üyelik ödemeleri." />
    <section className="card card-pad" aria-label="Platform özeti"><p>Kurum: {summary.total_institutions ?? 0} · Etkin üyelik: {summary.active_memberships ?? 0} · Ek sürede: {summary.grace_memberships ?? 0} · Erişimi kapalı: {summary.restricted_institutions ?? 0} · Paketsiz mevcut kurum: {summary.legacy_institutions ?? 0} · Bekleyen ödeme talebi: {summary.pending_invoices ?? 0}</p></section>
    <PaymentReadinessPanel />
    {error && <ErrorState message={error} retry={refresh} />}{loading && !tenants.length && <LoadingState />}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 330px), 1fr))", gap: 18, marginTop: 18 }}>
      <section className="card card-pad"><h2>{editingPlan ? "Paketi düzenle" : "Paket oluştur"}</h2><form aria-label="Paket yönetimi" key={editingPlan?.id || "new-plan"} onSubmit={savePlan}><fieldset disabled={busy} style={group}>
        {field("Paket kodu", "code", editingPlan?.code, 50, "text", true)}{field("Paket adı", "name", editingPlan?.name, 120, "text", true)}
        {[["Şube sınırı", "branch_limit"], ["Öğrenci sınırı", "student_limit"], ["Kullanıcı sınırı", "user_limit"]].map(([label, name]) => <label key={name}>{label}<input className="filter-select" name={name} type="number" min={1} max={2147483647} step={1} defaultValue={text(editingPlan?.[name])} required /></label>)}
        <label>Paket fiyatı<input className="filter-select" name="price" type="number" min={0} max="9999999999.99" step="0.01" defaultValue={text(editingPlan?.price)} required /></label>
        <label>Para birimi<select className="filter-select" name="currency" defaultValue={text(editingPlan?.currency) || "TRY"}>{["TRY", "USD", "EUR"].map((value) => <option key={value}>{value}</option>)}</select></label>
        <label>Paket dönemi<select className="filter-select" name="period_months" defaultValue={text(editingPlan?.period_months) || "1"}><option value="1">Aylık</option><option value="12">Yıllık</option></select></label>
        <label>Yeni satış durumu<select className="filter-select" name="is_active" defaultValue={editingPlan?.is_active === false ? "false" : "true"}><option value="true">Satışa açık</option><option value="false">Satışa kapalı</option></select></label><button className="btn btn-primary">Paketi kaydet</button>
      </fieldset></form>{editingPlan && <button className="btn btn-secondary" disabled={busy} onClick={() => setEditingPlan(null)}>Yeni paket taslağı</button>}</section>
      <section className="card card-pad"><h2>Yeni kurum ve sahibi hesabı</h2><form aria-label="Yeni kurum oluştur" onSubmit={provision} onChange={() => setRequestId(newRequestId())}><fieldset disabled={busy || !plans.length} style={group}>
        {field("Kurum adı", "name", "", 255, "text", true)}{field("Kurum sahibi adı", "owner_first_name", "", 100, "text", true)}{field("Kurum sahibi soyadı", "owner_last_name", "", 100, "text", true)}{field("Kurum sahibi e-postası", "owner_email", "", 255, "email", true)}
        <label>Başlangıç parolası<input className="filter-select" name="owner_password" type="password" minLength={8} maxLength={4096} autoComplete="new-password" required /></label>
        <label>Satın alınan paket<select className="filter-select" name="plan_id" required><option value="">Paket seçin</option>{plans.filter((plan) => plan.is_active).map((plan) => <option key={plan.id} value={plan.id}>{text(plan.name)} · {packagePrice(plan.price, plan.currency)}</option>)}</select></label>
        <label>Üyelik başlangıcı<input className="filter-select" type="datetime-local" name="period_start" /></label><label>Üyelik bitişi<input className="filter-select" type="datetime-local" name="period_end" /></label><p>Tarih girilmezse üyelik şimdi başlar ve paketin aylık/yıllık dönemi kullanılır.</p><button className="btn btn-primary">Kurumu ve sahibi hesabını oluştur</button>
      </fieldset></form>{!plans.some((plan) => plan.is_active) && <p>Önce satışa açık bir paket oluşturun.</p>}</section>
    </div>
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Paketler"><h2>Paketler</h2>{!plans.length ? <p>Henüz paket tanımlanmamış.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Paket</th><th>Sınırlar</th><th>Fiyat</th><th>Durum</th><th>İşlem</th></tr></thead><tbody>{plans.map((plan) => <tr key={plan.id}><td>{text(plan.name)}<br />{text(plan.code)}</td><td>{text(plan.branch_limit)} şube · {text(plan.student_limit)} öğrenci · {text(plan.user_limit)} kullanıcı</td><td>{packagePrice(plan.price, plan.currency)} / {text(plan.period_months)} ay</td><td>{plan.is_active ? "Satışa açık" : "Satışa kapalı"}</td><td><button className="btn btn-secondary" disabled={busy} onClick={() => setEditingPlan(plan)}>Paketi düzenle</button></td></tr>)}</tbody></table></div>}</section>
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Kurum üyelikleri"><h2>Kurumlar</h2><label>Kurum ara<input className="filter-select" value={search} disabled={busy} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label>
      {!tenants.length ? <p>Bu kapsamda kurum yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Kurum</th><th>Üyelik</th><th>Paket / kullanım</th><th>İşlem</th></tr></thead><tbody>{tenants.slice(0, 20).map((row) => <tr key={row.id}><td>{row.name}</td><td><Badge value={row.access.status} /><p>Bitiş: {stamp(row.access.period_end)}</p><p>Ek süre: {stamp(row.access.grace_end)}</p></td><td>{text(row.package?.name) || "Paket tanımlanmamış"}<p>Şube: {row.usage.branch_limit} / {text(row.package?.branch_limit) || "—"} · Öğrenci: {row.usage.student_limit} / {text(row.package?.student_limit) || "—"} · Kullanıcı: {row.usage.user_limit} / {text(row.package?.user_limit) || "—"}</p></td><td><button className="btn btn-primary" disabled={busy} onClick={() => openWorkspace(row)}>Kurum çalışma alanını aç</button><button className="btn btn-secondary" disabled={busy} onClick={() => setSelected(row)}>Üyeliği yönet</button><button className="btn btn-secondary" disabled={busy} onClick={() => toggle(row)}>{row.is_active ? "Kurum hesabını kapat" : "Kurum hesabını aç"}</button></td></tr>)}</tbody></table></div>}{pager("Kurum sayfaları", page, tenants.length, setPage)}</section>
    {selected && <section className="card card-pad" style={{ marginTop: 18 }}><h2>{selected.name} üyeliği</h2><form aria-label="Kurum üyeliğini düzenle" key={`${selected.id}-${selected.access.period_end}-${text(selected.package?.id)}`} onSubmit={membership}><fieldset disabled={busy} style={group}>
      <label>Üyelik paketi<select className="filter-select" name="plan_id" defaultValue={text(selected.package?.id)} required><option value="">Paket seçin</option>{plans.map((plan) => <option key={plan.id} value={plan.id}>{text(plan.name)} · {packagePrice(plan.price, plan.currency)}</option>)}</select></label>
      <label>Üyelik başlangıcı<input className="filter-select" type="datetime-local" name="period_start" defaultValue={inputTime(selected.period_start) || clock} required /></label><label>Üyelik bitişi<input className="filter-select" type="datetime-local" name="period_end" defaultValue={inputTime(selected.access.period_end)} required /></label>
      <label>Üyelik erişimi<select className="filter-select" name="admin_status" defaultValue={selected.access.status === "SUSPENDED" ? "SUSPENDED" : "ACTIVE"}><option value="ACTIVE">Açık</option><option value="SUSPENDED">Kapalı</option></select></label>
      <label>Ödeme yetkilisi<select className="filter-select" name="owner_user_id" value={billingOwner} onChange={(event) => setBillingOwner(event.target.value)}><option value="">Atama yok</option>{billingOwner && !people.some((person) => person.id === billingOwner) && <option value={billingOwner}>Mevcut ödeme yetkilisi</option>}{people.map((person) => <option key={person.id} value={person.id}>{person.name} · {person.email}</option>)}</select></label><button className="btn btn-primary">Üyeliği kaydet</button>
    </fieldset></form></section>}
    <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Kurum ödeme talepleri"><h2>Üyelik ödeme talepleri</h2>{!invoices.length ? <p>Henüz ödeme talebi yok.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Kurum / paket</th><th>Tutar</th><th>Üyelik aralığı</th><th>Durum</th><th>İşlem</th></tr></thead><tbody>{invoices.slice(0, 20).map((row) => <tr key={row.id}><td>{text(row.organization_name) || text(row.organization_id)}<br />{text(row.package_name)}</td><td>{packagePrice(row.amount, row.currency)}</td><td>{stamp(row.period_start)} – {stamp(row.period_end)}</td><td><Badge value={row.status} /></td><td>{row.status === "PENDING" && row.can_cancel !== false && <button className="btn btn-secondary" disabled={busy} onClick={() => setReceipt(row)}>Ödemeyi doğrula</button>}{["INITIALIZING", "PENDING", "REVIEW"].includes(text(row.checkout_status)) && <button className="btn btn-secondary" disabled={busy} onClick={() => paymentStatus(row)}>Ödeme sonucunu kontrol et</button>}{row.status === "PAID_REVIEW" && <button className="btn btn-primary" disabled={busy} onClick={() => setReview(row)}>Ödemeyi uzlaştır</button>}</td></tr>)}</tbody></table></div>}{pager("Platform ödeme sayfaları", invoicePage, invoices.length, setInvoicePage)}</section>
    {review && <PaymentReview key={review.id} invoice={review} onDone={() => { setReview(null); refresh(); showToast("Ödeme uzlaştırması kaydedildi"); }} onClose={() => setReview(null)} />}
    {receipt && <section className="card card-pad" style={{ marginTop: 18 }}><h2>Kontrol edilen ödeme kaydı</h2><p>{text(receipt.organization_name)} · {text(receipt.package_name)} · {packagePrice(receipt.amount, receipt.currency)}</p><form aria-label="Üyelik ödemesini doğrula" key={receipt.id} onSubmit={verifyReceipt}><fieldset disabled={busy} style={group}>
      {field("Ödeme referansı", "payment_reference", "", 240, "text", true)}<label>Alınan tutar<input className="filter-select" name="amount" type="number" min={0} step="0.01" defaultValue={text(receipt.amount)} required /></label><label>Ödeme para birimi<select className="filter-select" name="currency" defaultValue={text(receipt.currency)}>{["TRY", "USD", "EUR"].map((value) => <option key={value}>{value}</option>)}</select></label><label>Ödeme zamanı<input className="filter-select" name="paid_at" type="datetime-local" /></label><button className="btn btn-primary">Kontrol edilen ödemeyi kaydet</button>
    </fieldset></form></section>}
  </div>;
}
