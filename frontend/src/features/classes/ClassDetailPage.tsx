import { reportClientError } from "../../lib/diagnostics";
import { ArrowLeft, Pencil, BrainCircuit } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord } from "../../types/api";

export function ClassDetailPage() {
  const { id } = useParams();

  const [record, setRecord] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [aiLoading, setAiLoading] = useState(false);

  const can = useAuthStore((state) => state.can);

  // ---------------------------------------------------------
  // SINIF BİLGİLERİNİ GETİR
  // ---------------------------------------------------------
  useEffect(() => {
    if (!id) {
      setError("Sınıf ID bulunamadı.");
      setLoading(false);
      return;
    }

    

    api
      .get<ApiResponse<DataRecord>>(`/classes/${id}`)
      .then((r) => {
        
        
        
        
        

        setRecord(r.data.data);
      })
      .catch((e) => {
        reportClientError("DEBUG: API Error:", e);
        setError(apiMessage(e));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [id]);

  // ---------------------------------------------------------
  // AI SINIF ANALİZİ
  // ---------------------------------------------------------
  useEffect(() => {
    if (!record || !id) {
      return;
    }

    setAiLoading(true);

    api
      .get(`/ai/class-analysis/${id}`)
      .then((r) => {
        
        

        setAiAnalysis(r.data?.data || null);
      })
      .catch((e) => {
        reportClientError("AI analysis error:", e);
        setAiAnalysis(null);
      })
      .finally(() => {
        setAiLoading(false);
      });
  }, [record, id]);

  // ---------------------------------------------------------
  // LOADING
  // ---------------------------------------------------------
  if (loading) {
    return (
      <div className="card">
        <LoadingState />
      </div>
    );
  }

  // ---------------------------------------------------------
  // ERROR
  // ---------------------------------------------------------
  if (error || !record) {
    return (
      <div className="card">
        <ErrorState message={error || "Sınıf bulunamadı."} />
      </div>
    );
  }

  // ---------------------------------------------------------
  // SINIF BİLGİLERİ
  // ---------------------------------------------------------
  const displayName = String(record.name || "Sınıf");

  /*
   * ÖNEMLİ:
   *
   * /classes/{id} endpoint'i teacher_name göndermiyorsa,
   * AI endpoint'inden gelen teacher_name kullanılacak.
   *
   * Öncelik:
   * 1. record.teacher_name
   * 2. aiAnalysis.teacher_name
   * 3. —
   */
  const teacherName =
    record.teacher_name ||
    aiAnalysis?.teacher_name ||
    "—";

  const studentCount = aiAnalysis?.student_count ?? 0;

  const attendanceRate =
    typeof aiAnalysis?.attendance_rate === "number"
      ? aiAnalysis.attendance_rate
      : null;

  const avgGrade =
    typeof aiAnalysis?.avg_grade === "number"
      ? aiAnalysis.avg_grade
      : null;

  const performanceTrend =
    aiAnalysis?.performance_trend || "—";

  // ---------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------
  return (
    <>
      <PageHeader
        eyebrow="Sınıf profili"
        title={displayName}
        description="Kayıtla ilişkili temel bilgiler ve işlem geçmişi."
      >
        <Link className="btn btn-secondary" to="/classes">
          <ArrowLeft size={16} />
          Listeye dön
        </Link>

        {can("class.write") && (
          <Link
            className="btn btn-primary"
            to={`/classes/${id}/edit`}
          >
            <Pencil size={16} />
            Düzenle
          </Link>
        )}
      </PageHeader>

      <div className="detail-grid">

        {/* =====================================================
            GENEL BİLGİLER
        ====================================================== */}
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Genel bilgiler</h2>
              <p>Backend kaydından güncel bilgiler</p>
            </div>
          </div>

          <div className="tabs">
            <button className="tab active">
              Profil
            </button>
          </div>

          <div className="card-pad detail-list">

            {/* SINIF */}
            <div className="detail-item">
              <small>Sınıf</small>
              <strong>
                {String(record.name || "—")}
              </strong>
            </div>

            {/* KOD */}
            <div className="detail-item">
              <small>Kod</small>
              <strong>
                {String(record.code || "—")}
              </strong>
            </div>

            {/* DÖNEM */}
            <div className="detail-item">
              <small>Dönem</small>
              <strong>
                {String(record.academic_year || "—")}
              </strong>
            </div>

            {/* KAPASİTE */}
            <div className="detail-item">
              <small>Kapasite</small>
              <strong>
                {String(record.capacity ?? "—")}
              </strong>
            </div>

            {/* =================================================
                ÖĞRETMEN
                record.teacher_name yoksa
                aiAnalysis.teacher_name kullanılır.
            ================================================== */}
            <div className="detail-item">
              <small>Öğretmen</small>

              <strong>
                {String(teacherName)}
              </strong>
            </div>

            {/* DURUM */}
            <div className="detail-item">
              <small>Durum</small>

              <strong>
                {record.is_active
                  ? "Aktif"
                  : "Pasif"}
              </strong>
            </div>

          </div>
        </div>

        {/* =====================================================
            AI ANALİZİ
        ====================================================== */}
        <div
          className="card"
          style={{
            gridColumn: "1 / -1",
          }}
        >
          <div className="card-head">
            <div>
              <h2>AI Analizi</h2>

              <p>
                Yapay zeka destekli sınıf analizi
              </p>
            </div>

            <BrainCircuit
              size={20}
              color="#7fa89d"
            />
          </div>

          <div className="card-pad">

            {/* =================================================
                AI LOADING
            ================================================== */}
            {aiLoading && (
              <LoadingState />
            )}

            {/* =================================================
                AI VERİLERİ
            ================================================== */}
            {!aiLoading && aiAnalysis && (
              <>
                {/* ---------------------------------------------
                    ANA İSTATİSTİKLER
                ---------------------------------------------- */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(3, 1fr)",
                    gap: 16,
                    marginBottom: 20,
                  }}
                >

                  {/* ÖĞRENCİ SAYISI */}
                  <div
                    style={{
                      padding: 16,
                      borderRadius: 12,
                      background: "#f8faf8",
                      textAlign: "center",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        color: "#6e7b7d",
                        marginBottom: 8,
                        fontWeight: 600,
                      }}
                    >
                      Öğrenci Sayısı
                    </div>

                    <div
                      style={{
                        fontSize: 28,
                        fontWeight: 800,
                        color: "#1b2b2e",
                      }}
                    >
                      {studentCount}
                    </div>
                  </div>

                  {/* DEVAM ORANI */}
                  <div
                    style={{
                      padding: 16,
                      borderRadius: 12,
                      background:
                        attendanceRate === null
                          ? "#f8faf8"
                          : attendanceRate >= 85
                          ? "#dcfce7"
                          : attendanceRate >= 70
                          ? "#fef9c3"
                          : "#fee2e2",
                      textAlign: "center",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        color: "#6e7b7d",
                        marginBottom: 8,
                        fontWeight: 600,
                      }}
                    >
                      Devamsızlık Oranı
                    </div>

                    <div
                      style={{
                        fontSize: 28,
                        fontWeight: 800,
                        color: "#1b2b2e",
                      }}
                    >
                      {attendanceRate !== null
                        ? `%${attendanceRate}`
                        : "—"}
                    </div>
                  </div>

                  {/* ORTALAMA NOT */}
                  <div
                    style={{
                      padding: 16,
                      borderRadius: 12,
                      background:
                        avgGrade === null
                          ? "#f8faf8"
                          : avgGrade >= 80
                          ? "#dcfce7"
                          : avgGrade >= 70
                          ? "#fef9c3"
                          : "#fee2e2",
                      textAlign: "center",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        color: "#6e7b7d",
                        marginBottom: 8,
                        fontWeight: 600,
                      }}
                    >
                      Ortalama Not
                    </div>

                    <div
                      style={{
                        fontSize: 28,
                        fontWeight: 800,
                        color: "#1b2b2e",
                      }}
                    >
                      {avgGrade !== null
                        ? avgGrade
                        : "—"}
                    </div>
                  </div>
                </div>

                {/* ---------------------------------------------
                    KAPASİTE + ÖĞRETMEN
                ---------------------------------------------- */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(2, 1fr)",
                    gap: 16,
                    marginBottom: 20,
                  }}
                >

                  {/* KAPASİTE */}
                  <div
                    style={{
                      padding: 16,
                      borderRadius: 12,
                      background: "#f8faf8",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        color: "#6e7b7d",
                        marginBottom: 4,
                        fontWeight: 600,
                      }}
                    >
                      Kapasite
                    </div>

                    <div
                      style={{
                        fontSize: 18,
                        fontWeight: 700,
                        color: "#1b2b2e",
                      }}
                    >
                      {aiAnalysis.capacity ??
                        record.capacity ??
                        "—"}
                    </div>
                  </div>

                  {/* ÖĞRETMEN */}
                  <div
                    style={{
                      padding: 16,
                      borderRadius: 12,
                      background: "#f8faf8",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        color: "#6e7b7d",
                        marginBottom: 4,
                        fontWeight: 600,
                      }}
                    >
                      Öğretmen
                    </div>

                    <div
                      style={{
                        fontSize: 18,
                        fontWeight: 700,
                        color: "#1b2b2e",
                      }}
                    >
                      {aiAnalysis.teacher_name ||
                        teacherName}
                    </div>
                  </div>
                </div>

                {/* ---------------------------------------------
                    PERFORMANS TRENDİ
                ---------------------------------------------- */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(2, 1fr)",
                    gap: 16,
                    marginBottom: 20,
                  }}
                >
                  <div
                    style={{
                      padding: 16,
                      borderRadius: 12,
                      background:
                        performanceTrend ===
                        "Artış"
                          ? "#dcfce7"
                          : performanceTrend ===
                            "Stabil"
                          ? "#fef9c3"
                          : "#fee2e2",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 12,
                        color: "#6e7b7d",
                        marginBottom: 4,
                        fontWeight: 600,
                      }}
                    >
                      Performans Trendi
                    </div>

                    <div
                      style={{
                        fontSize: 18,
                        fontWeight: 700,
                        color: "#1b2b2e",
                      }}
                    >
                      {performanceTrend}
                    </div>
                  </div>
                </div>

                {/* ---------------------------------------------
                    ÖNERİLER
                ---------------------------------------------- */}
                {Array.isArray(
                  aiAnalysis.recommendations
                ) &&
                  aiAnalysis.recommendations.length >
                    0 && (
                    <div
                      style={{
                        padding: 16,
                        borderRadius: 12,
                        background: "#f0f9ff",
                        borderLeft:
                          "4px solid #0ea5e9",
                      }}
                    >
                      <div
                        style={{
                          fontSize: 14,
                          fontWeight: 700,
                          color: "#0c4a6e",
                          marginBottom: 12,
                        }}
                      >
                        Öneriler
                      </div>

                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: 20,
                          color: "#334155",
                        }}
                      >
                        {aiAnalysis.recommendations.map(
                          (
                            rec: string,
                            idx: number
                          ) => (
                            <li
                              key={idx}
                              style={{
                                marginBottom: 6,
                              }}
                            >
                              {rec}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}
              </>
            )}

            {/* =================================================
                AI VERİSİ YOK
            ================================================== */}
            {!aiLoading && !aiAnalysis && (
              <div
                className="state"
                style={{
                  minHeight: 100,
                  padding: 15,
                }}
              >
                <p>
                  AI analizi yüklenemedi.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}