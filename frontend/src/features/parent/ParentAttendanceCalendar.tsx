import { useState } from "react";

interface DayRecord {
  date: string;
  status?: string | null;
  check_in_time?: string | null;
  check_out_time?: string | null;
  note?: string | null;
}

const weekdays = ["Pt", "Sa", "Ça", "Pe", "Cu", "Ct", "Pz"];
const dayStatuses: Record<string, { label: string; color: string }> = {
  PRESENT: { label: "Mevcut", color: "#e4f4eb" },
  LATE: { label: "Geç", color: "#fff4d6" },
  ABSENT: { label: "Devamsız", color: "#ffe8e6" },
  EXCUSED: { label: "İzinli", color: "#e7f1fb" },
};

function readDay(calendar: unknown, day: number, date: string): DayRecord | null {
  if (!calendar || typeof calendar !== "object" || Array.isArray(calendar)) return null;
  const row = (calendar as Record<string, unknown>)[String(day)];
  return row && typeof row === "object" && "date" in row && row.date === date ? row as DayRecord : null;
}

export function ParentAttendanceCalendar({ year, month, calendar, initialDay }: {
  year: number; month: number; calendar: unknown; initialDay?: number;
}) {
  const [day, setDay] = useState(initialDay);
  const prefix = `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}`;
  const first = new Date(`${prefix}-01T00:00:00Z`);
  const last = new Date(first.getTime());
  last.setUTCMonth(last.getUTCMonth() + 1, 0);
  const offset = (first.getUTCDay() + 6) % 7;
  const dates = Array.from({ length: last.getUTCDate() }, (_, index) => {
    const number = index + 1;
    const date = `${prefix}-${String(number).padStart(2, "0")}`;
    const row = readDay(calendar, number, date);
    const status = row?.status ? dayStatuses[row.status] : undefined;
    return { number, date, row, label: status?.label ?? (row?.status ? "Durum belirtilmedi" : "Kayıt yok"), color: status?.color };
  });
  const selected = dates.find((date) => date.number === day);

  return <section className="card card-pad" aria-label="Aylık yoklama takvimi" style={{ marginTop: 16 }}>
    <h2>Yoklama takvimi</h2>
    {selected && <div aria-live="polite" style={{ marginBlock: 12, overflowWrap: "anywhere" }}>
      <strong>{selected.date} · {selected.label}</strong>
      {selected.row?.check_in_time && <p>Giriş · {selected.row.check_in_time}</p>}
      {selected.row?.check_out_time && <p>Çıkış · {selected.row.check_out_time}</p>}
      {selected.row?.note && <p style={{ whiteSpace: "pre-wrap" }}>{selected.row.note}</p>}
    </div>}
    <div role="group" aria-label="Yoklama günleri" style={{ display: "grid", gridTemplateColumns: "repeat(7, minmax(0, 1fr))", gap: 4 }}>
      {weekdays.map((weekday) => <span key={weekday} aria-hidden="true" style={{ textAlign: "center", overflowWrap: "anywhere" }}>{weekday}</span>)}
      {Array.from({ length: offset }, (_, index) => <span key={`empty-${index}`} aria-hidden="true" />)}
      {dates.map((date) => <button key={date.date} type="button" className="btn btn-secondary"
        aria-label={`${date.date} · ${date.label}`} aria-pressed={selected?.date === date.date} title={date.label}
        onClick={() => setDay(date.number)} style={{ padding: 0, minWidth: 0, minHeight: 44, overflowWrap: "anywhere",
          backgroundColor: date.color, borderColor: selected?.date === date.date ? "currentColor" : undefined }}>
        {date.number}
      </button>)}
    </div>
  </section>;
}
