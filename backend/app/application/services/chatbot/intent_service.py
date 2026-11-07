"""LLM-based intent detection service for chatbot."""

import asyncio
import logging
from typing import Optional

from app.application.services.chatbot.intent_schemas import ChatbotIntent, ChatbotContext
from app.application.services.chatbot.llm_provider import LLMProvider

logger = logging.getLogger(__name__)


# Intent definitions
INTENT_DESCRIPTIONS = """
GENERAL: General greeting or unclear request
STUDENT_INFO: Information about students (list, count, details)
ATTENDANCE: Attendance records, presence, absence
GRADES: Grades, exam scores, academic performance, GNO
HOMEWORK: Homework assignments, submissions, deadlines
PAYMENTS: Payment records, payment history
PAYMENT_SUMMARY: Summary of payments (totals by period), cash collection
DEBT: Debt status, outstanding amounts, payment due, collection risk
EXPENSES: School expenses, expenditures
CANTEEN: Canteen operations, food, revenue, sales, POS transactions
CANTEEN_BALANCE: Canteen card balance, wallet balance
ANNOUNCEMENTS: School announcements, notifications
NOTIFICATIONS: User notifications
CONNECT_TEACHER: Connect or communicate with teachers
TEACHER_INFO: Information about teachers
CLASS_INFO: Information about classes
USER_INFO: User account information
REPORTS: Reports and analytics
SYSTEM_STATUS: System status, overview, statistics
"""


INTENT_DETECTION_PROMPT = f"""You are an intent detection system for a school management chatbot. 
Analyze the user's query and determine the intent.

Available intents:
{INTENT_DESCRIPTIONS}

Rules:
- Detect the PRIMARY intent based on what the user wants to know or do
- If the query is vague or unclear, use GENERAL
- For finance queries, distinguish between:
  * PAYMENTS: User wants to see payment records/history
  * PAYMENT_SUMMARY: User wants totals/summaries (e.g., "how much did I pay this month")
  * DEBT: User wants to know about outstanding debts
  * EXPENSES: User wants to see school expenses (admin/staff only)
- For attendance queries, detect if they want:
  * Specific status (today, this week)
  * Summary/count
  * List of absent students
- For grades, detect if they want:
  * Specific subject grades
  * Overall performance
  * Recent exam results
- Extract any mentioned student/teacher names in search_text
- Extract time periods (today, this week, this month, last month, etc.)
- DO NOT make up student_id or teacher_id - leave them null unless explicitly provided
- Set confidence based on how clear the intent is (0.0-1.0)

Respond with valid JSON only.
"""


class IntentDetectionService:
    """Service for detecting user intent using LLM."""

    def __init__(self, llm_provider: LLMProvider, timeout_seconds: float = 12.0):
        self.llm_provider = llm_provider
        self.timeout_seconds = timeout_seconds

    async def detect_intent(
        self,
        query: str,
        context: ChatbotContext,
    ) -> ChatbotIntent:
        """
        Detect intent from user query using LLM.

        Args:
            query: User's natural language query
            context: Chatbot context including user role and accessible entities

        Returns:
            ChatbotIntent: Detected intent with extracted parameters
        """
        # Build messages for LLM
        messages = [
            {
                "role": "system",
                "content": INTENT_DETECTION_PROMPT,
            },
            {
                "role": "system",
                "content": f"User role: {context.role}\n"
                          f"Current date: {context.current_date}\n"
                          f"Accessible students: {len(context.accessible_students)}\n"
                          f"Accessible teachers: {len(context.accessible_teachers)}",
            },
            {
                "role": "user",
                "content": query,
            },
        ]

        # Add conversation history if available
        if context.conversation_history:
            history_text = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in context.conversation_history[-5:]  # Last 5 messages
            ])
            messages.insert(
                -1,
                {
                    "role": "system",
                    "content": f"Recent conversation history:\n{history_text}",
                }
            )

        try:
            # Get structured response from LLM
            response = await asyncio.wait_for(
                self.llm_provider.structured_completion(
                    messages=messages,
                    response_schema=ChatbotIntent.model_json_schema(),
                    temperature=0.3,
                ),
                timeout=self.timeout_seconds,
            )

            # Parse and validate response
            intent = ChatbotIntent(**response)

            logger.info(
                f"Intent detected: {intent.intent} (confidence: {intent.confidence}) "
                f"for query: '{query}'"
            )

            return intent

        except Exception as e:
            # The caller owns the deterministic fallback. Returning GENERAL here
            # made detect_intent_with_fallback treat LLM failures as successes.
            logger.warning("Intent detection failed for query %r: %s", query, e)
            raise

    async def detect_intent_with_fallback(
        self,
        query: str,
        context: ChatbotContext,
    ) -> ChatbotIntent:
        """
        Detect intent with keyword-based fallback if LLM fails.

        This provides a safety net if LLM is unavailable.
        """
        logger.info(f"Starting intent detection for query: '{query}'")
        follow_up_intent = self._follow_up_intent(query, context)
        if follow_up_intent:
            logger.info("Using conversation follow-up intent: %s", follow_up_intent.intent)
            return follow_up_intent
        try:
            intent = await self.detect_intent(query, context)
            if intent.intent == "GENERAL" or intent.confidence < 0.6:
                fallback = self._fallback_intent_detection(query, context)
                if fallback.intent != "GENERAL":
                    return fallback
            logger.info(f"LLM intent detection succeeded: {intent.intent}")
            return intent
        except Exception as e:
            logger.warning(f"LLM intent detection failed, using fallback: {e}")
            fallback_intent = self._fallback_intent_detection(query, context)
            logger.info(f"Fallback intent: {fallback_intent.intent}")
            return fallback_intent

    def _follow_up_intent(
        self,
        query: str,
        context: ChatbotContext,
    ) -> Optional[ChatbotIntent]:
        """Resolve short follow-ups such as 'detayları aç' without another LLM call."""
        normalized_query = query.lower().strip()
        # Only context-only commands inherit a previous topic. A new question
        # such as 'borçları göster' must not inherit an earlier grades intent.
        detail_phrases = {
            "detay", "detaylar", "detayları", "detayları aç", "detayları göster",
            "detayını aç", "detayını göster", "aç", "göster", "sayfaya git",
            "incele", "detaylı göster", "detay sayfasını aç",
        }
        if normalized_query.rstrip(".!?") not in detail_phrases:
            return None

        for message in reversed(context.conversation_history):
            intent = message.get("intent")
            if intent:
                return ChatbotIntent(intent=intent, confidence=0.9, operation="details")
        return None

    def _fallback_intent_detection(
        self,
        query: str,
        context: ChatbotContext,
    ) -> ChatbotIntent:
        """
        Simple keyword-based fallback intent detection.
        Used only when LLM is unavailable.
        """
        query_lower = query.lower()

        # Canteen revenue & sales queries (high priority)
        canteen_revenue_keywords = [
            "kantin kazancı", "kantin cirosu", "kantin geliri", "kantin hasılatı",
            "kantin ne kadar kazandı", "günlük kantin satışı", "ciro nedir",
            "kantin cirosu ne kadar", "kantin geliri ne kadar", "bugünkü kantin",
            "bugünkü kantin cirosu", "kantin hasılatı ne kadar", "kantin kazancı ne kadar"
        ]
        if any(kw in query_lower for kw in canteen_revenue_keywords):
            return ChatbotIntent(intent="CANTEEN", confidence=0.8, operation="summary")

        # Student grades & academic performance
        elif any(kw in query_lower for kw in ["not", "sınav", "puan", "karne", "başarı", "gno"]):
            return ChatbotIntent(intent="GRADES", confidence=0.7)

        # Attendance queries
        elif any(kw in query_lower for kw in ["yoklama", "devamsızlık", "geldimi", "gelmedi"]):
            return ChatbotIntent(intent="ATTENDANCE", confidence=0.7)

        # Financial queries - debt & collection
        debt_keywords = [
            "borç", "borcum", "geciken ödemeler", "tahsilat oranı",
            "vadesi geçen", "tahsilat riski", "gecikme"
        ]
        if any(kw in query_lower for kw in debt_keywords):
            return ChatbotIntent(intent="DEBT", confidence=0.7)

        # Financial queries - payments
        elif any(kw in query_lower for kw in ["ödeme", "ödemeler", "son ödeme", "tahsilat"]):
            return ChatbotIntent(intent="PAYMENTS", confidence=0.7)

        # Financial queries - cash & kasa
        cash_keywords = ["kasa", "nakit", "tahsil edilen", "bugünkü tahsilat"]
        if any(kw in query_lower for kw in cash_keywords):
            return ChatbotIntent(intent="PAYMENT_SUMMARY", confidence=0.7)

        # Financial queries - expenses
        elif any(kw in query_lower for kw in ["gider", "harcama", "masraf"]):
            return ChatbotIntent(intent="EXPENSES", confidence=0.7)

        # Canteen balance & card
        canteen_balance_keywords = ["kantin bakiyesi", "kart bakiyesi", "cüzdan", "bakiye"]
        if any(kw in query_lower for kw in canteen_balance_keywords):
            return ChatbotIntent(intent="CANTEEN_BALANCE", confidence=0.7)

        # General canteen queries
        elif any(kw in query_lower for kw in ["kantin", "yemek", "pos"]):
            return ChatbotIntent(intent="CANTEEN", confidence=0.6)

        # Homework
        elif any(kw in query_lower for kw in ["ödev", "ev ödevi"]):
            return ChatbotIntent(intent="HOMEWORK", confidence=0.6)

        # Announcements & notifications
        elif any(kw in query_lower for kw in ["duyuru", "bildirim"]):
            intent = "NOTIFICATIONS" if "bildirim" in query_lower else "ANNOUNCEMENTS"
            return ChatbotIntent(intent=intent, confidence=0.6)

        # Teacher communication
        elif any(kw in query_lower for kw in ["öğretmen", "hocam", "hoca"]):
            return ChatbotIntent(intent="CONNECT_TEACHER", confidence=0.6)

        # Student information
        elif any(kw in query_lower for kw in ["öğrenci", "çocuk", "oğlum", "kızım"]):
            return ChatbotIntent(intent="STUDENT_INFO", confidence=0.6)

        # System status & statistics
        elif any(kw in query_lower for kw in ["durum", "kaç", "toplam", "rapor"]):
            return ChatbotIntent(intent="SYSTEM_STATUS", confidence=0.6)

        else:
            return ChatbotIntent(intent="GENERAL", confidence=0.3)
