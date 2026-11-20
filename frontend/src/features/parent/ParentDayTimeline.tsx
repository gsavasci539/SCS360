import { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, ErrorState, LoadingState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
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

function DailyReportDetails({ details }: { details: DayEvent["details"] }) {
  const [expanded, setExpanded] = useState(false);
  const contentId = useId();
  const observations = [["Yemek", details.meal_status], ["Uyku", details.sleep_status], ["Duygu durumu", details.mood],
    ["Etkinlikler", formatDayActivities(details.activities)], ["Öğretmen notu", details.teacher_notes]].filter(([, value]) => value);

  return <>
    <button type="button" className="btn btn-ghost" style={{ marginTop: 8 }} aria-expanded={expanded} aria-controls={contentId}
      onClick={() => setExpanded((open) => !open)}>{expanded ? "Karne ayrıntısını kapat" : "Karne ayrıntısını aç"}</button>
    <div id={contentId} hidden={!expanded}>
      {expanded && (observations.length ? observations.map(([label, value]) =>
        <p key={label} style={{ overflowWrap: "anywhere" }}>{label} · {value}</p>) : <p>Bu karne için gözlem kaydı yok.</p>)}
    </div>
  </>;
}

export function ParentDayTimeline({ studentId, initialDate, selectedDate, onDayChange }: {
  studentId: string;
  initialDate: string;
  selectedDate?: string;
  onDayChange?: (date: string) => void;
}) {
  const canReadAttendance = useAuthStore((state) => state.can("parent.view_attendance"));
  const [localDay, setLocalDay] = useState(initialDate);
  const day = selectedDate ?? localDay;
  const setDay = onDayChange ?? setLocalDay;
  const [result, setResult] = useState<{ studentId: string; day: string; events: DayEvent[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!day) { setLoading(false); setError(""); setResult(null); return; }
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
        {events.map((event) => <li key={`${studentId}:${day}:${event.id}`} style={{ padding: "16px 0", borderBottom: "1px solid #e8eeeb" }}>
            <div className="toolbar" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
              <strong>{event.time || "Saat belirtilmedi"} · {event.title}</strong><Badge value={event.status} />
            </div>
            {event.type === "DAILY_REPORT" ? <DailyReportDetails details={event.details} /> : <>
              {(event.details.teacher_notes || event.details.notes || event.details.complaint || event.details.medicine_name || event.details.pickup_person_name) &&
                <p style={{ overflowWrap: "anywhere" }}>{[event.details.medicine_name, event.details.dosage,
                  event.details.teacher_notes || event.details.notes || event.details.complaint || event.details.pickup_person_name].filter(Boolean).join(" · ")}</p>}
              {(event.type !== "ATTENDANCE" || canReadAttendance) &&
                <Link to={event.detail_url} className="btn btn-ghost" style={{ marginTop: 8 }}
                  state={event.type === "ATTENDANCE" ? { parentAttendance: { studentId, date: day } } : undefined}>İlgili sayfayı aç</Link>}
            </>}
          </li>)}
      </ol>}
  </section>;
}
