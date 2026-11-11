import { DollarSign, GraduationCap, MessageSquare, Users } from "lucide-react";
import { StatCard } from "../../components/ui";

export interface RecordedOverviewSummary {
  period_start: string;
  period_end: string;
  requires_review: boolean;
  insights: {
    academic_performance: { average_grade: number | null; at_risk_students: number; overall_trend: string };
    attendance: { overall_rate: number | null; trend: string };
    financial: { collection_rate: number | null; forecast_trend: string | null };
    parent_satisfaction: { score: string | null; sentiment: string | null };
  };
  priority_actions: string[];
}

const percent = (value: number | null) => value == null ? "—" : `%${value}`;
export function RecordedOverviewPanel({ summary }: { summary: RecordedOverviewSummary }) {
  const { academic_performance: academic, attendance, financial, parent_satisfaction: parents } = summary.insights;
  return <section className="card" aria-label="Kayıtlı genel değerlendirme">
    <div className="card-head"><div><h2>Kayıtlı genel değerlendirme</h2><p>{summary.period_start} – {summary.period_end}</p></div></div>
    <div className="card-pad">
      <div className="grid stats-grid">
        <StatCard icon={<GraduationCap size={19} />} label="Kayıtlı not ortalaması" value={academic.average_grade == null ? "—" : `${academic.average_grade}/100`} meta={`${academic.at_risk_students} öğrenci 60/100 izleme eşiğinin altında`} />
        <StatCard icon={<Users size={19} />} label="Kayıtlı devam oranı" value={percent(attendance.overall_rate)} meta={attendance.trend} color="blue" />
        <StatCard icon={<DollarSign size={19} />} label="Borç tahsilat oranı" value={percent(financial.collection_rate)} meta="İptal edilmemiş borç kayıtları" color="blue" />
        <StatCard icon={<MessageSquare size={19} />} label="Veli memnuniyeti" value={parents.score ?? "Ölçülmedi"} meta={parents.sentiment ?? "Memnuniyet ölçümü bulunmuyor"} color="orange" />
      </div>
      {summary.requires_review && <p role="status">Bazı kayıtlar incelenmeli; eksik göstergeler gösterilmiyor.</p>}
      <p className="muted">Not ve yoklama göstergeleri seçili dönemi, tahsilat oranı iptal edilmemiş tüm borç kayıtlarını kapsar.</p>
      {summary.priority_actions.map((message, index) => <p key={index}>{message}</p>)}
    </div>
  </section>;
}

export interface RecordedOperationsSummary {
  counts: { class_count: number; active_students: number; assigned_active_students: number; unassigned_active_students: number; known_capacity: number; classes_without_capacity: number; staff_count: number };
  optimization_scores: { classroom_utilization: number | null };
  over_capacity_classes: Array<{ class_id: string; class_name: string; capacity: number; active_student_count: number }>;
  resource_allocation: { recommended_actions: string[] };
}

export function RecordedOperationsPanel({ summary }: { summary: RecordedOperationsSummary }) {
  return <section className="card" aria-label="Kayıtlı operasyon özeti">
    <div className="card-head"><div><h2>Kayıtlı operasyon özeti</h2><p>Etkin sınıflar, öğrenciler ve tanımlı kapasite</p></div></div>
    <div className="card-pad">
      <div className="grid stats-grid">
        <StatCard icon={<Users size={19} />} label="Etkin sınıf" value={summary.counts.class_count} />
        <StatCard icon={<GraduationCap size={19} />} label="Etkin öğrenci" value={summary.counts.active_students} color="blue" />
        <StatCard icon={<Users size={19} />} label="Kayıtlı personel" value={summary.counts.staff_count} color="blue" />
        <StatCard icon={<Users size={19} />} label="Kayıtlı sınıf doluluğu" value={percent(summary.optimization_scores.classroom_utilization)} meta={`${summary.counts.known_capacity} tanımlı kontenjan`} color="orange" />
      </div>
      <p>{summary.counts.assigned_active_students} öğrenci etkin sınıflara bağlı; {summary.counts.unassigned_active_students} öğrenci etkin bir sınıfa bağlı değil.</p>
      {summary.resource_allocation.recommended_actions.map((message, index) => <p key={index}>{message}</p>)}
      {summary.over_capacity_classes.length > 0 && <div style={{ overflowX: "auto" }}><table className="data-table" aria-label="Kapasiteyi aşan sınıflar">
        <thead><tr><th>Sınıf</th><th>Etkin öğrenci</th><th>Kapasite</th></tr></thead>
        <tbody>{summary.over_capacity_classes.map((row) => <tr key={row.class_id}><td>{row.class_name}</td><td>{row.active_student_count}</td><td>{row.capacity}</td></tr>)}</tbody>
      </table></div>}
    </div>
  </section>;
}
