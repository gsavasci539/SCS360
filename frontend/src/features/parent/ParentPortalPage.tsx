import { ParentSchoolCheckout, ParentCheckoutReturn } from "./ParentSchoolCheckout";
import { useSearchParams } from "react-router-dom";
import { CalendarCheck2, CreditCard, FileHeart, GraduationCap, HeartPulse, UsersRound, Activity, Clock, CheckCircle, XCircle, Wallet, MessageCircle, Bell, BookOpen, Brain, Lightbulb } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ErrorState, LoadingState, PageHeader, Badge } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse, DataRecord } from "../../types/api";
import { ChatInterface } from "./ChatInterface";
import { HomeworkSubmissions } from "../academic/HomeworkSubmissions";
import { downloadFile } from "../../lib/download";
import { ParentExcuseRequests } from "../communications/ExcuseRequests";
import { ParentDayTimeline } from "./ParentDayTimeline";
import { ParentCertificates } from "./ParentCertificates";
import { ParentReportCards } from "./ParentReportCards";
import { ParentConsents } from "./ParentConsents";
import { ParentSurveys } from "./ParentSurveys";
import { useAuthStore } from "../../stores/auth";

type View = "dashboard" | "children" | "attendance" | "finances" | "health" | "academic" | "schedule" | "homework" | "materials" | "communication" | "announcements" | "activities" | "reports" | "chat" | "consents" | "surveys";

const today = new Date();
const unwrap = <T,>(response: { data: ApiResponse<T> }) => response.data.data;

export function ParentPortalPage({ view }: { view: View }) {
  const canMakePayment = useAuthStore((state) => state.can("parent.make_payment"));
  const canSendMedicine = useAuthStore((state) => state.can("parent.medicine_request"));
  const canReadFinances = useAuthStore((state) => state.can("parent.view_finances"));
  const [medicineSubmitting, setMedicineSubmitting] = useState(false);
  const [children, setChildren] = useState<DataRecord[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [status, setStatus] = useState<DataRecord | null>(null);
  const [attendance, setAttendance] = useState<DataRecord | null>(null);
  const [finances, setFinances] = useState<DataRecord | null>(null);
  const [medicineRequests, setMedicineRequests] = useState<DataRecord[]>([]);
  const [medicine, setMedicine] = useState({ medicine_name: "", dosage: "", time_to_give: "", instructions: "" });
  const [requestMessage, setRequestMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [aiRecommendations, setAiRecommendations] = useState<any>(null);
  
  // New academic and activity data
  const [grades, setGrades] = useState<DataRecord[]>([]);
  const [schedule, setSchedule] = useState<DataRecord[]>([]);
  const [homework, setHomework] = useState<DataRecord[]>([]);
  const [materials, setMaterials] = useState<DataRecord[]>([]);
  const [materialError, setMaterialError] = useState("");
  const [downloadingMaterial, setDownloadingMaterial] = useState("");

  async function downloadMaterial(material: DataRecord) {
    setMaterialError("");
    setDownloadingMaterial(String(material.id));
    try {
      await downloadFile(`/parent/child/${selectedId}/materials/${material.id}/download`,
        String(material.file_name || material.title || "materyal"));
    } catch (err) {
      setMaterialError(apiMessage(err));
    } finally {
      setDownloadingMaterial("");
    }
  }
  const [communications, setCommunications] = useState<DataRecord[]>([]);
  const [announcements, setAnnouncements] = useState<DataRecord[]>([]);
  const [activities, setActivities] = useState<DataRecord[]>([]);
  const [weeklyReports, setWeeklyReports] = useState<DataRecord[]>([]);
  
  // Chat and new message functionality
  const [newMessageOpen, setNewMessageOpen] = useState(false);
  const [newMessage, setNewMessage] = useState({
    teacher_id: "",
    subject: "",
    message: ""
  });
  const [teachers, setTeachers] = useState<DataRecord[]>([]);
  const [chatTeacherId, setChatTeacherId] = useState("");
  const [chatTeacherName, setChatTeacherName] = useState("");
  const [paymentModal, setPaymentModal] = useState<{ debtId: string; amount: number; childName: string } | null>(null);
  const [paymentSearch, setPaymentSearch] = useSearchParams();
  const paymentController = useRef<AbortController | null>(null), paymentChild = useRef(selectedId);
  useLayoutEffect(() => { paymentChild.current = selectedId; paymentController.current?.abort(); }, [selectedId]);
  useEffect(() => { setPaymentModal(null); return () => paymentController.current?.abort(); }, [selectedId]);
  
  

  useEffect(() => {
    api.get<ApiResponse<DataRecord[]>>("/parent/my-children")
      .then((response) => {
        const records = response.data.data || [];
        setChildren(records);
        setSelectedId(records[0]?.student_id ? String(records[0].student_id) : "");
      })
      .catch((reason) => setError(apiMessage(reason)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setLoading(true); setError("");
    setStatus(null); setAttendance(null); setFinances(null); setMedicineRequests([]);
    setGrades([]); setSchedule([]); setHomework([]); setMaterials([]); setCommunications([]);
    setAnnouncements([]); setActivities([]); setWeeklyReports([]); setTeachers([]);
    setChatTeacherId(""); setAiRecommendations(null);
    const requests: Promise<unknown>[] = [api.get<ApiResponse<DataRecord>>(`/parent/child/${selectedId}/today-status`)];
    if (view === "attendance") requests.push(api.get<ApiResponse<DataRecord>>(`/parent/child/${selectedId}/attendance`, { params: { year: today.getFullYear(), month: today.getMonth() + 1 } }));
    if (view === "finances" || (view === "dashboard" && canReadFinances)) requests.push(api.get<ApiResponse<DataRecord>>(`/parent/child/${selectedId}/financial-invoices`));
    else if (view === "dashboard") requests.push(Promise.resolve({ data: { data: null } }));
    if (view === "health") requests.push(api.get<ApiResponse<DataRecord>>(`/parent/child/${selectedId}/medicine-requests`));
    if (view === "academic") requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/grades`));
    if (view === "schedule") requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/schedule`));
    if (view === "homework") requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/homework`));
    if (view === "materials") requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/materials`));
    if (view === "communication") {
      requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/communications`));
      requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/teachers`));
    }
    if (view === "chat") {
      requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/teachers`));
    }
    if (view === "announcements") requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/announcements`));
    if (view === "activities") requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/activities`));
    if (view === "reports") requests.push(api.get<ApiResponse<DataRecord[]>>(`/parent/child/${selectedId}/weekly-reports`));
    
    // Consent decisions depend on the document, not a student performance score.
    requests.push(view === "consents" || view === "surveys" ? Promise.resolve(null) : api.get(`/parent/child/${selectedId}/insights`, { params: { context: view } }).catch(() => null));
    
    Promise.all(requests).then((responses) => {
      if (cancelled) return;
      setStatus(unwrap(responses[0] as { data: ApiResponse<DataRecord> }));
      if (view === "attendance") setAttendance(unwrap(responses[1] as { data: ApiResponse<DataRecord> }));
      if (view === "finances" || view === "dashboard") setFinances(unwrap(responses[1] as { data: ApiResponse<DataRecord> }));
      if (view === "health") setMedicineRequests(((unwrap(responses[1] as { data: ApiResponse<DataRecord> }).medicine_requests as DataRecord[]) || []));
      if (view === "academic") setGrades(unwrap(responses[1] as { data: ApiResponse<DataRecord[]> }) || []);
      if (view === "schedule") setSchedule(unwrap(responses[1] as { data: ApiResponse<DataRecord[]> }) || []);
      if (view === "homework") setHomework(unwrap(responses[1] as { data: ApiResponse<DataRecord[]> }) || []);
      if (view === "materials") setMaterials(unwrap(responses[1] as { data: ApiResponse<DataRecord[]> }) || []);
      if (view === "announcements") setAnnouncements(unwrap(responses[1] as { data: ApiResponse<DataRecord[]> }) || []);
      if (view === "activities") setActivities(unwrap(responses[1] as { data: ApiResponse<DataRecord[]> }) || []);
      if (view === "reports") setWeeklyReports(unwrap(responses[1] as { data: ApiResponse<DataRecord[]> }) || []);
      if (view === "chat") setTeachers(unwrap(responses[1] as { data: ApiResponse<DataRecord[]> }) || []);
      if (view === "communication") {
        setCommunications(unwrap(responses[1] as { data: ApiResponse<DataRecord[]> }) || []);
        setTeachers(unwrap(responses[2] as { data: ApiResponse<DataRecord[]> }) || []);
      }
      // Hata durumunda istek ``null`` döner. Null üzerinde ``.data`` okumak
      // Promise.all akışını bozuyordu ve AI kartı hiç gösterilmiyordu.
      const aiResponse = responses[responses.length - 1] as { data?: ApiResponse<DataRecord> } | null;
      setAiRecommendations(aiResponse?.data?.data ?? null);
    }).catch((reason) => { if (!cancelled) setError(apiMessage(reason)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selectedId, view, canReadFinances]);

  const selected = children.find((child) => String(child.student_id) === selectedId);
  const heading = { 
    dashboard: "Veli Paneli", 
    children: "Çocuğum", 
    attendance: "Devamsızlık", 
    finances: "Ödemeler", 
    health: "Sağlık ve İzinler",
    academic: "Akademik Durum",
    schedule: "Ders Programı",
    homework: "Ödevler ve Projeler",
    materials: "Ders Materyalleri",
    communication: "İletişim Geçmişi",
    announcements: "Okul Duyuruları",
    activities: "Kulüp ve Aktiviteler",
    consents: "İzin ve Onay Belgeleri",
    surveys: "Veli Anketleri",
    reports: "Haftalık Raporlar",
    chat: "Canlı Sohbet"
  }[view];
  const description = { 
    dashboard: "Çocuğunuzun bugünkü durumu ve önemli bilgileri.", 
    children: "Çocuğunuzun sınıf ve günlük gelişim bilgileri.", 
    attendance: "Aylık devam durumunu takip edin.", 
    finances: "Eğitim ödemeleri ve kalan tutar.", 
    health: "İlaç talimatlarını paylaşın ve sağlık taleplerini takip edin.",
    academic: "Notlar, sınav sonuçları ve akademik performans.",
    schedule: "Haftalık ders programı ve saat bilgileri.",
    homework: "Ödev takvimi, projeler ve teslim tarihleri.",
    materials: "Ders notları, kitaplar ve eğitim materyalleri.",
    communication: "Öğretmenlerle yapılan iletişim kayıtları.",
    announcements: "Okul ve sınıf duyuruları.",
    activities: "Kulüp faaliyetleri ve etkinlik takvimi.",
    consents: "Çocuğunuzun izin belgelerini okuyun ve veli kararınızı kaydedin.",
    surveys: "Okulunuzun katılımınıza açtığı anketleri yanıtlayın.",
    reports: "Haftalık gelişim raporları ve değerlendirmeler.",
    chat: "Öğretmenlerle gerçek zamanlı sohbet."
  }[view];

  async function submitMedicine(event: React.FormEvent) {
    event.preventDefault();
    if (medicineSubmitting || !canSendMedicine) return;
    setMedicineSubmitting(true);
    setRequestMessage("");
    try {
      await api.post(`/parent/child/${selectedId}/medicine-requests`, medicine);
      setMedicine({ medicine_name: "", dosage: "", time_to_give: "", instructions: "" });
      setRequestMessage("İlaç talimatı okul ekibine iletildi.");
      const response = await api.get<ApiResponse<DataRecord>>(`/parent/child/${selectedId}/medicine-requests`);
      setMedicineRequests(((response.data.data?.medicine_requests as DataRecord[]) || []));
    } catch (reason) { setRequestMessage(apiMessage(reason)); }
    finally { setMedicineSubmitting(false); }
  }

  async function submitNewMessage(event: React.FormEvent) {
    event.preventDefault();
    setRequestMessage("");
    try {
      await api.post(`/parent/child/${selectedId}/send-message`, newMessage);
      setNewMessage({ teacher_id: "", subject: "", message: "" });
      setNewMessageOpen(false);
      setRequestMessage("Mesajınız başarıyla gönderildi.");
      // Refresh communications
      const response = await api.get(`/parent/child/${selectedId}/communications`);
      setCommunications(response.data.data || []);
    } catch (reason) { setRequestMessage(apiMessage(reason)); }
  }

  function initializePayment(debtId: string, amount: number) {
    setRequestMessage("");
    setPaymentModal({ debtId, amount, childName: [selected?.first_name, selected?.last_name].filter(Boolean).join(" ") });
  }

  

  function refreshPaymentFinances() {
    if (!selectedId || !canReadFinances) return;
    paymentController.current?.abort();
    const controller = new AbortController(); paymentController.current = controller;
    api.get(`/parent/child/${selectedId}/financial-invoices`, { signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted && paymentChild.current === selectedId) setFinances(response.data.data); })
      .catch((reason) => { if (!controller.signal.aborted && paymentChild.current === selectedId) setRequestMessage(apiMessage(reason)); });
  }
  function closePaymentModal() { setPaymentModal(null); refreshPaymentFinances(); }


  if (loading && !children.length) return <div className="card"><LoadingState /></div>;
  if (error && !children.length) return <div className="card"><ErrorState message={error} /></div>;
  if (!children.length) return <div className="card"><ErrorState message="Bu veli hesabına bağlı öğrenci bulunamadı." /></div>;

  const daily = status?.daily_report as DataRecord | undefined;
  const currentAttendance = status?.attendance as DataRecord | undefined;
  const summary = attendance?.summary as DataRecord | undefined;
  const invoices = (finances?.invoices as DataRecord[] | undefined) || [];

  return <>
    <PageHeader eyebrow="Veli Portalı" title={heading} description={description} />
    {view === "finances" && canMakePayment && paymentSearch.has("checkout") && <ParentCheckoutReturn
      checkoutId={paymentSearch.get("checkout") || ""} onComplete={refreshPaymentFinances}
      onClose={() => { const next = new URLSearchParams(paymentSearch); next.delete("checkout"); setPaymentSearch(next, { replace: true }); }} />}
    
    {/* Child Selector */}
    <div className="card parent-selector-gradient parent-animate-in">
      <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <label className="field-label" style={{ color: "rgba(255,255,255,0.9)", marginBottom: 8, display: "block", fontWeight: 600 }}>Öğrenci Seçin</label>
          <select 
            id="parent-child" 
            value={selectedId} 
            disabled={medicineSubmitting}
            onChange={(event) => setSelectedId(event.target.value)}
            className="parent-input-glass"
            style={{ 
              width: "100%", 
              padding: "12px 16px", 
              borderRadius: "12px", 
              border: "1px solid rgba(255,255,255,0.3)", 
              fontSize: "16px",
              cursor: "pointer",
              fontWeight: 500
            }}
          >
            {children.map((child) => (
              <option key={String(child.student_id)} value={String(child.student_id)} style={{ color: "#333" }}>
                {String(child.first_name)} {String(child.last_name)} · {String(child.class_name || "Sınıf bilgisi yok")}
              </option>
            ))}
          </select>
        </div>
        {selected && (
          <div style={{ display: "flex", alignItems: "center", gap: 12, background: "rgba(255,255,255,0.1)", padding: "12px 16px", borderRadius: "12px", backdropFilter: "blur(10px)" }}>
            <div className="parent-icon-circle">
              <UsersRound size={24} />
            </div>
            <div>
              <div style={{ fontSize: "18px", fontWeight: 700 }}>{String(selected.first_name)} {String(selected.last_name)}</div>
              <div style={{ fontSize: "14px", opacity: 0.9 }}>{String(selected.class_name || "Sınıf bilgisi yok")}</div>
            </div>
          </div>
        )}
      </div>
    </div>

    {error && <div className="card" style={{ marginBottom: 24 }}><ErrorState message={error} /></div>}
    {(view === "dashboard" || view === "children") && selectedId && status?.date &&
      <ParentDayTimeline key={`${selectedId}-${String(status.date)}`} studentId={selectedId} initialDate={String(status.date)} />}
    {view === "activities" && selectedId && <ParentCertificates key={selectedId} studentId={selectedId} />}
    {view === "academic" && selectedId && <ParentReportCards key={selectedId} studentId={selectedId} />}
    {view === "consents" && selectedId && <ParentConsents key={selectedId} studentId={selectedId} />}
    {view === "surveys" && selectedId && <ParentSurveys key={selectedId} studentId={selectedId} />}

    {aiRecommendations && (
      <div className="card parent-animate-in" style={{
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        color: "white", padding: "16px", marginBottom: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <Brain size={20} />
          <span style={{ fontSize: "12px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>Kayıt özeti</span>
        </div>
        <div style={{ fontSize: "14px", fontWeight: 700, marginBottom: 8 }}>
          {String(aiRecommendations.title || "Çocuğunuz için gelişim önerileri")}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, fontSize: 13, opacity: 0.95 }}>
          {Array.isArray(aiRecommendations.metrics) && aiRecommendations.metrics.length > 0 ? aiRecommendations.metrics.map((metric: { label?: string; value?: string }, index: number) => (
            <span key={index}>{String(metric.label || "Ölçüt")}: {String(metric.value ?? "-")}</span>
          )) : <span>{String(aiRecommendations.summary || "Görüntülenebilir kayıt yok")}</span>}
        </div>
        {Array.isArray(aiRecommendations.recommendations) && aiRecommendations.recommendations.map((recommendation: string, index: number) => (
          <div key={index} style={{ display: "flex", gap: 8, marginTop: 10, fontSize: 13 }}>
            <Lightbulb size={15} style={{ flexShrink: 0 }} />
            <span>{recommendation}</span>
          </div>
        ))}
      </div>
    )}

    {/* Dashboard View */}
    {view === "dashboard" && (
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
        <div className="card parent-stat-card parent-animate-in" style={{ 
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
          color: "white",
          padding: "16px",
          position: "relative",
          overflow: "hidden"
        }}>
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div className="parent-icon-circle" style={{ width: 32, height: 32 }}>
                <UsersRound size={16} />
              </div>
              <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Öğrenci</span>
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: 2 }}>
              {String(selected?.first_name || "")} {String(selected?.last_name || "")}
            </div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              {String(selected?.class_name || "Sınıf bilgisi yok")}
            </div>
          </div>
        </div>

        <div className="card parent-stat-card parent-animate-in" style={{ 
          background: "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)", 
          color: "white",
          padding: "16px",
          position: "relative",
          overflow: "hidden",
          animationDelay: "0.1s"
        }}>
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div className="parent-icon-circle" style={{ width: 32, height: 32 }}>
                <CalendarCheck2 size={16} />
              </div>
              <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Bugünkü Yoklama</span>
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: 2 }}>
              {String(currentAttendance?.status || "Henüz işlenmedi")}
            </div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              {currentAttendance?.check_in_time ? `Giriş: ${currentAttendance.check_in_time}` : ""}
            </div>
          </div>
        </div>

        <div className="card parent-stat-card parent-animate-in" style={{ 
          background: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)", 
          color: "white",
          padding: "16px",
          position: "relative",
          overflow: "hidden",
          animationDelay: "0.2s"
        }}>
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div className="parent-icon-circle" style={{ width: 32, height: 32 }}>
                <HeartPulse size={16} />
              </div>
              <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Günlük Durum</span>
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: 2 }}>
              {String(daily?.mood || "Henüz bildirilmedi")}
            </div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              {String(daily?.meal_status || "Yemek bilgisi yok")}
            </div>
          </div>
        </div>

        {canReadFinances && (
        <div className="card parent-stat-card parent-animate-in" style={{ 
          background: "linear-gradient(135deg, #fa709a 0%, #fee140 100%)", 
          color: "white",
          padding: "16px",
          position: "relative",
          overflow: "hidden",
          animationDelay: "0.3s"
        }}>
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div className="parent-icon-circle" style={{ width: 32, height: 32 }}>
                <CreditCard size={16} />
              </div>
              <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Kalan Ödeme</span>
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: 2 }}>
              ₺{Number(finances?.total_remaining || 0).toLocaleString("tr-TR")}
            </div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              {invoices.length} kayıt
            </div>
          </div>
        </div>
        )}

        <div className="card parent-stat-card parent-animate-in" style={{ 
          background: "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)", 
          color: "white",
          padding: "16px",
          position: "relative",
          overflow: "hidden",
          animationDelay: "0.4s"
        }}>
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div className="parent-icon-circle" style={{ width: 32, height: 32 }}>
                <Bell size={16} />
              </div>
              <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Son Duyurular</span>
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: 2 }}>
              {Array.isArray(announcements) ? announcements.length : 0}
            </div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              Okul duyuruları
            </div>
          </div>
        </div>

        <div className="card parent-stat-card parent-animate-in" style={{ 
          background: "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)", 
          color: "#2c3e50",
          padding: "16px",
          position: "relative",
          overflow: "hidden",
          animationDelay: "0.5s"
        }}>
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div className="parent-icon-circle" style={{ background: "rgba(44, 62, 80, 0.1)", width: 32, height: 32 }}>
                <FileHeart size={16} style={{ color: "#2c3e50" }} />
              </div>
              <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Haftalık Raporlar</span>
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: 2 }}>
              {Array.isArray(weeklyReports) ? weeklyReports.length : 0}
            </div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              Öğretmen raporları
            </div>
          </div>
        </div>

        {aiRecommendations?.recommendations?.length > 0 && (
          <div className="card parent-animate-in" style={{ 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            color: "white",
            padding: "16px",
            position: "relative",
            overflow: "hidden",
            animationDelay: "0.6s",
            gridColumn: "1 / -1"
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Brain size={20} />
                <span style={{ fontSize: "12px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Kayıt özeti</span>
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700, marginBottom: 8 }}>
                Çocuğunuzun akademik performansı için öneriler
              </div>
              {aiRecommendations.recommendations && aiRecommendations.recommendations.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  {aiRecommendations.recommendations.slice(0, 2).map((rec: string, index: number) => (
                    <div key={index} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8, fontSize: 13 }}>
                      <Lightbulb size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                      <span>{rec}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="card parent-stat-card parent-animate-in" style={{ 
          background: "linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)", 
          color: "#2c3e50",
          padding: "16px",
          position: "relative",
          overflow: "hidden",
          animationDelay: "0.6s"
        }}>
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div className="parent-icon-circle" style={{ background: "rgba(44, 62, 80, 0.1)", width: 32, height: 32 }}>
                <Activity size={16} style={{ color: "#2c3e50" }} />
              </div>
              <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>İletişim Geçmişi</span>
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: 2 }}>
              {Array.isArray(communications) ? communications.length : 0}
            </div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              Mesaj kayıtları
            </div>
          </div>
        </div>

        <div className="card parent-stat-card parent-animate-in" style={{ 
          background: "linear-gradient(135deg, #d299c2 0%, #fef9d7 100%)", 
          color: "#2c3e50",
          padding: "16px",
          position: "relative",
          overflow: "hidden",
          animationDelay: "0.7s"
        }}>
          <div style={{ position: "relative", zIndex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <div className="parent-icon-circle" style={{ background: "rgba(44, 62, 80, 0.1)", width: 32, height: 32 }}>
                <BookOpen size={16} style={{ color: "#2c3e50" }} />
              </div>
              <span style={{ fontSize: "10px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Ödevler</span>
            </div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: 2 }}>
              {Array.isArray(homework) ? homework.length : 0}
            </div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>
              Aktif ödevler
            </div>
          </div>
        </div>
      </div>
    )}

    {/* Children View */}
    {view === "children" && (
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 20 }}>
        <div className="card parent-animate-in" style={{ 
          padding: "24px", 
          background: "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
          border: "none"
        }}>
          <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24, color: "#2c3e50" }}>
            <div style={{ 
              width: 40, 
              height: 40, 
              borderRadius: 10, 
              background: "rgba(44, 62, 80, 0.1)", 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "center" 
            }}>
              <GraduationCap size={20} style={{ color: "#2c3e50" }} />
            </div>
            Günlük Gelişim
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div style={{ 
              display: "flex", 
              justifyContent: "space-between", 
              alignItems: "center", 
              padding: "16px", 
              background: "rgba(255,255,255,0.6)", 
              borderRadius: 12,
              backdropFilter: "blur(10px)"
            }}>
              <span style={{ color: "#546e7a", fontSize: "14px", fontWeight: 600 }}>Sınıf</span>
              <strong style={{ fontSize: "16px", color: "#2c3e50" }}>{String(selected?.class_name || "Henüz atanmadı")}</strong>
            </div>
            <div style={{ 
              display: "flex", 
              justifyContent: "space-between", 
              alignItems: "center", 
              padding: "16px", 
              background: "rgba(255,255,255,0.6)", 
              borderRadius: 12,
              backdropFilter: "blur(10px)"
            }}>
              <span style={{ color: "#546e7a", fontSize: "14px", fontWeight: 600 }}>Ruh Hali</span>
              <strong style={{ fontSize: "16px", color: "#2c3e50" }}>{String(daily?.mood || "Henüz bildirilmedi")}</strong>
            </div>
            <div style={{ 
              display: "flex", 
              justifyContent: "space-between", 
              alignItems: "center", 
              padding: "16px", 
              background: "rgba(255,255,255,0.6)", 
              borderRadius: 12,
              backdropFilter: "blur(10px)"
            }}>
              <span style={{ color: "#546e7a", fontSize: "14px", fontWeight: 600 }}>Yemek</span>
              <strong style={{ fontSize: "16px", color: "#2c3e50" }}>{String(daily?.meal_status || "Henüz bildirilmedi")}</strong>
            </div>
            <div style={{ 
              display: "flex", 
              justifyContent: "space-between", 
              alignItems: "center", 
              padding: "16px", 
              background: "rgba(255,255,255,0.6)", 
              borderRadius: 12,
              backdropFilter: "blur(10px)"
            }}>
              <span style={{ color: "#546e7a", fontSize: "14px", fontWeight: 600 }}>Uyku</span>
              <strong style={{ fontSize: "16px", color: "#2c3e50" }}>{String(daily?.sleep_status || "Henüz bildirilmedi")}</strong>
            </div>
            <div style={{ 
              padding: "16px", 
              background: "rgba(255,255,255,0.6)", 
              borderRadius: 12,
              backdropFilter: "blur(10px)"
            }}>
              <span style={{ color: "#546e7a", fontSize: "14px", fontWeight: 600, display: "block", marginBottom: 8 }}>Etkinlikler</span>
              <strong style={{ fontSize: "16px", color: "#2c3e50" }}>
                {Array.isArray(daily?.activities) ? (daily.activities as unknown[]).join(", ") : String(daily?.activities || "Henüz bildirilmedi")}
              </strong>
            </div>
          </div>
        </div>
        
        {daily?.teacher_notes && (
          <div className="card parent-animate-in" style={{ 
            padding: 24, 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            border: "none",
            color: "white",
            position: "relative",
            overflow: "hidden",
            animationDelay: "0.1s"
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <h3 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, color: "white" }}>
                <div style={{ 
                  width: 40, 
                  height: 40, 
                  borderRadius: 10, 
                  background: "rgba(255,255,255,0.2)", 
                  display: "flex", 
                  alignItems: "center", 
                  justifyContent: "center" 
                }}>
                  <Activity size={20} />
                </div>
                Öğretmen Notu
              </h3>
              <p style={{ margin: 0, lineHeight: 1.8, color: "rgba(255,255,255,0.95)", fontSize: "15px" }}>
                {String(daily.teacher_notes)}
              </p>
            </div>
            <div style={{ 
              position: "absolute", 
              right: -30, 
              bottom: -30, 
              width: 150, 
              height: 150, 
              borderRadius: "50%", 
              background: "rgba(255,255,255,0.1)" 
            }} />
          </div>
        )}
      </div>
    )}

    {/* Attendance View */}
    {view === "attendance" && (
      <>
        <ParentExcuseRequests key={selectedId} studentId={selectedId} />
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 20 }}>
          <div className="card parent-stat-card parent-animate-in" style={{ 
            textAlign: "center", 
            padding: "32px", 
            background: "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)", 
            border: "none",
            color: "white",
            position: "relative",
            overflow: "hidden"
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <div style={{ 
                width: 64, 
                height: 64, 
                borderRadius: 16, 
                background: "rgba(255,255,255,0.2)", 
                display: "flex", 
                alignItems: "center", 
                justifyContent: "center",
                margin: "0 auto 20px"
              }}>
                <CheckCircle size={32} />
              </div>
              <h3 style={{ fontSize: "48px", fontWeight: 700, marginBottom: 8, lineHeight: 1 }}>
                {String(summary?.present || 0)}
              </h3>
              <p style={{ fontSize: "16px", margin: 0, opacity: 0.95, fontWeight: 600 }}>Mevcut (Bu Ay)</p>
            </div>
          </div>
          
          <div className="card parent-stat-card parent-animate-in" style={{ 
            textAlign: "center", 
            padding: "32px", 
            background: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)", 
            border: "none",
            color: "white",
            position: "relative",
            overflow: "hidden",
            animationDelay: "0.1s"
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <div style={{ 
                width: 64, 
                height: 64, 
                borderRadius: 16, 
                background: "rgba(255,255,255,0.2)", 
                display: "flex", 
                alignItems: "center", 
                justifyContent: "center",
                margin: "0 auto 20px"
              }}>
                <Clock size={32} />
              </div>
              <h3 style={{ fontSize: "48px", fontWeight: 700, marginBottom: 8, lineHeight: 1 }}>
                {String(summary?.late || 0)}
              </h3>
              <p style={{ fontSize: "16px", margin: 0, opacity: 0.95, fontWeight: 600 }}>Geç (Bu Ay)</p>
            </div>
          </div>
          
          <div className="card parent-stat-card parent-animate-in" style={{ 
            textAlign: "center", 
            padding: "32px", 
            background: "linear-gradient(135deg, #fa709a 0%, #fee140 100%)", 
            border: "none",
            color: "white",
            position: "relative",
            overflow: "hidden",
            animationDelay: "0.2s"
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <div style={{ 
                width: 64, 
                height: 64, 
                borderRadius: 16, 
                background: "rgba(255,255,255,0.2)", 
                display: "flex", 
                alignItems: "center", 
                justifyContent: "center",
                margin: "0 auto 20px"
              }}>
                <XCircle size={32} />
              </div>
              <h3 style={{ fontSize: "48px", fontWeight: 700, marginBottom: 8, lineHeight: 1 }}>
                {String(summary?.absent || 0)}
              </h3>
              <p style={{ fontSize: "16px", margin: 0, opacity: 0.95, fontWeight: 600 }}>Devamsız (Bu Ay)</p>
            </div>
          </div>
        </div>

        {aiRecommendations?.recommendations?.length > 0 && (
          <div className="card parent-animate-in" style={{ 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            color: "white",
            padding: "16px",
            position: "relative",
            overflow: "hidden",
            marginTop: 20
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Brain size={20} />
                <span style={{ fontSize: "12px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Kayıt özeti</span>
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700, marginBottom: 8 }}>
                Devamsızlık analizi için öneriler
              </div>
              {aiRecommendations.recommendations && aiRecommendations.recommendations.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  {aiRecommendations.recommendations.slice(0, 2).map((rec: string, index: number) => (
                    <div key={index} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8, fontSize: 13 }}>
                      <Lightbulb size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                      <span>{rec}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </>
    )}

    {/* Finances View */}
    {view === "finances" && (
      <>
        <div className="card parent-animate-in" style={{ border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
          <div style={{ 
            padding: "24px", 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            borderRadius: "18px 18px 0 0",
            color: "white"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2 style={{ margin: 0, fontSize: "22px", fontWeight: 700, marginBottom: 8 }}>Ödeme Kayıtları</h2>
                <p style={{ margin: 0, fontSize: "14px", opacity: 0.9 }}>
                  Kalan toplam: <strong style={{ fontSize: "20px", fontWeight: 700 }}>₺{Number(finances?.total_remaining || 0).toLocaleString("tr-TR")}</strong>
                </p>
              </div>
              <div className="parent-icon-circle">
                <CreditCard size={28} />
              </div>
            </div>
          </div>
          {invoices.length ? (
            <div className="table-wrap" style={{ padding: "20px" }}>
              <table className="data-table" style={{ borderCollapse: "separate", borderSpacing: "0 8px" }}>
                <thead>
                  <tr>
                    <th style={{ 
                      padding: "16px", 
                      background: "#f8faf9", 
                      borderRadius: "8px 8px 0 0",
                      color: "#2c3e50",
                      fontWeight: 700,
                      fontSize: "12px",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px"
                    }}>Açıklama</th>
                    <th style={{ 
                      padding: "16px", 
                      background: "#f8faf9", 
                      borderRadius: "8px 8px 0 0",
                      color: "#2c3e50",
                      fontWeight: 700,
                      fontSize: "12px",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px"
                    }}>Vade</th>
                    <th style={{ 
                      padding: "16px", 
                      background: "#f8faf9", 
                      borderRadius: "8px 8px 0 0",
                      color: "#2c3e50",
                      fontWeight: 700,
                      fontSize: "12px",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px"
                    }}>Kalan</th>
                    <th style={{ 
                      padding: "16px", 
                      background: "#f8faf9", 
                      borderRadius: "8px 8px 0 0",
                      color: "#2c3e50",
                      fontWeight: 700,
                      fontSize: "12px",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px"
                    }}>Durum</th>
                    <th style={{ 
                      padding: "16px", 
                      background: "#f8faf9", 
                      borderRadius: "8px 8px 0 0",
                      color: "#2c3e50",
                      fontWeight: 700,
                      fontSize: "12px",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px"
                    }}>İşlem</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice) => (
                    <tr key={invoice.debt_id as string} className="parent-table-row" style={{ 
                      background: "white",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.04)"
                    }}>
                      <td style={{ 
                        padding: "16px", 
                        fontWeight: 600, 
                        color: "#2c3e50",
                        borderRadius: "8px 0 0 8px"
                      }}>{String(invoice.description || invoice.debt_type)}</td>
                      <td style={{ 
                        padding: "16px", 
                        color: "#546e7a",
                        borderRadius: "0"
                      }}>{String(invoice.due_date || "-")}</td>
                      <td style={{ 
                        padding: "16px", 
                        fontWeight: 700, 
                        color: "#e74c3c",
                        fontSize: "15px",
                        borderRadius: "0"
                      }}>₺{Number(invoice.remaining_amount || 0).toLocaleString("tr-TR")}</td>
                      <td style={{ 
                        padding: "16px", 
                        borderRadius: "0"
                      }}><Badge value={invoice.status} /></td>
                      <td style={{ 
                        padding: "16px", 
                        borderRadius: "0 8px 8px 0"
                      }}>
                        {canMakePayment && finances?.online_payment_available && ["UNPAID", "PARTIALLY_PAID", "OVERDUE"].includes(String(invoice.status)) && Number(invoice.remaining_amount || 0) > 0 && (
                          <button 
                            className="btn btn-primary" 
                            style={{ 
                              padding: "10px 20px", 
                              fontSize: "14px",
                              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                              border: "none",
                              borderRadius: 8,
                              fontWeight: 600
                            }}
                            onClick={() => initializePayment(String(invoice.debt_id), Number(invoice.remaining_amount))}
                          >
                            <Wallet size={16} style={{ marginRight: 8 }} />
                            Öde
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="parent-empty-state">
              <div className="parent-empty-icon">
                <CheckCircle size={40} style={{ color: "#2e7d32" }} />
              </div>
              <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Tebrikler!</h3>
              <p style={{ color: "#546e7a", fontSize: "14px" }}>Bekleyen ödeme bulunmuyor.</p>
            </div>
          )}
        </div>

        {aiRecommendations?.recommendations?.length > 0 && (
          <div className="card parent-animate-in" style={{ 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            color: "white",
            padding: "16px",
            position: "relative",
            overflow: "hidden",
            marginTop: 20
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Brain size={20} />
                <span style={{ fontSize: "12px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Kayıt özeti</span>
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700, marginBottom: 8 }}>
                Finansal planlama için öneriler
              </div>
              {aiRecommendations.recommendations && aiRecommendations.recommendations.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  {aiRecommendations.recommendations.slice(0, 2).map((rec: string, index: number) => (
                    <div key={index} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8, fontSize: 13 }}>
                      <Lightbulb size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                      <span>{rec}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </>
    )}

    {/* Health View */}
    {view === "health" && (
      <>
        <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(320px, 0.8fr)", gap: 24 }}>
          <section className="card parent-animate-in" style={{ 
            padding: "24px", 
            background: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)", 
            border: "none",
            color: "white",
            position: "relative",
            overflow: "hidden"
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8, color: "white" }}>
                <div className="parent-icon-circle">
                  <FileHeart size={20} />
                </div>
                İlaç Talimatı
              </h2>
              <p style={{ color: "rgba(255,255,255,0.9)", marginBottom: 24, fontSize: "14px" }}>
                Güncel doz ve saat bilgisini okul ekibiyle paylaşın.
              </p>
              {canSendMedicine && <form className="form-grid" aria-label="İlaç talimatı gönder" onSubmit={submitMedicine} style={{ gap: "16px" }}>
                <label className="field">
                  <span className="field-label" style={{ color: "rgba(255,255,255,0.9)" }}>İlaç Adı</span>
                  <input 
                    required 
                    value={medicine.medicine_name} 
                    maxLength={255}
                    disabled={medicineSubmitting}
                    onChange={(event) => setMedicine({ ...medicine, medicine_name: event.target.value })}
                    placeholder="Örn. Parasetamol"
                    className="parent-input-glass"
                  />
                </label>
                <label className="field">
                  <span className="field-label" style={{ color: "rgba(255,255,255,0.9)" }}>Doz</span>
                  <input 
                    required 
                    placeholder="Örn. 5 ml" 
                    value={medicine.dosage} 
                    maxLength={100}
                    disabled={medicineSubmitting}
                    onChange={(event) => setMedicine({ ...medicine, dosage: event.target.value })}
                    className="parent-input-glass"
                  />
                </label>
                <label className="field">
                  <span className="field-label" style={{ color: "rgba(255,255,255,0.9)" }}>Uygulama Saati</span>
                  <input 
                    required 
                    placeholder="Örn. 13:00" 
                    value={medicine.time_to_give} 
                    maxLength={100}
                    disabled={medicineSubmitting}
                    onChange={(event) => setMedicine({ ...medicine, time_to_give: event.target.value })}
                    className="parent-input-glass"
                  />
                </label>
                <label className="field"><span className="field-label" style={{ color: "rgba(255,255,255,0.9)" }}>İlaç talimatı notu</span><textarea className="parent-input-glass" maxLength={1000} disabled={medicineSubmitting} value={medicine.instructions} onChange={(event) => setMedicine({ ...medicine, instructions: event.target.value })} /></label>
                <div style={{ gridColumn: "1 / -1" }}>
                  <button 
                    className="btn btn-primary" 
                    type="submit" 
                    disabled={medicineSubmitting}
                    style={{ 
                      width: "100%", 
                      background: "white", 
                      color: "#f5576c",
                      fontWeight: 700,
                      padding: "14px"
                    }}
                  >
                    Talimatı Gönder
                  </button>
                </div>
              </form>}
              {requestMessage && (
                <div style={{ 
                  marginTop: 16, 
                  padding: 16, 
                  borderRadius: 12, 
                  background: requestMessage.includes("iletildi") ? "rgba(46, 125, 50, 0.2)" : "rgba(211, 47, 47, 0.2)",
                  color: "white",
                  fontSize: "14px",
                  backdropFilter: "blur(10px)"
                }}>
                  {requestMessage}
                </div>
              )}
            </div>
          </section>
          
          <section className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)", animationDelay: "0.1s" }}>
            <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20, color: "#2c3e50" }}>
              <div style={{ 
                width: 40, 
                height: 40, 
                borderRadius: 10, 
                background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                display: "flex", 
                alignItems: "center", 
                justifyContent: "center" 
              }}>
                <Activity size={20} style={{ color: "white" }} />
              </div>
              Mevcut Talepler
            </h2>
            {medicineRequests.length ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {medicineRequests.map((request, index) => (
                  <div 
                    key={String(request.id || index)}
                    className="parent-request-card"
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                      <strong style={{ fontSize: "18px", color: "#2c3e50", fontWeight: 700 }}>
                        {String(request.medicine_name || "İlaç talimatı")}
                      </strong>
                      <Badge value={request.status || "PENDING"} />
                    </div>
                    <div style={{ display: "flex", gap: 20, fontSize: "14px", color: "#546e7a" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontWeight: 600 }}>Doz:</span>
                        <span>{String(request.dosage || "-")}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontWeight: 600 }}>Saat:</span>
                        <span>{String(request.time_to_give || "-")}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="parent-empty-state">
                <div className="parent-empty-icon">
                  <FileHeart size={40} style={{ color: "#2e7d32" }} />
                </div>
                <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Sağlık Kayıtları</h3>
                <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz sağlık talebi bulunmuyor.</p>
              </div>
            )}
          </section>
        </div>

        {aiRecommendations?.recommendations?.length > 0 && (
          <div className="card parent-animate-in" style={{ 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            color: "white",
            padding: "16px",
            position: "relative",
            overflow: "hidden",
            marginTop: 20
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Brain size={20} />
                <span style={{ fontSize: "12px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Kayıt özeti</span>
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700, marginBottom: 8 }}>
                Sağlık ve gelişim için öneriler
              </div>
              {aiRecommendations.recommendations && aiRecommendations.recommendations.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  {aiRecommendations.recommendations.slice(0, 2).map((rec: string, index: number) => (
                    <div key={index} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8, fontSize: 13 }}>
                      <Lightbulb size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                      <span>{rec}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </>
    )}

    {/* Academic View */}
    {view === "academic" && (
      <>
        <div className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
          <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24, color: "#2c3e50" }}>
            <div style={{ 
              width: 40, 
              height: 40, 
              borderRadius: 10, 
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "center" 
            }}>
              <GraduationCap size={20} style={{ color: "white" }} />
            </div>
            Akademik Performans
          </h2>
          {grades.length ? (
            <div className="table-wrap">
              <table className="data-table" style={{ borderCollapse: "separate", borderSpacing: "0 8px" }}>
                <thead>
                  <tr>
                    <th style={{ padding: "16px", background: "#f8faf9", borderRadius: "8px 8px 0 0", color: "#2c3e50", fontWeight: 700, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Ders</th>
                    <th style={{ padding: "16px", background: "#f8faf9", borderRadius: "8px 8px 0 0", color: "#2c3e50", fontWeight: 700, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Sınav Türü</th>
                    <th style={{ padding: "16px", background: "#f8faf9", borderRadius: "8px 8px 0 0", color: "#2c3e50", fontWeight: 700, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Not / tam puan</th>
                    <th style={{ padding: "16px", background: "#f8faf9", borderRadius: "8px 8px 0 0", color: "#2c3e50", fontWeight: 700, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Tarih</th>
                    <th style={{ padding: "16px", background: "#f8faf9", borderRadius: "8px 8px 0 0", color: "#2c3e50", fontWeight: 700, fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" }}>Durum</th>
                  </tr>
                </thead>
                <tbody>
                  {grades.map((grade, index) => {
                    const ratio = grade.score != null && Number(grade.max_score) > 0 ? Number(grade.score) / Number(grade.max_score) * 100 : null;
                    return <tr key={`${grade.source ?? "GRADE"}:${grade.id ?? index}`} className="parent-table-row" style={{ background: "white", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
                      <td style={{ padding: "16px", fontWeight: 600, color: "#2c3e50", borderRadius: "8px 0 0 8px" }}>{String(grade.subject || "-")}</td>
                      <td style={{ padding: "16px", color: "#546e7a", borderRadius: "0" }}>{String(grade.exam_type || "-")}</td>
                      <td style={{ padding: "16px", fontWeight: 700, color: ratio === null || grade.valid_numeric_score === false ? "#546e7a" : ratio >= 70 ? "#2e7d32" : ratio >= 50 ? "#f57c00" : "#c62828", fontSize: "15px", borderRadius: "0" }}>{grade.score == null ? String(grade.grade_scale ?? "—") : `${grade.score} / ${grade.max_score ?? "—"}`}</td>
                      <td style={{ padding: "16px", color: "#546e7a", borderRadius: "0" }}>{String(grade.exam_date || "-")}</td>
                      <td style={{ padding: "16px", borderRadius: "0 8px 8px 0" }}><Badge value={grade.status || "COMPLETED"} /></td>
                    </tr>;
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="parent-empty-state">
              <div className="parent-empty-icon">
                <GraduationCap size={40} style={{ color: "#2e7d32" }} />
              </div>
              <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Akademik Kayıtlar</h3>
              <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz not bilgisi bulunmuyor.</p>
            </div>
          )}
        </div>

        {aiRecommendations?.recommendations?.length > 0 && (
          <div className="card parent-animate-in" style={{ 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            color: "white",
            padding: "16px",
            position: "relative",
            overflow: "hidden",
            marginTop: 20
          }}>
            <div style={{ position: "relative", zIndex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <Brain size={20} />
                <span style={{ fontSize: "12px", fontWeight: 600, opacity: 0.9, textTransform: "uppercase", letterSpacing: "0.5px" }}>Kayıt özeti</span>
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700, marginBottom: 8 }}>
                Akademik gelişim için öneriler
              </div>
              {aiRecommendations.recommendations && aiRecommendations.recommendations.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  {aiRecommendations.recommendations.slice(0, 2).map((rec: string, index: number) => (
                    <div key={index} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8, fontSize: 13 }}>
                      <Lightbulb size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                      <span>{rec}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </>
    )}

    {/* Schedule View */}
    {view === "schedule" && (
      <div className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24, color: "#2c3e50" }}>
          <div style={{ 
            width: 40, 
            height: 40, 
            borderRadius: 10, 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center" 
          }}>
            <Clock size={20} style={{ color: "white" }} />
          </div>
          Haftalık Ders Programı
        </h2>
        {schedule.length ? (
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
            {schedule.map((day, index) => (
              <div key={index} className="parent-request-card">
                <h3 style={{ fontSize: "16px", fontWeight: 700, color: "#2c3e50", marginBottom: 12 }}>{String(day.day_of_week || "-")}</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {Array.isArray(day.lessons) ? (day.lessons as DataRecord[]).map((lesson, lessonIndex) => (
                    <div key={lessonIndex} style={{ 
                      padding: "12px", 
                      background: "rgba(255,255,255,0.8)", 
                      borderRadius: 8,
                      border: "1px solid #e0e0e0"
                    }}>
                      <div style={{ fontWeight: 600, color: "#2c3e50", marginBottom: 4 }}>{String(lesson.subject || "-")}</div>
                      <div style={{ fontSize: "12px", color: "#546e7a" }}>
                        {String(lesson.start_time || "-")} - {String(lesson.end_time || "-")}
                      </div>
                      <div style={{ fontSize: "12px", color: "#546e7a" }}>{String(lesson.teacher || "-")}</div>
                    </div>
                  )) : <div style={{ fontSize: "14px", color: "#546e7a" }}>Ders bilgisi yok</div>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="parent-empty-state">
            <div className="parent-empty-icon">
              <Clock size={40} style={{ color: "#2e7d32" }} />
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Ders Programı</h3>
            <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz ders programı bilgisi bulunmuyor.</p>
          </div>
        )}
      </div>
    )}

    {/* Homework View */}
    {view === "homework" && (
      <div className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24, color: "#2c3e50" }}>
          <div style={{ 
            width: 40, 
            height: 40, 
            borderRadius: 10, 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center" 
          }}>
            <FileHeart size={20} style={{ color: "white" }} />
          </div>
          Ödevler ve Projeler
        </h2>
        {homework.length ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {homework.map((hw) => (
              <div key={String(hw.id)} className="parent-request-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <strong style={{ fontSize: "18px", color: "#2c3e50", fontWeight: 700 }}>
                    {String(hw.subject || "-")} - {String(hw.title || "-")}
                  </strong>
                  <Badge value={hw.status || "PENDING"} />
                </div>
                <div style={{ fontSize: "14px", color: "#546e7a", marginBottom: 8 }}>{String(hw.description || "-")}</div>
                <div style={{ display: "flex", gap: 20, fontSize: "12px", color: "#546e7a" }}>
                  <span style={{ fontWeight: 600 }}>Teslim Tarihi:</span>
                  <span>{String(hw.due_date || "-")}</span>
                </div>
                <HomeworkSubmissions key={`${selectedId}-${String(hw.id)}`} homeworkId={String(hw.id)} studentId={selectedId} />
              </div>
            ))}
          </div>
        ) : (
          <div className="parent-empty-state">
            <div className="parent-empty-icon">
              <FileHeart size={40} style={{ color: "#2e7d32" }} />
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Ödevler</h3>
            <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz ödev bilgisi bulunmuyor.</p>
          </div>
        )}
      </div>
    )}

    {/* Materials View */}
    {view === "materials" && (
      <div className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24, color: "#2c3e50" }}>
          <div style={{ 
            width: 40, 
            height: 40, 
            borderRadius: 10, 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center" 
          }}>
            <FileHeart size={20} style={{ color: "white" }} />
          </div>
          Ders Materyalleri
        </h2>
        {materialError && <div role="alert"><ErrorState message={materialError} /></div>}
        {materials.length ? (
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
            {materials.map((material, index) => (
              <div key={index} className="parent-request-card">
                <div style={{ fontWeight: 600, color: "#2c3e50", marginBottom: 8 }}>{String(material.title || "-")}</div>
                <div style={{ fontSize: "12px", color: "#546e7a", marginBottom: 8 }}>{String(material.subject || "-")}</div>
                <div style={{ fontSize: "12px", color: "#546e7a" }}>{String(material.type || "-")}</div>
                {material.file_url && (
                  <button
                    type="button"
                    onClick={() => downloadMaterial(material)}
                    disabled={Boolean(downloadingMaterial)}
                    style={{ 
                      display: "inline-block", 
                      marginTop: 12, 
                      padding: "8px 16px", 
                      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                      color: "white", 
                      borderRadius: 8, 
                      fontSize: "12px", 
                      fontWeight: 600,
                      textDecoration: "none"
                    }}
                  >
                    {downloadingMaterial === String(material.id) ? "İndiriliyor…" : "İndir"}
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="parent-empty-state">
            <div className="parent-empty-icon">
              <FileHeart size={40} style={{ color: "#2e7d32" }} />
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Materyaller</h3>
            <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz ders materyali bulunmuyor.</p>
          </div>
        )}
      </div>
    )}

    {/* Communication View */}
    {view === "communication" && (
      <div className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ display: "flex", alignItems: "center", gap: 12, color: "#2c3e50" }}>
            <div style={{ 
              width: 40, 
              height: 40, 
              borderRadius: 10, 
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "center" 
            }}>
              <Activity size={20} style={{ color: "white" }} />
            </div>
            İletişim Geçmişi
          </h2>
          <button 
            className="btn btn-primary"
            onClick={() => setNewMessageOpen(true)}
            style={{ display: "flex", alignItems: "center", gap: 8 }}
          >
            <Activity size={16} />
            Yeni Mesaj
          </button>
        </div>
        
        {communications.length ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {communications.map((comm, index) => (
              <div key={index} className="parent-request-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <strong style={{ fontSize: "16px", color: "#2c3e50", fontWeight: 700 }}>
                    {String(comm.teacher_name || "-")}
                  </strong>
                  <span style={{ fontSize: "12px", color: "#546e7a" }}>{String(comm.date || "-")}</span>
                </div>
                <div style={{ fontSize: "14px", color: "#546e7a", marginBottom: 8 }}>{String(comm.subject || "-")}</div>
                <div style={{ fontSize: "14px", color: "#2c3e50", lineHeight: 1.6 }}>{String(comm.message || "-")}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="parent-empty-state">
            <div className="parent-empty-icon">
              <Activity size={40} style={{ color: "#2e7d32" }} />
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>İletişim Kayıtları</h3>
            <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz iletişim kaydı bulunmuyor.</p>
          </div>
        )}
      </div>
    )}

    {/* New Message Modal */}
    {newMessageOpen && (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}>
        <div style={{
          background: 'white',
          borderRadius: 12,
          maxWidth: 500,
          width: '90%',
          maxHeight: '90vh',
          overflow: 'auto',
          padding: 24
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600 }}>
              Yeni Mesaj Gönder
            </h2>
            <button 
              onClick={() => setNewMessageOpen(false)}
              style={{ 
                background: 'none', 
                border: 'none', 
                fontSize: '24px', 
                cursor: 'pointer',
                color: '#666'
              }}
            >
              ×
            </button>
          </div>
          
          <form onSubmit={submitNewMessage} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 600, color: '#2c3e50' }}>
                Öğretmen Seçin
              </label>
              <select
                required
                value={newMessage.teacher_id}
                onChange={(e) => setNewMessage({ ...newMessage, teacher_id: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: 8,
                  border: '1px solid #e0e0e0',
                  fontSize: '14px'
                }}
              >
                <option value="">Öğretmen seçin...</option>
                {teachers.map((teacher) => (
                  <option key={String(teacher.id)} value={String(teacher.id)}>
                    {String(teacher.first_name)} {String(teacher.last_name)} - {String(teacher.subject || "-")}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 600, color: '#2c3e50' }}>
                Konu
              </label>
              <input
                required
                type="text"
                value={newMessage.subject}
                onChange={(e) => setNewMessage({ ...newMessage, subject: e.target.value })}
                placeholder="Mesaj konusu"
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: 8,
                  border: '1px solid #e0e0e0',
                  fontSize: '14px'
                }}
              />
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontWeight: 600, color: '#2c3e50' }}>
                Mesaj
              </label>
              <textarea
                required
                value={newMessage.message}
                onChange={(e) => setNewMessage({ ...newMessage, message: e.target.value })}
                placeholder="Mesajınızı yazın..."
                rows={4}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: 8,
                  border: '1px solid #e0e0e0',
                  fontSize: '14px',
                  resize: 'vertical'
                }}
              />
            </div>
            
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={() => setNewMessageOpen(false)}
                style={{
                  padding: '12px 24px',
                  borderRadius: 8,
                  border: '1px solid #e0e0e0',
                  background: 'white',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 600
                }}
              >
                İptal
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                style={{
                  padding: '12px 24px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 600
                }}
              >
                Gönder
              </button>
            </div>
          </form>
          
          {requestMessage && (
            <div style={{ 
              marginTop: 16, 
              padding: 12, 
              borderRadius: 8, 
              background: requestMessage.includes("başarıyla") ? "#e8f5e9" : "#fff0ef",
              color: requestMessage.includes("başarıyla") ? "#2e7d32" : "#c34b4b",
              fontSize: "14px"
            }}>
              {requestMessage}
            </div>
          )}
        </div>
      </div>
    )}

    {/* Announcements View */}
    {view === "announcements" && (
      <div className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24, color: "#2c3e50" }}>
          <div style={{ 
            width: 40, 
            height: 40, 
            borderRadius: 10, 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center" 
          }}>
            <Activity size={20} style={{ color: "white" }} />
          </div>
          Okul Duyuruları
        </h2>
        {announcements.length ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {announcements.map((announcement, index) => (
              <div key={index} className="parent-request-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <strong style={{ fontSize: "18px", color: "#2c3e50", fontWeight: 700 }}>
                    {String(announcement.title || "-")}
                  </strong>
                  <span style={{ fontSize: "12px", color: "#546e7a" }}>{String(announcement.date || "-")}</span>
                </div>
                <div style={{ fontSize: "14px", color: "#546e7a", marginBottom: 8 }}>{String(announcement.category || "-")}</div>
                <div style={{ fontSize: "14px", color: "#2c3e50", lineHeight: 1.6 }}>{String(announcement.content || "-")}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="parent-empty-state">
            <div className="parent-empty-icon">
              <Activity size={40} style={{ color: "#2e7d32" }} />
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Duyurular</h3>
            <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz duyuru bulunmuyor.</p>
          </div>
        )}
      </div>
    )}

    {/* Activities View */}
    {view === "activities" && (
      <div className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24, color: "#2c3e50" }}>
          <div style={{ 
            width: 40, 
            height: 40, 
            borderRadius: 10, 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center" 
          }}>
            <UsersRound size={20} style={{ color: "white" }} />
          </div>
          Kulüp ve Aktiviteler
        </h2>
        {activities.length ? (
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
            {activities.map((activity, index) => (
              <div key={index} className="parent-request-card">
                <div style={{ fontWeight: 600, color: "#2c3e50", marginBottom: 8 }}>{String(activity.name || "-")}</div>
                <div style={{ fontSize: "12px", color: "#546e7a", marginBottom: 8 }}>{String(activity.type || "-")}</div>
                <div style={{ fontSize: "12px", color: "#546e7a", marginBottom: 8 }}>
                  <span style={{ fontWeight: 600 }}>Gün:</span> {String(activity.day || "-")}
                </div>
                <div style={{ fontSize: "12px", color: "#546e7a" }}>
                  <span style={{ fontWeight: 600 }}>Saat:</span> {String(activity.time || "-")}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="parent-empty-state">
            <div className="parent-empty-icon">
              <UsersRound size={40} style={{ color: "#2e7d32" }} />
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Aktiviteler</h3>
            <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz aktivite bilgisi bulunmuyor.</p>
          </div>
        )}
      </div>
    )}

    {/* Reports View */}
    {view === "reports" && (
      <div className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
        <h2 style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24, color: "#2c3e50" }}>
          <div style={{ 
            width: 40, 
            height: 40, 
            borderRadius: 10, 
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center" 
          }}>
            <FileHeart size={20} style={{ color: "white" }} />
          </div>
          Haftalık Raporlar
        </h2>
        {weeklyReports.length ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {weeklyReports.map((report, index) => (
              <div key={index} className="parent-request-card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <strong style={{ fontSize: "18px", color: "#2c3e50", fontWeight: 700 }}>
                    {String(report.week_title || "-")}
                  </strong>
                  <span style={{ fontSize: "12px", color: "#546e7a" }}>{String(report.report_date || "-")}</span>
                </div>
                <div style={{ fontSize: "14px", color: "#546e7a", marginBottom: 8 }}>
                  <span style={{ fontWeight: 600 }}>Öğretmen:</span> {String(report.teacher_name || "-")}
                </div>
                <div style={{ fontSize: "14px", color: "#2c3e50", lineHeight: 1.6, marginBottom: 12 }}>
                  {String(report.summary || "-")}
                </div>
                <div style={{ display: "flex", gap: 12, fontSize: "12px", color: "#546e7a" }}>
                  <span style={{ fontWeight: 600 }}>Davranış:</span>
                  <span>{String(report.behavior || "-")}</span>
                </div>
                <div style={{ display: "flex", gap: 12, fontSize: "12px", color: "#546e7a" }}>
                  <span style={{ fontWeight: 600 }}>Sosyal:</span>
                  <span>{String(report.social || "-")}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="parent-empty-state">
            <div className="parent-empty-icon">
              <FileHeart size={40} style={{ color: "#2e7d32" }} />
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Haftalık Raporlar</h3>
            <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz haftalık rapor bulunmuyor.</p>
          </div>
        )}
      </div>
    )}
    
    {/* Chat View */}
    {view === "chat" && (
      <div className="card parent-animate-in" style={{ padding: "24px", border: "none", boxShadow: "0 8px 30px rgba(0,0,0,0.08)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ display: "flex", alignItems: "center", gap: 12, color: "#2c3e50" }}>
            <div style={{ 
              width: 40, 
              height: 40, 
              borderRadius: 10, 
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "center" 
            }}>
              <MessageCircle size={20} style={{ color: "white" }} />
            </div>
            Öğretmenler
          </h2>
        </div>
        
        {teachers.length ? (
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
            {teachers.map((teacher) => (
              <div key={String(teacher.id)} className="parent-request-card" style={{ 
                padding: "20px",
                cursor: "pointer",
                transition: "transform 0.2s, box-shadow 0.2s"
              }}
              onClick={() => {
                setChatTeacherId(String(teacher.id));
                setChatTeacherName(`${String(teacher.first_name)} ${String(teacher.last_name)}`);
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.1)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
                e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.04)";
              }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                  <div style={{ 
                    width: 48, 
                    height: 48, 
                    borderRadius: "50%", 
                    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                    display: "flex", 
                    alignItems: "center", 
                    justifyContent: "center",
                    color: "white",
                    fontWeight: 600,
                    fontSize: "18px"
                  }}>
                    {String(teacher.first_name)[0]}{String(teacher.last_name)[0]}
                  </div>
                  <div>
                    <div style={{ fontWeight: 600, color: "#2c3e50", fontSize: "16px" }}>
                      {String(teacher.first_name)} {String(teacher.last_name)}
                    </div>
                    <div style={{ fontSize: "12px", color: "#546e7a" }}>
                      {String(teacher.subject || "-")}
                    </div>
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  style={{
                    width: "100%",
                    padding: "10px",
                    fontSize: "14px",
                    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    border: "none",
                    borderRadius: 8,
                    fontWeight: 600
                  }}
                >
                  Mesaj Gönder
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="parent-empty-state">
            <div className="parent-empty-icon">
              <MessageCircle size={40} style={{ color: "#2e7d32" }} />
            </div>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#2c3e50", marginBottom: 8 }}>Öğretmenler</h3>
            <p style={{ color: "#546e7a", fontSize: "14px" }}>Henüz öğretmen bilgisi bulunmuyor.</p>
          </div>
        )}
      </div>
    )}

    {/* Chat Interface - Bottom Right Popup */}
    {chatTeacherId && (
      <div style={{ 
        position: "fixed", 
        bottom: 16,
        right: 16,
        width: "min(380px, calc(100vw - 32px))",
        height: "min(500px, calc(100dvh - 32px))",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
        borderRadius: 12,
        overflow: "hidden",
        background: "white"
      }}>
        <ChatInterface
          key={`${selectedId}-${chatTeacherId}`}
          studentId={selectedId}
          teacherId={chatTeacherId}
          teacherName={chatTeacherName}
          onBack={() => {
            setChatTeacherId("");
            setChatTeacherName("");
          }}
        />
      </div>
    )}

    {/* Payment Modal */}
    {paymentModal && <ParentSchoolCheckout debtId={paymentModal.debtId} amount={paymentModal.amount} childName={paymentModal.childName}
      available={Boolean(finances?.online_payment_available) && canMakePayment} onClose={closePaymentModal} onComplete={refreshPaymentFinances} />}

  </>;
}
