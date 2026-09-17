import { ArrowLeft, Users, AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState, PageHeader, Badge } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";

export function ClassOccupancyPage() {
  const { id } = useParams();
  const [classInfo, setClassInfo] = useState<DataRecord | null>(null);
  const [students, setStudents] = useState<DataRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [classRes, studentsRes] = await Promise.allSettled([
        api.get<ApiResponse<DataRecord>>(`/classes/${id}`),
        api.get<ApiResponse<DataRecord[]>>(`/classes/${id}/students`)
      ]);

      if (classRes.status === "fulfilled") {
        setClassInfo(classRes.value.data.data);
      } else {
        throw new Error(apiMessage(classRes.reason));
      }

      if (studentsRes.status === "fulfilled") {
        setStudents(studentsRes.value.data.data || []);
      } else {
        throw new Error(apiMessage(studentsRes.reason));
      }
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [id]);

  if (loading) return <div className="card"><LoadingState label="Sınıf doluluk bilgileri yükleniyor" /></div>;
  if (error || !classInfo) return <div className="card"><ErrorState message={error || "Sınıf bulunamadı."} /></div>;

  const capacity = Number(classInfo.capacity || 0);
  const occupancy = students.length;
  const occupancyRate = capacity > 0 ? Math.round((occupancy / capacity) * 100) : 0;
  const availableSlots = capacity - occupancy;
  const isNearFull = occupancyRate >= 90;
  const isFull = occupancy >= capacity;

  return (
    <>
      <PageHeader
        eyebrow="Sınıf doluluğu"
        title={String(classInfo.name)}
        description={`${String(classInfo.code)} kodlu sınıfın kapasite ve doluluk durumu.`}
      >
        <Link className="btn btn-secondary" to={`/classes/${id}`}>
          <ArrowLeft size={16} />Sınıfa dön
        </Link>
      </PageHeader>

      <div className="grid stats-grid">
        <div className="card stat-card" style={{ "--stat-bg": isFull ? "#fff0ef" : isNearFull ? "#fff2df" : "#e6f3ef", "--stat-ink": isFull ? "#b14545" : isNearFull ? "#ad7020" : "#176b5b", "--stat-color": isFull ? "#fff0ef" : isNearFull ? "#fff2df" : "#e6f3ef" } as React.CSSProperties}>
          <div className="stat-top">
            <div className="stat-icon"><Users size={19} /></div>
          </div>
          <div className="stat-label">Doluluk oranı</div>
          <div className="stat-value">{occupancyRate}%</div>
          <div className="stat-meta">{occupancy}/{capacity} öğrenci</div>
        </div>
        <div className="card stat-card" style={{ "--stat-bg": "#e8f1f5", "--stat-ink": "#397c92", "--stat-color": "#e8f1f5" } as React.CSSProperties}>
          <div className="stat-top">
            <div className="stat-icon"><Users size={19} /></div>
          </div>
          <div className="stat-label">Mevcut öğrenci</div>
          <div className="stat-value">{occupancy}</div>
          <div className="stat-meta">Kayıtlı öğrenci sayısı</div>
        </div>
        <div className="card stat-card" style={{ "--stat-bg": availableSlots > 0 ? "#e6f3ef" : "#fff0ef", "--stat-ink": availableSlots > 0 ? "#176b5b" : "#b14545", "--stat-color": availableSlots > 0 ? "#e6f3ef" : "#fff0ef" } as React.CSSProperties}>
          <div className="stat-top">
            <div className="stat-icon">{availableSlots > 0 ? <Users size={19} /> : <AlertTriangle size={19} />}</div>
          </div>
          <div className="stat-label">Boş kontenjan</div>
          <div className="stat-value">{availableSlots}</div>
          <div className="stat-meta">{isFull ? "Sınıf dolu" : "Yer var"}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <div>
            <h2>Kapasite göstergesi</h2>
            <p>Sınıfın doluluk durumu</p>
          </div>
        </div>
        <div className="card-pad">
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ font: "600 13px Manrope" }}>Doluluk</span>
              <span style={{ font: "600 13px Manrope" }}>{occupancyRate}%</span>
            </div>
            <div
              style={{
                height: 8,
                background: "#e7ece8",
                borderRadius: 4,
                overflow: "hidden"
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${occupancyRate}%`,
                  background: isFull ? "#b14545" : isNearFull ? "#ad7020" : "#2d8f78",
                  transition: "width 0.3s ease"
                }}
              />
            </div>
          </div>

          {isFull && (
            <div style={{
              padding: 12,
              background: "#fff0ef",
              borderRadius: 8,
              display: "flex",
              gap: 8,
              alignItems: "center",
              fontSize: 13,
              color: "#b14545"
            }}>
              <AlertTriangle size={16} />
              <span>Sınıf kapasitesi dolmuş. Yeni öğrenci eklemek için kapasite artırın veya başka sınıf kullanın.</span>
            </div>
          )}

          {isNearFull && !isFull && (
            <div style={{
              padding: 12,
              background: "#fff2df",
              borderRadius: 8,
              display: "flex",
              gap: 8,
              alignItems: "center",
              fontSize: 13,
              color: "#ad7020"
            }}>
              <AlertTriangle size={16} />
              <span>Sınıf kapasitesine yaklaşıyor. Yer kalmıyor.</span>
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-head">
          <div>
            <h2>Kayıtlı öğrenciler</h2>
            <p>Sınıftaki mevcut öğrenci listesi</p>
          </div>
        </div>
        {students.length === 0 ? (
          <div className="card-pad" style={{ textAlign: "center", padding: "40px 20px" }}>
            <Users size={48} style={{ color: "#d1d9d6", margin: "0 auto 16px" }} />
            <h3 style={{ font: "600 16px Manrope", marginBottom: 8 }}>Henüz öğrenci yok</h3>
            <p style={{ color: "#7a8888", fontSize: 13 }}>Bu sınıfa öğrenci atanmamış.</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Öğrenci</th>
                  <th>Öğrenci no</th>
                  <th>Kayıt tarihi</th>
                  <th>Durum</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student) => (
                  <tr key={student.id}>
                    <td>
                      <Link
                        to={`/students/${student.id}`}
                        style={{ font: "600 14px Manrope", color: "#2d8f78" }}
                      >
                        {[String(student.first_name), String(student.last_name)].filter(Boolean).join(" ")}
                      </Link>
                    </td>
                    <td>{String(student.student_number || "-")}</td>
                    <td>{student.enrollment_date ? new Date(String(student.enrollment_date)).toLocaleDateString("tr-TR") : "-"}</td>
                    <td><Badge value={student.status} /></td>
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
