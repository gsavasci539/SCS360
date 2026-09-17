import { Users, Calendar } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function ClubsPage() {
  const [clubs, setClubs] = useState<DataRecord[]>([]);
  const [events, setEvents] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [clubsRes, eventsRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/clubs"),
          api.get<ApiResponse<DataRecord[]>>("/clubs/events")
        ]);
        setClubs(clubsRes.data.data || []);
        setEvents(eventsRes.data.data || []);
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
        eyebrow="Kulüpler"
        title="Okul Kulüpleri"
        description="Kulüpler, üyelikler ve sosyal etkinlikler"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Kulüpler</h2>
          <span className="badge badge-green">{String(clubs.length)}</span>
        </div>
        <div className="card-pad">
          {clubs.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz kulüp oluşturulmadı</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Kulüp Adı</th>
                  <th>Danışman</th>
                  <th>Kapasite</th>
                  <th>Üye Sayısı</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {clubs.map((club) => (
                  <tr key={club.id}>
                    <td><Users size={14} /> {String(club.club_name)}</td>
                    <td>{String(club.advisor_teacher_name)}</td>
                    <td>{String(club.max_members)}</td>
                    <td>{String(club.current_members)}</td>
                    <td><Badge value={club.is_active ? "ACTIVE" : "INACTIVE"} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Etkinlikler</h2>
          <span className="badge badge-green">{String(events.length)}</span>
        </div>
        <div className="card-pad">
          {events.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz etkinlik oluşturulmadı</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Etkinlik Adı</th>
                  <th>Kulüp</th>
                  <th>Tarih</th>
                  <th>Konum</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id}>
                    <td><Calendar size={14} /> {String(event.event_name)}</td>
                    <td>{String(event.club_name)}</td>
                    <td>{String(event.event_date)}</td>
                    <td>{String(event.location)}</td>
                    <td><Badge value={String(event.status)} /></td>
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
