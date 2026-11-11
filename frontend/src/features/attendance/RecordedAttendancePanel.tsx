import { StatCard } from "../../components/ui";
import { CalendarDays, Users } from "lucide-react";

export interface RecordedAttendanceSummary {
  current_rate: number | null;
  total_records: number;
  total_analyzed: number;
  students_without_records: number;
  total_risk_students: number;
  monitoring_threshold: number;
  period_start: string;
  period_end: string;
  requires_review: boolean;
  risk_results_limited: boolean;
  risk_alerts: Array<{ student_id: string; student_name: string; current_rate: number; record_count: number; trend: string }>;
  patterns: Array<{ student_id: string; student_name: string; patterns: Array<{ day: string; rate: number; record_count: number }> }>;
  recommendations: string[];
}

export function RecordedAttendancePanel({ summary }: { summary: RecordedAttendanceSummary }) {
  return <section className="card" aria-label="Kayıtlı devam özeti" style={{ marginBottom: 18 }}>
    <div className="card-head"><div>
      <h2>Kayıtlı devam özeti</h2>
      <p>{summary.period_start} – {summary.period_end} · Kaydedilen yoklamalar</p>
    </div></div>
    <div className="card-pad">
      <div className="grid stats-grid">
        <StatCard icon={<CalendarDays size={19} />} label="Kayıtlı devam oranı" value={summary.current_rate == null ? "—" : `%${summary.current_rate}`} />
        <StatCard icon={<Users size={19} />} label="Yoklama kaydı olan öğrenci" value={summary.total_analyzed} color="blue" />
        <StatCard icon={<Users size={19} />} label={`%${summary.monitoring_threshold} izleme eşiğinin altında`} value={summary.total_risk_students} color="orange" />
      </div>
      <p>{summary.total_records} yoklama kaydı · {summary.students_without_records} öğrenci için bu dönemde yoklama kaydı yok.</p>
      <p className="muted">İzinli kayıtlar oran hesabının dışında tutulur; yarım gün 0,5 gün sayılır.</p>
      {summary.requires_review && <p role="status">Tanınmayan yoklama durumları var; oranlar incelenmeli.</p>}
      {summary.risk_alerts.length > 0 && <>
        <h3>İzleme eşiğinin altındaki öğrenciler</h3>
        {summary.risk_results_limited && <p>İlk {summary.risk_alerts.length} öğrenci gösteriliyor.</p>}
        <div style={{ overflowX: "auto" }}><table aria-label="Kayıtlı devam izleme listesi" className="data-table">
          <thead><tr><th>Öğrenci</th><th>Kayıtlı oran</th><th>Kayıt sayısı</th><th>Kayıtlı eğilim</th></tr></thead>
          <tbody>{summary.risk_alerts.map((row) => <tr key={row.student_id}>
            <td>{row.student_name}</td><td>%{row.current_rate}</td><td>{row.record_count}</td><td>{row.trend}</td>
          </tr>)}</tbody>
        </table></div>
      </>}
      {summary.patterns.length > 0 && <div style={{ marginTop: 16 }}>
        <h3>Öğrenci bazında kayıtlı gün örüntüleri</h3>
        {summary.patterns.map((row) => <div key={row.student_id} style={{ marginBottom: 12 }}>
          <strong>{row.student_name}</strong>
          {row.patterns.map((pattern) => <p key={pattern.day}>{pattern.day}: %{pattern.rate} devamsızlık · {pattern.record_count} kayıt</p>)}
        </div>)}
      </div>}
      {summary.recommendations.map((message, index) => <p key={index}>{message}</p>)}
    </div>
  </section>;
}
