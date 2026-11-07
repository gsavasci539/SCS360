import { getAnalysis } from "../../lib/analysis";
import { Users, Calendar, TrendingUp, Trophy } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";
import { ClubWorkspace } from "./ClubWorkspace";

export function ClubsPage() {
  const [clubs, setClubs] = useState<DataRecord[]>([]);
  const [events, setEvents] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [clubPage, setClubPage] = useState(1);
  const [eventPage, setEventPage] = useState(1);
  const [moreClubs, setMoreClubs] = useState(false);
  const [moreEvents, setMoreEvents] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const sequence = useRef(0);

  const load = useCallback(async () => {
      const request = ++sequence.current;
      setRefreshing(true);
      setError("");
      try {
        const [clubsRes, eventsRes, analysisRes] = await Promise.all([
          api.get<ApiResponse<DataRecord[]>>("/clubs", { params: { limit: 21, offset: (clubPage - 1) * 20 } }),
          api.get<ApiResponse<DataRecord[]>>("/clubs/events", { params: { limit: 21, offset: (eventPage - 1) * 20 } }),
          getAnalysis("/ai/clubs-analysis").catch(() => null),
        ]);
        if (request !== sequence.current) return;
        setClubs((clubsRes.data.data || []).slice(0, 20));
        setEvents((eventsRes.data.data || []).slice(0, 20));
        setMoreClubs((clubsRes.data.data || []).length > 20);
        setMoreEvents((eventsRes.data.data || []).length > 20);
        setAiAnalysis(analysisRes?.data.data || null);
      } catch (err) {
        if (request === sequence.current) setError(apiMessage(err));
      } finally {
        if (request === sequence.current) { setLoading(false); setRefreshing(false); }
      }
  }, [clubPage, eventPage]);
  useEffect(() => { void load(); }, [load]);


  if (loading) return <div className="card"><LoadingState label="Yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={() => void load()} /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Kulüpler"
        title="Okul Kulüpleri"
        description="Kulüpler, üyelikler ve sosyal etkinlikler"
      />
      {aiAnalysis && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>Kulüp özeti</h2>
              <p>Kayıtlardan hesaplanan kulüp bilgileri ve genel öneriler</p>
            </div>
            <Trophy size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", gap: 16, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Kulüp</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.total_clubs}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Üye</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.total_members}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Yaklaşan etkinlik</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.upcoming_events}</div>
              </div>
            </div>
            {aiAnalysis.recommendations && aiAnalysis.recommendations.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Genel öneriler</h3>
                {aiAnalysis.recommendations.slice(0, 3).map((rec: string, index: number) => (
                  <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}>
                    <TrendingUp size={16} color="#176b5b" style={{ flexShrink: 0, marginTop: 2 }} />
                    <span style={{ fontSize: 13 }}>{rec}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Kulüpler</h2>
          <span className="badge badge-green">{String(clubs.length)}</span>
        </div>
        <div className="card-pad table-wrap">
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
                    <td>{String(club.advisor_name || "—")}</td>
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

      {(moreClubs || clubPage > 1) && <div className="toolbar" aria-label="Kulüp sayfaları" style={{ marginTop: 12 }}>
        <button className="btn btn-secondary" disabled={refreshing || clubPage === 1} onClick={() => setClubPage((value) => value - 1)}>Önceki</button>
        <span>Sayfa {clubPage}</span><button className="btn btn-secondary" disabled={refreshing || !moreClubs} onClick={() => setClubPage((value) => value + 1)}>Sonraki</button>
      </div>}

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Etkinlikler</h2>
          <span className="badge badge-green">{String(events.length)}</span>
        </div>
        <div className="card-pad table-wrap">
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
                    <td>{String(event.location || "—")}</td>
                    <td><Badge value={String(event.status)} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      {(moreEvents || eventPage > 1) && <div className="toolbar" aria-label="Etkinlik sayfaları" style={{ marginTop: 12 }}>
        <button className="btn btn-secondary" disabled={refreshing || eventPage === 1} onClick={() => setEventPage((value) => value - 1)}>Önceki</button>
        <span>Sayfa {eventPage}</span><button className="btn btn-secondary" disabled={refreshing || !moreEvents} onClick={() => setEventPage((value) => value + 1)}>Sonraki</button>
      </div>}
      <ClubWorkspace onChange={load} />
    </>
  );
}
