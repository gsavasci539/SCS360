import { BellRing, Building2, CloudCog, Save, Upload, WalletCards } from "lucide-react";
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { useToast } from "../../components/Toast";
import { Field, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse } from "../../types/api";

const sections = [{ key: "general", label: "Genel", icon: Building2 }, { key: "integrations", label: "Entegrasyonlar", icon: CloudCog }, { key: "uploads", label: "Dosya yükleme", icon: Upload }, { key: "notifications", label: "Bildirimler", icon: BellRing }];

interface AppSettings {
  school_name: string;
  academic_year: string;
  default_currency: string;
  max_upload_size_mb: number;
  allowed_file_types: string;
  receipt_email_enabled: boolean;
  overdue_reminders_enabled: boolean;
  failed_notification_alerts_enabled: boolean;
}

interface IntegrationRecord {
  provider: string;
  is_active: boolean;
  config: Record<string, unknown> | null;
  requires_review?: boolean;
}

const defaultSettings: AppSettings = {
  school_name: "",
  academic_year: "2026-2027",
  default_currency: "TRY",
  max_upload_size_mb: 10,
  allowed_file_types: "pdf,jpg,jpeg,png,docx",
  receipt_email_enabled: true,
  overdue_reminders_enabled: true,
  failed_notification_alerts_enabled: false,
};

export function SettingsPage({ initialSection = "general" }: { initialSection?: string }) {
  const [section, setSection] = useState(initialSection);
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const canWrite = useAuthStore((state) => state.can("settings.write"));
  const principal = useAuthStore((state) => state.user);
  const paymentOwnerHint = Boolean(principal?.is_super_admin || principal?.roles.some((role) => role.slug === "owner"));
  const { showToast } = useToast();

  useEffect(() => {
    Promise.allSettled([
      api.get<ApiResponse<Partial<AppSettings>>>("/settings"),
    ]).then(([settingsResult]) => {
      if (settingsResult.status === "fulfilled" && settingsResult.value.data.data) {
        setSettings((current) => ({ ...current, ...settingsResult.value.data.data }));
      }
      if (settingsResult.status === "rejected") {
        showToast("Ayarlar yüklenemedi", apiMessage(settingsResult.reason), "error");
      }
    }).finally(() => setLoading(false));
  }, [showToast]);

  async function save() {
    if (!canWrite || section === "integrations") return;
    setSaving(true);
    try {
      await api.put("/settings", settings);
      showToast("Ayarlar kaydedildi", "Değişiklikler güvenli biçimde uygulandı.");
    } catch (error) {
      showToast("Ayarlar kaydedilemedi", apiMessage(error), "error");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="card"><LoadingState /></div>;
  return <>
    <PageHeader eyebrow="Sistem" title="Ayarlar" description="Kurum tercihlerini ve dış servis bağlantılarını tek yerden yönetin.">
      {paymentOwnerHint && <Link className="btn btn-secondary" to="/settings/payments"><WalletCards size={16} />Ödeme entegrasyonu</Link>}
      {canWrite && section !== "integrations" && <button className="btn btn-primary" onClick={save} disabled={saving}><Save size={16} />{saving ? "Kaydediliyor…" : "Değişiklikleri kaydet"}</button>}
    </PageHeader>
    <div className="detail-grid">
      <aside className="card card-pad"><div className="quick-list" style={{ padding: 0 }}>{sections.map((item) => { const Icon = item.icon; return <button key={item.key} className="quick-item" style={{ width: "100%", border: section === item.key ? "1px solid #8bb9ad" : "1px solid transparent", background: section === item.key ? "#eef6f2" : "transparent", textAlign: "left" }} onClick={() => setSection(item.key)} aria-pressed={section === item.key}><div className="quick-icon"><Icon size={16} /></div><div className="quick-copy"><strong>{item.label}</strong><span>{item.key === "integrations" ? "SMTP, SMS, WhatsApp" : "Kurum yapılandırması"}</span></div></button>; })}</div></aside>
      <section className="card form-card">
        {section === "general" && <SettingsSection title="Genel sistem bilgileri" description="Panel genelinde kullanılan kurum ve dönem ayarları."><Field label="Kurum adı"><input disabled={!canWrite} value={settings.school_name} onChange={(event) => setSettings({ ...settings, school_name: event.target.value })} /></Field><Field label="Akademik yıl"><input disabled={!canWrite} value={settings.academic_year} onChange={(event) => setSettings({ ...settings, academic_year: event.target.value })} /></Field><Field label="Para birimi"><select disabled={!canWrite} value={settings.default_currency} onChange={(event) => setSettings({ ...settings, default_currency: event.target.value })}><option value="TRY">Türk Lirası (TRY)</option><option value="EUR">Euro (EUR)</option><option value="USD">Dolar (USD)</option></select></Field></SettingsSection>}
        <div hidden={section !== "integrations"}><IntegrationConnections canWrite={canWrite} /></div>
        {section === "uploads" && <SettingsSection title="Dosya yükleme" description="Öğrenci belgeleri için boyut ve tür sınırları."><Field label="Maksimum boyut (MB)"><input disabled={!canWrite} type="number" min={1} value={settings.max_upload_size_mb} onChange={(event) => setSettings({ ...settings, max_upload_size_mb: Number(event.target.value) })} /></Field><Field label="İzin verilen uzantılar" full><input disabled={!canWrite} value={settings.allowed_file_types} onChange={(event) => setSettings({ ...settings, allowed_file_types: event.target.value })} /></Field></SettingsSection>}
        {section === "notifications" && <SettingsSection title="Bildirim tercihleri" description="Otomatik operasyon mesajlarını yönetin."><label className="checkbox-line"><input disabled={!canWrite} type="checkbox" checked={settings.receipt_email_enabled} onChange={(event) => setSettings({ ...settings, receipt_email_enabled: event.target.checked })} />Ödeme sonrası makbuz e-postası gönder</label><label className="checkbox-line"><input disabled={!canWrite} type="checkbox" checked={settings.overdue_reminders_enabled} onChange={(event) => setSettings({ ...settings, overdue_reminders_enabled: event.target.checked })} />Geciken borç hatırlatmalarını etkinleştir</label><label className="checkbox-line"><input disabled={!canWrite} type="checkbox" checked={settings.failed_notification_alerts_enabled} onChange={(event) => setSettings({ ...settings, failed_notification_alerts_enabled: event.target.checked })} />Başarısız gönderimlerde yöneticiye haber ver</label></SettingsSection>}
      </section>
    </div>
  </>;
}

function readIntegrationRecords(value: unknown): IntegrationRecord[] {
  if (!Array.isArray(value)) throw new Error("Entegrasyon yanıtı geçerli değil; ayarlar değiştirilmedi.");
  const providers = new Set<string>();
  for (const item of value) {
    if (!item || typeof item !== "object" || typeof item.provider !== "string" ||
      typeof item.is_active !== "boolean" || providers.has(item.provider) ||
      (item.requires_review !== undefined && typeof item.requires_review !== "boolean") ||
      (!item.requires_review && (!item.config || typeof item.config !== "object" || Array.isArray(item.config)))) {
      throw new Error("Entegrasyon yanıtı geçerli değil; ayarlar değiştirilmedi.");
    }
    providers.add(item.provider);
  }
  return value;
}

function IntegrationConnections({ canWrite }: { canWrite: boolean }) {
  const [records, setRecords] = useState<IntegrationRecord[] | null>(null);
  const [patches, setPatches] = useState<Record<string, Record<string, string>>>({});
  const [smsProvider, setSmsProvider] = useState("NETGSM");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [loadVersion, setLoadVersion] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const { showToast } = useToast();

  useEffect(() => {
    let current = true;
    api.get<ApiResponse<unknown>>("/settings/integrations").then((response) => {
      const next = readIntegrationRecords(response.data.data);
      if (!current) return;
      setRecords(next);
      setPatches({});
      const sms = next.find((item) => ["NETGSM", "TWILIO"].includes(item.provider) && item.is_active)
        || next.find((item) => ["NETGSM", "TWILIO"].includes(item.provider));
      setSmsProvider(sms?.provider || "NETGSM");
    }).catch((failure: unknown) => {
      if (current) setError(failure instanceof Error && failure.message.startsWith("Entegrasyon yanıtı") ? failure.message : apiMessage(failure));
    }).finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [loadVersion]);

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
    if (!canWrite || !records || busy || record(provider)?.requires_review || !patch || !Object.keys(patch).length) return;
    setBusy(provider);
    try {
      // Send only explicitly edited public fields. Backend merges with current
      // credentials/options and retains is_active; a view never activates a sender.
      await api.put("/settings/integrations", { provider, config: patch });
      setRecords((current) => {
        const previous = current?.find((item) => item.provider === provider);
        return [...(current || []).filter((item) => item.provider !== provider),
          { ...previous, provider, config: { ...previous?.config, ...patch }, is_active: previous?.is_active ?? false }];
      });
      setPatches((current) => ({ ...current, [provider]: {} }));
      showToast(`${label} ayarları kaydedildi`, "Yalnız değiştirdiğiniz alanlar kaydedildi. Gönderim durumu değiştirilmedi.");
    } catch (failure) {
      showToast(`${label} ayarları kaydedilemedi`, apiMessage(failure), "error");
    } finally { setBusy(null); }
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
