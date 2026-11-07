import { getAnalysis } from "../../lib/analysis";
import { reportClientError } from "../../lib/diagnostics";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, apiMessage } from "../../lib/api";
import { PageHeader } from "../../components/ui";
import { LoadingState } from "../../components/ui";
import { Search, Plus, Eye, Edit, Trash2, TrendingUp, AlertTriangle } from "lucide-react";

interface Student {
  id: string;
  student_number: string;
  first_name: string;
  last_name: string;
  class_id?: string;
  branch_id?: string;
  status: string;
  created_at: string;
}

export function StudentsPage() {
  const navigate = useNavigate();
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);

  const loadStudents = async () => {
    setLoading(true);
    setError("");
    try {
      const url = search 
        ? `/students?search=${encodeURIComponent(search)}&limit=50&offset=${(page - 1) * 50}`
        : `/students?limit=50&offset=${(page - 1) * 50}`;
      
      const response = await api.get<any>(url);
      
      const studentsData = Array.isArray(response.data.data?.items) ? response.data.data.items : (Array.isArray(response.data.data) ? response.data.data : []);
      const total = response.data.data?.total || studentsData.length;
      
      setStudents(studentsData);
      setTotal(total);
    } catch (err) {
      reportClientError("API Error:", err);
      setError(apiMessage(err));
      setStudents([]);
    } finally {
      setLoading(false);
    }
  };

  const loadAiAnalysis = async () => {
    try {
      const response = await getAnalysis<any>("/ai/students-overview");
      if (response.data.success) {
        setAiAnalysis(response.data.data);
      }
    } catch (err) {
      reportClientError("Failed to load AI analysis:", err);
    }
  };

  useEffect(() => {
    loadStudents();
    loadAiAnalysis();
  }, [page, search]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadStudents();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Bu öğrenciyi silmek istediğinize emin misiniz?")) return;
    
    try {
      await api.delete(`/students/${id}`);
      setStudents(students.filter(s => s.id !== id));
    } catch (err) {
      setError(apiMessage(err));
    }
  };

  if (loading && students.length === 0) return <div className="card"><LoadingState label="Yükleniyor" /></div>;

  return (
    <>
      <PageHeader
        eyebrow="Eğitim"
        title="Öğrenciler"
        description="Öğrenci yönetimi ve bilgileri"
      >
        <button className="btn btn-primary" onClick={() => navigate("/students/new")}><Plus size={16} /> Yeni Öğrenci</button>
      </PageHeader>

      {aiAnalysis && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Öğrenci Analizi</h2>
              <p>Genel performans ve trendler</p>
            </div>
            <TrendingUp size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Öğrenci</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.total_students}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Aktif Öğrenci</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.active_students}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: aiAnalysis.average_grade >= 75 ? "#dcfce7" : aiAnalysis.average_grade >= 60 ? "#fef3c7" : "#fee2e2" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Ortalama Not</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.average_grade}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: aiAnalysis.attendance_rate >= 85 ? "#dcfce7" : aiAnalysis.attendance_rate >= 75 ? "#fef3c7" : "#fee2e2" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Devamsızlık Oranı</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.attendance_rate}%</div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 11, background: aiAnalysis.at_risk_count > 0 ? "#fee2e2" : "#dcfce7" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Risk Altındaki Öğrenciler</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.at_risk_count}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Trend</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: aiAnalysis.trend === "improving" ? "#166534" : aiAnalysis.trend === "declining" ? "#991b1b" : "#1b2b2e" }}>
                  {aiAnalysis.trend === "improving" ? "Artış" : aiAnalysis.trend === "declining" ? "Düşüş" : "Stabil"}
                </div>
              </div>
            </div>
            {aiAnalysis.recommendations && aiAnalysis.recommendations.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Önerileri</h3>
                {aiAnalysis.recommendations.slice(0, 3).map((rec: string, index: number) => (
                  <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start" }}>
                    <AlertTriangle size={16} color={aiAnalysis.at_risk_count > 0 ? "#dc2626" : "#176b5b"} style={{ flexShrink: 0, marginTop: 2 }} />
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
          <h2>Öğrenci Listesi</h2>
          <form onSubmit={handleSearch} style={{ display: "flex", gap: 8 }}>
            <input
              type="text"
              placeholder="Öğrenci ara..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ padding: "6px 12px", border: "1px solid #d1d5db", borderRadius: 4 }}
            />
            <button type="submit" className="btn btn-secondary"><Search size={16} /></button>
          </form>
        </div>

        {error && <div style={{ padding: 12, background: "#fee2e2", color: "#dc2626", borderRadius: 4, marginBottom: 12 }}>{error}</div>}

        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
              <th style={{ padding: 12, textAlign: "left" }}>Öğrenci No</th>
              <th style={{ padding: 12, textAlign: "left" }}>Ad Soyad</th>
              <th style={{ padding: 12, textAlign: "left" }}>Durum</th>
              <th style={{ padding: 12, textAlign: "left" }}>İşlemler</th>
            </tr>
          </thead>
          <tbody>
            {students.map((student) => (
              <tr key={student.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={{ padding: 12 }}>{student.student_number}</td>
                <td style={{ padding: 12 }}>{student.first_name} {student.last_name}</td>
                <td style={{ padding: 12 }}>
                  <span style={{
                    padding: "2px 8px",
                    borderRadius: 4,
                    fontSize: 12,
                    background: student.status === "ACTIVE" ? "#dcfce7" : "#fee2e2",
                    color: student.status === "ACTIVE" ? "#166534" : "#dc2626"
                  }}>
                    {student.status === "ACTIVE" ? "Aktif" : "Pasif"}
                  </span>
                </td>
                <td style={{ padding: 12 }}>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button 
                      className="btn btn-secondary" 
                      onClick={() => navigate(`/students/${student.id}`)}
                      title="Görüntüle"
                    >
                      <Eye size={16} />
                    </button>
                    <button 
                      className="btn btn-secondary" 
                      onClick={() => navigate(`/students/${student.id}/edit`)}
                      title="Düzenle"
                    >
                      <Edit size={16} />
                    </button>
                    <button 
                      className="btn btn-danger" 
                      onClick={() => handleDelete(student.id)}
                      title="Sil"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {students.length === 0 && !loading && (
          <div style={{ padding: 48, textAlign: "center", color: "#6b7280" }}>
            Öğrenci bulunamadı
          </div>
        )}

        <div style={{ padding: 12, display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #e5e7eb" }}>
          <span>Toplam: {total} öğrenci</span>
          <div style={{ display: "flex", gap: 8 }}>
            <button 
              className="btn btn-secondary" 
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Önceki
            </button>
            <span>Sayfa {page}</span>
            <button 
              className="btn btn-secondary" 
              onClick={() => setPage(p => p + 1)}
              disabled={students.length < 50}
            >
              Sonraki
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
