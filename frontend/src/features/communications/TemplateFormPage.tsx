import { ArrowLeft, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useToast } from "../../components/Toast";
import { Field, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse } from "../../types/api";

interface Template {
  id?: string;
  name: string;
  code: string;
  channel: string;
  subject?: string;
  body_template: string;
  is_active: boolean;
}

const variables = [
  { name: "{{parent_name}}", description: "Veli adı" },
  { name: "{{student_name}}", description: "Öğrenci adı" },
  { name: "{{school_name}}", description: "Okul adı" },
  { name: "{{branch_name}}", description: "Şube adı" },
  { name: "{{class_name}}", description: "Sınıf adı" },
  { name: "{{amount}}", description: "Tutar" },
  { name: "{{due_date}}", description: "Vade tarihi" },
  { name: "{{payment_date}}", description: "Ödeme tarihi" }
];

export function TemplateFormPage() {
  const { id } = useParams();
  const editing = Boolean(id);
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [template, setTemplate] = useState<Template>({
    name: "",
    code: "",
    channel: "EMAIL",
    subject: "",
    body_template: "",
    is_active: true
  });
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const response = await api.get<ApiResponse<Template>>(`/notifications/templates/${id}`);
        setTemplate(response.data.data);
      } catch (err) {
        setError(apiMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (editing) {
        await api.put(`/notifications/templates/${id}`, template);
        showToast("Şablon güncellendi", "Değişiklikler kaydedildi.");
      } else {
        await api.post("/notifications/templates", template);
        showToast("Şablon oluşturuldu", "Yeni şablon eklendi.");
      }
      navigate("/notifications/templates");
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="card"><LoadingState label="Şablon yükleniyor" /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Mesaj şablonları"
        title={editing ? "Şablon düzenle" : "Yeni şablon"}
        description="Değişken destekli mesaj şablonları oluşturun."
      >
        <Link className="btn btn-secondary" to="/notifications/templates">
          <ArrowLeft size={16} />Listeye dön
        </Link>
      </PageHeader>

      <form className="card form-card" onSubmit={save}>
        {error && (
          <div className="field-error" style={{ marginBottom: 18, padding: 12, borderRadius: 10, background: "#fff0ef" }}>
            {error}
          </div>
        )}

        <div className="form-section">
          <h2>Temel bilgiler</h2>
          <p>Şablonun kimlik ve kanal bilgileri.</p>
          <div className="form-grid">
            <Field label="Şablon adı" required>
              <input
                type="text"
                value={template.name}
                onChange={(e) => setTemplate({ ...template, name: e.target.value })}
                placeholder="Örn: Ödeme hatırlatma"
                required
              />
            </Field>
            <Field label="Kod" required>
              <input
                type="text"
                value={template.code}
                onChange={(e) => setTemplate({ ...template, code: e.target.value })}
                placeholder="Örn: PAYMENT_REMINDER"
                required
              />
            </Field>
            <Field label="Kanal" required>
              <select
                value={template.channel}
                onChange={(e) => setTemplate({ ...template, channel: e.target.value })}
                required
              >
                <option value="EMAIL">E-posta</option>
                <option value="SMS">SMS</option>
                <option value="WHATSAPP">WhatsApp</option>
              </select>
            </Field>
            {template.channel === "EMAIL" && (
              <Field label="Konu">
                <input
                  type="text"
                  value={template.subject || ""}
                  onChange={(e) => setTemplate({ ...template, subject: e.target.value })}
                  placeholder="E-posta konusu"
                />
              </Field>
            )}
            <Field label="Durum">
              <label className="checkbox-line">
                <input
                  type="checkbox"
                  checked={template.is_active}
                  onChange={(e) => setTemplate({ ...template, is_active: e.target.checked })}
                />
                Aktif
              </label>
            </Field>
          </div>
        </div>

        <div className="form-section">
          <h2>Mesaj içeriği</h2>
          <p>Değişken kullanarak dinamik mesajlar oluşturun.</p>
          <Field label="Mesaj şablonu" required full>
            <textarea
              value={template.body_template}
              onChange={(e) => setTemplate({ ...template, body_template: e.target.value })}
              placeholder="Sayın {{parent_name}}, {{student_name}} için ödeme hatırlatması..."
              rows={8}
              required
            />
          </Field>
          <div style={{ marginTop: 12, padding: 12, background: "#f8f9fa", borderRadius: 8 }}>
            <div style={{ font: "600 13px Manrope", marginBottom: 8 }}>Kullanılabilir değişkenler:</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {variables.map((variable) => (
                <button
                  key={variable.name}
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setTemplate({ 
                    ...template, 
                    body_template: template.body_template + variable.name 
                  })}
                  style={{ fontSize: 12, padding: "4px 8px" }}
                  title={variable.description}
                >
                  {variable.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="form-actions">
          <Link className="btn btn-secondary" to="/notifications/templates">
            Vazgeç
          </Link>
          <button className="btn btn-primary" disabled={saving}>
            <Save size={16} />
            {saving ? "Kaydediliyor..." : "Kaydet"}
          </button>
        </div>
      </form>
    </>
  );
}
