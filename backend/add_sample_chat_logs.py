import asyncio
from datetime import datetime
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import hash_password
from app.infrastructure.models.models import (
    AiChatAuditLog, User
)

async def add_sample_chat_logs():
    async for db in get_db():
        # Get super admin user
        user_result = await db.execute(
            select(User).where(User.email == "superadmin@scs360.com")
        )
        super_admin = user_result.scalar_one_or_none()
        
        if not super_admin:
            print("Super admin bulunamadı!")
            return
        
        print(f"Super admin bulundu: {super_admin.first_name} {super_admin.last_name}")
        print(f"Organization ID: {super_admin.organization_id}")
        
        if not super_admin.organization_id:
            print("Super admin'in organization_id'si None, varsayılan olarak 1 kullanılıyor")
            super_admin.organization_id = "1"
        
        # Sample chat logs
        sample_logs = [
            {
                "session_id": "SES-SUP-001",
                "user_query": "Kantin cirosu ne kadar?",
                "ai_response": "Bugunku toplam kantin cirosu 1420 TL olup 68 fis kesilmistir.",
                "detected_intent": "CANTEEN",
                "topic_category": "Kantin & Finans",
                "sentiment": "QUESTION",
                "quality_rating": 4,
                "feedback_status": "VERIFIED",
                "token_count": 25,
                "latency_ms": 1200,
                "is_fine_tuning_ready": True,
            },
            {
                "session_id": "SES-SUP-002",
                "user_query": "Bugunku okul devam orani nedir?",
                "ai_response": "Bugunku okul devam orani %92.5 olarak olculmustur.",
                "detected_intent": "ATTENDANCE",
                "topic_category": "Yoklama",
                "sentiment": "QUESTION",
                "quality_rating": 5,
                "feedback_status": "VERIFIED",
                "token_count": 30,
                "latency_ms": 1500,
                "is_fine_tuning_ready": True,
            },
            {
                "session_id": "SES-SUP-003",
                "user_query": "Ali Demir'in not durumu nasil?",
                "ai_response": "Ali Demir (8-A) GNO: 88.50 / 100 ile sinif 2.sidir.",
                "detected_intent": "GRADES",
                "topic_category": "Akademik & Karne",
                "sentiment": "QUESTION",
                "quality_rating": 3,
                "feedback_status": "NEEDS_REVIEW",
                "token_count": 28,
                "latency_ms": 1800,
                "is_fine_tuning_ready": False,
            },
            {
                "session_id": "SES-SUP-004",
                "user_query": "Gunluk tahsilat durumu nedir?",
                "ai_response": "Bugunku toplam tahsilat 15000 TL olup vadesi gecen borc 2500 TL'dir.",
                "detected_intent": "PAYMENT_SUMMARY",
                "topic_category": "Finans",
                "sentiment": "QUESTION",
                "quality_rating": 4,
                "feedback_status": "VERIFIED",
                "token_count": 32,
                "latency_ms": 1100,
                "is_fine_tuning_ready": True,
            },
            {
                "session_id": "SES-SUP-005",
                "user_query": "Tesekkurler, cok yardimci oldunuz!",
                "ai_response": "Rica ederim! Baska bir konuda yardimci olabilir miyim?",
                "detected_intent": "GENERAL",
                "topic_category": "Genel",
                "sentiment": "POSITIVE",
                "quality_rating": 5,
                "feedback_status": "VERIFIED",
                "token_count": 20,
                "latency_ms": 800,
                "is_fine_tuning_ready": True,
            },
        ]
        
        # Add sample logs
        for i, log_data in enumerate(sample_logs):
            audit_log = AiChatAuditLog(
                session_id=log_data["session_id"],
                user_id=super_admin.id,
                organization_id=super_admin.organization_id or "1",
                user_query=log_data["user_query"],
                ai_response=log_data["ai_response"],
                detected_intent=log_data["detected_intent"],
                topic_category=log_data["topic_category"],
                sentiment=log_data["sentiment"],
                quality_rating=log_data["quality_rating"],
                feedback_status=log_data["feedback_status"],
                token_count=log_data["token_count"],
                latency_ms=log_data["latency_ms"],
                is_fine_tuning_ready=log_data["is_fine_tuning_ready"],
                meta_data={
                    "sender_role": "SUPERADMIN",
                    "confidence": 0.85,
                }
            )
            db.add(audit_log)
            print(f"  - Sample log {i+1} eklendi: {log_data['user_query'][:30]}...")
        
        await db.commit()
        print(f"\nToplam {len(sample_logs)} örnek chat log eklendi!")
        
        break

if __name__ == "__main__":
    asyncio.run(add_sample_chat_logs())
