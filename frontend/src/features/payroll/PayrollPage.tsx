import { DollarSign, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function PayrollPage() {
  const [timesheets, setTimesheets] = useState<DataRecord[]>([]);
  const [payroll, setPayroll] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [timesheetsRes, payrollRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/payroll/timesheets?limit=50"),
          api.get<ApiResponse<DataRecord[]>>("/payroll/records?limit=50")
        ]);
        setTimesheets(timesheetsRes.data.data || []);
        setPayroll(payrollRes.data.data || []);
      } catch (err) {
        setError(apiMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="card"><LoadingState label="Yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Personel"
        title="Bordro & Puantaj"
        description="Personel puantaj kayıtları ve bordro yönetimi"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Puantaj Kayıtları</h2>
          <span className="badge badge-green">{String(timesheets.length)}</span>
        </div>
        <div className="card-pad">
          {timesheets.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz puantaj kaydı yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Personel</th>
                  <th>Tarih</th>
                  <th>Çalışma Saati</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {timesheets.map((ts) => (
                  <tr key={ts.id}>
                    <td>{String(ts.staff_name)}</td>
                    <td>{String(ts.date)}</td>
                    <td><Clock size={14} /> {String(ts.work_hours)} saat</td>
                    <td><Badge value={String(ts.status)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Bordro Kayıtları</h2>
          <span className="badge badge-green">{String(payroll.length)}</span>
        </div>
        <div className="card-pad">
          {payroll.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz bordro kaydı yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Personel</th>
                  <th>Dönem</th>
                  <th>Net Maaş</th>
                  <th>Ödeme Tarihi</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {payroll.map((pr) => (
                  <tr key={pr.id}>
                    <td>{String(pr.staff_name)}</td>
                    <td>{String(pr.period)} {String(pr.year)}</td>
                    <td><DollarSign size={14} /> {String(pr.net_salary)} TL</td>
                    <td>{String(pr.payment_date)}</td>
                    <td><Badge value={String(pr.status)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
