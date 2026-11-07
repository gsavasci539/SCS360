import { useEffect, useRef, useState, type FormEvent } from "react";
import { Field, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { newRequestId } from "../../lib/requestId";
import { useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";

type Environment = "SANDBOX" | "LIVE";
type Merchant = { can_manage: true; configured: boolean; enabled: boolean; environment: Environment | null;
  account_id: string | null; revision: string | null; has_api_key: boolean; has_secret_key: boolean;
  callback_configured: boolean; portal_configured: boolean; encryption_configured: boolean; production_compatible: boolean;
  available: boolean; updated_at: string | null };
type Information = Merchant | { can_manage: false; available: boolean };
type SaveRequest = Readonly<{ request_id: string; expected_revision: string | null; enabled: boolean;
  environment: Environment; replace_account: boolean; api_key?: string; secret_key?: string }>;

function object(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function information(value: unknown): Information {
  if (!object(value) || typeof value.can_manage !== "boolean" || typeof value.available !== "boolean") throw new Error("Ödeme ayarlarının yanıtı geçersiz.");
  if (!value.can_manage) return { can_manage: false, available: value.available };
  const booleans = ["configured", "enabled", "has_api_key", "has_secret_key", "callback_configured", "portal_configured", "encryption_configured", "production_compatible"];
  if (!booleans.every((field) => typeof value[field] === "boolean") || ![null, "SANDBOX", "LIVE"].includes(value.environment as Environment | null)
    || !["account_id", "revision", "updated_at"].every((field) => value[field] === null || typeof value[field] === "string")) throw new Error("Ödeme ayarlarının yanıtı geçersiz.");
  return value as Merchant;
}
function responseStatus(error: unknown): number | undefined {
  return object(error) && object(error.response) && typeof error.response.status === "number" ? error.response.status : undefined;
}
function status(row: Merchant) {
  if (!row.configured) return "Merchant kurulumu bekleniyor";
  if (!row.enabled) return "Yapılandırıldı · kapalı";
  if (!row.available) return "Yapılandırma kontrolü gerekiyor";
  return row.environment === "SANDBOX" ? "iyzico Sandbox · test ortamı" : "Canlı ödeme yapılandırıldı";
}

export function SchoolPaymentSettings() {
  const user = useAuthStore((state) => state.user), workspace = usePlatformWorkspace((state) => state.workspace);
  const organization = user?.is_super_admin ? workspace?.operatorId === user.id ? workspace.id : null : user?.organization_id;
  if (!organization || !user) return <><PageHeader eyebrow="Kurum ayarları" title="Ödeme entegrasyonu" description="Öğrenci tahsilatları için kuruma ait iyzico hesabı." /><p>Önce kurum çalışma alanını seçin.</p></>;
  return <SchoolPaymentForm key={`${user.id}:${organization}`} />;
}

function SchoolPaymentForm() {
  const [data, setData] = useState<Information | null>(null), [loading, setLoading] = useState(true);
  const [environment, setEnvironment] = useState<Environment>("LIVE"), [enabled, setEnabled] = useState(false), [replaceAccount, setReplaceAccount] = useState(false);
  const [apiKey, setApiKey] = useState(""), [secretKey, setSecretKey] = useState("");
  const [busy, setBusy] = useState(false), [uncertain, setUncertain] = useState(false), [conflict, setConflict] = useState(false);
  const [conflictChecked, setConflictChecked] = useState(false);
  const [error, setError] = useState(""), [notice, setNotice] = useState("");
  const pending = useRef<SaveRequest | null>(null), mounted = useRef(true), loadController = useRef<AbortController | null>(null);
  const baselineRevision = useRef<string | null>(null);

  function resetForm(row: Merchant) {
    baselineRevision.current = row.revision;
    setEnvironment(row.environment || "LIVE"); setEnabled(row.enabled); setReplaceAccount(false); setApiKey(""); setSecretKey("");
  }
  async function load(reset = false, review = false) {
    loadController.current?.abort(); const controller = new AbortController(); loadController.current = controller;
    setLoading(true);
    try {
      const response = await api.get("/payments/merchant", { signal: controller.signal });
      const current = information(response.data.data);
      if (!mounted.current || controller.signal.aborted) return;
      setData(current);
      if (current.can_manage) {
        if (reset || !data) resetForm(current);
        else if (!pending.current && current.revision !== baselineRevision.current) { setConflict(true); setConflictChecked(true); }
        if (review) setConflictChecked(true);
      }
      if (!current.can_manage) { pending.current = null; setApiKey(""); setSecretKey(""); setUncertain(false); setConflict(false); }
    } catch (reason) { if (mounted.current && !controller.signal.aborted) setError(apiMessage(reason)); }
    finally { if (mounted.current && !controller.signal.aborted) setLoading(false); }
  }
  useEffect(() => {
    mounted.current = true; void load(true);
    return () => { mounted.current = false; pending.current = null; loadController.current?.abort(); };
    // Each user/organization combination mounts a fresh form and secret memory.
  }, []);

  async function send(body: SaveRequest) {
    if (busy) return; setBusy(true); setError(""); setNotice("");
    try {
      const response = await api.put("/payments/merchant", body);
      const current = information(response.data.data);
      if (!mounted.current) return;
      setData(current); pending.current = null; setUncertain(false); setConflict(false); setApiKey(""); setSecretKey("");
      if (current.can_manage) resetForm(current);
      setNotice("Ödeme ayarları kaydedildi. Bu işlem sağlayıcıya ödeme göndermez; sağlayıcı kabulü ayrıca yapılmalıdır.");
    } catch (reason) {
      if (!mounted.current) return;
      setError(apiMessage(reason));
      const statusCode = responseStatus(reason);
      if (statusCode === 422) { pending.current = null; setUncertain(false); }
      else if (statusCode === 409) {
        pending.current = null; setUncertain(false); setConflict(true); setConflictChecked(false); await load(false, true);
      } else if (statusCode === 401 || statusCode === 403) {
        pending.current = null; setApiKey(""); setSecretKey(""); setConflict(true); setConflictChecked(false); await load(false, true);
      } else { setUncertain(true); }
    } finally { if (mounted.current) setBusy(false); }
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!data?.can_manage || busy || loading || uncertain || conflict || pending.current) return;
    setError(""); setNotice("");
    if (data.environment && environment !== data.environment && !replaceAccount) { setError("Ortam değiştirmek için yeni merchant hesabı kullanımını açıkça onaylayın."); return; }
    if ((!data.configured || replaceAccount) && (!apiKey.trim() || !secretKey.trim())) { setError("Yeni hesap veya hesap değişimi için API ve secret key birlikte girilmelidir."); return; }
    const body: SaveRequest = Object.freeze({ request_id: newRequestId(), expected_revision: baselineRevision.current,
      enabled, environment, replace_account: replaceAccount,
      ...(apiKey.trim() ? { api_key: apiKey.trim() } : {}), ...(secretKey.trim() ? { secret_key: secretKey.trim() } : {}) });
    pending.current = body; await send(body);
  }
  const manager = data?.can_manage ? data : null;
  const blocked = busy || loading || uncertain || conflict;
  return <>
    <PageHeader eyebrow="Kurum ayarları" title="Ödeme entegrasyonu" description="Öğrenci tahsilatları, kurumunuza ait iyzico merchant hesabı üzerinden alınır." />
    <section className="card card-pad" aria-label="Kurum ödeme hesabı durumu">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}><h2>iyzico bağlantısı</h2><button className="btn btn-secondary" disabled={loading || busy} onClick={() => { setError(""); void load(false, conflict); }}>Ayar durumunu kontrol et</button></div>
      {loading && !data && <p role="status">Ödeme ayarları yükleniyor…</p>}
      {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
      {data && !data.can_manage && <p>Ödeme hesabını yalnız kurum sahibi veya seçili kurumun platform yöneticisi yönetebilir. Kurum sahibinizle iletişime geçin.</p>}
      {manager && <><p><strong>{status(manager)}</strong></p><p>API key: {manager.has_api_key ? "Kayıtlı" : "Eksik"} · Secret key: {manager.has_secret_key ? "Kayıtlı" : "Eksik"}</p>
        {!manager.callback_configured && <p>Ödeme dönüş adresi sunucuda yapılandırılmalı.</p>}
        {!manager.portal_configured && <p>Ödeme sonuç sayfası sunucuda yapılandırılmalı.</p>}
        {!manager.encryption_configured && <p>Merchant şifreleme anahtarı sunucuda yapılandırılmalı.</p>}
        {!manager.production_compatible && <p>Seçili merchant ortamı sunucu ortamında etkinleştirmeye uygun değil.</p>}
        {manager.environment === "SANDBOX" && <p>Sandbox test ortamıdır. Bu ayar gerçek canlı tahsilat kabulü anlamına gelmez.</p>}
        <p>SCS360 üyelik ödemesi bu hesaptan alınmaz. Bu form kart bilgisi almaz ve ödeme veya iade başlatmaz.</p></>}
    </section>
    {manager && <section className="card form-card" style={{ marginTop: 18 }}>
      {uncertain && <div className="form-section"><p role="status">Kaydetme sonucuna ulaşılamadı. Form kilitlendi; aynı isteği tekrar deneyin veya sunucudaki ayar durumunu kontrol edin. Sayfayı yenilerseniz anahtar alanları temizlenir.</p><button type="button" className="btn btn-secondary" disabled={busy || loading} onClick={() => { if (pending.current) void send(pending.current); }}>Aynı kaydı tekrar dene</button></div>}
      {conflict && <div className="form-section"><p role="status">Ayar kaydı değişmiş veya erişim güncellenmiş. Sunucudaki son durumu inceleyin; eski form otomatik uygulanmadı.</p><button type="button" className="btn btn-secondary" disabled={busy || loading || !conflictChecked} onClick={() => { if (manager) { resetForm(manager); setConflict(false); setConflictChecked(false); setError(""); setNotice("Son ayarlar forma alındı. Anahtar alanları temizlendi; değişiklikleri yeniden inceleyin."); } }}>Son durumu inceledim; formu yenile</button></div>}
      <form onSubmit={submit} aria-label="Kurum iyzico hesabı ayarları"><fieldset disabled={blocked} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
        <div className="form-section"><h2>Merchant hesabı</h2><p>Hesabınıza ait anahtarları girin. Kayıtlı anahtarlar hiçbir zaman gösterilmez; mevcut hesapta boş alanlar kayıtlı değeri korur.</p><div className="form-grid">
          <Field label="Ödeme ortamı"><select value={environment} onChange={(event) => setEnvironment(event.target.value as Environment)}><option value="LIVE">Canlı (LIVE)</option><option value="SANDBOX">Sandbox (test)</option></select></Field>
          <label className="checkbox-line"><input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />Online öğrenci ödemesini etkinleştir</label>
          {manager.account_id && <label className="checkbox-line" style={{ gridColumn: "1 / -1" }}><input type="checkbox" checked={replaceAccount} onChange={(event) => setReplaceAccount(event.target.checked)} />Yeni merchant hesabı veya farklı ortam kullanacağım</label>}
          {(replaceAccount || (manager.environment && environment !== manager.environment)) && <p style={{ gridColumn: "1 / -1" }}>Hesap veya ortam değişiminde iki anahtarı da girin. Önceki ödemeler, başlatıldıkları merchant bilgileriyle doğrulanmaya devam eder.</p>}
          <Field label="API key" required={!manager.configured || replaceAccount}><input type="password" autoComplete="new-password" spellCheck={false} maxLength={2048} value={apiKey} required={!manager.configured || replaceAccount} onChange={(event) => setApiKey(event.target.value)} /></Field>
          <Field label="Secret key" required={!manager.configured || replaceAccount}><input type="password" autoComplete="new-password" spellCheck={false} maxLength={2048} value={secretKey} required={!manager.configured || replaceAccount} onChange={(event) => setSecretKey(event.target.value)} /></Field>
        </div></div><div className="form-actions"><button className="btn btn-primary" disabled={blocked}>{busy ? "Kaydediliyor…" : "Ödeme ayarlarını kaydet"}</button></div>
      </fieldset></form>
    </section>}
  </>;
}
