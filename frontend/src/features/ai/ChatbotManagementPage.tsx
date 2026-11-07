import { reportClientError } from "../../lib/diagnostics";
import { 
  MessageSquare, 
  Brain, 
  Download, 
  Search, 
  Tag, 
  Star, 
  CheckCircle, 
  XCircle, 
  Edit,
  Calendar,
  User,
  Bot,
  TrendingUp,
  RefreshCw,
} from "lucide-react";
import { useEffect, useState } from "react";
import { ErrorState, LoadingState, PageHeader, StatCard, Tabs } from "../../components/ui";
import { api, apiMessage } from "../../lib/api";

interface ChatAuditLog {
  id: string;
  session_id: string;
  user_id: string;
  organization_id: string;
  user_query: string;
  ai_response: string;
  detected_intent: string;
  topic_category: string;
  sentiment: "POSITIVE" | "NEUTRAL" | "QUESTION" | "CRITICAL";
  quality_rating: number;
  feedback_status: "VERIFIED" | "CORRECTED" | "NEEDS_REVIEW";
  corrected_response?: string;
  token_count: number;
  latency_ms: number;
  is_fine_tuning_ready: boolean;
  meta_data?: any;
  created_at: string;
  updated_at: string;
  sender_name: string;
  sender_role: string;
}

interface AnalyticsOverview {
  overview: {
    total_logs: number;
    avg_latency_ms: number;
    avg_quality_rating: number;
    finetuning_ready_count: number;
  };
  distributions: {
    sentiment: Record<string, number>;
    topic: Record<string, number>;
    intent: Record<string, number>;
    feedback_status: Record<string, number>;
  };
}

export function ChatbotManagementPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("conversations");
  
  // Conversation logs state
  const [logs, setLogs] = useState<ChatAuditLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<ChatAuditLog[]>([]);
  const [selectedLog, setSelectedLog] = useState<ChatAuditLog | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [topicFilter, setTopicFilter] = useState("");
  const [sentimentFilter, setSentimentFilter] = useState("");
  const [feedbackFilter, setFeedbackFilter] = useState("");
  
  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  
  // Editing state
  const [editingLog, setEditingLog] = useState<ChatAuditLog | null>(null);
  const [editedResponse, setEditedResponse] = useState("");
  const [editedRating, setEditedRating] = useState(0);
  const [editedStatus, setEditedStatus] = useState<"VERIFIED" | "CORRECTED" | "NEEDS_REVIEW">("NEEDS_REVIEW");
  
  // Export
  const [exportFormat, setExportFormat] = useState("jsonl");
  const [exportLoading, setExportLoading] = useState(false);

  // Load data
  async function loadConversationLogs() {
    try {
      const params = new URLSearchParams();
      if (topicFilter) params.append("topic", topicFilter);
      if (feedbackFilter) params.append("feedback_status", feedbackFilter);
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      
      const response = await api.get(`/v1/chatbot/ai/audit-logs?${params.toString()}`);
      setLogs(response.data.data.logs);
      setFilteredLogs(response.data.data.logs);
      setTotal(response.data.data.total);
    } catch (err) {
      setError(apiMessage(err));
    }
  }

  async function loadAnalytics() {
    try {
      const response = await api.get("/v1/chatbot/ai/analytics/overview");
      setAnalytics(response.data.data);
    } catch (err) {
      reportClientError("Analytics load error:", err);
    }
  }

  async function loadAllData() {
    setLoading(true);
    setError("");
    try {
      await Promise.all([
        loadConversationLogs(),
        loadAnalytics()
      ]);
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadAllData();
  }, [page, topicFilter, feedbackFilter]);

  useEffect(() => {
    // Apply client-side filters
    let filtered = [...logs];
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(log => 
        log.user_query.toLowerCase().includes(query) ||
        log.ai_response.toLowerCase().includes(query) ||
        log.sender_name.toLowerCase().includes(query) ||
        log.topic_category.toLowerCase().includes(query)
      );
    }
    
    if (sentimentFilter) {
      filtered = filtered.filter(log => log.sentiment === sentimentFilter);
    }
    
    setFilteredLogs(filtered);
  }, [searchQuery, sentimentFilter, logs]);

  function handleRefresh() {
    setRefreshing(true);
    loadAllData();
  }

  async function handleUpdateFeedback(logId: string) {
    try {
      await api.put(`/v1/chatbot/ai/audit-logs/${logId}/verify`, {
        quality_rating: editedRating,
        feedback_status: editedStatus,
        corrected_response: editedStatus === "CORRECTED" ? editedResponse : undefined,
        is_fine_tuning_ready: editedStatus === "VERIFIED"
      });
      
      setEditingLog(null);
      setEditedResponse("");
      setEditedRating(0);
      setEditedStatus("NEEDS_REVIEW");
      
      await loadConversationLogs();
      await loadAnalytics();
    } catch (err) {
      setError(apiMessage(err));
    }
  }

  async function handleExport() {
    setExportLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("format", exportFormat);
      if (feedbackFilter) params.append("feedback_status", feedbackFilter);
      
      const response = await api.get(`/v1/chatbot/ai/export-dataset?${params.toString()}`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `scs360_finetuning_dataset.${exportFormat}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError(apiMessage(err));
    } finally {
      setExportLoading(false);
    }
  }

  function getSentimentColor(sentiment: string) {
    switch (sentiment) {
      case "POSITIVE": return "#16a34a";
      case "NEUTRAL": return "#6b7280";
      case "QUESTION": return "#2563eb";
      case "CRITICAL": return "#dc2626";
      default: return "#6b7280";
    }
  }

  function getFeedbackStatusColor(status: string) {
    switch (status) {
      case "VERIFIED": return "#16a34a";
      case "CORRECTED": return "#ca8a04";
      case "NEEDS_REVIEW": return "#dc2626";
      default: return "#6b7280";
    }
  }

  if (loading) {
    return <LoadingState />;
  }

  if (error) {
    return <ErrorState message={error} retry={loadAllData} />;
  }

  return (
    <>
      <PageHeader
        title="AI Chatbot Yönetimi"
        description="Chatbot görüşmeleri, LLM eğitimi ve analitik yönetimi"
      />

      <div className="page-content">
        <Tabs 
          activeTab={activeTab} 
          onTabChange={setActiveTab} 
          tabs={[
            { id: "conversations", label: "Görüşmeler" },
            { id: "analytics", label: "Analitik" },
            { id: "training", label: "LLM Eğitimi" }
          ]} 
        />

        {activeTab === "conversations" && (
          <div className="tab-content">
            {/* Filters */}
            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ padding: 16, display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, border: "1px solid #e5e7eb", borderRadius: 8, padding: "8px 12px" }}>
                    <Search size={16} color="#6e7b7d" />
                    <input
                      type="text"
                      placeholder="Mesajlarda ara..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      style={{ border: "none", outline: "none", flex: 1, fontSize: 13 }}
                    />
                  </div>
                </div>
                
                <select
                  value={topicFilter}
                  onChange={(e) => setTopicFilter(e.target.value)}
                  style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 13 }}
                >
                  <option value="">Tüm Konular</option>
                  {analytics?.distributions.topic && Object.keys(analytics.distributions.topic).map(topic => (
                    <option key={topic} value={topic}>{topic}</option>
                  ))}
                </select>
                
                <select
                  value={sentimentFilter}
                  onChange={(e) => setSentimentFilter(e.target.value)}
                  style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 13 }}
                >
                  <option value="">Tüm Duygular</option>
                  <option value="POSITIVE">Pozitif</option>
                  <option value="NEUTRAL">Nötr</option>
                  <option value="QUESTION">Soru</option>
                  <option value="CRITICAL">Kritik</option>
                </select>
                
                <select
                  value={feedbackFilter}
                  onChange={(e) => setFeedbackFilter(e.target.value)}
                  style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 13 }}
                >
                  <option value="">Tüm Durumlar</option>
                  <option value="VERIFIED">Doğrulanmış</option>
                  <option value="CORRECTED">Düzeltilmiş</option>
                  <option value="NEEDS_REVIEW">İnceleme Gerekiyor</option>
                </select>
                
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    background: "#fff",
                    fontSize: 13,
                    cursor: refreshing ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 6
                  }}
                >
                  <RefreshCw size={16} style={refreshing ? { animation: "spin 1s linear infinite" } : {}} />
                  Yenile
                </button>
              </div>
            </div>

            {/* Conversation List */}
            <div className="card">
              <div className="card-head">
                <div>
                  <h2>Chatbot Görüşmeleri</h2>
                  <p>Toplam {total} görüşme • {filteredLogs.length} filtrelendi</p>
                </div>
              </div>
              
              <div style={{ padding: 0 }}>
                {filteredLogs.length === 0 ? (
                  <div style={{ padding: 40, textAlign: "center", color: "#6e7b7d" }}>
                    Görüşme bulunamadı
                  </div>
                ) : (
                  filteredLogs.map((log) => (
                    <div
                      key={log.id}
                      style={{
                        padding: 16,
                        borderBottom: "1px solid #e5e7eb",
                        cursor: "pointer",
                        transition: "background 0.2s"
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = "#f9fafb"}
                      onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                      onClick={() => setSelectedLog(log)}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <User size={16} color="#6e7b7d" />
                          <span style={{ fontSize: 13, fontWeight: 600 }}>{log.sender_name}</span>
                          <span style={{ fontSize: 11, color: "#6e7b7d", background: "#f3f4f6", padding: "2px 6px", borderRadius: 4 }}>
                            {log.sender_role}
                          </span>
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ fontSize: 11, color: "#6e7b7d" }}>
                            {new Date(log.created_at).toLocaleString('tr-TR')}
                          </span>
                          <span 
                            style={{ 
                              fontSize: 11, 
                              color: getFeedbackStatusColor(log.feedback_status),
                              background: `${getFeedbackStatusColor(log.feedback_status)}20`,
                              padding: "2px 6px",
                              borderRadius: 4,
                              fontWeight: 600
                            }}
                          >
                            {log.feedback_status}
                          </span>
                        </div>
                      </div>
                      
                      <div style={{ marginBottom: 8 }}>
                        <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>Kullanıcı:</div>
                        <div style={{ fontSize: 13, color: "#1b2b2e", marginBottom: 8 }}>{log.user_query}</div>
                        
                        <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>AI:</div>
                        <div style={{ fontSize: 13, color: "#1b2b2e" }}>{log.ai_response.substring(0, 150)}...</div>
                      </div>
                      
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <span style={{ fontSize: 11, color: "#6e7b7d", background: "#f3f4f6", padding: "2px 6px", borderRadius: 4 }}>
                          <Tag size={12} style={{ display: "inline", verticalAlign: "middle" }} />
                          {log.topic_category}
                        </span>
                        <span style={{ fontSize: 11, color: "#6e7b7d", background: "#f3f4f6", padding: "2px 6px", borderRadius: 4 }}>
                          <Bot size={12} style={{ display: "inline", verticalAlign: "middle" }} />
                          {log.detected_intent}
                        </span>
                        <span 
                          style={{ 
                            fontSize: 11, 
                            color: getSentimentColor(log.sentiment),
                            background: `${getSentimentColor(log.sentiment)}20`,
                            padding: "2px 6px",
                            borderRadius: 4
                          }}
                        >
                          {log.sentiment}
                        </span>
                        {log.is_fine_tuning_ready && (
                          <span style={{ fontSize: 11, color: "#16a34a", background: "#dcfce7", padding: "2px 6px", borderRadius: 4 }}>
                            <Star size={12} style={{ display: "inline", verticalAlign: "middle" }} />
                            Eğitim Hazır
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              {/* Pagination */}
              {total > pageSize && (
                <div style={{ padding: 16, borderTop: "1px solid #e5e7eb", display: "flex", justifyContent: "center", gap: 8 }}>
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #e5e7eb", background: "#fff", cursor: page === 1 ? "not-allowed" : "pointer" }}
                  >
                    Önceki
                  </button>
                  <span style={{ padding: "8px 16px", fontSize: 13 }}>
                    Sayfa {page} / {Math.ceil(total / pageSize)}
                  </span>
                  <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={page >= Math.ceil(total / pageSize)}
                    style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #e5e7eb", background: "#fff", cursor: page >= Math.ceil(total / pageSize) ? "not-allowed" : "pointer" }}
                  >
                    Sonraki
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "analytics" && analytics && (
          <div className="tab-content">
            <div className="grid stats-grid">
              <StatCard 
                icon={<MessageSquare size={19} />} 
                label="Toplam Görüşme" 
                value={analytics.overview.total_logs} 
                color="blue"
              />
              <StatCard 
                icon={<TrendingUp size={19} />} 
                label="Ortalama Gecikme" 
                value={`${Math.round(analytics.overview.avg_latency_ms)}ms`} 
                color="green"
              />
              <StatCard 
                icon={<Star size={19} />} 
                label="Ortalama Kalite" 
                value={`${analytics.overview.avg_quality_rating.toFixed(1)}/5`} 
                color="orange"
              />
              <StatCard 
                icon={<Brain size={19} />} 
                label="Eğitim Hazır" 
                value={analytics.overview.finetuning_ready_count} 
                color="blue"
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16, marginTop: 16 }}>
              <div className="card">
                <div className="card-head">
                  <h3>Konu Dağılımı</h3>
                </div>
                <div style={{ padding: 16 }}>
                  {Object.entries(analytics.distributions.topic).map(([topic, count]) => (
                    <div key={topic} style={{ marginBottom: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 13 }}>{topic}</span>
                        <span style={{ fontSize: 13, fontWeight: 600 }}>{count}</span>
                      </div>
                      <div style={{ height: 8, background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
                        <div 
                          style={{ 
                            height: "100%", 
                            background: "#2563eb", 
                            width: `${(count / analytics.overview.total_logs) * 100}%` 
                          }} 
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <div className="card-head">
                  <h3>Niyet (Intent) Dağılımı</h3>
                </div>
                <div style={{ padding: 16 }}>
                  {Object.entries(analytics.distributions.intent).map(([intent, count]) => (
                    <div key={intent} style={{ marginBottom: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 13 }}>{intent}</span>
                        <span style={{ fontSize: 13, fontWeight: 600 }}>{count}</span>
                      </div>
                      <div style={{ height: 8, background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
                        <div 
                          style={{ 
                            height: "100%", 
                            background: "#16a34a", 
                            width: `${(count / analytics.overview.total_logs) * 100}%` 
                          }} 
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <div className="card-head">
                  <h3>Duygu Dağılımı</h3>
                </div>
                <div style={{ padding: 16 }}>
                  {Object.entries(analytics.distributions.sentiment).map(([sentiment, count]) => (
                    <div key={sentiment} style={{ marginBottom: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 13 }}>{sentiment}</span>
                        <span style={{ fontSize: 13, fontWeight: 600 }}>{count}</span>
                      </div>
                      <div style={{ height: 8, background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
                        <div 
                          style={{ 
                            height: "100%", 
                            background: getSentimentColor(sentiment), 
                            width: `${(count / analytics.overview.total_logs) * 100}%` 
                          }} 
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <div className="card-head">
                  <h3>Geri Bildirim Durumu</h3>
                </div>
                <div style={{ padding: 16 }}>
                  {Object.entries(analytics.distributions.feedback_status).map(([status, count]) => (
                    <div key={status} style={{ marginBottom: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 13 }}>{status}</span>
                        <span style={{ fontSize: 13, fontWeight: 600 }}>{count}</span>
                      </div>
                      <div style={{ height: 8, background: "#e5e7eb", borderRadius: 4, overflow: "hidden" }}>
                        <div 
                          style={{ 
                            height: "100%", 
                            background: getFeedbackStatusColor(status), 
                            width: `${(count / analytics.overview.total_logs) * 100}%` 
                          }} 
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "training" && (
          <div className="tab-content">
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-head">
                <div>
                  <h2>LLM Fine-Tuning Dataset Export</h2>
                  <p>Chatbot verilerini farklı formatlarda dışa aktararak LLM modellerini eğitin</p>
                </div>
              </div>
              <div style={{ padding: 16 }}>
                <div style={{ display: "flex", gap: 12, alignItems: "flex-end", marginBottom: 16 }}>
                  <div>
                    <label style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, display: "block" }}>Export Format</label>
                    <select
                      value={exportFormat}
                      onChange={(e) => setExportFormat(e.target.value)}
                      style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 13, minWidth: 200 }}
                    >
                      <option value="jsonl">OpenAI/Gemini JSONL</option>
                      <option value="alpaca">Stanford Alpaca</option>
                      <option value="llama">Meta LLaMA 3</option>
                      <option value="csv">Tabular CSV</option>
                    </select>
                  </div>
                  
                  <div>
                    <label style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4, display: "block" }}>Geri Bildirim Durumu</label>
                    <select
                      value={feedbackFilter}
                      onChange={(e) => setFeedbackFilter(e.target.value)}
                      style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 13, minWidth: 200 }}
                    >
                      <option value="">Tümü</option>
                      <option value="VERIFIED">Sadece Doğrulanmış</option>
                      <option value="CORRECTED">Sadece Düzeltilmiş</option>
                    </select>
                  </div>
                  
                  <button
                    onClick={handleExport}
                    disabled={exportLoading}
                    style={{
                      padding: "8px 16px",
                      borderRadius: 8,
                      border: "1px solid #e5e7eb",
                      background: "#2563eb",
                      color: "#fff",
                      fontSize: 13,
                      cursor: exportLoading ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 6
                    }}
                  >
                    <Download size={16} />
                    {exportLoading ? "İndiriliyor..." : "Dataset İndir"}
                  </button>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 16 }}>
                  <div style={{ padding: 16, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>OpenAI/Gemini JSONL</div>
                    <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                      Chat completion formatı. OpenAI ChatGPT ve Google Gemini için uygun.
                    </div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Stanford Alpaca</div>
                    <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                      Instruction tuning formatı. Alpaca ve benzeri modeller için uygun.
                    </div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Meta LLaMA 3</div>
                    <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                      LLaMA 3 chat template formatı. Meta LLaMA modelleri için uygun.
                    </div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 8, background: "#f8faf8", border: "1px solid #e5e7eb" }}>
                    <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Tabular CSV</div>
                    <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                      Excel ve BI araçları için tabular format. Analiz ve raporlama için ideal.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-head">
                <div>
                  <h2>RLHF (Reinforcement Learning from Human Feedback)</h2>
                  <p>İnsan geri bildirimi ile LLM kalitesini artırın</p>
                </div>
              </div>
              <div style={{ padding: 16 }}>
                <div style={{ fontSize: 13, color: "#6e7b7d", marginBottom: 16 }}>
                  Görüşmeler sekmesinden bir görüşme seçerek düzeltebilir, kalite puanı verebilir ve eğitim için işaretleyebilirsiniz.
                </div>
                
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
                  <div style={{ padding: 16, borderRadius: 8, background: "#dcfce7", border: "1px solid #16a34a" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                      <CheckCircle size={20} color="#16a34a" />
                      <span style={{ fontSize: 14, fontWeight: 600 }}>Doğrula</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                      Yanıtı doğru olarak işaretleyin ve eğitim veri setine ekleyin.
                    </div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 8, background: "#fef3c7", border: "1px solid #ca8a04" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                      <Edit size={20} color="#ca8a04" />
                      <span style={{ fontSize: 14, fontWeight: 600 }}>Düzelt</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                      Yanıtı düzenleyin ve düzeltilmiş versiyonu eğitim için kullanın.
                    </div>
                  </div>
                  <div style={{ padding: 16, borderRadius: 8, background: "#fee2e2", border: "1px solid #dc2626" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                      <XCircle size={20} color="#dc2626" />
                      <span style={{ fontSize: 14, fontWeight: 600 }}>İncele</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#6e7b7d" }}>
                      İnceleme gerektiren yanıtları işaretleyin.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Detail Modal */}
        {selectedLog && (
          <div style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000
          }}>
            <div style={{
              background: "#fff",
              borderRadius: 12,
              maxWidth: 800,
              width: "90%",
              maxHeight: "90vh",
              overflow: "auto",
              padding: 24
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
                <h2 style={{ fontSize: 18, fontWeight: 700 }}>Görüşme Detayı</h2>
                <button
                  onClick={() => setSelectedLog(null)}
                  style={{ padding: 8, borderRadius: 8, border: "none", background: "#f3f4f6", cursor: "pointer" }}
                >
                  ✕
                </button>
              </div>

              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>
                  <User size={12} style={{ display: "inline", verticalAlign: "middle" }} />
                  {selectedLog.sender_name} ({selectedLog.sender_role})
                </div>
                <div style={{ fontSize: 12, color: "#6e7b7d", marginBottom: 4 }}>
                  <Calendar size={12} style={{ display: "inline", verticalAlign: "middle" }} />
                  {new Date(selectedLog.created_at).toLocaleString('tr-TR')}
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                  <span style={{ fontSize: 11, background: "#f3f4f6", padding: "2px 6px", borderRadius: 4 }}>
                    {selectedLog.topic_category}
                  </span>
                  <span style={{ fontSize: 11, background: "#f3f4f6", padding: "2px 6px", borderRadius: 4 }}>
                    {selectedLog.detected_intent}
                  </span>
                  <span style={{ fontSize: 11, color: getSentimentColor(selectedLog.sentiment), background: `${getSentimentColor(selectedLog.sentiment)}20`, padding: "2px 6px", borderRadius: 4 }}>
                    {selectedLog.sentiment}
                  </span>
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Kullanıcı Sorgusu:</div>
                <div style={{ padding: 12, background: "#f8faf8", borderRadius: 8, fontSize: 13 }}>
                  {selectedLog.user_query}
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>AI Yanıtı:</div>
                <div style={{ padding: 12, background: "#f0fdf4", borderRadius: 8, fontSize: 13 }}>
                  {selectedLog.corrected_response || selectedLog.ai_response}
                </div>
              </div>

              {selectedLog.corrected_response && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Orijinal Yanıt:</div>
                  <div style={{ padding: 12, background: "#fef3c7", borderRadius: 8, fontSize: 13 }}>
                    {selectedLog.ai_response}
                  </div>
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 16 }}>
                <div style={{ padding: 8, borderRadius: 8, background: "#f8faf8", textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "#6e7b7d" }}>Token</div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{selectedLog.token_count}</div>
                </div>
                <div style={{ padding: 8, borderRadius: 8, background: "#f8faf8", textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "#6e7b7d" }}>Gecikme</div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{selectedLog.latency_ms}ms</div>
                </div>
                <div style={{ padding: 8, borderRadius: 8, background: "#f8faf8", textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "#6e7b7d" }}>Kalite</div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{selectedLog.quality_rating}/5</div>
                </div>
                <div style={{ padding: 8, borderRadius: 8, background: selectedLog.is_fine_tuning_ready ? "#dcfce7" : "#f8faf8", textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "#6e7b7d" }}>Eğitim</div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>
                    {selectedLog.is_fine_tuning_ready ? "Hazır" : "Değil"}
                  </div>
                </div>
              </div>

              <div style={{ display: "flex", gap: 8 }}>
                <button
                  onClick={() => {
                    setEditingLog(selectedLog);
                    setEditedResponse(selectedLog.corrected_response || selectedLog.ai_response);
                    setEditedRating(selectedLog.quality_rating);
                    setEditedStatus(selectedLog.feedback_status);
                  }}
                  style={{
                    flex: 1,
                    padding: "10px 16px",
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    background: "#fff",
                    fontSize: 13,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6
                  }}
                >
                  <Edit size={16} />
                  Düzenle
                </button>
                <button
                  onClick={() => setSelectedLog(null)}
                  style={{
                    padding: "10px 16px",
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    background: "#fff",
                    fontSize: 13,
                    cursor: "pointer"
                  }}
                >
                  Kapat
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Edit Modal */}
        {editingLog && (
          <div style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000
          }}>
            <div style={{
              background: "#fff",
              borderRadius: 12,
              maxWidth: 700,
              width: "90%",
              maxHeight: "90vh",
              overflow: "auto",
              padding: 24
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
                <h2 style={{ fontSize: 18, fontWeight: 700 }}>Geri Bildirim</h2>
                <button
                  onClick={() => setEditingLog(null)}
                  style={{ padding: 8, borderRadius: 8, border: "none", background: "#f3f4f6", cursor: "pointer" }}
                >
                  ✕
                </button>
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: "block" }}>
                  Kalite Puanı (1-5)
                </label>
                <div style={{ display: "flex", gap: 8 }}>
                  {[1, 2, 3, 4, 5].map((rating) => (
                    <button
                      key={rating}
                      onClick={() => setEditedRating(rating)}
                      style={{
                        padding: "8px 12px",
                        borderRadius: 8,
                        border: "1px solid #e5e7eb",
                        background: editedRating >= rating ? "#fbbf24" : "#fff",
                        cursor: "pointer",
                        fontSize: 16
                      }}
                    >
                      {editedRating >= rating ? "★" : "☆"}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: "block" }}>
                  Durum
                </label>
                <select
                  value={editedStatus}
                  onChange={(e) => setEditedStatus(e.target.value as any)}
                  style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 13, width: "100%" }}
                >
                  <option value="NEEDS_REVIEW">İnceleme Gerekiyor</option>
                  <option value="VERIFIED">Doğrulanmış</option>
                  <option value="CORRECTED">Düzeltilmiş</option>
                </select>
              </div>

              {editedStatus === "CORRECTED" && (
                <div style={{ marginBottom: 16 }}>
                  <label style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: "block" }}>
                    Düzeltilmiş Yanıt
                  </label>
                  <textarea
                    value={editedResponse}
                    onChange={(e) => setEditedResponse(e.target.value)}
                    rows={6}
                    style={{
                      width: "100%",
                      padding: "12px",
                      borderRadius: 8,
                      border: "1px solid #e5e7eb",
                      fontSize: 13,
                      fontFamily: "inherit"
                    }}
                  />
                </div>
              )}

              <div style={{ display: "flex", gap: 8 }}>
                <button
                  onClick={() => handleUpdateFeedback(editingLog.id)}
                  style={{
                    flex: 1,
                    padding: "10px 16px",
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    background: "#2563eb",
                    color: "#fff",
                    fontSize: 13,
                    cursor: "pointer"
                  }}
                >
                  Kaydet
                </button>
                <button
                  onClick={() => setEditingLog(null)}
                  style={{
                    padding: "10px 16px",
                    borderRadius: 8,
                    border: "1px solid #e5e7eb",
                    background: "#fff",
                    fontSize: 13,
                    cursor: "pointer"
                  }}
                >
                  İptal
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
