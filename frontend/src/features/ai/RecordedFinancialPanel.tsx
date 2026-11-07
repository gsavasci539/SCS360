import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PaymentForecastCard } from "../finance/PaymentForecastCard";
import { money } from "../../lib/format";
import type { DataRecord, RecordValue } from "../../types/api";

function amount(value: unknown): number | null {
  if ((typeof value !== "number" && typeof value !== "string") || (typeof value === "string" && !value.trim())) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}
function shownAmount(value: unknown) {
  const parsed = amount(value);
  return parsed === null ? "—" : money(parsed);
}
function monthRows(value: RecordValue, amountKey: string, countKey: string) {
  if (!Array.isArray(value)) return [];
  return value.flatMap((row) => {
    if (!row || typeof row !== "object" || typeof row.month !== "string" || !/^\d{4}-(0[1-9]|1[0-2])$/.test(row.month)) return [];
    const count = row[countKey];
    return [{ month: row.month, amount: amount(row[amountKey]), count: typeof count === "number" && Number.isInteger(count) && count >= 0 ? count : null }];
  });
}
function monthLabel(value: string) {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(value) || Number(value.slice(0, 4)) < 1) return "—";
  return new Intl.DateTimeFormat("tr-TR", { month: "short", year: "numeric" }).format(new Date(`${value}-01T12:00:00Z`));
}

export function RecordedFinancialPanel({ summary }: { summary: DataRecord }) {
  const history = monthRows(summary.historical_monthly, "collected_amount", "payment_count");
  const schedule = monthRows(summary.monthly_forecast, "scheduled_amount", "debt_count");
  const canChart = history.length >= 2 && history.every((row) => row.amount !== null);
  return <div className="tab-content">
    <div className="card card-pad" style={{ marginBottom: 18 }}>
      <h2>Kayıtlı finans analizi</h2><p>Tamamlanmış tahsilat geçmişi ve kayıtlı borçların vade takvimi.</p>
      <Link className="btn btn-secondary" to="/finance/debts">Borç listesini aç</Link>
    </div>
    <PaymentForecastCard summary={summary} />
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: 18 }}>
      <section className="card card-pad" style={{ minWidth: 0 }} aria-label="Tahsilat geçmişi">
        <h3>Kayıtlı tahsilat geçmişi</h3><p>Ödeme tarihinin okul takvimindeki ayına göre tamamlanmış kayıtlar.</p>
        {history.length ? <div className="table-wrap"><table className="data-table" aria-label="Kayıtlı tahsilat geçmişi">
          <thead><tr><th>Ay</th><th>Tahsil edilen</th><th>İşlem</th></tr></thead>
          <tbody>{history.map((row) => <tr key={row.month}><td>{monthLabel(row.month)}</td><td>{shownAmount(row.amount)}</td><td>{row.count ?? "—"}</td></tr>)}</tbody>
        </table></div> : <p>{summary.payment_count === 0 ? "Henüz tamamlanmış tahsilat kaydı bulunmuyor."
          : "Tahsilat kayıtları incelenmeli; aylık dağılım gösterilemiyor."}</p>}
      </section>
      <section className="card card-pad" style={{ minWidth: 0 }} aria-label="Kayıtlı vade takvimi">
        <h3>Kayıtlı vade takvimi</h3><p>Gösterilen tutarlar açık borçların kayıtlı vadeleridir; gerçekleşmiş gelir değildir.</p>
        {schedule.length ? <div className="table-wrap"><table className="data-table" aria-label="Kayıtlı vade takvimi">
          <thead><tr><th>Vade ayı</th><th>Açık bakiye</th><th>Borç kaydı</th></tr></thead>
          <tbody>{schedule.map((row) => <tr key={row.month}><td>{monthLabel(row.month)}</td><td>{shownAmount(row.amount)}</td><td>{row.count ?? "—"}</td></tr>)}</tbody>
        </table></div> : <p>Bu dönem için gösterilecek vade kaydı bulunmuyor.</p>}
      </section>
    </div>
    {canChart && <section className="card card-pad" style={{ marginTop: 18, minWidth: 0 }} aria-label="Aylık kayıtlı tahsilat grafiği">
      <h3>Aylık tamamlanmış tahsilatlar</h3>
      <div style={{ height: 260, width: "100%", minWidth: 0 }}><ResponsiveContainer width="100%" height="100%">
        <BarChart data={history}><CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="month" tickFormatter={monthLabel} /><YAxis />
          <Tooltip formatter={(value) => [shownAmount(value), "Tamamlanan tahsilat"]} labelFormatter={(value) => monthLabel(String(value))} />
          <Bar dataKey="amount" fill="#176b5b" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer></div>
    </section>}
  </div>;
}
