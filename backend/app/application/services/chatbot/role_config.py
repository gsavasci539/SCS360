"""Role-based chatbot configuration for greetings, themes, and suggestion chips."""

from typing import Literal
from pydantic import BaseModel


class SuggestionChip(BaseModel):
    label: str
    action_tag: str


class RoleChatConfig(BaseModel):
    role: str
    greeting_title: str
    greeting_subtitle: str
    theme_color: str
    suggestion_chips: list[SuggestionChip]


ROLE_CONFIGS: dict[str, RoleChatConfig] = {
    "super_admin": RoleChatConfig(
        role="SUPERADMIN",
        greeting_title="Sistem Yönetimi, LLM Fine-Tuning ve Chat Analitik Danışmanı",
        greeting_subtitle="SCS360 yapay zeka sistemlerinin yönetimi ve analitiği için buradayım.",
        theme_color="#7C3AED",
        suggestion_chips=[
            SuggestionChip(
                label="🧠 LLM Chat Analitiği ve Konuşma Denetimi",
                action_tag="NAV_AI_ANALYTICS"
            ),
            SuggestionChip(
                label="📦 Fine-Tuning Eğitim Veri Seti Çıkar",
                action_tag="NAV_EXPORT_DATASET"
            ),
            SuggestionChip(
                label="📊 Konsolide Şube & Sistem Sağlığı",
                action_tag="NAV_SYSTEM_HEALTH"
            ),
        ]
    ),
    "owner": RoleChatConfig(
        role="OWNER",
        greeting_title="Kurumsal Yönetim & Finans Yapay Zeka Danışmanı",
        greeting_subtitle="Okulunuzun finansal ve operasyonel performansını analiz ediyorum.",
        theme_color="#059669",
        suggestion_chips=[
            SuggestionChip(
                label="📊 90 Günlük Nakit Akış Tahmini",
                action_tag="NAV_CASH_FLOW"
            ),
            SuggestionChip(
                label="🏫 Şubelerin Doluluk & Devam Oranları",
                action_tag="NAV_BRANCH_METRICS"
            ),
            SuggestionChip(
                label="⚠️ Vadesi Geçen Tahsilat Riski",
                action_tag="NAV_OVERDUE_RISK"
            ),
        ]
    ),
    "admin": RoleChatConfig(
        role="ADMIN",
        greeting_title="Okul Yönetimi, Operasyon & Yoklama Danışmanı",
        greeting_subtitle="Günlük operasyonlar, devam oranları ve okul yönetimi için yanıtlayabilirim.",
        theme_color="#2563EB",
        suggestion_chips=[
            SuggestionChip(
                label="📋 Bugünkü Okul Devam Oranı",
                action_tag="NAV_TODAY_ATTENDANCE"
            ),
            SuggestionChip(
                label="🥪 Günlük Kantin Kazancı & Ciro",
                action_tag="NAV_CANTEEN_REVENUE"
            ),
            SuggestionChip(
                label="📢 Yeni Kurumsal Duyuru Oluştur",
                action_tag="NAV_CREATE_ANNOUNCEMENT"
            ),
        ]
    ),
    "manager": RoleChatConfig(
        role="MANAGER",
        greeting_title="Şube Yönetimi & Operasyon Danışmanı",
        greeting_subtitle="Şube operasyonları, personel ve günlük yönetim için buradayım.",
        theme_color="#0891B2",
        suggestion_chips=[
            SuggestionChip(
                label="📋 Bugünkü Şube Devam Oranı",
                action_tag="NAV_TODAY_ATTENDANCE"
            ),
            SuggestionChip(
                label="🥪 Günlük Kantin Kazancı & Ciro",
                action_tag="NAV_CANTEEN_REVENUE"
            ),
            SuggestionChip(
                label="👥 Personel Durumu & Atamalar",
                action_tag="NAV_STAFF_STATUS"
            ),
        ]
    ),
    "teacher": RoleChatConfig(
        role="TEACHER",
        greeting_title="Öğretmen & Pedagojik AI Asistanı",
        greeting_subtitle="Ders planlama, öğrenci takibi ve eğitim materyalleri için yanıtlayabilirim.",
        theme_color="#D97706",
        suggestion_chips=[
            SuggestionChip(
                label="📝 8-A Matematik için 5 Soruluk Sınav Üret",
                action_tag="NAV_GENERATE_EXAM"
            ),
            SuggestionChip(
                label="📊 Ali Demir'in Akademik Gelişim Karnesi",
                action_tag="NAV_STUDENT_PROGRESS"
            ),
            SuggestionChip(
                label="💡 Ders İçi Etkinlik Önerisi",
                action_tag="NAV_CLASS_ACTIVITY"
            ),
        ]
    ),
    "accountant": RoleChatConfig(
        role="FINANCE",
        greeting_title="Mali İşler & Tahsilat Danışmanı",
        greeting_subtitle="Finansal raporlar, tahsilatlar ve muhasebe işlemleri için buradayım.",
        theme_color="#DC2626",
        suggestion_chips=[
            SuggestionChip(
                label="💰 Bugünkü Tahsilat ve Kasa Durumu",
                action_tag="NAV_DAILY_COLLECTION"
            ),
            SuggestionChip(
                label="⏳ Vadesi Yaklaşan Ödemeler Listesi",
                action_tag="NAV_UPCOMING_PAYMENTS"
            ),
            SuggestionChip(
                label="🥪 Kantin POS & Günlük Gelir Raporu",
                action_tag="NAV_CANTEEN_REVENUE"
            ),
        ]
    ),
    "parent": RoleChatConfig(
        role="PARENT",
        greeting_title="Veli Bilgilendirme & Öğrenci Rehberi",
        greeting_subtitle="Çocuğunuzun okul durumu, notları ve etkinlikleri hakkında bilgi alabilirsiniz.",
        theme_color="#7C3AED",
        suggestion_chips=[
            SuggestionChip(
                label="📊 Çocuğumun Notları ve Ders Durumu",
                action_tag="NAV_GRADES"
            ),
            SuggestionChip(
                label="🥪 Kantin Harcamaları ve Kart Bakiyesi",
                action_tag="NAV_CANTEEN_BALANCE"
            ),
            SuggestionChip(
                label="📅 Sınav Tarihleri ve Ödevler",
                action_tag="NAV_EXAMS_HOMEWORK"
            ),
        ]
    ),
    "canteen_staff": RoleChatConfig(
        role="CANTEEN",
        greeting_title="Kantin & POS Satış Asistanı",
        greeting_subtitle="Kantin satışları, stok durumu ve günlük raporlar için buradayım.",
        theme_color="#EA580C",
        suggestion_chips=[
            SuggestionChip(
                label="💰 Bugünkü Toplam Kantin Cirosu",
                action_tag="NAV_CANTEEN_REVENUE"
            ),
            SuggestionChip(
                label="🥪 En Çok Satan Ürünler ve Stok Durumu",
                action_tag="NAV_TOP_PRODUCTS"
            ),
            SuggestionChip(
                label="📄 Günlük Mali Z-Raporu Dökümü",
                action_tag="NAV_Z_REPORT"
            ),
        ]
    ),
}


def get_role_config(role: str) -> RoleChatConfig:
    """Get chatbot configuration for a specific role."""
    normalized_role = role.lower().strip()
    
    # Map common role variations
    role_mapping = {
        "superadmin": "super_admin",
        "org_admin": "admin",
        "branch_manager": "manager",
        "administrator": "admin",
        "finance": "accountant",
        "canteen": "canteen_staff",
    }
    
    normalized_role = role_mapping.get(normalized_role, normalized_role)
    
    return ROLE_CONFIGS.get(normalized_role, ROLE_CONFIGS["parent"])


def get_all_role_configs() -> list[RoleChatConfig]:
    """Get all role configurations."""
    return list(ROLE_CONFIGS.values())
