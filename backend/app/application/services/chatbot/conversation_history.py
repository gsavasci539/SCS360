"""Conversation history tracking service for multi-turn chatbot conversations."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.models import AiChatAuditLog as AiChatAuditLogModel

logger = logging.getLogger(__name__)


class ConversationHistoryService:
    """Service for managing conversation history and context."""
    
    @staticmethod
    async def get_conversation_history(
        db: AsyncSession,
        session_id: str,
        limit: int = 10,
        *,
        user_id: UUID,
        organization_id: UUID | None,
    ) -> list[dict]:
        """
        Get conversation history for a session.
        
        Args:
            db: Database session
            session_id: Session identifier
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of conversation messages in chronological order
        """
        try:
            result = await db.execute(
                select(AiChatAuditLogModel)
                .where(AiChatAuditLogModel.session_id == session_id)
                .where(AiChatAuditLogModel.user_id == user_id, AiChatAuditLogModel.organization_id == organization_id)
                .order_by(AiChatAuditLogModel.created_at.asc(), AiChatAuditLogModel.id.asc())
                .limit(limit)
            )
            logs = result.scalars().all()
            
            history = []
            for log in logs:
                history.append({
                    "role": "user",
                    "content": log.user_query,
                    "timestamp": log.created_at.isoformat(),
                    "intent": log.detected_intent,
                    "sentiment": log.sentiment,
                })
                history.append({
                    "role": "assistant",
                    "content": log.ai_response,
                    "timestamp": log.created_at.isoformat(),
                    "sentiment": log.sentiment,
                })
            
            return history
        
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            raise
    
    @staticmethod
    async def get_recent_context(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 5,
    ) -> list[dict]:
        """
        Get recent chatbot interactions for a user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of recent interactions
            
        Returns:
            List of recent interactions
        """
        try:
            result = await db.execute(
                select(AiChatAuditLogModel)
                .where(AiChatAuditLogModel.user_id == user_id)
                .order_by(AiChatAuditLogModel.created_at.desc())
                .limit(limit)
            )
            logs = result.scalars().all()
            
            context = []
            for log in logs:
                context.append({
                    "query": log.user_query,
                    "response": log.ai_response,
                    "intent": log.detected_intent,
                    "topic": log.topic_category,
                    "timestamp": log.created_at.isoformat(),
                })
            
            return context
        
        except Exception as e:
            logger.error(f"Error getting recent context: {e}")
            return []
    
    @staticmethod
    async def get_session_summary(
        db: AsyncSession,
        session_id: str,
        *,
        user_id: UUID,
        organization_id: UUID | None,
    ) -> dict:
        """
        Get summary statistics for a conversation session.
        
        Args:
            db: Database session
            session_id: Session identifier
            
        Returns:
            Session summary with statistics
        """
        try:
            result = await db.execute(
                select(AiChatAuditLogModel)
                .where(AiChatAuditLogModel.session_id == session_id)
                .where(AiChatAuditLogModel.user_id == user_id, AiChatAuditLogModel.organization_id == organization_id)
                .order_by(AiChatAuditLogModel.created_at.asc(), AiChatAuditLogModel.id.asc())
            )
            logs = result.scalars().all()
            
            if not logs:
                return {
                    "session_id": session_id,
                    "message_count": 0,
                    "intents": [],
                    "topics": [],
                    "avg_latency": 0,
                    "sentiment_distribution": {},
                }
            
            # Calculate statistics
            message_count = len(logs)
            intents = [log.detected_intent for log in logs if log.detected_intent]
            topics = [log.topic_category for log in logs if log.topic_category]
            latencies = [log.latency_ms for log in logs if log.latency_ms]
            sentiments = [log.sentiment for log in logs if log.sentiment]
            
            # Intent distribution
            intent_distribution = {}
            for intent in intents:
                intent_distribution[intent] = intent_distribution.get(intent, 0) + 1
            
            # Topic distribution
            topic_distribution = {}
            for topic in topics:
                topic_distribution[topic] = topic_distribution.get(topic, 0) + 1
            
            # Sentiment distribution
            sentiment_distribution = {}
            for sentiment in sentiments:
                sentiment_distribution[sentiment] = sentiment_distribution.get(sentiment, 0) + 1
            
            # Average latency
            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            
            return {
                "session_id": session_id,
                "message_count": message_count,
                "intents": list(set(intents)),
                "topics": list(set(topics)),
                "intent_distribution": intent_distribution,
                "topic_distribution": topic_distribution,
                "avg_latency": round(avg_latency, 2),
                "sentiment_distribution": sentiment_distribution,
                "first_message_time": logs[0].created_at.isoformat() if logs else None,
                "last_message_time": logs[-1].created_at.isoformat() if logs else None,
            }
        
        except Exception as e:
            logger.error(f"Error getting session summary: {e}")
            raise
    
    @staticmethod
    async def get_user_conversation_stats(
        db: AsyncSession,
        user_id: UUID,
        *,
        organization_id: UUID | None,
    ) -> dict:
        """
        Get conversation statistics for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            User conversation statistics
        """
        try:
            result = await db.execute(
                select(AiChatAuditLogModel)
                .where(AiChatAuditLogModel.user_id == user_id)
                .where(AiChatAuditLogModel.organization_id == organization_id)
            )
            logs = result.scalars().all()
            
            if not logs:
                return {
                    "user_id": str(user_id),
                    "total_messages": 0,
                    "total_sessions": 0,
                    "favorite_topics": [],
                    "avg_quality_rating": 0,
                }
            
            # Get unique sessions
            sessions = set(log.session_id for log in logs)
            
            # Topic distribution
            topics = [log.topic_category for log in logs if log.topic_category]
            topic_distribution = {}
            for topic in topics:
                topic_distribution[topic] = topic_distribution.get(topic, 0) + 1
            
            # Favorite topics (top 3)
            favorite_topics = sorted(
                topic_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            # Average quality rating
            quality_ratings = [log.quality_rating for log in logs if log.quality_rating is not None and log.quality_rating > 0]
            avg_quality = sum(quality_ratings) / len(quality_ratings) if quality_ratings else 0
            
            return {
                "user_id": str(user_id),
                "total_messages": len(logs),
                "total_sessions": len(sessions),
                "favorite_topics": [{"topic": k, "count": v} for k, v in favorite_topics],
                "avg_quality_rating": round(avg_quality, 2),
                "topic_distribution": topic_distribution,
            }
        
        except Exception as e:
            logger.error(f"Error getting user conversation stats: {e}")
            raise


# Global conversation history service instance
conversation_history_service = ConversationHistoryService()
