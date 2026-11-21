import { BellRing, Building2, CloudCog, Save, Upload, WalletCards } from "lucide-react";
import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { useToast } from "../../components/Toast";
import { ErrorState, Field, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import { usePlatformWorkspace } from "../../stores/platformWorkspace";
import type { ApiResponse } from "../../types/api";
import { notificationPreferences, preferenceChanges, readPreferences, sectionFields, type AppSettings, type OrganizationPreferences } from "./organizationPreferences";

const sections = [{ key: "general", label: "Genel", icon: Building2 }, { key: "integrations", label: "Entegrasyonlar", icon: CloudCog }, { key: "uploads", label: "Dosya yükleme", icon: Upload }, { key: "notifications", label: "Bildirimler", icon: BellRing }];

interface IntegrationRecord {
  id: string;
  organization_id: string;
  provider: string;
  is_active: boolean;
  config: Record<string, unknown> | null;
  requires_review?: boolean;
}

export function SettingsPage({ initialSection = "general" }: { initialSection?: string }) {
  const [section, setSection] = useState(initialSection);
  const [snapshot, setSnapshot] = useState<OrganizationPreferences | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState("");
  const [reload, setReload] = useState(0);
  const savingNow = useRef(false);
  const canWrite = useAuthStore((state) => state.can("settings.write"));
  const principal = useAuthStore((state) => state.user);
  const workspace = usePlatformWorkspace((state) => state.workspace);
  const organization = principal?.is_super_admin && workspace?.operatorId === principal.id
    ? workspace.id : principal?.organization_id;
  const paymentOwnerHint = Boolean(principal?.is_super_admin || principal?.roles.some((role) => role.slug === "owner"));
  const { showToast } = useToast();

  useEffect(() => {
    const controller = new AbortController();
    api.get<ApiResponse<OrganizationPreferences>>("/settings/preferences", { signal: controller.signal }).then(({ data }) => {
      if (controller.signal.aborted) return;
      const response = readPreferences(data.success ? data.data : undefined, organization);
      setSnapshot(response);
      setSettings(response.values);
      setFailure("");
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setFailure(apiMessage(error));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [organization, reload]);

  async function save() {
    if (!canWrite || savingNow.current || !settings || snapshot?.organization_id !== organization || !sectionFields[section]) return;
    savingNow.current = true;
    setSaving(true);
    try {
      const patch = preferenceChanges(snapshot, settings, section);
      const keys = Object.keys(patch.changes) as (keyof AppSettings)[];
      if (!keys.length) return;
      const { data: written } = await api.put<ApiResponse<OrganizationPreferences>>("/settings/preferences", patch);
      readPreferences(written.success ? written.data : undefined, organization);
      const { data: result } = await api.get<ApiResponse<OrganizationPreferences>>("/settings/preferences");
      const current = readPreferences(result.success ? result.data : undefined, organization);
      if (keys.some((key) => current.values[key] !== patch.changes[key])) throw new Error("Kaydedilen tercihler doğrulanamadı.");
      setSnapshot(current);
      setSettings((draft) => draft && Object.fromEntries(Object.entries(current.values).map(([key, value]) => {
        const field = key as keyof AppSettings;
        return [key, keys.includes(field) || draft[field] === snapshot.values[field] ? value : draft[field]];
      })) as AppSettings | null);
      showToast("Kurum tercihleri kaydedildi");
    } catch (error) {
      showToast("Ayarlar kaydedilemedi", apiMessage(error), "error");
    } finally {
      savingNow.current = false;
      setSaving(false);
    }
  }

  const ready = settings && snapshot?.organization_id === organization && !loading && !failure;
  return <>
    <PageHeader eyebrow="Sistem" title="Ayarlar" description="Kurum tercihlerini ve dış servis bağlantılarını tek yerden yönetin.">
      {paymentOwnerHint && <Link className="btn btn-secondary" to="/settings/payments"><WalletCards size={16} />Ödeme entegrasyonu</Link>}
      {canWrite && ready && section !== "integrations" && <button className="btn btn-primary" onClick={save} disabled={saving}><Save size={16} />{saving ? "Kaydediliyor…" : "Değişiklikleri kaydet"}</button>}
    </PageHeader>
    <div className="detail-grid">
      <aside className="card card-pad"><div className="quick-list" style={{ padding: 0 }}>{sections.map((item) => { const Icon = item.icon; return <button key={item.key} className="quick-item" style={{ width: "100%", border: section === item.key ? "1px solid #8bb9ad" : "1px solid transparent", background: section === item.key ? "#eef6f2" : "transparent", textAlign: "left" }} onClick={() => setSection(item.key)} aria-pressed={section === item.key}><div className="quick-icon"><Icon size={16} /></div><div className="quick-copy"><strong>{item.label}</strong><span>{item.key === "integrations" ? "SMTP, SMS, WhatsApp" : "Kurum yapılandırması"}</span></div></button>; })}</div></aside>
      <section className="card form-card">
        {section !== "integrations" && !ready && (loading || !failure
          ? <LoadingState label="Kurum tercihleri yükleniyor" />
          : <ErrorState message={failure} retry={() => { setLoading(true); setReload((value) => value + 1); }} />)}
        {section === "general" && ready && settings && <SettingsSection title="Genel kurum tercihleri" description="Kurum için kayıtlı ad, dönem ve para birimi."><Field label="Kurum adı"><input disabled={!canWrite || saving} value={settings.school_name} onChange={(event) => setSettings({ ...settings, school_name: event.target.value })} /></Field><Field label="Akademik yıl"><input disabled={!canWrite || saving} value={settings.academic_year ?? ""} onChange={(event) => setSettings({ ...settings, academic_year: event.target.value })} /></Field><Field label="Para birimi"><select disabled={!canWrite || saving} value={settings.default_currency} onChange={(event) => setSettings({ ...settings, default_currency: event.target.value })}><option value="TRY">Türk Lirası (TRY)</option><option value="EUR">Euro (EUR)</option><option value="USD">Dolar (USD)</option></select></Field></SettingsSection>}
        <div hidden={section !== "integrations"}>{organization && <IntegrationConnections key={organization} organization={organization} canWrite={canWrite} />}</div>
        {section === "uploads" && ready && settings && snapshot && <SettingsSection title="Öğrenci belgeleri" description={`Sunucu üst sınırı ${snapshot.upload_policy.max_size_mb} MB. İzinli uzantılar ${snapshot.upload_policy.allowed_extensions.join(", ")}.`}><Field label="Maksimum boyut (MB)"><input disabled={!canWrite || saving} type="number" min={1} max={snapshot.upload_policy.max_size_mb} value={settings.max_upload_size_mb} onChange={(event) => setSettings({ ...settings, max_upload_size_mb: Number(event.target.value) })} /></Field><Field label="İzin verilen uzantılar" full><input disabled={!canWrite || saving} value={settings.allowed_file_types} onChange={(event) => setSettings({ ...settings, allowed_file_types: event.target.value })} /></Field></SettingsSection>}
        {section === "notifications" && ready && settings && <SettingsSection title="Kayıtlı bildirim tercihleri" description="Gönderim için ilgili servis bağlantısı ve otomasyon kurulumu gerekir.">{notificationPreferences.map(([key, label]) => <Field key={key} label={label}><select disabled={!canWrite || saving} value={String(settings[key])} onChange={(event) => setSettings({ ...settings, [key]: event.target.value === "null" ? null : event.target.value === "true" })}><option value="null">Tanımlanmadı</option><option value="true">Açık tercih</option><option value="false">Kapalı tercih</option></select></Field>)}</SettingsSection>}
      </section>
    </div>
  </>;
}

function readIntegrationRecords(value: unknown, organization: string): IntegrationRecord[] {
  if (!Array.isArray(value)) throw new Error("Entegrasyon yanıtı geçerli değil; ayarlar değiştirilmedi.");
  const providers = new Set<string>();
  for (const item of value) {
    if (!item || typeof item !== "object" || typeof item.id !== "string" || !item.id ||
      item.organization_id !== organization || typeof item.provider !== "string" ||
      typeof item.is_active !== "boolean" || providers.has(item.provider) ||
      (item.requires_review !== undefined && typeof item.requires_review !== "boolean") ||
      (!item.requires_review && (!item.config || typeof item.config !== "object" || Array.isArray(item.config)))) {
      throw new Error("Entegrasyon yanıtı geçerli değil; ayarlar değiştirilmedi.");
    }
    providers.add(item.provider);
  }
  return value;
}

function IntegrationConnections({ organization, canWrite }: { organization: string; canWrite: boolean }) {
  const [records, setRecords] = useState<IntegrationRecord[] | null>(null);
  const [patches, setPatches] = useState<Record<string, Record<string, string>>>({});
  const [smsProvider, setSmsProvider] = useState("NETGSM");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [loadVersion, setLoadVersion] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const inFlight = useRef(false);
  const { showToast } = useToast();

  useEffect(() => {
    const controller = new AbortController();
    api.get<ApiResponse<unknown>>("/settings/integrations", { params: { organization_id: organization }, signal: controller.signal }).then(({ data }) => {
      if (controller.signal.aborted) return;
      const next = readIntegrationRecords(data.success ? data.data : undefined, organization);
      setRecords(next);
      setPatches({});
      const sms = next.find((item) => ["NETGSM", "TWILIO"].includes(item.provider) && item.is_active)
        || next.find((item) => ["NETGSM", "TWILIO"].includes(item.provider));
      setSmsProvider(sms?.provider || "NETGSM");
    }).catch((failure: unknown) => {
      if (!controller.signal.aborted) setError(failure instanceof Error && failure.message.startsWith("Entegrasyon yanıtı") ? failure.message : apiMessage(failure));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [loadVersion, organization]);

  const record = (provider: string) => records?.find((item) => item.provider === provider);
  function originalText(provider: string, key: string) {
    const value = record(provider)?.config?.[key];
    return typeof value === "string" || typeof value === "number" ? String(value) : "";
  }
  function blocked(provider: string, key: string) {
    const source = record(provider);
    const value = source?.config?.[key];
    return Boolean(source?.requires_review || (value !== undefined && typeof value !== "string" && typeof value !== "number"));
  }
  function edit(provider: string, key: string, value: string) {
    if (!canWrite || loading || busy || blocked(provider, key)) return;
    setPatches((current) => {
      const patch = { ...current[provider] };
      if (value === originalText(provider, key)) delete patch[key];
      else patch[key] = value;
      return { ...current, [provider]: patch };
    });
  }
  async function saveProvider(provider: string, label: string) {
    const patch = patches[provider];
    const previous = record(provider);
    if (!canWrite || !records || inFlight.current || previous?.requires_review || !patch || !Object.keys(patch).length) return;
    inFlight.current = true;
    setBusy(provider);
    try {
      const { data: result } = await api.put<ApiResponse<Pick<IntegrationRecord, "id" | "provider" | "organization_id">>>("/settings/integrations", {
        organization_id: organization, provider, config: patch,
        expected_config: Object.fromEntries(Object.keys(patch).map((key) => [key, previous?.config?.[key] ?? null])),
      });
      const stored = result.data;
      if (!result.success || !stored?.id || stored.provider !== provider || stored.organization_id !== organization) {
        throw new Error("Entegrasyon kaydı doğrulanamadı.");
      }
      const { data } = await api.get<ApiResponse<unknown>>("/settings/integrations", { params: { organization_id: organization } });
      const refreshed = readIntegrationRecords(data.success ? data.data : undefined, organization);
      const verified = refreshed.find((entry) => entry.id === stored.id && entry.provider === provider);
      if (verified?.requires_review || !verified || Object.entries(patch).some(([key, value]) => verified.config?.[key] !== value)) {
        throw new Error("Kaydedilen entegrasyon doğrulanamadı.");
      }
      setRecords(refreshed);
      setPatches((current) => ({ ...current, [provider]: {} }));
      showToast(`${label} ayarları kaydedildi`);
    } catch (failure) {
      showToast(`${label} ayarları kaydedilemedi`, apiMessage(failure), "error");
    } finally { inFlight.current = false; setBusy(null); }
  }
  function status(provider: string) {
    const source = record(provider);
    return source?.requires_review ? "Eski kayıt inceleme gerektiriyor; bu formdan değiştirilemez."
      : source ? `Kayıt durumu: ${source.is_active ? "etkin" : "pasif"}. Sağlayıcıyla gönderim doğrulanmadı.`
        : "Henüz kayıt yok. Kaydetmek gönderimi etkinleştirmez.";
  }
  function field(provider: string, key: string, label: string) {
    const invalidType = blocked(provider, key);
    return <Field label={label} error={invalidType && !record(provider)?.requires_review ? "Mevcut alan farklı bir veri türünde; inceleme gerektiriyor." : undefined}>
      <input disabled={!canWrite || Boolean(busy) || invalidType} value={patches[provider]?.[key] ?? originalText(provider, key)}
        onChange={(event) => edit(provider, key, event.target.value)} />
    </Field>;
  }
  function saveButton(provider: string, label: string) {
    return canWrite && <button type="button" className="btn btn-secondary"
      disabled={Boolean(busy) || Boolean(record(provider)?.requires_review) || !Object.keys(patches[provider] || {}).length}
      onClick={() => saveProvider(provider, label)}>{busy === provider ? "Kaydediliyor…" : `${label} ayarlarını kaydet`}</button>;
  }

  if (loading) return <LoadingState label="Entegrasyonlar yükleniyor" />;
  if (error || !records) return <div><p role="alert">{error || "Entegrasyonlar yüklenemedi."}</p>
    <button type="button" className="btn btn-secondary" onClick={() => { setLoading(true); setError(""); setLoadVersion((current) => current + 1); }}>Entegrasyonları yeniden yükle</button></div>;
  return <>
    <div className="form-section"><h2>Servis bağlantıları</h2><p>Bu ekran kurumun kayıtlı bağlantı alanlarını düzenler. Gizli değerler gösterilmez. Gönderim kurulumu ayrıca sunucu yapılandırması ve sağlayıcı hesabıyla doğrulanmalıdır; kayıt durumu tek başına çalışan bağlantı anlamına gelmez.</p></div>
    <SettingsSection title="SMTP" description={status("SMTP")}>
      {field("SMTP", "host", "SMTP sunucusu")}{field("SMTP", "port", "SMTP portu")}{field("SMTP", "username", "SMTP kullanıcı adı")}
      <div className="field field-full">{saveButton("SMTP", "SMTP")}</div>
    </SettingsSection>
    <SettingsSection title="SMS" description="Sağlayıcı seçimi yalnız kayıtlı durumu görüntüler; SMS hesabı oluşturmaz veya etkinleştirmez.">
      <Field label="SMS sağlayıcısı"><select value={smsProvider} disabled={Boolean(busy)} onChange={(event) => setSmsProvider(event.target.value)}><option value="NETGSM">NETGSM</option><option value="TWILIO">TWILIO</option></select></Field>
      <p className="field field-full">{status(smsProvider)}</p>
    </SettingsSection>
    <SettingsSection title="WhatsApp" description={status("META_WHATSAPP")}>
      {field("META_WHATSAPP", "phone_id", "WhatsApp telefon ID")}
      <div className="field field-full">{saveButton("META_WHATSAPP", "WhatsApp")}</div>
    </SettingsSection>
  </>;
}

function SettingsSection({ title, description, children }: { title: string; description: string; children: React.ReactNode }) { return <div className="form-section"><h2>{title}</h2><p>{description}</p><div className="form-grid">{children}</div></div>; }
