import { Bus, MapPin, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function BusPage() {
  const [routes, setRoutes] = useState<DataRecord[]>([]);
  const [attendance, setAttendance] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [routesRes, attendanceRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/bus/routes"),
          api.get<ApiResponse<DataRecord[]>>("/bus/attendance?limit=50")
        ]);
        setRoutes(routesRes.data.data || []);
        setAttendance(attendanceRes.data.data || []);
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
        eyebrow="Ulaşım"
        title="Servis Yönetimi"
        description="Okul servis rotaları ve öğrenci katılımı"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Servis Rotaları</h2>
          <span className="badge badge-green">{String(routes.length)}</span>
        </div>
        <div className="card-pad">
          {routes.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz rota oluşturulmadı</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rota Adı</th>
                  <th>Plaka</th>
                  <th>Sürücü</th>
                  <th>Kapasite</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {routes.map((route) => (
                  <tr key={route.id}>
                    <td><Bus size={14} /> {String(route.route_name)}</td>
                    <td>{String(route.plate_number)}</td>
                    <td>{String(route.driver_name)}</td>
                    <td><Users size={14} /> {String(route.capacity)}</td>
                    <td><Badge value={route.is_active ? "ACTIVE" : "INACTIVE"} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Son Katılımlar</h2>
          <span className="badge badge-green">{String(attendance.length)}</span>
        </div>
        <div className="card-pad">
          {attendance.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz katılım kaydı yok</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Rota</th>
                  <th>Tarih</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {attendance.map((att) => (
                  <tr key={att.id}>
                    <td>{String(att.student_name)}</td>
                    <td><MapPin size={14} /> {String(att.route_name)}</td>
                    <td>{String(att.attendance_date)}</td>
                    <td><Badge value={String(att.status)} /></td>
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
