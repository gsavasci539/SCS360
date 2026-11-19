import { getAnalysis } from "../../lib/analysis";
import { CalendarCheck2, ChevronRight, CreditCard, GraduationCap, ReceiptText, UserPlus, UsersRound, WalletCards, Bell, BookOpen, ClipboardCheck, MessageCircle, Brain, TrendingUp, AlertTriangle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorState, LoadingState, Modal, PageHeader, StatCard, Tabs } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { money } from "../../lib/format";
import { hasPermission, useAuthStore } from "../../stores/auth";
import { StaffStudentChat } from "../parent/StaffStudentChat";
import { ExcuseReviewPanel } from "../communications/ExcuseRequests";
import type { ApiResponse } from "../../types/api";

interface Summary { total_students?: number; active_students?: number; total_branches?: number; total_classes?: number; absent_today?: number; monthly_payments?: string | number; pending_debt?: string | number; overdue_debt?: string | number }
interface Charts { monthly_income?: Array<{ month?: string; label?: string; amount?: number; income?: number }>; income?: Array<{ month?: string; amount?: number }> }

const fallbackChart: Array<{ month: string; amount: number }> = [];

export function DashboardPage() {
  const [summary, setSummary] = useState<Summary>({}); const [chart, setChart] = useState(fallbackChart); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [aiInsights, setAiInsights] = useState<any>(null);
  const user = useAuthStore((state) => state.user);
  const can = useAuthStore((state) => state.can);
  const isTeacher = user?.roles?.some((r) => r.slug === "teacher1" || r.slug === "teacher2" || r.slug === "teacher3") || false;
  
  const [activeTab, setActiveTab] = useState("overview");

  async function load() {
    setLoading(true); setError("");
    try {
      const [summaryResult, chartResult, aiResult] = await Promise.allSettled([api.get<ApiResponse<Summary>>("/dashboard/summary"), api.get<ApiResponse<Charts>>("/dashboard/charts"), getAnalysis("/ai/insights-report").catch(() => null)]);
      if (summaryResult.status === "fulfilled") setSummary(summaryResult.value.data.data || {}); else {
        const overview = await api.get<ApiResponse<Summary>>("/dashboard/overview"); setSummary(overview.data.data || {});
      }
      if (chartResult.status === "fulfilled") {
        const rows = chartResult.value.data.data?.monthly_income || chartResult.value.data.data?.income || [];
        setChart(rows.map((row: { month?: string; label?: string; amount?: number; income?: number }) => ({ month: row.month || row.label || "", amount: Number(row.amount ?? row.income ?? 0) })));
      }
      if (aiResult.status === "fulfilled" && aiResult.value) setAiInsights(aiResult.value.data.data);
    } catch (err) { setError(apiMessage(err)); } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);
  if (loading) return <div className="card"><LoadingState label="Günün özeti hazırlanıyor" /></div>;
  
  if (isTeacher) {
    return <TeacherDashboard summary={summary} error={error} load={load} />;
  }
  
  return (
    <>
      <PageHeader 
        eyebrow="Günlük görünüm" 
        title="Günaydın, yönetim merkezi hazır." 
        description="Kurumunuzdaki önemli gelişmeler ve hızlı aksiyonlar tek bakışta burada." 
      >
        {can("students.write") && <Link to="/students/new" className="btn btn-primary">
          <UserPlus size={16} />Yeni öğrenci
        </Link>}
      </PageHeader>
      {can("students.write") && can("branch.read") && can("dashboard.view") && <ExcuseReviewPanel />}
      {error && (
        <div className="card" style={{ marginBottom: 18 }}>
          <ErrorState message={error} retry={load} />
        </div>
      )}
      {aiInsights && (
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="card-head">
            <div>
              <h2>AI Insights</h2>
              <p>Yapay zeka destekli öncelikli aksiyonlar</p>
            </div>
            <Brain size={20} color="#176b5b" />
          </div>
          <div className="card-pad">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <GraduationCap size={16} color="#176b5b" />
                  <div style={{ fontSize: 11, color: "#6e7b7d", fontWeight: 600 }}>Akademik</div>
                </div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e", marginBottom: 4 }}>
                  {aiInsights.insights?.academic_performance?.overall_trend || "Veri yok"}
                </div>
                <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                  {aiInsights.insights?.academic_performance?.at_risk_students || 0} risk öğrenci
                </div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <CalendarCheck2 size={16} color="#16a34a" />
                  <div style={{ fontSize: 11, color: "#6e7b7d", fontWeight: 600 }}>Devamsızlık</div>
                </div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e", marginBottom: 4 }}>
                  %{aiInsights.insights?.attendance?.overall_rate || 0}
                </div>
                <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                  {aiInsights.insights?.attendance?.trend || "Veri yok"}
                </div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <WalletCards size={16} color="#dc2626" />
                  <div style={{ fontSize: 11, color: "#6e7b7d", fontWeight: 600 }}>Finansal</div>
                </div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e", marginBottom: 4 }}>
                  %{aiInsights.insights?.financial?.collection_rate || 0}
                </div>
                <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                  {aiInsights.insights?.financial?.forecast_trend || "Veri yok"}
                </div>
              </div>
              <div style={{ padding: 12, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                  <MessageCircle size={16} color="#f59e0b" />
                  <div style={{ fontSize: 11, color: "#6e7b7d", fontWeight: 600 }}>Veli</div>
                </div>
                <div style={{ fontSize: 18, fontWeight: 700, color: "#1b2b2e", marginBottom: 4 }}>
                  {aiInsights.insights?.parent_satisfaction?.score || "Veri yok"}
                </div>
                <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                  {aiInsights.insights?.parent_satisfaction?.sentiment || "Veri yok"}
                </div>
              </div>
            </div>
            {aiInsights.priority_actions && aiInsights.priority_actions.length > 0 && 
              aiInsights.priority_actions.slice(0, 3).map((action: string, index: number) => (
                <div 
                  key={index} 
                  style={{ 
                    display: "flex", 
                    alignItems: "center", 
                    gap: 12, 
                    padding: 14, 
                    borderRadius: 11, 
                    background: index === 0 ? "#fff3cd" : "#f8faf8", 
                    marginBottom: 8, 
                    border: index === 0 ? "1px solid #ffc107" : "none" 
                  }}
                >
                  {index === 0 ? <AlertTriangle size={18} color="#856404" /> : <TrendingUp size={18} color="#176b5b" />}
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{action}</span>
                </div>
              ))
            }
            {!aiInsights.priority_actions || aiInsights.priority_actions.length === 0 && (
              <div style={{ padding: 12, borderRadius: 8, background: "#f0fdf4", border: "1px solid #16a34a" }}>
                <span style={{ fontSize: 13, color: "#16a34a" }}>Tüm göstergeler normal seviyede</span>
              </div>
            )}
            <Link className="btn btn-ghost" to="/ai-analytics" style={{ marginTop: 12 }}>
              Tüm AI analizlerini gör <ChevronRight size={14} />
            </Link>
          </div>
        </div>
      )}
      <div className="card">
        <Tabs 
          activeTab={activeTab} 
          onTabChange={setActiveTab} 
          tabs={[
            { id: "overview", label: "Genel Bakış" }, 
            { id: "chat", label: "Mesajlar" }
          ]} 
        />
        {activeTab === "overview" && (
          <div className="tab-content">
            <div className="grid stats-grid">
              <StatCard 
                icon={<UsersRound size={19} />} 
                label="Aktif öğrenci" 
                value={summary.active_students ?? summary.total_students ?? 0} 
                change="Bu dönem" 
                meta={`${summary.total_students ?? 0} toplam kayıt`} 
              />
              <StatCard 
                icon={<WalletCards size={19} />} 
                label="Bu ay tahsilat" 
                value={money(summary.monthly_payments)} 
                meta="Onaylanmış ödemeler" 
                color="blue" 
              />
              <StatCard 
                icon={<CalendarCheck2 size={19} />} 
                label="Bugün devamsız" 
                value={summary.absent_today ?? 0} 
                meta="Yoklama kayıtlarına göre" 
                color="orange" 
              />
              <StatCard 
                icon={<CreditCard size={19} />} 
                label="Geciken borç" 
                value={money(summary.overdue_debt)} 
                meta={`${money(summary.pending_debt)} toplam bekleyen`} 
                color="red" 
              />
            </div>
            <div className="grid dashboard-grid">
              <section className="card">
                <div className="card-head">
                  <div>
                    <h2>Aylık tahsilat akışı</h2>
                    <p>Son altı ayın tamamlanan ödemeleri</p>
                  </div>
                  <Link className="btn btn-ghost" to="/reports">Raporu aç <ChevronRight size={14} /></Link>
                </div>
                <div className="chart-box">
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={chart} margin={{ top: 12, right: 12, left: 5, bottom: 0 }}>
                      <defs>
                        <linearGradient id="income" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#2d8f78" stopOpacity={.32} />
                          <stop offset="95%" stopColor="#2d8f78" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                      <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#6b7280" }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#6b7280" }} />
                      <Tooltip contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} />
                      <Area type="monotone" dataKey="amount" stroke="#2d8f78" strokeWidth={2} fillOpacity={1} fill="url(#income)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </section>
              <section className="card">
                <div className="card-head">
                  <div>
                    <h2>Hızlı aksiyonlar</h2>
                    <p>Sık kullanılan işlemler için kısayollar</p>
                  </div>
                </div>
                <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
                  <Quick to="/attendance" icon={<CalendarCheck2 size={24} />} title="Yoklama Al" caption="Günlük yoklama kaydı" />
                  <Quick to="/finance/payments" icon={<WalletCards size={24} />} title="Ödemeler" caption="Tahsilat ve borç yönetimi" />
                  <Quick to="/announcements" icon={<Bell size={24} />} title="Duyurular" caption="Okul duyuruları ve bildirimler" />
                  <Quick to="/reports" icon={<ReceiptText size={24} />} title="Raporlar" caption="Detaylı analiz ve istatistikler" />
                </div>
              </section>
            </div>
          </div>
        )}
        {activeTab === "chat" && (
          <div className="tab-content"><StaffStudentChat area="/admin" /></div>
        )}
      </div>
    </>
  );
}

function TeacherDashboard({ summary, error, load }: { summary: Summary; error: string; load: () => void }) {
  const totalStudents = summary?.total_students ?? 0;
  const activeStudents = summary?.active_students ?? 0;
  const absentToday = summary?.absent_today ?? 0;
  const totalClasses = summary?.total_classes ?? 0;
  
  const canOpenChat = useAuthStore((state) =>
    hasPermission(state.user, "messaging.read") && hasPermission(state.user, "students.read"));
  const [showQuickChat, setShowQuickChat] = useState(false);
  const closeQuickChat = useCallback(() => setShowQuickChat(false), []);

  return (
    <>
      <PageHeader 
        eyebrow="Öğretmen paneli" 
        title="Günaydın, öğretmen paneli hazır." 
        description="Sınıfınız, öğrencileriniz ve günlük aktiviteleriniz tek bakışta burada." 
      >
        <Link to="/attendance" className="btn btn-primary"><CalendarCheck2 size={16} />Yoklama Al</Link>
      </PageHeader>
      {error && <div className="card" style={{ marginBottom: 18 }}><ErrorState message={error} retry={load} /></div>}
      <div className="grid stats-grid">
        <StatCard icon={<UsersRound size={19} />} label="Sınıf öğrencisi" value={activeStudents} change="Bu dönem" meta={`${totalStudents} toplam kayıt`} />
        <StatCard icon={<ClipboardCheck size={19} />} label="Bugün devamsız" value={absentToday} meta="Yoklama kayıtlarına göre" color="orange" />
        <StatCard icon={<BookOpen size={19} />} label="Sınıflar" value={totalClasses} meta="Atanmış sınıflarınız" color="blue" />
        <StatCard icon={<Bell size={19} />} label="Bildirimler" value={0} meta="Yeni bildirimler" color="blue" />
      </div>
      <div className="grid dashboard-grid">
        <section className="card">
          <div className="card-head">
            <div>
              <h2>Hızlı işlemler</h2>
              <p>Günlük öğretmen aktiviteleri</p>
            </div>
          </div>
          <div className="quick-actions">
            <Quick to="/attendance" icon={<CalendarCheck2 size={20} />} title="Yoklama" caption="Sınıf yoklaması al" />
            <Quick to="/students" icon={<GraduationCap size={20} />} title="Öğrenciler" caption="Öğrenci listesi" />
            <Quick to="/announcements/new" icon={<Bell size={20} />} title="Duyuru" caption="Velilere duyuru" />
            <Quick to="/reports" icon={<ReceiptText size={20} />} title="Raporlar" caption="Günlük raporlar" />
          </div>
        </section>
        <section className="card">
          <div className="card-head">
            <div>
              <h2>Sınıf durumu</h2>
              <p>Öğrenci aktivite özeti</p>
            </div>
          </div>
          <div className="class-status">
            <div className="status-item">
              <div className="status-label">Toplam öğrenci</div>
              <div className="status-value">{totalStudents}</div>
            </div>
            <div className="status-item">
              <div className="status-label">Bugün devamsız</div>
              <div className="status-value absent">{absentToday}</div>
            </div>
            <div className="status-item">
              <div className="status-label">Katılım oranı</div>
              <div className="status-value success">
                {totalStudents > 0 
                  ? Math.round(((totalStudents - absentToday) / totalStudents) * 100) 
                  : 0}%
              </div>
            </div>
          </div>
        </section>
      </div>

      {canOpenChat && (
        <>
          <button type="button" className="btn btn-primary" aria-haspopup="dialog"
            style={{ position: "fixed", insetInlineEnd: "1.25rem", bottom: "1.25rem", zIndex: 900,
              maxWidth: "calc(100% - 2.5rem)", whiteSpace: "normal" }}
            onClick={() => setShowQuickChat(true)}>
            <MessageCircle size={20} aria-hidden="true" /> Hızlı mesaj
          </button>
          <Modal open={showQuickChat} title="Hızlı mesaj" onClose={closeQuickChat}>
            <StaffStudentChat area="/teacher" />
          </Modal>
        </>
      )}
    </>
  );
}

function Quick({ to, icon, title, caption }: { to: string; icon: React.ReactNode; title: string; caption: string }) {
  const permission = ({ "/attendance": "attendance.read", "/students": "students.read", "/finance/payments": "finance.read", "/finance/payments/new": "finance.write", "/announcements": "announcement.read", "/announcements/new": "announcement.write", "/finance/receipts": "receipt.read", "/reports": "report.read" } as Record<string, string>)[to];
  const allowed = useAuthStore((state) => state.can(permission));
  return allowed ? <Link className="quick-item" to={to}><div className="quick-icon">{icon}</div><div className="quick-copy"><strong>{title}</strong><span>{caption}</span></div><ChevronRight size={15} color="#91a09f" /></Link> : null;
}
