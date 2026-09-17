import { BellRing, Building2, CloudCog, Save, Upload } from "lucide-react";
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
  config: Record<string, unknown>;
}

interface IntegrationForm {
  smtp_host: string;
  smtp_port: string;
  smtp_username: string;
  sms_provider: "NETGSM" | "TWILIO";
  whatsapp_phone_id: string;
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

const defaultIntegrations: IntegrationForm = {
  smtp_host: "",
  smtp_port: "587",
  smtp_username: "",
  sms_provider: "NETGSM",
  whatsapp_phone_id: "",
};

const configText = (config: Record<string, unknown> | undefined, key: string, fallback = "") => {
  const value = config?.[key];
  return typeof value === "string" || typeof value === "number" ? String(value) : fallback;
};

export function SettingsPage({ initialSection = "general" }: { initialSection?: string }) {
  const [section, setSection] = useState(initialSection);
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [integrations, setIntegrations] = useState<IntegrationForm>(defaultIntegrations);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const canWrite = useAuthStore((state) => state.can("settings.write"));
  const { showToast } = useToast();

  useEffect(() => {
    Promise.allSettled([
      api.get<ApiResponse<Partial<AppSettings>>>("/settings"),
      api.get<ApiResponse<IntegrationRecord[]>>("/settings/integrations"),
    ]).then(([settingsResult, integrationsResult]) => {
      if (settingsResult.status === "fulfilled" && settingsResult.value.data.data) {
        setSettings((current) => ({ ...current, ...settingsResult.value.data.data }));
      }
      if (integrationsResult.status === "fulfilled") {
        const records = Array.isArray(integrationsResult.value.data.data) ? integrationsResult.value.data.data : [];
        const smtp = records.find((item) => item.provider === "SMTP");
        const sms = records.find((item) => item.provider === "NETGSM" || item.provider === "TWILIO");
        const whatsapp = records.find((item) => item.provider === "META_WHATSAPP");
        setIntegrations({
          smtp_host: configText(smtp?.config, "host"),
          smtp_port: configText(smtp?.config, "port", "587"),
          smtp_username: configText(smtp?.config, "username"),
          sms_provider: sms?.provider === "TWILIO" ? "TWILIO" : "NETGSM",
          whatsapp_phone_id: configText(whatsapp?.config, "phone_id"),
        });
      }
      if (settingsResult.status === "rejected" && integrationsResult.status === "rejected") {
        showToast("Ayarlar yüklenemedi", apiMessage(settingsResult.reason), "error");
      }
    }).finally(() => setLoading(false));
  }, [showToast]);

  async function save() {
    if (!canWrite) return;
    setSaving(true);
    try {
      if (section === "integrations") {
        await Promise.all([
          api.put("/settings/integrations", { provider: "SMTP", is_active: true, config: { host: integrations.smtp_host, port: integrations.smtp_port, username: integrations.smtp_username } }),
          api.put("/settings/integrations", { provider: integrations.sms_provider, is_active: true, config: {} }),
          api.put("/settings/integrations", { provider: "META_WHATSAPP", is_active: true, config: { phone_id: integrations.whatsapp_phone_id } }),
        ]);
      } else {
        await api.put("/settings", settings);
      }
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
      {canWrite && <button className="btn btn-primary" onClick={save} disabled={saving}><Save size={16} />{saving ? "Kaydediliyor…" : "Değişiklikleri kaydet"}</button>}
    </PageHeader>
    <div className="detail-grid">
      <aside className="card card-pad"><div className="quick-list" style={{ padding: 0 }}>{sections.map((item) => { const Icon = item.icon; return <button key={item.key} className="quick-item" style={{ width: "100%", border: section === item.key ? "1px solid #8bb9ad" : "1px solid transparent", background: section === item.key ? "#eef6f2" : "transparent", textAlign: "left" }} onClick={() => setSection(item.key)} aria-pressed={section === item.key}><div className="quick-icon"><Icon size={16} /></div><div className="quick-copy"><strong>{item.label}</strong><span>{item.key === "integrations" ? "SMTP, SMS, WhatsApp" : "Kurum yapılandırması"}</span></div></button>; })}</div></aside>
      <section className="card form-card">
        {section === "general" && <SettingsSection title="Genel sistem bilgileri" description="Panel genelinde kullanılan kurum ve dönem ayarları."><Field label="Kurum adı"><input disabled={!canWrite} value={settings.school_name} onChange={(event) => setSettings({ ...settings, school_name: event.target.value })} /></Field><Field label="Akademik yıl"><input disabled={!canWrite} value={settings.academic_year} onChange={(event) => setSettings({ ...settings, academic_year: event.target.value })} /></Field><Field label="Para birimi"><select disabled={!canWrite} value={settings.default_currency} onChange={(event) => setSettings({ ...settings, default_currency: event.target.value })}><option value="TRY">Türk Lirası (TRY)</option><option value="EUR">Euro (EUR)</option><option value="USD">Dolar (USD)</option></select></Field></SettingsSection>}
        {section === "integrations" && <SettingsSection title="Servis bağlantıları" description="Kimlik bilgileri backend tarafında şifrelenerek saklanır."><Field label="SMTP sunucusu"><input disabled={!canWrite} value={integrations.smtp_host} onChange={(event) => setIntegrations({ ...integrations, smtp_host: event.target.value })} /></Field><Field label="SMTP portu"><input disabled={!canWrite} value={integrations.smtp_port} onChange={(event) => setIntegrations({ ...integrations, smtp_port: event.target.value })} /></Field><Field label="SMTP kullanıcı adı"><input disabled={!canWrite} value={integrations.smtp_username} onChange={(event) => setIntegrations({ ...integrations, smtp_username: event.target.value })} /></Field><Field label="SMS sağlayıcısı"><select disabled={!canWrite} value={integrations.sms_provider} onChange={(event) => setIntegrations({ ...integrations, sms_provider: event.target.value as IntegrationForm["sms_provider"] })}><option value="NETGSM">NETGSM</option><option value="TWILIO">TWILIO</option></select></Field><Field label="WhatsApp telefon ID"><input disabled={!canWrite} value={integrations.whatsapp_phone_id} onChange={(event) => setIntegrations({ ...integrations, whatsapp_phone_id: event.target.value })} /></Field></SettingsSection>}
        {section === "uploads" && <SettingsSection title="Dosya yükleme" description="Öğrenci belgeleri için boyut ve tür sınırları."><Field label="Maksimum boyut (MB)"><input disabled={!canWrite} type="number" min={1} value={settings.max_upload_size_mb} onChange={(event) => setSettings({ ...settings, max_upload_size_mb: Number(event.target.value) })} /></Field><Field label="İzin verilen uzantılar" full><input disabled={!canWrite} value={settings.allowed_file_types} onChange={(event) => setSettings({ ...settings, allowed_file_types: event.target.value })} /></Field></SettingsSection>}
        {section === "notifications" && <SettingsSection title="Bildirim tercihleri" description="Otomatik operasyon mesajlarını yönetin."><label className="checkbox-line"><input disabled={!canWrite} type="checkbox" checked={settings.receipt_email_enabled} onChange={(event) => setSettings({ ...settings, receipt_email_enabled: event.target.checked })} />Ödeme sonrası makbuz e-postası gönder</label><label className="checkbox-line"><input disabled={!canWrite} type="checkbox" checked={settings.overdue_reminders_enabled} onChange={(event) => setSettings({ ...settings, overdue_reminders_enabled: event.target.checked })} />Geciken borç hatırlatmalarını etkinleştir</label><label className="checkbox-line"><input disabled={!canWrite} type="checkbox" checked={settings.failed_notification_alerts_enabled} onChange={(event) => setSettings({ ...settings, failed_notification_alerts_enabled: event.target.checked })} />Başarısız gönderimlerde yöneticiye haber ver</label></SettingsSection>}
      </section>
    </div>
  </>;
}

function SettingsSection({ title, description, children }: { title: string; description: string; children: React.ReactNode }) { return <div className="form-section"><h2>{title}</h2><p>{description}</p><div className="form-grid">{children}</div></div>; }
