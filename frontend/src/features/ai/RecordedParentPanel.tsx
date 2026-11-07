import { shortDate } from "../../lib/format";
import { Link } from "react-router-dom";

type Metrics = Record<string, unknown>;
type Summary = { as_of?: unknown; period_start?: unknown; period_end_exclusive?: unknown;
  registration_metrics?: Metrics; communication_metrics?: Metrics; requires_review?: boolean };
function count(value: unknown) {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? String(value) : "—";
}
function percent(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100 ? `%${value}` : "—";
}
function day(value: unknown) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const timestamp = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === value ? value : null;
}
export function RecordedParentPanel({ summary }: { summary: Summary }) {
  const registration = summary.registration_metrics || {}, communication = summary.communication_metrics || {};
  const asOf = day(summary.as_of), start = day(summary.period_start), end = day(summary.period_end_exclusive);
  const stats = [["Veli iletişim kaydı", registration.total_records], ["İletişim bilgisi olan kayıt", registration.records_with_contact],
    ["İletişim bilgisi eksik kayıt", registration.records_without_contact], ["Giriş hesabına bağlı kayıt", registration.account_linked_records],
    ["Bildirim tercihi açık kayıt", registration.notification_allowed_records], ["Bildirim tercihi kapalı kayıt", registration.notification_declined_records]];
  return <div className="tab-content">
    <section className="card card-pad" style={{ marginBottom: 18 }}>
      <h2>Veli iletişim özeti</h2><p>İletişim kayıtları, hesap bağlantıları ve veli kaydına bağlı gönderim sonuçları.</p>
      <Link className="btn btn-secondary" to="/parents">Veli kayıtlarını aç</Link>
      <p>Bu sayımlar veli duygu veya memnuniyetini ölçmez. Aynı kişiye ait birden fazla iletişim kaydı ayrı sayılır.</p>
      {asOf && <p className="cell-sub">İletişim kayıtlarının güncel durumu: {shortDate(asOf)}</p>}
      {summary.requires_review && <p role="status">Bazı tercih veya gönderim sonuçları incelenmeli; bilinmeyen değerler — ile gösterilir.</p>}
      <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))", gap: 16 }}>
        {stats.map(([label, value]) => <div key={String(label)}><dt>{String(label)}</dt><dd>{count(value)}</dd></div>)}
        <div><dt>İletişim bilgisi bulunma oranı</dt><dd>{percent(registration.contact_availability_rate)}</dd></div>
        <div><dt>Bildirim tercihi açık kayıt oranı</dt><dd>{percent(registration.notification_consent_rate)}</dd></div>
        <div><dt>Bildirim tercihi bilinmeyen kayıt</dt><dd>{count(registration.notification_unknown_records)}</dd></div>
      </dl>
      <p className="cell-sub">Hesap bağlantısı, veli kaydının aynı kurumdaki silinmemiş bir giriş hesabına bağlı olduğunu belirtir; oturum kullanımı değildir.</p>
    </section>
    <section className="card card-pad" style={{ minWidth: 0 }}>
      <h3>Veli kaydına bağlı gönderimler</h3>
      <Link className="btn btn-secondary" to="/outbox">Gönderim kayıtlarını aç</Link>
      {start && end && start < end && <p>Kayıt dönemi: {shortDate(start)} ve sonrası, {shortDate(end)} tarihinden önce oluşturulan gönderimler.</p>}
      <p>Gönderildi durumu kayıtlı sağlayıcı gönderim sonucudur; okundu veya teslim edildi anlamına gelmez. Genel görevler ve veliye bağlanmamış alıcılar bu sayımlara dahil edilmez.</p>
      <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 240px), 1fr))", gap: 16 }}>
        <div><dt>Gönderim kaydı</dt><dd>{count(communication.record_count)}</dd></div>
        <div><dt>Sonuçlanan gönderimlerde gönderildi oranı</dt><dd>{percent(communication.send_success_rate)}</dd></div>
      </dl>
      {communication.record_count === 0 ? <p>Bu dönemde veli kaydına bağlı gönderim kaydı bulunmuyor.</p> : <div className="table-wrap">
        <table className="data-table" aria-label="Veli gönderim kayıtları"><thead><tr><th>Kayıtlı durum</th><th>Alıcı kaydı</th></tr></thead>
          <tbody>{[["Gönderildi", communication.sent_count], ["Bekliyor", communication.pending_count],
            ["Başarısız", communication.failed_count], ["İptal", communication.cancelled_count], ["İncelenmeli", communication.unknown_count]]
            .map(([label, value]) => <tr key={String(label)}><td>{String(label)}</td><td>{count(value)}</td></tr>)}</tbody>
        </table></div>}
      <p className="cell-sub">Oran yalnız gönderildi ve başarısız kayıtları karşılaştırır. Bekleyen, iptal ve bilinmeyen kayıtlar bu oranın dışında tutulur.</p>
    </section>
  </div>;
}
