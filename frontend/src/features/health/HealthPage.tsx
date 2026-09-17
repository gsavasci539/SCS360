import { HeartPulse, Calendar } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function HealthPage() {
  const [records, setRecords] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await api.get<ApiResponse<DataRecord[]>>("/infirmary/health-records");
        setRecords(res.data.data || []);
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
        eyebrow="Sağlık"
        title="Revir & İlaç Kayıtları"
        description="Öğrenci sağlık kayıtları ve ilaç programları"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Sağlık Kayıtları</h2>
          <span className="badge badge-green">{String(records.length)}</span>
        </div>
        <div className="card-pad">
          {records.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz sağlık kaydı yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Şikayet</th>
                  <th>Tarih</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.id}>
                    <td>{String(record.student_name)}</td>
                    <td><HeartPulse size={14} /> {String(record.complaint)}</td>
                    <td><Calendar size={14} /> {String(record.visit_date)}</td>
                    <td><Badge value={String(record.status)} /></td>
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
