import { CalendarCheck2, ChevronRight, CreditCard, GraduationCap, ReceiptText, UserPlus, UsersRound, WalletCards, Bell, BookOpen, ClipboardCheck, MessageCircle, X, Send, Brain, TrendingUp, AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorState, LoadingState, PageHeader, StatCard, Tabs } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { money } from "../../lib/format";
import { useAuthStore } from "../../stores/auth";
import { ChatInterface } from "../parent/ChatInterface";
import type { ApiResponse } from "../../types/api";

interface Summary { total_students?: number; active_students?: number; total_branches?: number; total_classes?: number; absent_today?: number; monthly_payments?: string | number; pending_debt?: string | number; overdue_debt?: string | number }
interface Charts { monthly_income?: Array<{ month?: string; label?: string; amount?: number; income?: number }>; income?: Array<{ month?: string; amount?: number }> }

interface StudentWithParent {
  student_id: string;
  student_name: string;
  class_name: string;
  parent_id: string;
  parent_name: string;
  is_primary: boolean;
}

const fallbackChart = [{ month: "Oca", amount: 210000 }, { month: "Şub", amount: 245000 }, { month: "Mar", amount: 228000 }, { month: "Nis", amount: 306000 }, { month: "May", amount: 334000 }, { month: "Haz", amount: 382000 }];

export function DashboardPage() {
  const [summary, setSummary] = useState<Summary>({}); const [chart, setChart] = useState(fallbackChart); const [loading, setLoading] = useState(true); const [error, setError] = useState(""); const [aiInsights, setAiInsights] = useState<any>(null);
  const user = useAuthStore((state) => state.user);
  const isTeacher = user?.roles?.some((r: any) => r.slug === "teacher1" || r.slug === "teacher2" || r.slug === "teacher3") || false;
  
  // Admin chat state
  const [activeTab, setActiveTab] = useState("overview");
  const [students, setStudents] = useState<StudentWithParent[]>([]);
  const [chatStudentId, setChatStudentId] = useState<string>("");
  const [chatParentName, setChatParentName] = useState<string>("");
  const [studentsLoading, setStudentsLoading] = useState(false);
  
  async function load() {
    setLoading(true); setError("");
    try {
      const [summaryResult, chartResult, aiResult] = await Promise.allSettled([api.get<ApiResponse<Summary>>("/dashboard/summary"), api.get<ApiResponse<Charts>>("/dashboard/charts"), api.get("/ai/insights-report").catch(() => null)]);
      if (summaryResult.status === "fulfilled") setSummary(summaryResult.value.data.data || {}); else {
        const overview = await api.get<ApiResponse<Summary>>("/dashboard/overview"); setSummary(overview.data.data || {});
      }
      if (chartResult.status === "fulfilled") {
        const rows = chartResult.value.data.data?.monthly_income || chartResult.value.data.data?.income || [];
        if (rows.length) setChart(rows.map((row: { month?: string; label?: string; amount?: number; income?: number }) => ({ month: row.month || row.label || "", amount: Number(row.amount ?? row.income ?? 0) })));
      }
      if (aiResult.status === "fulfilled" && aiResult.value) setAiInsights(aiResult.value.data.data);
    } catch (err) { setError(apiMessage(err)); } finally { setLoading(false); }
  }

  const loadStudents = async () => {
    setStudentsLoading(true);
    try {
      const result = await api.get<ApiResponse<StudentWithParent[]>>("/admin/students");
      setStudents(result.data.data || []);
    } catch (err) {
      console.error("Failed to load students:", err);
    } finally {
      setStudentsLoading(false);
    }
  };

  const openChat = (studentId: string, parentName: string) => {
    setChatStudentId(studentId);
    setChatParentName(parentName);
  };

  useEffect(() => { load(); }, []);
  useEffect(() => { if (activeTab === "chat") loadStudents(); }, [activeTab]);
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
        <Link to="/students/new" className="btn btn-primary">
          <UserPlus size={16} />Yeni öğrenci
        </Link>
      </PageHeader>
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
                  <Link to="/attendance" className="card" style={{ padding: 20, textDecoration: "none", color: "inherit", display: "flex", alignItems: "center", gap: 12, transition: "transform 0.2s" }} onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-4px)"} onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}><div style={{ width: 48, height: 48, borderRadius: 12, background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}><CalendarCheck2 size={24} /></div><div><div style={{ fontWeight: 600, marginBottom: 4 }}>Yoklama Al</div><div style={{ fontSize: 12, color: "#666" }}>Günlük yoklama kaydı</div></div></Link>
                  <Link to="/finance" className="card" style={{ padding: 20, textDecoration: "none", color: "inherit", display: "flex", alignItems: "center", gap: 12, transition: "transform 0.2s" }} onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-4px)"} onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}><div style={{ width: 48, height: 48, borderRadius: 12, background: "linear-gradient(135deg, #11998e 0%, #38ef7d 100%)", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}><WalletCards size={24} /></div><div><div style={{ fontWeight: 600, marginBottom: 4 }}>Ödemeler</div><div style={{ fontSize: 12, color: "#666" }}>Tahsilat ve borç yönetimi</div></div></Link>
                  <Link to="/communications" className="card" style={{ padding: 20, textDecoration: "none", color: "inherit", display: "flex", alignItems: "center", gap: 12, transition: "transform 0.2s" }} onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-4px)"} onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}><div style={{ width: 48, height: 48, borderRadius: 12, background: "linear-gradient(135deg, #fa709a 0%, #fee140 100%)", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}><Bell size={24} /></div><div><div style={{ fontWeight: 600, marginBottom: 4 }}>Duyurular</div><div style={{ fontSize: 12, color: "#666" }}>Okul duyuruları ve bildirimler</div></div></Link>
                  <Link to="/reports" className="card" style={{ padding: 20, textDecoration: "none", color: "inherit", display: "flex", alignItems: "center", gap: 12, transition: "transform 0.2s" }} onMouseEnter={(e) => e.currentTarget.style.transform = "translateY(-4px)"} onMouseLeave={(e) => e.currentTarget.style.transform = "translateY(0)"}><div style={{ width: 48, height: 48, borderRadius: 12, background: "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}><ReceiptText size={24} /></div><div><div style={{ fontWeight: 600, marginBottom: 4 }}>Raporlar</div><div style={{ fontSize: 12, color: "#666" }}>Detaylı analiz ve istatistikler</div></div></Link>
                </div>
              </section>
            </div>
          </div>
        )}
        {activeTab === "chat" && (
          <div className="tab-content">
            {chatStudentId ? (
              <ChatInterface studentId={chatStudentId} teacherName={chatParentName} onBack={() => { setChatStudentId(""); setChatParentName(""); }} apiBase="/admin" />
            ) : (
              <div>
                {studentsLoading ? (
                  <LoadingState label="Öğrenciler yükleniyor..." />
                ) : (
                  <>
                    <h3 style={{ marginBottom: 16 }}>Öğrenciler ve Veliler</h3>
                    <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16 }}>
                      {students.map((student) => (
                        <div key={student.student_id} className="card" style={{ padding: 16, cursor: "pointer" }} onClick={() => openChat(student.student_id, student.parent_name)}>
                          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                            <div style={{ width: 40, height: 40, borderRadius: "50%", background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 600 }}>{student.student_name[0]}</div>
                            <div>
                              <div style={{ fontWeight: 600 }}>{student.student_name}</div>
                              <div style={{ fontSize: 12, color: "#666" }}>{student.class_name} - {student.parent_name}</div>
                            </div>
                          </div>
                          <button className="btn btn-primary" style={{ width: "100%", padding: 8, fontSize: 14 }}>
                            <MessageCircle size={16} style={{ marginRight: 8 }} />Mesaj Gönder
                          </button>
                        </div>
                      ))}
                    </div>
                    {students.length === 0 && (
                      <div style={{ textAlign: "center", padding: 40, color: "#666" }}>Öğrenci bulunamadı</div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
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
  
  // Chat widget state
  const [showQuickChat, setShowQuickChat] = useState(false);
  const [chatCategory, setChatCategory] = useState<'parents' | 'class' | 'admin'>('parents');
  const [selectedRecipient, setSelectedRecipient] = useState<string>('');
  const [messageInput, setMessageInput] = useState('');
  const [sending, setSending] = useState(false);
  const [users, setUsers] = useState<any[]>([]);
  const [students, setStudents] = useState<any[]>([]);
  const [loadingContacts, setLoadingContacts] = useState(false);

  const loadContacts = async () => {
    setLoadingContacts(true);
    try {
      // Load users (for admin category)
      const usersResult = await api.get<ApiResponse<any[]>>("/users");
      setUsers(usersResult.data.data || []);
      
      // Load students (for parents/class categories)
      const studentsResult = await api.get<ApiResponse<any[]>>("/students");
      setStudents(studentsResult.data.data || []);
    } catch (err) {
      console.error("Failed to load contacts:", err);
    } finally {
      setLoadingContacts(false);
    }
  };

  useEffect(() => {
    if (showQuickChat) {
      loadContacts();
    }
  }, [showQuickChat]);
  
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

      {/* Quick Chat Widget - Fixed Bottom Right */}
      {showQuickChat && (
        <div style={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          width: 380,
          maxHeight: 500,
          background: 'white',
          borderRadius: 12,
          boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
          zIndex: 1000,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{
            padding: 16,
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            borderRadius: '12px 12px 0 0',
            color: 'white'
          }}>
            <div style={{ fontWeight: 600 }}>Hızlı Mesaj</div>
            <button
              onClick={() => setShowQuickChat(false)}
              style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer' }}
            >
              <X size={20} />
            </button>
          </div>
          <div style={{ padding: 12, borderBottom: '1px solid #e5e7eb' }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setChatCategory('parents')}
                style={{
                  flex: 1,
                  padding: 8,
                  border: chatCategory === 'parents' ? '2px solid #667eea' : '1px solid #e5e7eb',
                  borderRadius: 6,
                  background: chatCategory === 'parents' ? '#f0f4ff' : 'white',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: chatCategory === 'parents' ? 600 : 400
                }}
              >
                Veliler
              </button>
              <button
                onClick={() => setChatCategory('class')}
                style={{
                  flex: 1,
                  padding: 8,
                  border: chatCategory === 'class' ? '2px solid #667eea' : '1px solid #e5e7eb',
                  borderRadius: 6,
                  background: chatCategory === 'class' ? '#f0f4ff' : 'white',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: chatCategory === 'class' ? 600 : 400
                }}
              >
                Sınıf
              </button>
              <button
                onClick={() => setChatCategory('admin')}
                style={{
                  flex: 1,
                  padding: 8,
                  border: chatCategory === 'admin' ? '2px solid #667eea' : '1px solid #e5e7eb',
                  borderRadius: 6,
                  background: chatCategory === 'admin' ? '#f0f4ff' : 'white',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: chatCategory === 'admin' ? 600 : 400
                }}
              >
                İdare
              </button>
            </div>
          </div>
          <div style={{ padding: 16, flex: 1, overflowY: 'auto', maxHeight: 350 }}>
            {loadingContacts && (
              <div style={{ textAlign: 'center', padding: 20, color: '#666' }}>
                Yükleniyor...
              </div>
            )}
            {chatCategory === 'parents' && !loadingContacts && (
              <>
                <p style={{ color: '#666', fontSize: 14, marginBottom: 12 }}>
                  Velilere mesaj göndermek için öğrenci seçin:
                </p>
                {students.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: 20, color: '#666' }}>
                    Öğrenci bulunamadı
                  </div>
                ) : (
                  students.slice(0, 10).map((student) => (
                    <div
                      key={student.id}
                      style={{
                        padding: 12,
                        border: '1px solid #e5e7eb',
                        borderRadius: 8,
                        marginBottom: 8,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                      onClick={() => {
                        setSelectedRecipient(student.id);
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                    >
                      <div style={{ fontWeight: 600 }}>{student.first_name} {student.last_name}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>{student.class_name || 'Sınıf atanmamış'}</div>
                    </div>
                  ))
                )}
              </>
            )}
            {chatCategory === 'class' && !loadingContacts && (
              <>
                <p style={{ color: '#666', fontSize: 14, marginBottom: 12 }}>
                  Sınıf içi iletişim:
                </p>
                {students.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: 20, color: '#666' }}>
                    Öğrenci bulunamadı
                  </div>
                ) : (
                  students.slice(0, 10).map((student) => (
                    <div
                      key={student.id}
                      style={{
                        padding: 12,
                        border: '1px solid #e5e7eb',
                        borderRadius: 8,
                        marginBottom: 8,
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                      onClick={() => {
                        setSelectedRecipient(student.id);
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                    >
                      <div style={{ fontWeight: 600 }}>{student.first_name} {student.last_name}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>{student.class_name || 'Sınıf atanmamış'}</div>
                    </div>
                  ))
                )}
              </>
            )}
            {chatCategory === 'admin' && !loadingContacts && (
              <>
                <p style={{ color: '#666', fontSize: 14, marginBottom: 12 }}>
                  İdare ile iletişim:
                </p>
                {!selectedRecipient ? (
                  <>
                    {users.length === 0 ? (
                      <div style={{ textAlign: 'center', padding: 20, color: '#666' }}>
                        Personel bulunamadı
                      </div>
                    ) : (
                      users.filter((u) => u.roles?.some((r: any) => r.slug === 'admin' || r.slug === 'super_admin' || r.slug === 'teacher')).map((user) => (
                        <div
                          key={user.id}
                          style={{
                            padding: 12,
                            border: '1px solid #e5e7eb',
                            borderRadius: 8,
                            marginBottom: 8,
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                          }}
                          onClick={() => setSelectedRecipient(user.id)}
                          onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                        >
                          <div style={{ fontWeight: 600 }}>{user.first_name} {user.last_name}</div>
                          <div style={{ fontSize: 12, color: '#666' }}>
                            {user.roles?.map((r: any) => r.name).join(', ') || 'Rol atanmamış'}
                          </div>
                        </div>
                      ))
                    )}
                  </>
                ) : (
                  <>
                    <div style={{ marginBottom: 12 }}>
                      <button
                        onClick={() => setSelectedRecipient('')}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#667eea',
                          cursor: 'pointer',
                          fontSize: 13,
                          padding: 0
                        }}
                      >
                        ← Geri dön
                      </button>
                      <div style={{ fontWeight: 600, marginTop: 8 }}>
                        {users.find((u) => u.id === selectedRecipient)?.first_name} {users.find((u) => u.id === selectedRecipient)?.last_name}
                      </div>
                    </div>
                    <textarea
                      value={messageInput}
                      onChange={(e) => setMessageInput(e.target.value)}
                      placeholder="Mesajınızı yazın..."
                      style={{
                        width: '100%',
                        minHeight: 100,
                        padding: 12,
                        border: '1px solid #e5e7eb',
                        borderRadius: 8,
                        fontSize: 14,
                        resize: 'vertical',
                        marginBottom: 12,
                        fontFamily: 'inherit'
                      }}
                    />
                    <button
                      onClick={async () => {
                        if (!messageInput.trim()) return;
                        setSending(true);
                        try {
                          // TODO: Implement actual message sending
                          console.log('Sending message to:', selectedRecipient, 'Message:', messageInput);
                          setMessageInput('');
                          setSelectedRecipient('');
                          setShowQuickChat(false);
                        } catch (err) {
                          console.error('Failed to send message:', err);
                        } finally {
                          setSending(false);
                        }
                      }}
                      disabled={sending || !messageInput.trim()}
                      style={{
                        width: '100%',
                        padding: 12,
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white',
                        border: 'none',
                        borderRadius: 8,
                        cursor: sending || !messageInput.trim() ? 'not-allowed' : 'pointer',
                        fontSize: 14,
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 8,
                        opacity: sending || !messageInput.trim() ? 0.5 : 1
                      }}
                    >
                      {sending ? 'Gönderiliyor...' : (
                        <>
                          <Send size={16} />
                          Gönder
                        </>
                      )}
                    </button>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Quick Chat Toggle Button */}
      {!showQuickChat && (
        <button
          onClick={() => setShowQuickChat(true)}
          style={{
            position: 'fixed',
            bottom: 20,
            right: 20,
            width: 60,
            height: 60,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0 4px 20px rgba(102, 126, 234, 0.4)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 0.2s'
          }}
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.1)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          <MessageCircle size={28} />
        </button>
      )}
    </>
  );
}

function Quick({ to, icon, title, caption }: { to: string; icon: React.ReactNode; title: string; caption: string }) {
  const permission = ({ "/attendance": "attendance.read", "/finance/payments/new": "finance.write", "/announcements/new": "announcement.write", "/finance/receipts": "receipt.read" } as Record<string, string>)[to];
  const allowed = useAuthStore((state) => state.can(permission));
  return allowed ? <Link className="quick-item" to={to}><div className="quick-icon">{icon}</div><div className="quick-copy"><strong>{title}</strong><span>{caption}</span></div><ChevronRight size={15} color="#91a09f" /></Link> : null;
}
