import { ArrowLeft, CalendarCheck2, CreditCard, FileText, Pencil, User, Phone, Mail, IdCard, Brain, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState, PageHeader, Badge } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { textValue, toArray } from "../../lib/data";
import { shortDate, titleCase } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord, Paginated } from "../../types/api";

export function StudentDetailPage() {
  const { id } = useParams();
  const [student, setStudent] = useState<DataRecord | null>(null);
  const [parents, setParents] = useState<DataRecord[]>([]);
  const [classInfo, setClassInfo] = useState<DataRecord | null>(null);
  const [aiPrediction, setAiPrediction] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const can = useAuthStore((state) => state.can);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const studentRes = await api.get<ApiResponse<DataRecord>>(`/students/${id}`);
        const studentRecord = studentRes.data.data;
        if (!studentRecord) throw new Error("Öğrenci bulunamadı.");
        setStudent(studentRecord);
        const classId = textValue(studentRecord.class_id, "");
        const [parentsRes, classRes, aiRes] = await Promise.allSettled([
          api.get<ApiResponse<DataRecord[] | Paginated<DataRecord>>>(`/students/${id}/parents`),
          classId ? api.get<ApiResponse<DataRecord>>(`/classes/${classId}`) : Promise.resolve(null),
          api.get(`/ai/student-performance/${id}`).catch(() => null),
        ]);
        if (parentsRes.status === "fulfilled") {
          setParents(toArray(parentsRes.value.data.data));
        }
        if (classRes.status === "fulfilled" && classRes.value) {
          setClassInfo(classRes.value.data.data);
        }
        if (aiRes.status === "fulfilled" && aiRes.value) {
          console.log("AI Response:", aiRes.value.data);
          setAiPrediction(aiRes.value.data.data);
        }
      } catch (err) {
        setError(apiMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) return <div className="card"><LoadingState label="Öğrenci bilgileri yükleniyor" /></div>;
  if (error || !student) return <div className="card"><ErrorState message={error || "Öğrenci bulunamadı."} /></div>;

  const displayName = [student.first_name, student.last_name].map((value) => textValue(value, "")).filter(Boolean).join(" ");

  return (
    <>
      <PageHeader
        eyebrow="Öğrenci profili"
        title={displayName}
        description="Öğrenci bilgileri, veli kayıtları ve sınıf atamaları."
      >
        <Link className="btn btn-secondary" to="/students">
          <ArrowLeft size={16} />Listeye dön
        </Link>
        {can("student.write") && (
          <Link className="btn btn-primary" to={`/students/${id}/edit`}>
            <Pencil size={16} />Düzenle
          </Link>
        )}
      </PageHeader>

      <div className="detail-grid">
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Kişisel bilgiler</h2>
              <p>Öğrencinin temel kimlik ve iletişim bilgileri</p>
            </div>
          </div>
          <div className="card-pad detail-list">
            <div className="detail-item">
              <small>Ad</small>
              <strong>{titleCase(textValue(student.first_name))}</strong>
            </div>
            <div className="detail-item">
              <small>Soyad</small>
              <strong>{titleCase(textValue(student.last_name))}</strong>
            </div>
            <div className="detail-item">
              <small>Doğum tarihi</small>
              <strong>{shortDate(student.date_of_birth || student.birth_date)}</strong>
            </div>
            <div className="detail-item">
              <small>Cinsiyet</small>
              <strong>{student.gender === "MALE" ? "Erkek" : student.gender === "FEMALE" ? "Kadın" : "Belirtilmemiş"}</strong>
            </div>
            <div className="detail-item">
              <small>Kayıt tarihi</small>
              <strong>{shortDate(student.enrollment_date)}</strong>
            </div>
            <div className="detail-item">
              <small>Durum</small>
              <strong><Badge value={student.status} /></strong>
            </div>
            {student.address && (
              <div className="detail-item">
                <small>Adres</small>
                <strong>{textValue(student.address)}</strong>
              </div>
            )}
            {student.notes && (
              <div className="detail-item">
                <small>Notlar</small>
                <strong>{textValue(student.notes)}</strong>
              </div>
            )}
          </div>
        </div>

        <aside className="card card-pad">
          <h2 style={{ margin: "0 0 15px", font: "700 15px Manrope" }}>Hızlı bağlantılar</h2>
          <div className="quick-list" style={{ padding: 0 }}>
            <Link className="quick-item" to={`/students/${id}/files`}>
              <div className="quick-icon"><FileText size={16} /></div>
              <div className="quick-copy">
                <strong>Öğrenci dosyaları</strong>
                <span>Belgeler ve sözleşmeler</span>
              </div>
            </Link>
            <Link className="quick-item" to={`/students/${id}/parents`}>
              <div className="quick-icon"><User size={16} /></div>
              <div className="quick-copy">
                <strong>Veli bilgileri</strong>
                <span>İletişim ve yetki</span>
              </div>
            </Link>
            <Link className="quick-item" to={`/finance/payments?student_id=${id}`}>
              <div className="quick-icon"><CreditCard size={16} /></div>
              <div className="quick-copy">
                <strong>Ödeme geçmişi</strong>
                <span>Tahsilat ve makbuzlar</span>
              </div>
            </Link>
            <Link className="quick-item" to={`/attendance?student_id=${id}`}>
              <div className="quick-icon"><CalendarCheck2 size={16} /></div>
              <div className="quick-copy">
                <strong>Devamsızlık</strong>
                <span>Yoklama kayıtları</span>
              </div>
            </Link>
            <Link className="quick-item" to={`/rfid-cards?holder_id=${id}`}>
              <div className="quick-icon"><IdCard size={16} /></div>
              <div className="quick-copy">
                <strong>RFID Kartı</strong>
                <span>Kart atama ve yönetim</span>
              </div>
            </Link>
          </div>
        </aside>
      </div>

      {aiPrediction && (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Performans Analizi</h2>
              <p>Yapay zeka destekli kapsamlı akademik performans analizi</p>
            </div>
            <Brain size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 20 }}>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Tahmini Not</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{aiPrediction.predicted_grade}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Mevcut Ortalama</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{aiPrediction.current_average || "-"}</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Güven</div>
                <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{aiPrediction.confidence}%</div>
              </div>
              <div style={{ padding: 16, borderRadius: 11, background: aiPrediction.trend === "improving" ? "#dcfce7" : aiPrediction.trend === "declining" ? "#fee2e2" : "#f8faf8" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Trend</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: "#1b2b2e" }}>{aiPrediction.trend === "improving" ? "Yükselişte" : aiPrediction.trend === "declining" ? "Düşüşte" : "Stabil"}</div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 20 }}>
              <div style={{ padding: 12, borderRadius: 8, background: aiPrediction.risk_level === "critical" ? "#fee2e2" : aiPrediction.risk_level === "high" ? "#fef3c7" : "#dcfce7", border: "1px solid " + (aiPrediction.risk_level === "critical" ? "#fecaca" : aiPrediction.risk_level === "high" ? "#fde68a" : "#bbf7d0") }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Risk Seviyesi</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#1b2b2e" }}>{aiPrediction.risk_level === "critical" ? "Kritik" : aiPrediction.risk_level === "high" ? "Yüksek" : aiPrediction.risk_level === "medium" ? "Orta" : "Düşük"}</div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Öğrenme Stili</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#1b2b2e" }}>{aiPrediction.learning_style === "highly_engaged" ? "Yüksek Katılımlı" : aiPrediction.learning_style === "consistent" ? "Tutarlı" : aiPrediction.learning_style === "self_motivated" ? "Öz Motivasyonlu" : "Destek Gerektiriyor"}</div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#eff6ff", border: "1px solid #bfdbfe" }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Sınıf Percentili</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#1b2b2e" }}>{aiPrediction.peer_percentile}%</div>
              </div>
            </div>

            {aiPrediction.factors && (
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Performans Faktörleri</h3>
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                  <div style={{ flex: 1, minWidth: 200, padding: 12, borderRadius: 8, background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
                    <div style={{ fontSize: 12, color: "#166534", marginBottom: 4 }}>Notlar</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#166534" }}>{aiPrediction.factors.grades_impact}%</div>
                  </div>
                  <div style={{ flex: 1, minWidth: 200, padding: 12, borderRadius: 8, background: "#eff6ff", border: "1px solid #bfdbfe" }}>
                    <div style={{ fontSize: 12, color: "#1e40af", marginBottom: 4 }}>Devamsızlık</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#1e40af" }}>{aiPrediction.factors.attendance_impact}%</div>
                  </div>
                  <div style={{ flex: 1, minWidth: 200, padding: 12, borderRadius: 8, background: "#fef9c3", border: "1px solid #fde047" }}>
                    <div style={{ fontSize: 12, color: "#854d0e", marginBottom: 4 }}>Çalışma</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#854d0e" }}>{aiPrediction.factors.study_impact}%</div>
                  </div>
                </div>
              </div>
            )}

            {aiPrediction.historical_performance && (
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Geçmiş Performans</h3>
                <div style={{ display: "flex", gap: 8, alignItems: "center", padding: 12, borderRadius: 8, background: "#f8faf8" }}>
                  <div style={{ fontSize: 13, color: "#6e7b7d" }}>Son notlar:</div>
                  {aiPrediction.historical_performance.grades.map((grade: number, idx: number) => (
                    <div key={idx} style={{ padding: "4px 8px", borderRadius: 4, background: grade >= 80 ? "#dcfce7" : grade >= 60 ? "#fef3c7" : "#fee2e2", fontSize: 12, fontWeight: 600, color: "#1b2b2e" }}>{grade}</div>
                  ))}
                </div>
              </div>
            )}

            {aiPrediction.subject_performance && (
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Ders Bazlı Performans</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 12 }}>
                  {Object.entries(aiPrediction.subject_performance).map(([subject, grade]) => (
                    <div key={subject} style={{ padding: 12, borderRadius: 8, background: (grade as number) >= 80 ? "#dcfce7" : (grade as number) >= 60 ? "#fef3c7" : "#fee2e2", border: "1px solid " + ((grade as number) >= 80 ? "#bbf7d0" : (grade as number) >= 60 ? "#fde68a" : "#fecaca") }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>{subject}</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>{String(grade)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(aiPrediction.strengths || aiPrediction.weaknesses) && (
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Güçlü ve Zayıf Yönler</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
                  {aiPrediction.strengths && aiPrediction.strengths.length > 0 && (
                    <div style={{ padding: 12, borderRadius: 8, background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
                      <div style={{ fontSize: 12, color: "#166534", marginBottom: 8, fontWeight: 600 }}>Güçlü Yönler</div>
                      {aiPrediction.strengths.map((strength: string, idx: number) => (
                        <div key={idx} style={{ fontSize: 13, color: "#1b2b2e", marginBottom: 4 }}>• {strength}</div>
                      ))}
                    </div>
                  )}
                  {aiPrediction.weaknesses && aiPrediction.weaknesses.length > 0 && (
                    <div style={{ padding: 12, borderRadius: 8, background: "#fef2f2", border: "1px solid #fecaca" }}>
                      <div style={{ fontSize: 12, color: "#991b1b", marginBottom: 8, fontWeight: 600 }}>Geliştirme Alanları</div>
                      {aiPrediction.weaknesses.map((weakness: string, idx: number) => (
                        <div key={idx} style={{ fontSize: 13, color: "#1b2b2e", marginBottom: 4 }}>• {weakness}</div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {aiPrediction.behavioral_analysis && (
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Davranışsal Analiz</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
                  <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e2e8f0" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Davranış Puanı</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>{aiPrediction.behavioral_analysis.score}</div>
                  </div>
                  <div style={{ padding: 12, borderRadius: 8, background: aiPrediction.behavioral_analysis.assessment === "excellent" ? "#dcfce7" : aiPrediction.behavioral_analysis.assessment === "good" ? "#fef9c3" : "#fee2e2", border: "1px solid " + (aiPrediction.behavioral_analysis.assessment === "excellent" ? "#bbf7d0" : aiPrediction.behavioral_analysis.assessment === "good" ? "#fde047" : "#fecaca") }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Değerlendirme</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: "#1b2b2e" }}>{aiPrediction.behavioral_analysis.assessment === "excellent" ? "Mükemmel" : aiPrediction.behavioral_analysis.assessment === "good" ? "İyi" : aiPrediction.behavioral_analysis.assessment === "needs_improvement" ? "Geliştirilmeli" : "Endişe Verici"}</div>
                  </div>
                  <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e2e8f0" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Öğrenme Potansiyeli</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: "#1b2b2e" }}>{aiPrediction.learning_potential === "high" ? "Yüksek" : aiPrediction.learning_potential === "moderate" ? "Orta" : "Sınırlı"}</div>
                  </div>
                </div>
              </div>
            )}

            {aiPrediction.recommendations && aiPrediction.recommendations.length > 0 && (
              <div>
                <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Önerileri</h3>
                {aiPrediction.recommendations.map((rec: string, index: number) => (
                  <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, alignItems: "flex-start", padding: 12, borderRadius: 8, background: index === 0 ? "#fff7ed" : "#f8faf8", border: index === 0 ? "1px solid #fed7aa" : "none" }}>
                    <TrendingUp size={16} color="#176b5b" style={{ flexShrink: 0, marginTop: 2 }} />
                    <span style={{ fontSize: 13 }}>{rec}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {classInfo && (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="card-head">
            <div>
              <h2>Sınıf bilgisi</h2>
              <p>Öğrencinin kayıtlı olduğu sınıf</p>
            </div>
          </div>
          <div className="card-pad detail-list">
            <div className="detail-item">
              <small>Sınıf adı</small>
              <strong>{textValue(classInfo.name)}</strong>
            </div>
            <div className="detail-item">
              <small>Sınıf kodu</small>
              <strong>{textValue(classInfo.code)}</strong>
            </div>
            <div className="detail-item">
              <small>Öğretmen</small>
              <strong>{textValue(classInfo.teacher_name, "Atanmamış")}</strong>
            </div>
            <div className="detail-item">
              <small>Kapasite</small>
              <strong>{textValue(classInfo.capacity, "0")} öğrenci</strong>
            </div>
          </div>
        </div>
      )}

      {parents.length > 0 && (
        <div className="card" style={{ marginTop: 18 }}>
          <div className="card-head">
            <div>
              <h2>Veli bilgileri</h2>
              <p>Öğrenci ile ilişkili veli kayıtları</p>
            </div>
          </div>
          <div className="card-pad">
            {parents.map((parent) => (
              <div key={parent.id} style={{ padding: "12px 0", borderBottom: "1px solid #e7ece8" }}>
                <div style={{ font: "600 14px Manrope", marginBottom: 4 }}>
                  {[parent.first_name, parent.last_name].map((value) => textValue(value, "")).filter(Boolean).join(" ")}
                </div>
                <div style={{ display: "flex", gap: 16, fontSize: 13, color: "#5e6c6d" }}>
                  {parent.phone && (
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <Phone size={12} />{textValue(parent.phone)}
                    </span>
                  )}
                  {parent.email && (
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <Mail size={12} />{textValue(parent.email)}
                    </span>
                  )}
                  {(parent.relationship || parent.relation_type) && (
                    <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <User size={12} />{textValue(parent.relationship || parent.relation_type)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
