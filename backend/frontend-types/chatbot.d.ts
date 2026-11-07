/**
 * SCS360 AI Chatbot Frontend Type Definitions
 * TypeScript interfaces for frontend integration with the chatbot API
 */

// ============================================
// Chat Message & Dialog Models
// ============================================

export interface ChatAction {
  label: string;      // Buton üstündeki yazı (örn: "💳 POS Satış Ekranı")
  actionTag: string;  // Web yönlendirme rotası (örn: "NAV_POS", "NAV_FINANCE")
}

export interface ChatMessage {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: string;
  senderRole: 'SUPERADMIN' | 'OWNER' | 'ADMIN' | 'MANAGER' | 'TEACHER' | 'FINANCE' | 'PARENT' | 'CANTEEN';
  actions?: ChatAction[];
  sentiment?: 'POSITIVE' | 'NEUTRAL' | 'QUESTION' | 'CRITICAL';
}

// ============================================
// LLM Fine-Tuning & Audit Log Models
// ============================================

export interface AiChatAuditLog {
  id: string;               // Benzersiz log ID (örn: "LOG-2026-001")
  sessionId: string;        // Oturum ID (örn: "SES-PAR-882")
  senderName: string;       // Kullanıcı Adı
  senderRole: string;       // Kullanıcı Rolü
  userQuery: string;        // Kullanıcının yazdığı orijinal prompt
  aiResponse: string;       // Chatbot'un ürettiği cevap
  topicCategory: string;    // Konu (örn: "Akademik & Karne", "Kantin & Finans", "Yoklama")
  timestamp: string;        // Tarih/Saat
  sentiment: 'POSITIVE' | 'NEUTRAL' | 'QUESTION' | 'CRITICAL';
  qualityRating: number;    // 1-5 arası insan puanı
  feedbackStatus: 'VERIFIED' | 'CORRECTED' | 'NEEDS_REVIEW';
  correctedResponse?: string; // RLHF kapsamında editlenmiş kusursuz yanıt
  tokenCount: number;       // Prompt + Completion tahmini token sayısı
  latencyMs: number;        // Yanıt süresi (ms)
  isFineTuningReady: boolean; // Dataset'e dahil edilsin mi?
}

// ============================================
// Role-Based Configuration Models
// ============================================

export interface SuggestionChip {
  label: string;
  actionTag: string;
}

export interface RoleChatConfig {
  role: string;
  greetingTitle: string;
  greetingSubtitle: string;
  themeColor: string;
  suggestionChips: SuggestionChip[];
}

// ============================================
// API Request/Response Models
// ============================================

export interface ChatbotQueryRequest {
  query: string;
  role: string;
  studentId?: string;
  conversationHistory: ChatbotHistoryMessage[];
}

export interface ChatbotHistoryMessage {
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
}

export interface ChatbotQueryResponse {
  success: boolean;
  intent: string;
  responseMarkdown: string;
  suggestedActions: ChatAction[];
  sentiment?: 'POSITIVE' | 'NEUTRAL' | 'QUESTION' | 'CRITICAL';
  timestamp?: string;
}

export interface FeedbackPayload {
  qualityRating: number;  // 1-5
  feedbackStatus: 'VERIFIED' | 'CORRECTED' | 'NEEDS_REVIEW';
  correctedResponse?: string;
  isFineTuningReady: boolean;
}

export interface AuditLogListResponse {
  success: boolean;
  logs: AiChatAuditLog[];
  total: number;
  page: number;
  pageSize: number;
}

// ============================================
// Analytics Models
// ============================================

export interface AnalyticsOverview {
  success: boolean;
  overview: {
    totalLogs: number;
    avgLatencyMs: number;
    avgQualityRating: number;
    finetuningReadyCount: number;
  };
  distributions: {
    sentiment: Record<string, number>;
    topic: Record<string, number>;
    intent: Record<string, number>;
    feedbackStatus: Record<string, number>;
  };
}

export interface AnalyticsTrends {
  success: boolean;
  periodDays: number;
  dailyTrends: Array<{ date: string; count: number }>;
  sentimentTrends: Record<string, Record<string, number>>;
}

export interface IntentPerformance {
  success: boolean;
  intentPerformance: Array<{
    intent: string;
    count: number;
    avgLatencyMs: number;
    avgQualityRating: number;
    verifiedCount: number;
    verificationRate: number;
  }>;
}

// ============================================
// WebSocket Event Types (for real-time updates)
// ============================================

export interface ChatbotWebSocketEvent {
  type: 'message' | 'typing' | 'error' | 'analytics_update';
  data: any;
  timestamp: string;
}

export interface RealtimeChatUpdate {
  sessionId: string;
  message: ChatMessage;
  intent?: string;
  sentiment?: string;
}

// ============================================
// Utility Types
// ============================================

export type ExportFormat = 'jsonl' | 'alpaca' | 'llama' | 'csv';

export type UserRole = 'SUPERADMIN' | 'OWNER' | 'ADMIN' | 'MANAGER' | 'TEACHER' | 'FINANCE' | 'PARENT' | 'CANTEEN';

export type SentimentType = 'POSITIVE' | 'NEUTRAL' | 'QUESTION' | 'CRITICAL';

export type FeedbackStatusType = 'VERIFIED' | 'CORRECTED' | 'NEEDS_REVIEW';
