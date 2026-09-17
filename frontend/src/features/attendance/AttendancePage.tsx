import { CalendarDays, Check, Save, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useToast } from "../../components/Toast";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { dateInputValue } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

const statuses = [{ value: "PRESENT", label: "Geldi" }, { value: "ABSENT", label: "Gelmedi" }, { value: "EXCUSED", label: "İzinli" }, { value: "LATE", label: "Geç geldi" }, { value: "HALF_DAY", label: "Yarım gün" }];
const today = dateInputValue();
const items = (data: DataRecord[] | Paginated<DataRecord>) => Array.isArray(data) ? data : data?.items || [];

export function AttendancePage() {
  const [classes, setClasses] = useState<DataRecord[]>([]); 
  const [students, setStudents] = useState<DataRecord[]>([]); 
  const [classId, setClassId] = useState(""); 
  const [date, setDate] = useState(today); 
  const [records, setRecords] = useState<Record<string, { status: string; notes: string }>>({}); 
  const [loading, setLoading] = useState(true); 
  const [saving, setSaving] = useState(false); 
  const [error, setError] = useState(""); 
  const [aiAnalysis, setAiAnalysis] = useState<any>(null); 
  const { showToast } = useToast(); 
  const canWrite = useAuthStore((state) => state.can("attendance.write"));

  useEffect(() => { 
    api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/classes", { params: { limit: 100, page_size: 100 } }).then((r) => { 
      const list = items(r.data.data); 
      setClasses(list); 
      if (list[0]) setClassId(list[0].id); 
    }).catch((e) => setError(apiMessage(e))).finally(() => setLoading(false)); 
  }, []);

  useEffect(() => { 
    if (!classId) return; 
    setLoading(true); 
    api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>("/students", { params: { class_id: classId, limit: 100, page_size: 100 } }).then((r) => { 
      const list = items(r.data.data); 
      setStudents(list); 
      setRecords(Object.fromEntries(list.map((student) => [student.id, { status: "PRESENT", notes: "" }]))); 
    }).catch((e) => setError(apiMessage(e))).finally(() => setLoading(false)); 
  }, [classId]);

  useEffect(() => { 
    api.get("/ai/attendance-analysis").then((r) => setAiAnalysis(r.data.data)).catch(() => {}); 
  }, []);

  const counts = useMemo(() => statuses.map((status) => ({ ...status, count: Object.values(records).filter((value) => value.status === status.value).length })), [records]);

  async function save() { 
    if (!canWrite) return; 
    setSaving(true); 
    try { 
      await api.post("/attendance/bulk", { class_id: classId, attendance_date: date, records: students.map((student) => ({ student_id: student.id, status: records[student.id]?.status || "PRESENT", notes: records[student.id]?.notes || "" })) }); 
      showToast("Yoklama kaydedildi", `${students.length} öğrencinin durumu işlendi.`); 
    } catch (e) { 
      showToast("Yoklama kaydedilemedi", apiMessage(e), "error"); 
    } finally { 
      setSaving(false); 
    } 
  }

  return (
    <>
      <PageHeader eyebrow="Günlük akış" title="Yoklama" description="Sınıfı ve tarihi seçin, öğrenci durumlarını tek ekrandan kaydedin.">
        {canWrite && (
          <button className="btn btn-primary" onClick={save} disabled={!students.length || saving}>
            <Save size={16} />
            {saving ? "Kaydediliyor…" : "Yoklamayı kaydet"}
          </button>
        )}
      </PageHeader>
      {aiAnalysis && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Devamsızlık Analizi</h2>
              <p>Geçen 30 günlük devamsızlık verileri ve tahminler</p>
            </div>
            <Users size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 16 }}>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Mevcut Oran</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.current_rate}%</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: aiAnalysis.trend === "improving" ? "#dcfce7" : aiAnalysis.trend === "declining" ? "#fee2e2" : "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Tahmini Oran</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.predicted_rate}%</div>
              </div>
            </div>
            {aiAnalysis.risk_students && aiAnalysis.risk_students.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Riskli Öğrenciler ({aiAnalysis.risk_students.length})</h3>
                {aiAnalysis.risk_students.slice(0, 3).map((student: any, index: number) => (
                  <div key={index} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 12, borderRadius: 8, background: student.risk_level === "critical" ? "#fee2e2" : "#fef3c7", marginBottom: 8 }}>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>Öğrenci #{student.student_id.slice(0, 8)}</span>
                    <span style={{ fontSize: 12, color: "#6e7b7d" }}>{student.attendance_rate}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      <div className="card">
        <div className="toolbar">
          <select className="filter-select" value={classId} onChange={(e) => setClassId(e.target.value)} aria-label="Sınıf seç">
            <option value="">Sınıf seçin</option>
            {classes.map((item) => (
              <option value={item.id} key={item.id}>
                {String(item.name)}
              </option>
            ))}
          </select>
          <div className="search" style={{ maxWidth: 180 }}>
            <CalendarDays size={16} />
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} aria-label="Yoklama tarihi" />
          </div>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6, flexWrap: "wrap" }}>
            {counts.map((status) => (
              <span className="badge badge-neutral" key={status.value}>
                {status.label}: {status.count}
              </span>
            ))}
          </div>
        </div>
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} />
        ) : !classId ? (
          <EmptyState title="Önce bir sınıf seçin" />
        ) : students.length === 0 ? (
          <EmptyState title="Bu sınıfta öğrenci yok" description="Sınıfa öğrenci atadıktan sonra yoklama alabilirsiniz." />
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Durum</th>
                  <th>Not</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student) => (
                  <tr key={student.id}>
                    <td>
                      <div className="cell-main">
                        {String(student.first_name)} {String(student.last_name)}
                      </div>
                      <div className="cell-sub">
                        {String(student.student_number || "Öğrenci kaydı")}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {statuses.map((status) => (
                          <button
                            key={status.value}
                            type="button"
                            disabled={!canWrite}
                            className={`btn ${records[student.id]?.status === status.value ? "btn-primary" : "btn-secondary"}`}
                            style={{ minHeight: 34, padding: "0 10px" }}
                            onClick={() =>
                              setRecords((current) => ({ ...current, [student.id]: { ...current[student.id], status: status.value } }))
                            }
                          >
                            {records[student.id]?.status === status.value && <Check size={13} />}
                            {status.label}
                          </button>
                        ))}
                      </div>
                    </td>
                    <td>
                      <input
                        className="filter-select"
                        style={{ width: "100%" }}
                        placeholder="İsteğe bağlı not"
                        aria-label={`${String(student.first_name)} ${String(student.last_name)} için yoklama notu`}
                        disabled={!canWrite}
                        value={records[student.id]?.notes || ""}
                        onChange={(event) =>
                          setRecords((current) => ({ ...current, [student.id]: { ...current[student.id], notes: event.target.value } }))
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
