import { useEffect, useState } from "react";
import { api, apiMessage } from "../../lib/api";

type Readiness = {
  state: string; mode: string; available: boolean; enabled: boolean; configured: boolean;
  missing_fields: string[]; invalid_fields: string[]; warnings: string[]; organization_id: string | null;
};
type Report = { saas: Readiness; school: Readiness; provider_verified: false };

function validReport(value: unknown): value is Report {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const report = value as Record<string, unknown>;
  return report.provider_verified === false && [report.saas, report.school].every((row) => {
    if (!row || typeof row !== "object" || Array.isArray(row)) return false;
    const current = row as Record<string, unknown>;
    return ["available", "enabled", "configured"].every((field) => typeof current[field] === "boolean")
      && typeof current.state === "string" && typeof current.mode === "string"
      && (current.organization_id === null || typeof current.organization_id === "string")
      && ["missing_fields", "invalid_fields", "warnings"].every((field) => Array.isArray(current[field]) && (current[field] as unknown[]).every((item) => typeof item === "string"));
  });
}

function status(row: Readiness) {
  if (row.state === "blocked_environment") return "Ortam ayarı engelliyor";
  if (!row.configured) return "Kurulum bekleniyor";
  if (!row.enabled) return "Yapılandırıldı · kapalı";
  return row.mode === "sandbox" ? "iyzico Sandbox · test ortamı" : "Canlı ortam yapılandırıldı";
}

export function PaymentReadinessPanel() {
  const [data, setData] = useState<Report | null>(null), [error, setError] = useState("");
  const [loading, setLoading] = useState(true), [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError("");
    api.get("/platform/payment-readiness", { signal: controller.signal }).then((response) => {
      if (!controller.signal.aborted) {
        if (!validReport(response.data.data)) { setData(null); throw new Error("Ödeme yapılandırmasının yanıtı geçersiz."); }
        setData(response.data.data);
      }
    }).catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [revision]);
  return <section className="card card-pad" style={{ marginTop: 18 }} aria-label="Online ödeme kurulumu">
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}><h2>Online ödeme kurulumu</h2>
      <button className="btn btn-secondary" disabled={loading} onClick={() => setRevision((value) => value + 1)}>Ödeme ayarlarını yenile</button></div>
    <p>Üyelik gelirleri ile okulların öğrenci tahsilatları ayrı ödeme hesaplarıdır. Anahtar değerleri bu ekrana gönderilmez.</p>
    {error && <p role="alert">{error}</p>}{loading && !data && <p role="status">Ödeme yapılandırması kontrol ediliyor…</p>}
    {data && <><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 290px), 1fr))", gap: 18 }}>
      {([ ["saas", "SCS360 üyelik ödemeleri"], ["school", "Mevcut kurum öğrenci ödemeleri"] ] as const).map(([key, title]) => {
        const row = data[key];
        return <article key={key} aria-label={title} style={{ padding: 18, border: "1px solid var(--line)", borderRadius: 12, minWidth: 0 }}>
          <h3 style={{ marginTop: 0 }}>{title}</h3><p><strong>{status(row)}</strong></p>
          {key === "school" && <p>Bu alan, tek kuruma açıkça bağlanan mevcut öğrenci ödeme hesabını gösterir.</p>}
          {row.organization_id && <p style={{ overflowWrap: "anywhere" }}>Bağlı kurum: {row.organization_id}</p>}
          {row.missing_fields.length > 0 && <><h4>Eksik ayarlar</h4><ul>{row.missing_fields.map((field) => <li style={{ overflowWrap: "anywhere" }} key={field}>{field}</li>)}</ul></>}
          {row.invalid_fields.length > 0 && <><h4>Kontrol edilmesi gereken ayarlar</h4><ul>{row.invalid_fields.map((field) => <li style={{ overflowWrap: "anywhere" }} key={field}>{field}</li>)}</ul></>}
          {row.state === "blocked_environment" && <p>Üretim veya staging ortamında sandbox ödemesi açılamaz.</p>}
          {row.warnings.includes("PUBLIC_HTTPS_CALLBACK_REQUIRED_FOR_PROVIDER_ACCEPTANCE") && <p>Yerel dönüş adresi tanımlı. Sağlayıcı kabulü için geçerli SSL sertifikalı erişilebilir bir dönüş adresi gerekir.</p>}
          {row.available && <p>Bu durum ayarların kontrol edildiğini gösterir. Sağlayıcıyla başarılı ödeme ve sonuç doğrulaması ayrıca test edilmelidir.</p>}
        </article>;
      })}
    </div><p>Sandbox hesabınız ve API anahtarlarınız yoksa iyzico hesabınızdan edinmelisiniz. Başka hesaptan anahtar veya hazır test tahsilatı kullanılmaz.</p></>}
  </section>;
}
