import { FileText, Award, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { PageHeader, Badge, LoadingState, ErrorState } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function ExamsPage() {
  const [exams, setExams] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  if (loading) return <div className="card"><LoadingState label="Yükleniyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Akademik"
        title="Sınavlar & Karne"
        description="Sınavlar, sonuçlar ve karneler yönetimi"
      />
      <div className="card" style={{ marginTop: 18 }}>
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
                    <td><FileText size={14} /> {String(exam.name)}</td>
                    <td>{String(exam.subject_name)}</td>
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
