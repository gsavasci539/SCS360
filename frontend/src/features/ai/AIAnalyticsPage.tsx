import { Users, DollarSign, MessageSquare, GraduationCap, AlertTriangle, CheckCircle, ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorState, LoadingState, PageHeader, StatCard, Tabs } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";
import { money } from "../../lib/format";

interface AttendanceAnalysis {
  current_rate: number;
  predicted_rate: number;
  trend: string;
  patterns: Array<{ type: string; day: string; rate: number; severity: string }>;
  risk_students: Array<{ student_id: string; attendance_rate: number; risk_level: string }>;
  recommendations: string[];
}

interface PaymentForecast {
  monthly_forecast: Array<{ month: string; predicted_amount: number; confidence: number }>;
  total_expected: number;
  outstanding_debt: number;
  collection_rate: number;
  trend: string;
  recommendations: string[];
}

interface ParentSatisfaction {
  satisfaction_score: number;
  sentiment: string;
  key_issues: Array<{ category: string; mentions: number; severity: string }>;
  avg_response_time_hours: number;
  total_feedback: number;
  recommendations: string[];
}

interface InsightsReport {
  insights: {
    academic_performance: any;
    attendance: any;
    financial: any;
    parent_satisfaction: any;
  };
  priority_actions: string[];
}

export function AIAnalyticsPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  
  const [attendanceAnalysis, setAttendanceAnalysis] = useState<AttendanceAnalysis | null>(null);
  const [paymentForecast, setPaymentForecast] = useState<PaymentForecast | null>(null);
  const [parentSatisfaction, setParentSatisfaction] = useState<ParentSatisfaction | null>(null);
  const [insightsReport, setInsightsReport] = useState<InsightsReport | null>(null);

  useEffect(() => {
    loadAllData();
  }, []);

  async function loadAllData() {
    setLoading(true);
    setError("");
    try {
      const [attendance, payment, satisfaction, insights] = await Promise.allSettled([
        api.get("/ai/attendance-analysis"),
        api.get("/ai/payment-forecast"),
        api.get("/ai/parent-satisfaction"),
        api.get("/ai/insights-report")
      ]);

      if (attendance.status === "fulfilled") setAttendanceAnalysis(attendance.value.data.data);
      if (payment.status === "fulfilled") setPaymentForecast(payment.value.data.data);
      if (satisfaction.status === "fulfilled") setParentSatisfaction(satisfaction.value.data.data);
      if (insights.status === "fulfilled") setInsightsReport(insights.value.data.data);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="card"><LoadingState label="AI analizleri hazırlanıyor" /></div>;
  if (error) return <div className="card"><ErrorState message={error} retry={loadAllData} /></div>;

  return (
    <>
      <PageHeader 
        eyebrow="Yapay Zeka Analizleri" 
        title="AI-Powered Insights" 
        description="Veri odaklı kararlar için yapay zeka destekli analizler ve tahminler."
      />
      
      <div className="card">
        <Tabs 
          activeTab={activeTab} 
          onTabChange={setActiveTab} 
          tabs={[
            { id: "overview", label: "Genel Bakış" },
            { id: "attendance", label: "Devamsızlık" },
            { id: "financial", label: "Finansal" },
            { id: "satisfaction", label: "Memnuniyet" }
          ]} 
        />
        
        {activeTab === "overview" && (
          <div className="tab-content">
            {insightsReport && (
              <>
                <div className="grid stats-grid">
                  <StatCard 
                    icon={<GraduationCap size={19} />} 
                    label="Akademik Trend" 
                    value={insightsReport.insights.academic_performance.overall_trend} 
                    meta={`${insightsReport.insights.academic_performance.at_risk_students} risk öğrenci`} 
                    color="blue"
                  />
                  <StatCard 
                    icon={<Users size={19} />} 
                    label="Devamsızlık Oranı" 
                    value={`${insightsReport.insights.attendance.overall_rate}%`} 
                    meta={insightsReport.insights.attendance.trend} 
                    color="green"
                  />
                  <StatCard 
                    icon={<DollarSign size={19} />} 
                    label="Tahsilat Oranı" 
                    value={`${insightsReport.insights.financial.collection_rate}%`} 
                    meta={insightsReport.insights.financial.forecast_trend} 
                    color="blue"
                  />
                  <StatCard 
                    icon={<MessageSquare size={19} />} 
                    label="Veli Memnuniyeti" 
                    value={insightsReport.insights.parent_satisfaction.score} 
                    meta={insightsReport.insights.parent_satisfaction.sentiment} 
                    color="orange"
                  />
                </div>

                <div className="card" style={{ marginTop: 18 }}>
                  <div className="card-head">
                    <div>
                      <h2>Öncelikli Aksiyonlar</h2>
                      <p>AI tarafından önerilen kritik eylemler</p>
                    </div>
                  </div>
                  <div style={{ padding: "0 21px 21px" }}>
                    {insightsReport.priority_actions.map((action, index) => (
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
                        {index === 0 ? <AlertTriangle size={18} color="#856404" /> : <CheckCircle size={18} color="#28a745" />}
                        <span style={{ fontSize: 13, fontWeight: 500 }}>{action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === "attendance" && attendanceAnalysis && (
          <div className="tab-content">
            <div className="grid dashboard-grid">
              <section className="card">
                <div className="card-head">
                  <div>
                    <h2>Devamsızlık Analizi</h2>
                    <p>Geçen 30 günlük devamsızlık verileri</p>
                  </div>
                </div>
                <div style={{ padding: "0 21px 21px" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
                    <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Mevcut Oran</div>
                      <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{attendanceAnalysis.current_rate}%</div>
                    </div>
                    <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Tahmini Oran</div>
                      <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{attendanceAnalysis.predicted_rate}%</div>
                    </div>
                  </div>

                  {attendanceAnalysis.patterns.length > 0 && (
                    <div style={{ marginBottom: 20 }}>
                      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Problemli Günler</h3>
                      {attendanceAnalysis.patterns.map((pattern, index) => (
                        <div 
                          key={index}
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            padding: 12,
                            borderRadius: 8,
                            background: pattern.severity === "high" ? "#fee2e2" : "#fef3c7",
                            marginBottom: 8
                          }}
                        >
                          <span style={{ fontSize: 13, fontWeight: 600 }}>{pattern.day}</span>
                          <span style={{ fontSize: 12, color: "#6e7b7d" }}>{pattern.rate}%</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {attendanceAnalysis.recommendations.length > 0 && (
                    <div>
                      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Öneriler</h3>
                      {attendanceAnalysis.recommendations.map((rec, index) => (
                        <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                          <ArrowRight size={16} color="#176b5b" />
                          <span style={{ fontSize: 13 }}>{rec}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </section>

              <section className="card">
                <div className="card-head">
                  <div>
                    <h2>Riskli Öğrenciler</h2>
                    <p>Devamsızlık riski yüksek öğrenciler</p>
                  </div>
                </div>
                <div style={{ padding: "0 21px 21px" }}>
                  {attendanceAnalysis.risk_students.length > 0 ? (
                    attendanceAnalysis.risk_students.map((student, index) => (
                      <div 
                        key={index}
                        style={{
                          padding: 12,
                          borderRadius: 8,
                          background: student.risk_level === "critical" ? "#fee2e2" : "#fef3c7",
                          marginBottom: 8
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontSize: 13, fontWeight: 600 }}>Öğrenci #{index + 1}</span>
                          <span style={{ fontSize: 12, color: "#6e7b7d" }}>{student.attendance_rate}%</span>
                        </div>
                        <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                          Risk Seviyesi: {student.risk_level}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ padding: 20, textAlign: "center", color: "#6e7b7d" }}>
                      Riskli öğrenci bulunmuyor
                    </div>
                  )}
                </div>
              </section>
            </div>
          </div>
        )}

        {activeTab === "financial" && paymentForecast && (
          <div className="tab-content">
            <div className="card">
              <div className="card-head">
                <div>
                  <h2>Ödeme Tahmini</h2>
                  <p>Gelecek 6 ay için tahsilat tahminleri</p>
                </div>
              </div>
              <div style={{ padding: "0 21px 21px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 20 }}>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Beklenen</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{money(paymentForecast.total_expected)}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Borçlu Tutar</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{money(paymentForecast.outstanding_debt)}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Tahsilat Oranı</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{paymentForecast.collection_rate}%</div>
                  </div>
                </div>

                <div style={{ height: 300, marginBottom: 20 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={paymentForecast.monthly_forecast}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                      <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#6b7280" }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: "#6b7280" }} />
                      <Tooltip contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }} />
                      <Bar dataKey="predicted_amount" fill="#176b5b" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {paymentForecast.recommendations.length > 0 && (
                  <div>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Öneriler</h3>
                    {paymentForecast.recommendations.map((rec, index) => (
                      <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                        <ArrowRight size={16} color="#176b5b" />
                        <span style={{ fontSize: 13 }}>{rec}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === "satisfaction" && parentSatisfaction && (
          <div className="tab-content">
            <div className="grid dashboard-grid">
              <section className="card">
                <div className="card-head">
                  <div>
                    <h2>Veli Memnuniyeti</h2>
                    <p>Velilerden gelen geri bildirim analizi</p>
                  </div>
                </div>
                <div style={{ padding: "0 21px 21px" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
                    <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Memnuniyet Skoru</div>
                      <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{parentSatisfaction.satisfaction_score}/5</div>
                    </div>
                    <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                      <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Duygu Analizi</div>
                      <div style={{ fontSize: 28, fontWeight: 800, color: "#1b2b2e" }}>{parentSatisfaction.sentiment}</div>
                    </div>
                  </div>

                  <div style={{ marginBottom: 20 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Ana Konular</h3>
                    {parentSatisfaction.key_issues.map((issue, index) => (
                      <div 
                        key={index}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          padding: 12,
                          borderRadius: 8,
                          background: issue.severity === "high" ? "#fee2e2" : "#f8faf8",
                          marginBottom: 8
                        }}
                      >
                        <span style={{ fontSize: 13, fontWeight: 600 }}>{issue.category}</span>
                        <span style={{ fontSize: 12, color: "#6e7b7d" }}>{issue.mentions} bahsetme</span>
                      </div>
                    ))}
                  </div>

                  {parentSatisfaction.recommendations.length > 0 && (
                    <div>
                      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Öneriler</h3>
                      {parentSatisfaction.recommendations.map((rec, index) => (
                        <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                          <ArrowRight size={16} color="#176b5b" />
                          <span style={{ fontSize: 13 }}>{rec}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </section>

              <section className="card">
                <div className="card-head">
                  <div>
                    <h2>İletişim Metrikleri</h2>
                    <p>Veli iletişim performansı</p>
                  </div>
                </div>
                <div style={{ padding: "0 21px 21px" }}>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", marginBottom: 16 }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Ortalama Yanıt Süresi</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{parentSatisfaction.avg_response_time_hours} saat</div>
                  </div>

                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Toplam Geri Bildirim</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{parentSatisfaction.total_feedback}</div>
                  </div>
                </div>
              </section>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
