import { getAnalysis } from "../../lib/analysis";
import { FileText, Award, AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function ExamsPage() {
  const [exams, setExams] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [aiInsights, setAiInsights] = useState<any>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await api.get<ApiResponse<DataRecord[]>>("/exams");
        setExams(res.data.data || []);
      } catch (err) {
        setError(apiMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    getAnalysis("/ai/academic-performance").then((r) => setAiInsights(r.data.data)).catch(() => {});
  }, []);

  if (loading) return <div className="card"><LoadingState label="Yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Akademik"
        title="Sınavlar & Karne"
        description="Sınavlar, sonuçlar ve karneler yönetimi"
      />
      {aiInsights && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Akademik Performans Analizi</h2>
              <p>Not ortalaması, geçme oranı ve riskli öğrenciler</p>
            </div>
            <Award size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 180px), 1fr))", gap: 16, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Not Ortalaması</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{typeof aiInsights.average_grade === "number" ? aiInsights.average_grade.toFixed(1) : "—"}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: aiInsights.passing_rate >= 80 ? "#dcfce7" : "#fef3c7" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Geçme Oranı</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{typeof aiInsights.passing_rate === "number" ? `%${aiInsights.passing_rate}` : "—"}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: aiInsights.trend === "improving" ? "#dcfce7" : aiInsights.trend === "declining" ? "#fee2e2" : "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Trend</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiInsights.trend === "improving" ? "Artış" : aiInsights.trend === "declining" ? "Düşüş" : aiInsights.trend === "stable" ? "Stabil" : "Veri yetersiz"}</div>
              </div>
            </div>
            {aiInsights.at_risk_students && aiInsights.at_risk_students.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
                  <AlertTriangle size={16} color="#dc2626" />
                  Riskli Öğrenciler ({aiInsights.at_risk_count})
                </h3>
                {aiInsights.at_risk_students.slice(0, 3).map((student: any, index: number) => (
                  <div key={index} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12, borderRadius: 8, background: "#fee2e2", marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>{student.name}</span>
                    <span style={{ fontSize: 12, color: "#6e7b7d" }}>Ort: {student.average.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      <div className="card">
        <div className="card-head">
          <h2>Sınavlar</h2>
          <span className="badge badge-green">{String(exams.length)}</span>
        </div>
        <div className="card-pad">
          {exams.length === 0 ? (
            <p style={{ color: "#5e6c6d" }}>Henüz sınav oluşturulmadı</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Sınav Adı</th>
                  <th>Ders</th>
                  <th>Tarih</th>
                  <th>Sınıf</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((exam) => (
                  <tr key={exam.id}>
                    <td><FileText size={14} /> {String(exam.title ?? "—")}</td>
                    <td>{String(exam.subject_name ?? "—")}</td>
                    <td>{String(exam.exam_date)}</td>
                    <td>{String(exam.class_name)}</td>
                    <td><Badge value={String(exam.status)} /></td>
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
