import { Send, ArrowLeft } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { api, apiMessage } from "../../lib/api";
import type { ApiResponse } from "../../types/api";

interface ChatMessage {
  id: string;
  sender_id: string;
  receiver_id: string;
  content: string;
  is_read: boolean;
  sent_at: string;
  sender_name?: string;
  is_current_user: boolean;
}

interface ChatInterfaceProps {
  studentId: string;
  teacherId?: string;
  parentId?: string;
  teacherName: string;
  onBack: () => void;
  apiBase?: string;
}

export function ChatInterface({ studentId, teacherId, parentId, teacherName, onBack, apiBase = "/parent" }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadMessages();
    // Poll for new messages every 5 seconds
    const interval = setInterval(loadMessages, 5000);
    return () => clearInterval(interval);
  }, [studentId, teacherId, parentId, apiBase]);

  async function loadMessages() {
    try {
      const endpoint = teacherId 
        ? `${apiBase}/child/${studentId}/chat/${teacherId}`
        : `${apiBase}/chat/${studentId}${parentId ? `?parent_id=${encodeURIComponent(parentId)}` : ""}`;
      const response = await api.get<ApiResponse<ChatMessage[]>>(endpoint);
      setMessages(response.data.data || []);
      setError("");
    } catch (reason) {
      setError(apiMessage(reason));
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!newMessage.trim() || sending) return;

    setSending(true);
    try {
      const endpoint = teacherId 
        ? `${apiBase}/child/${studentId}/chat/${teacherId}`
        : `${apiBase}/chat/${studentId}${parentId ? `?parent_id=${encodeURIComponent(parentId)}` : ""}`;
      await api.post(endpoint, {
        message: newMessage
      });
      setNewMessage("");
      await loadMessages();
    } catch (reason) {
      setError(apiMessage(reason));
    } finally {
      setSending(false);
    }
  }

  return (
    <div style={{ height: "100%", minHeight: 0, display: "flex", flexDirection: "column" }}>
      {/* Chat Header */}
      <div style={{
        padding: "16px 24px",
        borderBottom: "1px solid #e0e0e0",
        background: "white",
        display: "flex",
        alignItems: "center",
        gap: 16
      }}>
        <button
          aria-label="Sohbeti kapat"
          onClick={onBack}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 8,
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}
        >
          <ArrowLeft size={20} style={{ color: "#666" }} />
        </button>
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 600, color: "#2c3e50" }}>
            {teacherName}
          </h3>
          <p style={{ margin: 0, fontSize: "12px", color: "#546e7a" }}>
            {messages.length > 0 ? `${messages.length} mesaj` : "Yeni mesaj"}
          </p>
        </div>
      </div>

      {/* Messages Area */}
      <div style={{
        flex: 1,
        overflow: "auto",
        padding: "24px 32px",
        background: "#f8faf9",
        display: "flex",
        flexDirection: "column",
        gap: 16
      }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 40 }}>
            <div style={{ color: "#999", fontSize: "14px" }}>Mesajlar yükleniyor...</div>
          </div>
        ) : error ? (
          <div style={{ textAlign: "center", padding: 40, color: "#c34b4b" }}>
            {error}
          </div>
        ) : messages.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40, color: "#546e7a" }}>
            <div style={{ fontSize: "48px", marginBottom: 16 }}>💬</div>
            <p style={{ margin: 0, fontSize: "16px" }}>Henüz mesaj yok</p>
            <p style={{ margin: 0, fontSize: "14px", marginTop: 8 }}>
              İlk mesajı göndererek konuşmayı başlatın
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                display: "flex",
                justifyContent: msg.is_current_user ? "flex-end" : "flex-start",
                maxWidth: "70%"
              }}
            >
              <div style={{
                padding: "12px 16px",
                borderRadius: 16,
                background: msg.is_current_user 
                  ? "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
                  : "white",
                color: msg.is_current_user ? "white" : "#2c3e50",
                boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
                borderBottomLeftRadius: msg.is_current_user ? 16 : 4,
                borderBottomRightRadius: msg.is_current_user ? 4 : 16
              }}>
                <div style={{ fontSize: "14px", lineHeight: 1.5, marginBottom: 4 }}>
                  {msg.content}
                </div>
                <div style={{ 
                  fontSize: "11px", 
                  opacity: 0.7,
                  textAlign: "right"
                }}>
                  {new Date(msg.sent_at).toLocaleTimeString("tr-TR", {
                    hour: "2-digit",
                    minute: "2-digit"
                  })}
                  {msg.is_current_user && msg.is_read && " ✓"}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input */}
      <div style={{
        padding: "16px 24px",
        borderTop: "1px solid #e0e0e0",
        background: "white"
      }}>
        <form onSubmit={sendMessage} style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
          <div style={{ flex: 1 }}>
            <textarea
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Mesajınızı yazın..."
              rows={1}
              style={{
                width: "100%",
                padding: "12px 16px",
                borderRadius: 24,
                border: "1px solid #e0e0e0",
                fontSize: "14px",
                resize: "none",
                outline: "none",
                maxHeight: 120
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage(e);
                }
              }}
            />
          </div>
          <button
            type="submit"
            aria-label="Sohbet mesajını gönder"
            disabled={!newMessage.trim() || sending}
            className="btn btn-primary"
            style={{
              width: 48,
              height: 48,
              padding: 0,
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              opacity: (!newMessage.trim() || sending) ? 0.5 : 1
            }}
          >
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
}
