import { reportClientError } from "../lib/diagnostics";
import { useState, useRef, useEffect } from "react";
import { X, Send, Loader2 } from "lucide-react";
import { BrandMark } from "./Brand";
import { useNavigate } from "react-router-dom";
import { api, apiMessage } from "../lib/api";
import { useAuthStore } from "../stores/auth";
import ReactMarkdown from "react-markdown";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  actions?: SuggestedAction[];
  intent?: string;
  showStudentSelector?: boolean;
  sourceQuery?: string;
}

interface SuggestedAction {
  label: string;
  action_tag: string;
  target_teacher_id?: string;
}

interface RoleBasedGreeting {
  title: string;
  subtitle: string;
  suggestions: string[];
}

interface StudentOption {
  student_id: string;
  first_name: string;
  last_name: string;
}

interface ChatbotResponse {
  success: boolean;
  intent: string;
  response_markdown: string;
  suggested_actions: SuggestedAction[];
}

const isDetailRequest = (value: string) => /detay|sayfaya git|incele|aç|göster/i.test(value);

const ROLE_BASED_GREETINGS: Record<string, RoleBasedGreeting> = {
  "super_admin": {
    title: "Sistem Yönetimi, LLM Fine-Tuning ve Chat Analitik Danışmanı",
    subtitle: "Size nasıl yardımcı olabilirim?",
    suggestions: [
      "🧠 LLM Chat Analitiği ve Konuşma Denetimi",
      "📦 Fine-Tuning Eğitim Veri Seti Çıkar",
      "📊 Konsolide Şube & Sistem Sağlığı"
    ]
  },
  "owner": {
    title: "Kurumsal Yönetim & Finans Yapay Zeka Danışmanı",
    subtitle: "Size nasıl yardımcı olabilirim?",
    suggestions: [
      "📊 90 Günlük Nakit Akış Tahmini",
      "🏫 Şubelerin Doluluk & Devam Oranları",
      "⚠️ Vadesi Geçen Tahsilat Riski"
    ]
  },
  "admin": {
    title: "Okul Yönetimi, Operasyon & Yoklama Danışmanı",
    subtitle: "Size nasıl yardımcı olabilirim?",
    suggestions: [
      "📋 Bugünkü Okul Devam Oranı",
      "🥪 Günlük Kantin Kazancı & Ciro",
      "📢 Yeni Kurumsal Duyuru Oluştur"
    ]
  },
  "teacher": {
    title: "Öğretmen & Pedagojik AI Asistanı",
    subtitle: "Size nasıl yardımcı olabilirim?",
    suggestions: [
      "📝 8-A Matematik için 5 Soruluk Sınav Üret",
      "📊 Ali Demir'in Akademik Gelişim Karnesi",
      "💡 Ders İçi Etkinlik Önerisi"
    ]
  },
  "finance": {
    title: "Mali İşler & Tahsilat Danışmanı",
    subtitle: "Size nasıl yardımcı olabilirim?",
    suggestions: [
      "💰 Bugünkü Tahsilat ve Kasa Durumu",
      "⏳ Vadesi Yaklaşan Ödemeler Listesi",
      "🥪 Kantin POS & Günlük Gelir Raporu"
    ]
  },
  "parent": {
    title: "Veli Bilgilendirme & Öğrenci Rehberi",
    subtitle: "Size nasıl yardımcı olabilirim?",
    suggestions: [
      "📊 Çocuğumun Notları ve Ders Durumu",
      "🥪 Kantin Harcamaları ve Kart Bakiyesi",
      "📅 Sınav Tarihleri ve Ödevler"
    ]
  },
  "canteen": {
    title: "Kantin & POS Satış Asistanı",
    subtitle: "Size nasıl yardımcı olabilirim?",
    suggestions: [
      "💰 Bugünkü Toplam Kantin Cirosu",
      "🥪 En Çok Satan Ürünler ve Stok Durumu",
      "📄 Günlük Mali Z-Raporu Dökümü"
    ]
  }
};

export function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [students, setStudents] = useState<StudentOption[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageSequence = useRef(0);
  const nextMessageId = () => String(++messageSequence.current);
  const canReadStudents = useAuthStore((state) => state.can("students.read"));

  const isParent = !user?.is_super_admin && (user?.roles.some((role) => role.slug.toLowerCase() === "parent") ?? false);
  const isStaff = Boolean(user?.is_super_admin || user?.roles.some((role) => role.slug.toLowerCase() !== "parent"));

  const userRole = user?.is_super_admin ? "super_admin" : isParent ? "parent" : user?.roles?.[0]?.slug?.toLowerCase() || "staff";
  const greetingRoles: Record<string, string> = { accountant: "finance", canteen_staff: "canteen", administrator: "admin", org_admin: "admin", branch_manager: "admin", manager: "admin" };
  const roleGreeting = ROLE_BASED_GREETINGS[greetingRoles[userRole] || userRole] || {
    title: "SCS360 Asistan", subtitle: "Size nasıl yardımcı olabilirim?", suggestions: ["Merhaba", "Hangi işlemleri yapabilirim?"],
  };

  useEffect(() => {
    if (!isOpen || students.length) return;

    if (isParent) {
      api.get<{ data?: StudentOption[] }>("/parent/my-children")
        .then((response) => {
          const availableStudents = response.data.data || [];
          setStudents(availableStudents);
          setSelectedStudentId(availableStudents[0]?.student_id || "");
        })
        .catch(() => setStudents([]));
    } else if (isStaff && canReadStudents) {
      // For staff users, get all students
      api.get<{ data?: { id: string; first_name: string; last_name: string }[] | { items: { id: string; first_name: string; last_name: string }[] } }>("/students", { params: { page: 1, page_size: 100 } })
        .then((response) => {
          const result = response.data.data;
          const records = Array.isArray(result) ? result : result?.items || [];
          const availableStudents = records.map((s) => ({
            student_id: s.id,
            first_name: s.first_name,
            last_name: s.last_name
          }));
          setStudents(availableStudents);
          setSelectedStudentId(availableStudents[0]?.student_id || "");
        })
        .catch(() => setStudents([]));
    }
  }, [isOpen, isParent, isStaff, canReadStudents, students.length]);

  const getStudentId = () => selectedStudentId || null;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (query = input, chosenStudentId = selectedStudentId) => {
    const queryText = query.trim();
    if (!queryText || isLoading) return;

    const userMessage: Message = {
      id: nextMessageId(),
      role: "user",
      content: queryText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const studentId = chosenStudentId || null;
      const conversationHistory = messages
        .filter((message) => message.content)
        .slice(-6)
        .map((message) => ({ role: message.role, content: message.content, intent: message.intent }));


      const payload = {
        query: queryText,
        role: userRole.toUpperCase(),
        student_id: studentId,
        conversation_history: conversationHistory,
      };
      const response = isParent
        ? await api.post<ChatbotResponse>("/parent/chatbot", payload)
        : await api.post<ChatbotResponse>("/v1/chatbot/process-query", payload);


      // Handle ApiResponse wrapper structure
      const responseData = (response.data as any).data || response.data;
      
      const assistantMessage: Message = {
        id: nextMessageId(),
        role: "assistant",
        content: responseData.response_markdown || "Yanıt alınamadı.",
        timestamp: new Date(),
        intent: responseData.intent,
        showStudentSelector: responseData.response_markdown?.includes("öğrenci seçin") && !studentId,
        sourceQuery: queryText,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // A short follow-up such as "detayları aç" should navigate immediately;
      // regular responses keep their detail buttons visible for the user.
      const detailAction = isDetailRequest(queryText) && responseData.intent !== "GENERAL"
        ? responseData.suggested_actions?.find((action: SuggestedAction) => action.action_tag.startsWith("VIEW_"))
        : undefined;
      if (detailAction) {
        await handleActionClick(detailAction);
        return;
      }

      // Handle suggested actions
      if (responseData.suggested_actions && responseData.suggested_actions.length > 0) {
        const actionsMessage: Message = {
          id: nextMessageId(),
          role: "assistant",
          content: "",
          timestamp: new Date(),
          actions: responseData.suggested_actions,
        };
        setMessages((prev) => [...prev, actionsMessage]);
      }
    } catch (error) {
      const errorResponse: Message = {
        id: nextMessageId(),
        role: "assistant",
        content: apiMessage(error),
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorResponse]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleActionClick = async (action: SuggestedAction) => {
    // Handle teacher connection
    if (action.action_tag.startsWith("CONNECT_TEACHER_")) {
      try {
        const teacherId = action.target_teacher_id;
        const studentId = getStudentId();
        
        if (!teacherId || !studentId) {
          const errorMessage: Message = {
            id: nextMessageId(),
            role: "assistant",
            content: "Öğretmen bağlantısı için lütfen önce bir öğrenci seçin.",
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errorMessage]);
          return;
        }

        const response = await api.post("/v1/chatbot/chat/conversations/connect-teacher", {
          student_id: studentId,
          teacher_id: teacherId,
          teacher_name: action.label.replace("💬 ", "").replace("'a Bağlan", ""),
          initial_message: "Chatbot Asistanı üzerinden ulaşıyorum.",
          created_via: "CHATBOT",
        });

        const connection = response.data.data || response.data;
        const successMessage: Message = {
          id: nextMessageId(),
          role: "assistant",
          content: `✅ ${connection.participant_name} ile sohbet başlatıldı!`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, successMessage]);
      } catch (error: any) {
        reportClientError("Connect teacher error:", error);
        const errorMessage: Message = {
          id: nextMessageId(),
          role: "assistant",
          content: "Sohbet başlatılırken bir hata oluştu.",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    }
    else {
      const parentPaths: Record<string, string> = {
        VIEW_ATTENDANCE: "/parent/attendance",
        VIEW_ATTENDANCE_REPORT: "/parent/attendance",
        VIEW_GRADES: "/parent/academic",
        VIEW_PAYMENTS: "/parent/finances",
        VIEW_DEBTS: "/parent/finances",
        VIEW_STUDENTS: "/parent/children",
        VIEW_HOMEWORK: "/parent/homework",
        VIEW_ANNOUNCEMENTS: "/parent/announcements",
        VIEW_NOTIFICATIONS: "/parent/dashboard",
        VIEW_REPORTS: "/parent/reports",
      };
      const staffPaths: Record<string, string> = {
        VIEW_ATTENDANCE: "/attendance",
        VIEW_ATTENDANCE_REPORT: "/reports/attendance",
        VIEW_GRADES: "/students",
        VIEW_PAYMENTS: "/finance/payments",
        VIEW_DEBTS: "/finance/debts",
        VIEW_EXPENSES: "/finance/expenses",
        VIEW_STUDENTS: "/students",
        VIEW_DASHBOARD: "/dashboard",
        VIEW_USERS: "/users",
        VIEW_HOMEWORK: "/homework",
        VIEW_ANNOUNCEMENTS: "/announcements",
        VIEW_NOTIFICATIONS: "/notifications",
        VIEW_CANTEEN: "/canteen",
        VIEW_CANTEEN_BALANCE: "/canteen/card-balance",
        VIEW_REPORTS: "/reports",
      };
      const path = (isParent ? parentPaths : staffPaths)[action.action_tag];

      if (path) {
        setIsOpen(false);
        navigate(path);
        return;
      }

      setMessages((prev) => [...prev, {
        id: Date.now().toString(),
        role: "assistant",
        content: `${action.label} sayfası için erişim yetkiniz bulunmuyor.`,
        timestamp: new Date(),
      }]);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="chatbot-fab"
        style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          width: "56px",
          height: "56px",
          borderRadius: "18px",
          backgroundColor: "transparent",
          color: "white",
          border: "none",
          cursor: "pointer",
          boxShadow: "0 4px 12px rgba(20, 42, 45, 0.25)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 900,
          transition: "transform 0.2s, box-shadow 0.2s",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = "scale(1.05)";
          e.currentTarget.style.boxShadow = "0 6px 16px rgba(20, 42, 45, 0.35)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = "scale(1)";
          e.currentTarget.style.boxShadow = "0 4px 12px rgba(20, 42, 45, 0.25)";
        }}
        aria-label="Chatbot'u aç"
      >
        <BrandMark size={56} />
      </button>
    );
  }

  return (
    <div
      className="chatbot-container"
      style={{
        position: "fixed",
        bottom: "24px",
        right: "24px",
        width: "min(380px, calc(100vw - 48px))",
        maxHeight: "min(600px, calc(100dvh - 48px))",
        backgroundColor: "white",
        borderRadius: "16px",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.12)",
        zIndex: 900,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "16px",
          backgroundColor: "#163b3b",
          color: "white",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <BrandMark size={30} />
          <div>
            <div style={{ fontWeight: 600, fontSize: "16px" }}>SCS360 Asistan</div>
            <div style={{ fontSize: "12px", opacity: 0.9 }}>Size nasıl yardımcı olabilirim?</div>
          </div>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          style={{
            background: "none",
            border: "none",
            color: "white",
            cursor: "pointer",
            padding: "4px",
            borderRadius: "4px",
          }}
          aria-label="Chatbot'u kapat"
        >
          <X size={20} />
        </button>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
          maxHeight: "400px",
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: "center",
              color: "#6b7280",
              padding: "20px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}><BrandMark size={48} /></div>
            <div style={{ fontWeight: 600, fontSize: "16px", marginBottom: "4px" }}>
              {roleGreeting.title}
            </div>
            <div style={{ fontSize: "12px", marginBottom: "16px" }}>
              {roleGreeting.subtitle}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "12px" }}>
              {roleGreeting.suggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => void handleSendMessage(suggestion)}
                  style={{
                    padding: "8px 12px",
                    backgroundColor: "#f3f4f6",
                    color: "#1f2937",
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                    cursor: "pointer",
                    fontSize: "13px",
                    textAlign: "left",
                    transition: "background 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = "#e5e7eb";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = "#f3f4f6";
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            style={{
              display: "flex",
              flexDirection: message.role === "user" ? "row-reverse" : "row",
              gap: "8px",
            }}
          >
            <div
              style={{
                maxWidth: "80%",
                padding: "12px",
                borderRadius: "12px",
                backgroundColor: message.role === "user" ? "#2563eb" : "#f3f4f6",
                color: message.role === "user" ? "white" : "#1f2937",
                fontSize: "14px",
                lineHeight: "1.5",
              }}
            >
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p style={{ margin: "0 0 8px 0" }}>{children}</p>,
                  ul: ({ children }) => <ul style={{ margin: "0 0 8px 0", paddingLeft: "20px" }}>{children}</ul>,
                  ol: ({ children }) => <ol style={{ margin: "0 0 8px 0", paddingLeft: "20px" }}>{children}</ol>,
                  li: ({ children }) => <li style={{ marginBottom: "4px" }}>{children}</li>,
                  strong: ({ children }) => <strong>{children}</strong>,
                  em: ({ children }) => <em>{children}</em>,
                  code: ({ children }) => <code style={{ backgroundColor: "#f3f4f6", padding: "2px 4px", borderRadius: "4px", fontSize: "12px" }}>{children}</code>,
                }}
              >
                {message.content}
              </ReactMarkdown>
              {(message as any).showStudentSelector && students.length > 0 && (
                <div style={{ marginTop: "12px" }}>
                  <select
                    aria-label="Bu mesaj için öğrenci seçin"
                    value={selectedStudentId}
                    onChange={(event) => {
                      const nextStudent = event.target.value;
                      setSelectedStudentId(nextStudent);
                      if (nextStudent && message.sourceQuery) void handleSendMessage(message.sourceQuery, nextStudent);
                    }}
                    style={{
                      padding: "8px 12px",
                      border: "1px solid #d1d5db",
                      borderRadius: "8px",
                      fontSize: "13px",
                      width: "100%",
                      maxWidth: "200px",
                    }}
                  >
                    <option value="">Öğrenci seçin...</option>
                    {students.map((student) => (
                      <option key={student.student_id} value={student.student_id}>
                        {student.first_name} {student.last_name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {(message as any).actions && (message as any).actions.length > 0 && (
                <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                  {(message as any).actions.map((action: SuggestedAction, idx: number) => (
                    <button
                      key={idx}
                      onClick={() => handleActionClick(action)}
                      style={{
                        padding: "8px 12px",
                        backgroundColor: message.role === "user" ? "#1d4ed8" : "#e5e7eb",
                        color: message.role === "user" ? "white" : "#1f2937",
                        border: "none",
                        borderRadius: "8px",
                        cursor: "pointer",
                        fontSize: "13px",
                        textAlign: "left",
                        transition: "background 0.2s",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = message.role === "user" ? "#1e40af" : "#d1d5db";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = message.role === "user" ? "#1d4ed8" : "#e5e7eb";
                      }}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div style={{ display: "flex", gap: "8px", padding: "12px" }}>
            <div
              style={{
                padding: "12px",
                borderRadius: "12px",
                backgroundColor: "#f3f4f6",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <Loader2 size={16} className="animate-spin" />
              <span style={{ fontSize: "14px", color: "#6b7280" }}>Yazıyor...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div
        style={{
          padding: "12px",
          borderTop: "1px solid #e5e7eb",
          display: "flex",
          gap: "8px",
        }}
      >
        {(isParent || isStaff) && students.length > 0 && (
          <select
            value={selectedStudentId}
            onChange={(event) => setSelectedStudentId(event.target.value)}
            disabled={isLoading}
            aria-label="Öğrenci seçin"
            style={{ maxWidth: "145px", padding: "10px 6px", border: "1px solid #d1d5db", borderRadius: "8px", fontSize: "13px" }}
          >
            {students.map((student) => (
              <option key={student.student_id} value={student.student_id}>
                {student.first_name} {student.last_name}
              </option>
            ))}
          </select>
        )}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Bir şey yazın..."
          disabled={isLoading}
          style={{
            flex: 1,
            padding: "10px 14px",
            border: "1px solid #d1d5db",
            borderRadius: "8px",
            fontSize: "14px",
            outline: "none",
          }}
          onFocus={(e) => e.currentTarget.style.borderColor = "#2563eb"}
          onBlur={(e) => e.currentTarget.style.borderColor = "#d1d5db"}
        />
        <button
          aria-label="Mesaj gönder"
          onClick={() => void handleSendMessage()}
          disabled={!input.trim() || isLoading}
          style={{
            padding: "10px 14px",
            backgroundColor: input.trim() && !isLoading ? "#2563eb" : "#9ca3af",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor: input.trim() && !isLoading ? "pointer" : "not-allowed",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
        </button>
      </div>
    </div>
  );
}
