import { Calendar, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function TutoringPage() {
  const [sessions, setSessions] = useState<DataRecord[]>([]);
  const [requests, setRequests] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [sessionsRes, requestsRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/tutoring/sessions"),
          api.get<ApiResponse<DataRecord[]>>("/tutoring/requests")
        ]);
        setSessions(sessionsRes.data.data || []);
        setRequests(requestsRes.data.data || []);
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
        eyebrow="Etüt & Birebir Ders"
        title="Etüt Yönetimi"
        description="Etüt oturumları ve birebir ders talepleri"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Etüt Oturumları</h2>
          <span className="badge badge-green">{String(sessions.length)}</span>
        </div>
        <div className="card-pad">
          {sessions.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz etüt oturumu yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Ders</th>
                  <th>Tarih</th>
                  <th>Saat</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id}>
                    <td>{String(session.student_name)}</td>
                    <td>{String(session.subject)}</td>
                    <td><Calendar size={14} /> {String(session.session_date)}</td>
                    <td><Clock size={14} /> {String(session.start_time)} - {String(session.end_time)}</td>
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
          <h2>Ders Talepleri</h2>
          <span className="badge badge-green">{String(requests.length)}</span>
        </div>
        <div className="card-pad">
          {requests.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz ders talebi yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Ders</th>
                  <th>İstenen Tarih</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => (
                  <tr key={request.id}>
                    <td>{String(request.student_name)}</td>
                    <td>{String(request.subject)}</td>
                    <td><Calendar size={14} /> {String(request.requested_date)}</td>
                    <td><Badge value={String(request.status)} /></td>
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
