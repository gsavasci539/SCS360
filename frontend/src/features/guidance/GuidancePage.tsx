import { MessageSquare, AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function GuidancePage() {
  const [sessions, setSessions] = useState<DataRecord[]>([]);
  const [incidents, setIncidents] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [sessionsRes, incidentsRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/guidance/sessions"),
          api.get<ApiResponse<DataRecord[]>>("/guidance/incidents")
        ]);
        setSessions(sessionsRes.data.data || []);
        setIncidents(incidentsRes.data.data || []);
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
        eyebrow="Rehberlik"
        title="Rehberlik Servisi"
        description="Öğrenci rehberlik oturumları ve davranış kayıtları"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Rehberlik Oturumları</h2>
          <span className="badge badge-green">{String(sessions.length)}</span>
        </div>
        <div className="card-pad">
          {sessions.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz oturum kaydı yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Tarih</th>
                  <th>Konu</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id}>
                    <td>{String(session.student_name)}</td>
                    <td>{String(session.session_date)}</td>
                    <td><MessageSquare size={14} /> {String(session.topic)}</td>
                    <td><Badge value={String(session.status)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Davranış Kayıtları</h2>
          <span className="badge badge-green">{String(incidents.length)}</span>
        </div>
        <div className="card-pad">
          {incidents.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz davranış kaydı yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Tarih</th>
                  <th>Tür</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((incident) => (
                  <tr key={incident.id}>
                    <td>{String(incident.student_name)}</td>
                    <td>{String(incident.incident_date)}</td>
                    <td><AlertTriangle size={14} /> {String(incident.incident_type)}</td>
                    <td><Badge value={String(incident.status)} /></td>
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
