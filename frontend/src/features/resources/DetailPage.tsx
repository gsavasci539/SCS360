import { getAnalysis } from "../../lib/analysis";
import { ArrowLeft, CalendarCheck2, CreditCard, FileText, Pencil, UserRound, BrainCircuit } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge, ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { CapacityValue } from "../../components/DataTable";
import { resources } from "../../config/resources";
import { api, apiMessage } from "../../lib/api";
import { shortDate, titleCase } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import type { ApiResponse, DataRecord } from "../../types/api";
import { ParentAccountAccess } from "../parent/ParentAccountAccess";

export function DetailPage({ resourceKey }: { resourceKey: string }) {
  const config = resources[resourceKey];
  const { id } = useParams();
  const [record, setRecord] = useState<DataRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const can = useAuthStore((state) => state.can);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setRecord(null);
    
    
    
    // For classes, call the classes endpoint directly, not the AI endpoint
    const endpoint = resourceKey === "classes" ? "/classes" : config.endpoint;
    
    
    api.get<ApiResponse<DataRecord>>(`${endpoint}/${id}`, { signal: controller.signal })
      .then((r) => {
        if (controller.signal.aborted) return;
        
        
        
        
        setRecord(r.data.data);
      })
      .catch((e) => { if (!controller.signal.aborted) setError(apiMessage(e)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [config.endpoint, id, resourceKey]);

  // Load AI analysis for parents
  useEffect(() => {
    if (resourceKey === "parents" && record) {
      setAiLoading(true);
      getAnalysis(`/ai/parent-analysis/${id}`)
        .then((r) => setAiAnalysis(r.data.data))
        .catch((e) => console.error("AI analysis error:", e))
        .finally(() => setAiLoading(false));
    }
  }, [resourceKey, record, id]);

  // Load AI analysis for classes
  useEffect(() => {
    if (resourceKey === "classes" && record) {
      setAiLoading(true);
      getAnalysis(`/ai/class-analysis/${id}`)
        .then((r) => setAiAnalysis(r.data.data))
        .catch((e) => console.error("AI analysis error:", e))
        .finally(() => setAiLoading(false));
    }
  }, [resourceKey, record, id]);

  if (loading) return <div className="card"><LoadingState /></div>;
  if (error || !record) return <div className="card"><ErrorState message={error || "Kayıt bulunamadı."} /></div>;

  const displayName = [record.first_name, record.last_name].filter(Boolean).join(" ") || String(record.name || config.singular);
  const registry = ["organizations", "branches"].includes(resourceKey);
  const detailColumns = registry ? [
    ...config.fields.filter((field) => field.name !== "organization_id").map((field) => ({
      key: field.name, label: field.label,
      type: field.name === "capacity" ? "capacity" : "text",
    })),
    { key: "is_active", label: "Durum", type: "status" },
  ] : config.columns.filter((column) => column.key !== "status");

  return (
    <>
      <PageHeader 
        eyebrow={`${config.singular} profili`} 
        title={displayName} 
        description="Kayıtla ilişkili temel bilgiler ve işlem geçmişi."
      >
        <Link className="btn btn-secondary" to={config.listPath || config.detailPath || `/${resourceKey}`}>
          <ArrowLeft size={16} />Listeye dön
        </Link>
        {config.permissionWrite && can(config.permissionWrite) && (
          <Link className="btn btn-primary" to={`${config.detailPath || `/${resourceKey}`}/${id}/edit`}>
            <Pencil size={16} />Düzenle
          </Link>
        )}
      </PageHeader>

      {resourceKey === "parents" && id && can("parents.write") && can("users.write") && <ParentAccountAccess key={id} parentId={id} />}

      <div className="detail-grid">
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Genel bilgiler</h2>
              <p>Backend kaydından güncel bilgiler</p>
            </div>
          </div>
          <div className="tabs">
            <button className="tab active">Profil</button>
            {resourceKey === "students" && (
              <>
                <button className="tab">Veliler</button>
                <button className="tab">Finans</button>
                <button className="tab">Yoklama</button>
                <button className="tab">Dosyalar</button>
              </>
            )}
          </div>
          <div className="card-pad detail-list">
            {detailColumns.map((column) => {
              const value = record[column.key];
              return (
                <div className="detail-item" key={column.key}>
                  <small>{column.label}</small>
                  <div className="detail-value">
                    {column.type === "status" ? <Badge value={value ? "ACTIVE" : "PASSIVE"} /> :
                     column.type === "capacity" ? <CapacityValue count={record.student_count ?? record.occupancy} capacity={value} /> :
                     registry ? <strong>{String(value ?? "—")}</strong> :
                     column.type === "date" ? shortDate(value) : 
                     column.key === "teacher_name" ? String(value || "—") :
                     titleCase(value)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <aside className="card card-pad">
          <h2 style={{ margin: "0 0 15px", font: "700 15px Manrope" }}>Hızlı bağlantılar</h2>
          {resourceKey === "students" ? (
            <div className="quick-list" style={{ padding: 0 }}>
              <Link className="quick-item" to={`/students/${id}/files`}>
                <div className="quick-icon"><FileText size={16} /></div>
                <div className="quick-copy">
                  <strong>Öğrenci dosyaları</strong>
                  <span>Belgeler ve sözleşmeler</span>
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
                  <span>Günlük yoklama geçmişi</span>
                </div>
              </Link>
            </div>
          ) : (
            <div className="state" style={{ minHeight: 180, padding: 15 }}>
              <div>
                <UserRound size={28} color="#7fa89d" />
                <h3>{registry ? (record.is_active ? "Kayıt aktif" : "Kayıt pasif") : "Kayıt bilgileri"}</h3>
                <p>İlişkili işlemler ilgili modüllerde görüntülenir.</p>
              </div>
            </div>
          )}
        </aside>

        {/* AI Analysis Card for Parents - positioned at bottom */}
        {resourceKey === "parents" && (
          <div className="card" style={{ gridColumn: "1 / -1" }}>
            <div className="card-head">
              <div>
                <h2>AI Analizi</h2>
                <p>Yapay zeka destekli veli analizi</p>
              </div>
              <BrainCircuit size={20} color="#7fa89d" />
            </div>
            <div className="card-pad">
              {aiLoading ? (
                <LoadingState />
              ) : aiAnalysis ? (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 20 }}>
                  <div style={{ padding: 16, borderRadius: 12, background: "#f8faf8", textAlign: "center" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 8, fontWeight: 600 }}>Öğrenci Sayısı</div>
                    <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.student_count || 0}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 12, background: aiAnalysis.engagement_score >= 70 ? "#dcfce7" : aiAnalysis.engagement_score >= 50 ? "#fef9c3" : "#fee2e2", textAlign: "center" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 8, fontWeight: 600 }}>Katılım Puanı</div>
                    <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.engagement_score}/100</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 12, background: aiAnalysis.payment_compliance >= 70 ? "#dcfce7" : "#fee2e2", textAlign: "center" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 8, fontWeight: 600 }}>Ödeme Uyumu</div>
                    <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>%{aiAnalysis.payment_compliance}</div>
                  </div>
                </div>
              ) : (
                <div className="state" style={{ minHeight: 100, padding: 15 }}>
                  <p>AI analizi yüklenemedi.</p>
                </div>
              )}
              
              {aiAnalysis && (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 20 }}>
                    <div style={{ padding: 16, borderRadius: 12, background: aiAnalysis.has_contact_info ? "#dcfce7" : "#fee2e2" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, fontWeight: 600 }}>İletişim Bilgileri</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>{aiAnalysis.has_contact_info ? "Mevcut" : "Eksik"}</div>
                    </div>
                    <div style={{ padding: 16, borderRadius: 12, background: aiAnalysis.receives_notifications ? "#dcfce7" : "#fee2e2" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, fontWeight: 600 }}>Bildirim Tercihleri</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>{aiAnalysis.receives_notifications ? "Açık" : "Kapalı"}</div>
                    </div>
                  </div>
                  
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 20 }}>
                    <div style={{ padding: 16, borderRadius: 12, background: "#f8faf8" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, fontWeight: 600 }}>Toplam Borç</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>₺{aiAnalysis.total_debt?.toFixed(2) || "0.00"}</div>
                    </div>
                    <div style={{ padding: 16, borderRadius: 12, background: "#f8faf8" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, fontWeight: 600 }}>Ödenen Tutar</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>₺{aiAnalysis.total_paid?.toFixed(2) || "0.00"}</div>
                    </div>
                  </div>
                  
                  <div style={{ padding: 16, borderRadius: 12, background: aiAnalysis.attendance_rate >= 80 ? "#dcfce7" : aiAnalysis.attendance_rate >= 60 ? "#fef9c3" : "#fee2e2", marginBottom: 20 }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, fontWeight: 600 }}>Devamsızlık Oranı</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>%{aiAnalysis.attendance_rate}</div>
                  </div>
                  
                  {aiAnalysis.recommendations && aiAnalysis.recommendations.length > 0 && (
                    <div style={{ padding: 16, borderRadius: 12, background: "#f0f9ff", borderLeft: "4px solid #0ea5e9" }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: "#0c4a6e", marginBottom: 12 }}>Öneriler</div>
                      <ul style={{ margin: 0, paddingLeft: 20, color: "#334155" }}>
                        {aiAnalysis.recommendations.map((rec: string, idx: number) => (
                          <li key={idx} style={{ marginBottom: 6 }}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {/* AI Analysis Card for Classes - positioned at bottom */}
        {resourceKey === "classes" && (
          <div className="card" style={{ gridColumn: "1 / -1" }}>
            <div className="card-head">
              <div>
                <h2>AI Analizi</h2>
                <p>Yapay zeka destekli sınıf analizi</p>
              </div>
              <BrainCircuit size={20} color="#7fa89d" />
            </div>
            <div className="card-pad">
              {aiLoading ? (
                <LoadingState />
              ) : aiAnalysis ? (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 20 }}>
                  <div style={{ padding: 16, borderRadius: 12, background: "#f8faf8", textAlign: "center" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 8, fontWeight: 600 }}>Öğrenci Sayısı</div>
                    <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.student_count || 0}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 12, background: aiAnalysis.attendance_rate >= 85 ? "#dcfce7" : aiAnalysis.attendance_rate >= 70 ? "#fef9c3" : "#fee2e2", textAlign: "center" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 8, fontWeight: 600 }}>Devamsızlık Oranı</div>
                    <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>%{aiAnalysis.attendance_rate}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 12, background: aiAnalysis.avg_grade >= 80 ? "#dcfce7" : aiAnalysis.avg_grade >= 70 ? "#fef9c3" : "#fee2e2", textAlign: "center" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 8, fontWeight: 600 }}>Ortalama Not</div>
                    <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{aiAnalysis.avg_grade}</div>
                  </div>
                </div>
              ) : (
                <div className="state" style={{ minHeight: 100, padding: 15 }}>
                  <p>AI analizi yüklenemedi.</p>
                </div>
              )}
              
              {aiAnalysis && (
                <>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 20 }}>
                    <div style={{ padding: 16, borderRadius: 12, background: "#f8faf8" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, fontWeight: 600 }}>Kapasite</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>{aiAnalysis.capacity}</div>
                    </div>
                    <div style={{ padding: 16, borderRadius: 12, background: "#f8faf8" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, fontWeight: 600 }}>Öğretmen</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>{aiAnalysis.teacher_name || "—"}</div>
                    </div>
                  </div>
                  
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginBottom: 20 }}>
                    <div style={{ padding: 16, borderRadius: 12, background: aiAnalysis.performance_trend === "Artış" ? "#dcfce7" : aiAnalysis.performance_trend === "Stabil" ? "#fef9c3" : "#fee2e2" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, fontWeight: 600 }}>Performans Trendi</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e" }}>{aiAnalysis.performance_trend}</div>
                    </div>
                  </div>
                  
                  {aiAnalysis.recommendations && aiAnalysis.recommendations.length > 0 && (
                    <div style={{ padding: 16, borderRadius: 12, background: "#f0f9ff", borderLeft: "4px solid #0ea5e9" }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: "#0c4a6e", marginBottom: 12 }}>Öneriler</div>
                      <ul style={{ margin: 0, paddingLeft: 20, color: "#334155" }}>
                        {aiAnalysis.recommendations.map((rec: string, idx: number) => (
                          <li key={idx} style={{ marginBottom: 6 }}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
