import { money, shortDate } from "../../lib/format";
import type { DataRecord, RecordValue } from "../../types/api";

function knownMoney(value: RecordValue) {
  return (typeof value === "number" || typeof value === "string") && value !== "" && Number.isFinite(Number(value)) ? money(value) : "—";
}
function recordedDay(value: RecordValue) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const timestamp = Date.parse(`${value}T00:00:00Z`);
  return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === value ? value : null;
}
export function PaymentForecastCard({ summary }: { summary: DataRecord }) {
  const rate = Number(summary.collection_rate);
  const asOf = recordedDay(summary.as_of), start = recordedDay(summary.period_start), end = recordedDay(summary.period_end_exclusive);
  const months = typeof summary.months === "number" && Number.isInteger(summary.months) && summary.months >= 1 && summary.months <= 24 ? summary.months : null;
  return <section className="card" style={{ padding: 20, marginBottom: 18 }}>
    <h2>Tahsilat özeti</h2><p>Kayıtlı borç ve tamamlanmış tahsilatlar. Dönem tutarı vade kayıtlarından hesaplanır.</p>
    {asOf && <p className="cell-sub">Kayıt tarihi: {shortDate(asOf)}</p>}
    {start && end && start < end && <p className="cell-sub">Vade dönemi{months ? ` (${months} takvim ayı)` : ""}: {shortDate(start)} ve sonrası, {shortDate(end)} tarihinden önceki vadeler.</p>}
    {summary.requires_review === true && <p role="status">Eski tutar veya tarih kayıtları incelenmeli. Eksik toplamlar — ile gösterilir.</p>}
    <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 150px), 1fr))", gap: 16 }}>
      <div><dt>Dönem vadeli bakiye</dt><dd>{knownMoney(summary.total_expected)}</dd></div>
      <div><dt>Açık borç</dt><dd>{knownMoney(summary.outstanding_debt)}</dd></div>
      <div><dt>Tahsilat oranı</dt><dd>{summary.collection_rate != null && Number.isFinite(rate) && rate >= 0 && rate <= 100 ? `%${rate}` : "—"}</dd></div>
      <div><dt>Vadesi geçmiş bakiye</dt><dd>{knownMoney(summary.overdue_amount)}</dd></div>
      <div><dt>Kayıtlı tahsilat toplamı</dt><dd>{knownMoney(summary.collected_total)}</dd></div>
    </dl>
    {Array.isArray(summary.recommendations) && summary.recommendations.filter((row) => typeof row === "string").map((row, index) => <p key={index}>{String(row)}</p>)}
  </section>;
}
