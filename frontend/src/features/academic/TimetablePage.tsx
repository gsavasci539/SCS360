import { Calendar, Clock, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function TimetablePage() {
  const [slots, setSlots] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await api.get<ApiResponse<DataRecord[]>>("/timetable/slots");
        setSlots(res.data.data || []);
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
        eyebrow="Akademik"
        title="Ders Programı"
        description="Sınıf ve öğretmen ders programları yönetimi"
      />
      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <h2>Ders Slotları</h2>
          <span className="badge badge-green">{String(slots.length)}</span>
        </div>
        <div className="card-pad">
          {slots.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz ders slotu oluşturulmadı</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Gün</th>
                  <th>Saat</th>
                  <th>Ders</th>
                  <th>Sınıf</th>
                  <th>Öğretmen</th>
                </tr>
              </thead>
              <tbody>
                {slots.map((slot) => (
                  <tr key={slot.id}>
                    <td><Calendar size={14} /> {String(slot.day_of_week)}</td>
                    <td><Clock size={14} /> {String(slot.start_time)} - {String(slot.end_time)}</td>
                    <td>{String(slot.subject_name)}</td>
                    <td>{String(slot.class_name)}</td>
                    <td><Users size={14} /> {String(slot.teacher_name)}</td>
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
