import { RecordedParentPanel } from "./RecordedParentPanel";
import { RecordedFinancialPanel } from "./RecordedFinancialPanel";
import { canAnalyze, getAnalysis } from "../../lib/analysis";
import { Users, DollarSign, MessageSquare, GraduationCap, RefreshCw, Activity, Target, Zap } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatCard, Tabs } from "../../components/ui";
import { apiMessage } from "../../lib/api";

interface InsightsReport {
  insights: {
    academic_performance: {
      overall_trend: string;
      at_risk_students: number;
    };
    attendance: {
      overall_rate: number;
      trend: string;
    };
    financial: {
      collection_rate: number;
      forecast_trend: string;
    };
    parent_satisfaction: {
      score: string;
      sentiment: string;
    };
  };
}

export function AIAnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("overview");
  const [dateRange, setDateRange] = useState(30);
  const [financialMonths, setFinancialMonths] = useState(6);
  const tabs = [
    { id: "overview", label: "Genel Bakış", path: "/ai/insights-report" },
    { id: "academic", label: "Akademik özet", path: "/ai/ai-academic-predictions" },
    { id: "attendance", label: "Devamsızlık AI", path: "/ai/ai-attendance-predictions" },
    { id: "financial", label: "Finansal özet", path: "/ai/ai-financial-predictions" },
    { id: "parent", label: "Veli iletişimi", path: "/ai/ai-parent-sentiment" },
    { id: "operational", label: "Operasyonel AI", path: "/ai/ai-operational-optimization" },
  ].filter((tab) => canAnalyze(tab.path));
  const currentTab = tabs.some((tab) => tab.id === activeTab) ? activeTab : (tabs[0]?.id || "none");

  const [academicPredictions, setAcademicPredictions] = useState<any>(null);
  const [attendancePredictions, setAttendancePredictions] = useState<any>(null);
  const [financialPredictions, setFinancialPredictions] = useState<any>(null);
  const [parentSentiment, setParentSentiment] = useState<any>(null);
  const [operationalOptimization, setOperationalOptimization] = useState<any>(null);
  const [insightsReport, setInsightsReport] = useState<InsightsReport | null>(null);

  const loadRequest = useRef<AbortController | null>(null);
  async function loadAllData() {
    loadRequest.current?.abort();
    const controller = new AbortController(); loadRequest.current = controller;
    setError("");
    if (currentTab === "none") { setLoading(false); return; }
    setLoading(true);
    if (currentTab === "academic") setAcademicPredictions(null);
    if (currentTab === "attendance") setAttendancePredictions(null);
    if (currentTab === "financial") setFinancialPredictions(null);
    if (currentTab === "parent") setParentSentiment(null);
    if (currentTab === "operational") setOperationalOptimization(null);
    if (currentTab === "overview") setInsightsReport(null);
    try {
      const config = { signal: controller.signal };
      const response = currentTab === "academic" ? await getAnalysis(`/ai/ai-academic-predictions?days=${dateRange}`, config)
        : currentTab === "attendance" ? await getAnalysis(`/ai/ai-attendance-predictions?days=${dateRange}`, config)
        : currentTab === "financial" ? await getAnalysis(`/ai/ai-financial-predictions?months=${financialMonths}`, config)
        : currentTab === "parent" ? await getAnalysis(`/ai/ai-parent-sentiment?days=${dateRange}`, config)
        : currentTab === "operational" ? await getAnalysis("/ai/ai-operational-optimization", config)
        : await getAnalysis("/ai/insights-report", config);
      if (controller.signal.aborted) return;
      if (!response.data.success || !response.data.data) throw new Error("Analiz verileri alınamadı");
      const data = response.data.data;
      if (currentTab === "academic") setAcademicPredictions(data);
      if (currentTab === "attendance") setAttendancePredictions(data);
      if (currentTab === "financial") setFinancialPredictions(data);
      if (currentTab === "parent") setParentSentiment(data);
      if (currentTab === "operational") setOperationalOptimization(data);
      if (currentTab === "overview") setInsightsReport(data);
    } catch (err) {
      if (!controller.signal.aborted) setError(apiMessage(err));
    } finally {
      if (!controller.signal.aborted) { setLoading(false); setRefreshing(false); }
    }
  }

  useEffect(() => {
    loadAllData();
    return () => loadRequest.current?.abort();
  }, [dateRange, currentTab, financialMonths]);

  function handleRefresh() {
    setRefreshing(true);
    loadAllData();
  }

  if (loading) {
    return <LoadingState />;
  }

  return (
    <>
      <PageHeader
        title="AI Analitiği"
        description="Yapay zeka destekli analizler ve tahminler"
      />

      <div className="page-content">
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 16 }}>
          {["academic", "attendance", "parent"].includes(currentTab) && <select
            aria-label={currentTab === "parent" ? "Veli iletişim dönemi" : "Analiz dönemi"}
            value={dateRange}
            onChange={(e) => setDateRange(Number(e.target.value))}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              fontSize: 13,
              color: "#1b2b2e"
            }}
          >
            <option value={7}>Son 7 gün</option>
            <option value={30}>Son 30 gün</option>
            <option value={90}>Son 90 gün</option>
          </select>}
          {currentTab === "financial" && <select aria-label="Finans vade dönemi" value={financialMonths}
            onChange={(event) => setFinancialMonths(Number(event.target.value))} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb" }}>
            {[1, 3, 6, 12, 24].map((months) => <option key={months} value={months}>{months} takvim ayı</option>)}
          </select>}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              background: "#fff",
              fontSize: 13,
              color: "#1b2b2e",
              cursor: refreshing ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6
            }}
          >
            <RefreshCw size={16} className={refreshing ? "spin" : ""} />
            Yenile
          </button>
        </div>
        {tabs.length === 0 && <EmptyState title="Yetkiniz kapsamında analiz bulunmuyor" description="Görüntüleyebileceğiniz analiz alanları hesap izinlerinize göre açılır." />}
        {error && <div role="alert"><ErrorState message={error} retry={loadAllData} /></div>}
        <Tabs 
          activeTab={currentTab} 
          onTabChange={setActiveTab} 
          tabs={tabs} 
        />

        {currentTab === "overview" && (
          <div className="tab-content">
            {!insightsReport || !insightsReport.insights ? (
              <div style={{ padding: 40, textAlign: "center", color: "#6e7b7d" }}>
                AI insights verisi yüklenemedi
              </div>
            ) : (
              <>
                <div className="grid stats-grid">
                  <StatCard 
                    icon={<GraduationCap size={19} />} 
                    label="Akademik AI Skoru" 
                    value={insightsReport.insights?.academic_performance?.overall_trend || "Veri yok"} 
                    meta={`${insightsReport.insights?.academic_performance?.at_risk_students || 0} risk öğrenci`} 
                    color="blue"
                  />
                  <StatCard 
                    icon={<Users size={19} />} 
                    label="Devamsızlık AI" 
                    value={`${insightsReport.insights?.attendance?.overall_rate || 0}%`} 
                    meta={insightsReport.insights?.attendance?.trend || "Veri yok"} 
                    color="green"
                  />
                  <StatCard 
                    icon={<DollarSign size={19} />} 
                    label="Finansal AI" 
                    value={`${insightsReport.insights?.financial?.collection_rate || 0}%`} 
                    meta={insightsReport.insights?.financial?.forecast_trend || "Veri yok"} 
                    color="blue"
                  />
                  <StatCard 
                    icon={<MessageSquare size={19} />} 
                    label="Veli AI Analizi" 
                    value={insightsReport.insights?.parent_satisfaction?.score || "Veri yok"} 
                    meta={insightsReport.insights?.parent_satisfaction?.sentiment || "Veri yok"} 
                    color="orange"
                  />
                </div>

                <div className="card" style={{ marginTop: 24 }}>
                  <div className="card-head">
                    <div>
                      <h2>AI Analitiği Hakkında</h2>
                      <p>Yapay zeka algoritmaları ile tahminler ve öneriler</p>
                    </div>
                  </div>
                  <div style={{ padding: "0 21px 21px" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
                      <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                        <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Akademik Tahminler</div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: "#1b2b2e", marginBottom: 8 }}>Not ortalamaları</div>
                        <div style={{ fontSize: 11, color: "#6e7b7d" }}>Öğrenci not trend analizi</div>
                      </div>
                      <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                        <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Devamsızlık AI</div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: "#1b2b2e", marginBottom: 8 }}>Pattern Recognition</div>
                        <div style={{ fontSize: 11, color: "#6e7b7d" }}>Gün bazlı devamsızlık patternleri</div>
                      </div>
                      <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                        <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Finansal AI</div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: "#1b2b2e", marginBottom: 8 }}>Time Series</div>
                        <div style={{ fontSize: 11, color: "#6e7b7d" }}>Nakit akışı tahminleri</div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {currentTab === "academic" && academicPredictions && (
          <div className="tab-content">
            <div className="card">
              <div className="card-head">
                <div>
                  <h2>Kayıtlı not analizi</h2>
                  <p>Seçili dönemdeki sınav ve değerlendirmelerin 100 üzerinden eşit ağırlıklı ortalamaları.</p>
                </div>
              </div>
              <div style={{ padding: "0 21px 21px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 180px), 1fr))", gap: 16, marginBottom: 24 }}>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Analiz Edilen</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{academicPredictions.total_analyzed || 0}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Riskli Öğrenci</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#dc2626" }}>{academicPredictions.total_risk_students ?? academicPredictions.risk_students?.length ?? 0}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>İzleme eşiği</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{academicPredictions.risk_threshold ?? "—"}/100</div>
                  </div>
                </div>

                {academicPredictions.students_without_grades > 0 && <p>{academicPredictions.students_without_grades} öğrenci için seçili dönemde değerlendirme kaydı yok.</p>}
                {academicPredictions.total_risk_students > academicPredictions.risk_students?.length && <p>En düşük ortalamaya sahip ilk 10 öğrenci gösterilir.</p>}

                {academicPredictions.risk_students && academicPredictions.risk_students.length > 0 && (
                  <div style={{ marginBottom: 24 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>İzleme eşiğinin altındaki öğrenciler</h3>
                    {academicPredictions.risk_students.map((student: any, index: number) => (
                      <div 
                        key={index}
                        style={{
                          padding: 12,
                          borderRadius: 8,
                          background: student.risk_level === "yüksek" ? "#fee2e2" : "#fef3c7",
                          marginBottom: 8,
                          borderLeft: `4px solid ${student.risk_level === "yüksek" ? "#dc2626" : "#ca8a04"}`
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontSize: 13, fontWeight: 600 }}>{student.student_name}</span>
                          <span style={{ fontSize: 12, fontWeight: 700, color: student.risk_level === "yüksek" ? "#dc2626" : "#ca8a04" }}>{student.current_average}</span>
                        </div>
                        <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                          Değerlendirme: {student.grade_count ?? "—"} | Son notların yönü: {student.trend}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {academicPredictions.recommendations && academicPredictions.recommendations.length > 0 && (
                  <div>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Önerileri</h3>
                    {academicPredictions.recommendations.map((rec: string, index: number) => (
                      <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, padding: 8, borderRadius: 6, background: "#f0fdf4" }}>
                        <Target size={16} color="#176b5b" />
                        <span style={{ fontSize: 13 }}>{rec}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {currentTab === "attendance" && attendancePredictions && (
          <div className="tab-content">
            <div className="card">
              <div className="card-head">
                <div>
                  <h2>Devamsızlık AI</h2>
                  <p>Pattern recognition ve tahmin analizi - {attendancePredictions.ai_model}</p>
                </div>
              </div>
              <div style={{ padding: "0 21px 21px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 24 }}>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Analiz Edilen</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{attendancePredictions.total_analyzed || 0}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Risk Uyarıları</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#dc2626" }}>{attendancePredictions.risk_alerts?.length || 0}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Analiz Dönemi</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{attendancePredictions.analysis_period_days || 0} gün</div>
                  </div>
                </div>

                {attendancePredictions.risk_alerts && attendancePredictions.risk_alerts.length > 0 && (
                  <div style={{ marginBottom: 24 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Risk Uyarıları</h3>
                    {attendancePredictions.risk_alerts.map((alert: any, index: number) => (
                      <div 
                        key={index}
                        style={{
                          padding: 12,
                          borderRadius: 8,
                          background: alert.risk_level === "kritik" ? "#fee2e2" : alert.risk_level === "yüksek" ? "#fef3c7" : "#f0fdf4",
                          marginBottom: 8,
                          borderLeft: `4px solid ${alert.risk_level === "kritik" ? "#dc2626" : alert.risk_level === "yüksek" ? "#ca8a04" : "#16a34a"}`
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontSize: 13, fontWeight: 600 }}>{alert.student_name}</span>
                          <span style={{ fontSize: 12, fontWeight: 700, color: alert.risk_level === "kritik" ? "#dc2626" : alert.risk_level === "yüksek" ? "#ca8a04" : "#16a34a" }}>{alert.current_rate}%</span>
                        </div>
                        <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                          Tahmin: {alert.predicted_rate}% | Trend: {alert.trend} | Risk: {alert.risk_level}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {attendancePredictions.patterns && attendancePredictions.patterns.length > 0 && (
                  <div style={{ marginBottom: 24 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Tespit Edilen Patternler</h3>
                    {attendancePredictions.patterns.map((pattern: any, index: number) => (
                      <div key={index} style={{ marginBottom: 8 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{pattern.student_name}</div>
                        {pattern.patterns.map((dayPattern: any, pIndex: number) => (
                          <div 
                            key={pIndex}
                            style={{
                              padding: 8,
                              borderRadius: 6,
                              background: dayPattern.severity === "high" ? "#fee2e2" : "#fef3c7",
                              marginBottom: 4,
                              marginLeft: 12
                            }}
                          >
                            <span style={{ fontSize: 12 }}>{dayPattern.day}: %{dayPattern.rate} devamsızlık ({dayPattern.severity})</span>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                )}

                {attendancePredictions.recommendations && attendancePredictions.recommendations.length > 0 && (
                  <div>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Önerileri</h3>
                    {attendancePredictions.recommendations.map((rec: string, index: number) => (
                      <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, padding: 8, borderRadius: 6, background: "#f0fdf4" }}>
                        <Activity size={16} color="#176b5b" />
                        <span style={{ fontSize: 13 }}>{rec}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {currentTab === "financial" && financialPredictions && <RecordedFinancialPanel summary={financialPredictions} />}

        {currentTab === "parent" && parentSentiment && <RecordedParentPanel summary={parentSentiment} />}

        {currentTab === "operational" && operationalOptimization && (
          <div className="tab-content">
            <div className="card">
              <div className="card-head">
                <div>
                  <h2>Operasyonel AI</h2>
                  <p>Resource optimization ve verimlilik analizi - {operationalOptimization.ai_model}</p>
                </div>
              </div>
              <div style={{ padding: "0 21px 21px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 24 }}>
                  <div style={{ padding: 16, borderRadius: 11, background: operationalOptimization.optimization_scores?.overall_score >= 75 ? "#dcfce7" : operationalOptimization.optimization_scores?.overall_score >= 50 ? "#fef3c7" : "#fee2e2", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>AI Genel Skor</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{operationalOptimization.optimization_scores?.overall_score || 0}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Sınıf Verimliliği</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{operationalOptimization.optimization_scores?.classroom_utilization || 0}</div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Personel Verimliliği</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#1b2b2e" }}>{operationalOptimization.optimization_scores?.staff_efficiency || 0}</div>
                  </div>
                </div>

                <div style={{ marginBottom: 24 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Optimizasyon Potansiyeli</h3>
                  <div style={{ padding: 16, borderRadius: 11, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>İyileştirme Potansiyeli</div>
                    <div style={{ fontSize: 28, fontWeight: 800, color: "#176b5b" }}>{operationalOptimization.optimization_potential || 0}%</div>
                  </div>
                </div>

                {operationalOptimization.resource_allocation?.recommended_actions && operationalOptimization.resource_allocation.recommended_actions.length > 0 && (
                  <div style={{ marginBottom: 24 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Önerilen Eylemler</h3>
                    {operationalOptimization.resource_allocation.recommended_actions.map((action: string, index: number) => (
                      <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, padding: 8, borderRadius: 6, background: "#f0fdf4" }}>
                        <Zap size={16} color="#176b5b" />
                        <span style={{ fontSize: 13 }}>{action}</span>
                      </div>
                    ))}
                  </div>
                )}

                {operationalOptimization.recommendations && operationalOptimization.recommendations.length > 0 && (
                  <div>
                    <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>AI Önerileri</h3>
                    {operationalOptimization.recommendations.map((rec: string, index: number) => (
                      <div key={index} style={{ display: "flex", gap: 8, marginBottom: 8, padding: 8, borderRadius: 6, background: "#f0fdf4" }}>
                        <Target size={16} color="#176b5b" />
                        <span style={{ fontSize: 13 }}>{rec}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
