import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse } from "../../types/api";

interface DayEvent {
  id: string;
  type: string;
  title: string;
  status: string;
  time: string | null;
  detail_url: string;
  details: { notes?: string; teacher_notes?: string; medicine_name?: string; dosage?: string; activities?: unknown;
    meal_status?: string; sleep_status?: string; mood?: string;
    complaint?: string; pickup_person_name?: string };
}

export function formatDayActivities(value: unknown): string {
  if (typeof value === "string") return value.trim();
  if (!Array.isArray(value)) return "";
  return value.flatMap((entry) => typeof entry === "string" && entry.trim() ? [entry.trim()] : []).join(", ");
}

export function ParentDayTimeline({ studentId, initialDate }: { studentId: string; initialDate: string }) {
  const [day, setDay] = useState(initialDate);
  const [result, setResult] = useState<{ studentId: string; day: string; events: DayEvent[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!day) { setLoading(false); return; }
    const controller = new AbortController();
    setLoading(true);
    setResult(null);
    setError("");
    api.get<ApiResponse<{ student_id: string; date: string; events: DayEvent[] }>>(`/parent/child/${studentId}/timeline`, {
      params: { date: day }, signal: controller.signal,
    }).then((response) => {
      if (controller.signal.aborted) return;
      const data = response.data.data;
      if (data.student_id !== studentId || data.date !== day || !Array.isArray(data.events)) throw new Error("Günlük akış seçimi doğrulanamadı.");
      setResult({ studentId, day, events: data.events });
    })
      .catch((reason) => { if (!controller.signal.aborted) setError(apiMessage(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [studentId, day, retry]);
  const events = result?.studentId === studentId && result.day === day ? result.events : [];
  return <section className="card card-pad" aria-label="Çocuğun günlük akışı" style={{ margin: "20px 0" }}>
    <div className="toolbar" style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
      <h2>Günün akışı</h2>
      <label>Akış tarihi<input aria-label="Akış tarihi" type="date" value={day} className="filter-select" onChange={(event) => setDay(event.target.value)} /></label>
    </div>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => setRetry((value) => value + 1)} /> : events.length === 0 ?
      <p>Bu gün için kayıtlı etkinlik yok.</p> : <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {events.map((event) => {
          const activities = formatDayActivities(event.details.activities);
          const observations = [["Yemek", event.details.meal_status], ["Uyku", event.details.sleep_status],
            ["Duygu durumu", event.details.mood]].filter(([, value]) => value);
          return <li key={event.id} style={{ padding: "16px 0", borderBottom: "1px solid #e8eeeb" }}>
            <div className="toolbar" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
              <strong>{event.time || "Saat belirtilmedi"} · {event.title}</strong><Badge value={event.status} />
            </div>
            {(event.details.teacher_notes || event.details.notes || event.details.complaint || event.details.medicine_name || event.details.pickup_person_name) &&
              <p style={{ overflowWrap: "anywhere" }}>{[event.details.medicine_name, event.details.dosage,
                event.details.teacher_notes || event.details.notes || event.details.complaint || event.details.pickup_person_name].filter(Boolean).join(" · ")}</p>}
            {observations.map(([label, value]) => <p key={label} style={{ overflowWrap: "anywhere" }}>{label} · {value}</p>)}
            {activities && <p style={{ overflowWrap: "anywhere" }}>Etkinlikler · {activities}</p>}
            <Link to={event.detail_url} className="btn btn-ghost" style={{ marginTop: 8 }}>İlgili sayfayı aç</Link>
          </li>;
        })}
      </ol>}
  </section>;
}
