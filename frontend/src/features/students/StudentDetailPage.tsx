import { getAnalysis } from "../../lib/analysis";
import { ArrowLeft, CalendarCheck2, CreditCard, FileText, Pencil, User, Phone, Mail, IdCard, Brain } from "lucide-react";
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
          getAnalysis(`/ai/student-performance/${id}`).catch(() => null),
        ]);
        if (parentsRes.status === "fulfilled") {
          setParents(toArray(parentsRes.value.data.data));
        }
        if (classRes.status === "fulfilled" && classRes.value) {
          setClassInfo(classRes.value.data.data);
        }
        if (aiRes.status === "fulfilled" && aiRes.value) {
          
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
        <section className="card" style={{ marginTop: 18 }} aria-label="Öğrenci kayıt özeti">
          <div className="card-head"><div><h2>Kayıtlara dayalı öğrenci özeti</h2><p>{aiPrediction.summary}</p></div><Brain size={20} color="#176b5b" /></div>
          <div className="card-pad detail-list">
            {(aiPrediction.metrics || []).map((metric: { label: string; value: string }) => <div className="detail-item" key={metric.label}><small>{metric.label}</small><strong>{metric.value}</strong></div>)}
          </div>
        </section>
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
