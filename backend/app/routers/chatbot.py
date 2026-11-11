from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy import String, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.platform_workspace import WorkspacePrincipal
from app.core.permissions import PermissionChecker
from app.core.responses import success_response

from app.domain.entities.user import User
from app.domain.entities.student_teacher import (
    ChatbotQueryRequest,
    TeacherInfo,
    ChatAction,
)
from app.domain.entities.chat_conversation import ChatConversationCreate
from app.domain.entities.ai_chat_audit_log import (
    AiChatAuditLogResponse,
    AuditLogListResponse,
    FeedbackPayload,
)

from app.infrastructure.models.models import (
    ChatConversation,
    ChatMessage,
    Student,
    StudentTeacherAssignment,
    User as UserModel,
    ClassRoom,
    AiChatAuditLog as AiChatAuditLogModel,
)

from app.application.services.chatbot.context_service import ContextService
from app.application.services.chatbot.date_resolution import DateResolutionService
from app.core.exceptions import AppException
from app.application.services.chatbot.handlers import HandlerDispatcher
from app.application.services.chatbot.intent_schemas import ResolvedIntent
from app.application.services.chatbot.intent_service import IntentDetectionService
from app.application.services.chatbot.llm_provider import get_llm_provider
from app.application.services.chatbot.role_config import get_role_config
from app.application.services.chatbot.dataset_export import DatasetExportService
from app.application.services.chatbot.sentiment_analysis import analyze_sentiment
from app.application.services.chatbot.conversation_history import conversation_history_service

router = APIRouter(
    prefix="/api/v1/chatbot",
    tags=["Chatbot"],
)

logger = logging.getLogger(__name__)


async def require_ai_workspace_admin(user: User = Depends(get_current_user)):
    """Only a real platform operator with an explicitly selected institution."""
    if not isinstance(user, WorkspacePrincipal):
        raise HTTPException(403, "Sohbet denetimi için platform yöneticisi kurum seçmelidir")
    return user

ROLE_PARENT = "parent"
ROLE_TEACHER = "teacher"
ADMIN_ROLES = {"super_admin", "org_admin", "branch_manager", "manager", "administrator", "owner"}
STAFF_ROLES = {"accountant", "staff", "canteen_staff"}

# Initialize services
settings = get_settings()

# Configure LLM provider based on settings
if settings.CHATBOT_LLM_PROVIDER == "ollama":
    llm_provider = get_llm_provider(
        provider_type="ollama",
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        timeout_seconds=settings.CHATBOT_LLM_TIMEOUT_SECONDS,
    )
elif settings.CHATBOT_LLM_PROVIDER == "openai":
    llm_provider = get_llm_provider(
        provider_type="openai",
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        base_url=settings.OPENAI_BASE_URL,
        timeout_seconds=settings.CHATBOT_LLM_TIMEOUT_SECONDS,
    )
else:
    llm_provider = get_llm_provider(provider_type="mock")

intent_service = IntentDetectionService(
    llm_provider,
    timeout_seconds=settings.CHATBOT_LLM_TIMEOUT_SECONDS,
)
context_service = ContextService()
date_resolver = DateResolutionService()
handler_dispatcher = HandlerDispatcher()


def safe_name(
    first_name: Optional[str],
    last_name: Optional[str],
) -> str:
    first = first_name or ""
    last = last_name or ""

    full_name = f"{first} {last}".strip()

    return full_name or "Kullanıcı"


def format_date(value) -> str:
    if not value:
        return "-"

    try:
        if hasattr(value, "strftime"):
            return value.strftime("%d.%m.%Y")

        return str(value)

    except Exception:
        return "-"


def format_datetime(value) -> str:
    if not value:
        return "-"

    try:
        if hasattr(value, "strftime"):
            return value.strftime("%d.%m.%Y %H:%M")

        return str(value)

    except Exception:
        return "-"


def format_amount(value) -> str:
    if value is None:
        return "0 TL"

    try:
        return f"{float(value):,.2f} TL".replace(
            ",",
            "X",
        ).replace(
            ".",
            ",",
        ).replace(
            "X",
            ".",
        )

    except Exception:
        return f"{value} TL"


def detail_action_for_intent(intent: str) -> Optional[dict]:
    """Provide a navigation action even when the summary has no records."""
    actions = {
        "ATTENDANCE": {"label": "📊 Devamsızlık Detayları", "action_tag": "VIEW_ATTENDANCE_REPORT"},
        "GRADES": {"label": "📊 Tüm Notlar", "action_tag": "VIEW_GRADES"},
        "PAYMENTS": {"label": "💳 Ödeme Detayları", "action_tag": "VIEW_PAYMENTS"},
        "PAYMENT_SUMMARY": {"label": "💳 Ödeme Detayları", "action_tag": "VIEW_PAYMENTS"},
        "DEBT": {"label": "💳 Borç Detayları", "action_tag": "VIEW_DEBTS"},
        "EXPENSES": {"label": "📉 Gider Detayları", "action_tag": "VIEW_EXPENSES"},
        "HOMEWORK": {"label": "📚 Ödev Detayları", "action_tag": "VIEW_HOMEWORK"},
        "ANNOUNCEMENTS": {"label": "📢 Duyuru Detayları", "action_tag": "VIEW_ANNOUNCEMENTS"},
        "NOTIFICATIONS": {"label": "🔔 Bildirimler", "action_tag": "VIEW_NOTIFICATIONS"},
        "CANTEEN": {"label": "🍽️ Kantin Detayları", "action_tag": "VIEW_CANTEEN"},
        "CANTEEN_BALANCE": {"label": "💳 Kart Bakiyesi", "action_tag": "VIEW_CANTEEN_BALANCE"},
        "REPORTS": {"label": "📈 Raporlar", "action_tag": "VIEW_REPORTS"},
    }
    return actions.get(intent)


def estimate_token_count(text: str) -> int:
    """Rough token count estimation (approximate 4 chars per token for Turkish)."""
    if not text:
        return 0
    return len(text) // 4


def map_intent_to_topic_category(intent: str) -> str:
    """Map detected intent to topic category for analytics."""
    topic_mapping = {
        "ATTENDANCE": "Yoklama",
        "GRADES": "Akademik & Karne",
        "PAYMENTS": "Finans",
        "PAYMENT_SUMMARY": "Finans",
        "DEBT": "Finans",
        "EXPENSES": "Finans",
        "HOMEWORK": "Akademik & Karne",
        "ANNOUNCEMENTS": "Duyurular",
        "NOTIFICATIONS": "Bildirimler",
        "CANTEEN": "Kantin & Finans",
        "CANTEEN_BALANCE": "Kantin & Finans",
        "REPORTS": "Raporlar",
        "EXAMS": "Akademik & Karne",
        "TEACHERS": "Öğretmenler",
        "STUDENTS": "Öğrenciler",
        "CLASSES": "Sınıflar",
    }
    return topic_mapping.get(intent, "Genel")


# ============================================================
# ROLE HELPERS
# ============================================================

def normalize_role(role: Optional[str]) -> str:
    if not role:
        return ""

    return role.lower().strip()


def get_user_role(current_user: User) -> str:
    """
    Try different common role properties.
    """

    role = getattr(current_user, "role", None)

    if role:
        if hasattr(role, "value"):
            return normalize_role(role.value)

        return normalize_role(str(role))

    roles = getattr(current_user, "roles", None)

    if roles:
        try:
            first_role = roles[0]

            if hasattr(first_role, "name"):
                return normalize_role(first_role.name)

            if hasattr(first_role, "value"):
                return normalize_role(first_role.value)

            return normalize_role(str(first_role))

        except Exception:
            pass

    return ""


def is_parent(role: str) -> bool:
    return role == ROLE_PARENT


def is_teacher(role: str) -> bool:
    return role == ROLE_TEACHER


def is_admin(role: str) -> bool:
    return role in ADMIN_ROLES


def is_staff(role: str) -> bool:
    return role in STAFF_ROLES


def can_manage_students(role: str) -> bool:
    return (
        is_admin(role)
        or is_teacher(role)
    )


def can_manage_finance(role: str) -> bool:
    return (
        is_admin(role)
        or is_parent(role)
    )


# ============================================================
# TENANT HELPERS (kept for other endpoints)
# ============================================================

def organization_id_of(user: User):
    return getattr(user, "organization_id", None)


async def verify_student_access(
    db: AsyncSession,
    current_user: User,
    student_id: UUID,
) -> Student:

    role = get_user_role(current_user)

    organization_id = organization_id_of(current_user)

    if not organization_id:
        raise HTTPException(
            status_code=403,
            detail="User organization not found",
        )

    # --------------------------------------------------------
    # Base student query
    # --------------------------------------------------------

    result = await db.execute(
        select(Student).where(
            and_(
                Student.id == student_id,
                Student.organization_id == organization_id,
            )
        )
    )

    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found",
        )

    # --------------------------------------------------------
    # Admin
    # --------------------------------------------------------

    if is_admin(role):
        return student

    # --------------------------------------------------------
    # Parent
    # --------------------------------------------------------

    if is_parent(role):

        from app.infrastructure.models.models import (
            Parent,
            StudentParent,
        )

        parent_result = await db.execute(
            select(Parent).where(
                Parent.user_id == current_user.id
            )
        )

        parent = parent_result.scalar_one_or_none()

        if not parent:
            raise HTTPException(
                status_code=403,
                detail="Parent record not found",
            )

        relation_result = await db.execute(
            select(StudentParent).where(
                and_(
                    StudentParent.parent_id == parent.id,
                    StudentParent.student_id == student_id,
                )
            )
        )

        relation = relation_result.scalar_one_or_none()

        if not relation:
            raise HTTPException(
                status_code=403,
                detail="Student does not belong to this parent",
            )

        return student

    # --------------------------------------------------------
    # Teacher
    # --------------------------------------------------------

    if is_teacher(role):

        assignment_result = await db.execute(
            select(StudentTeacherAssignment).where(
                and_(
                    StudentTeacherAssignment.student_id == student_id,
                    StudentTeacherAssignment.teacher_id == current_user.id,
                )
            )
        )

        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            raise HTTPException(
                status_code=403,
                detail="Teacher is not assigned to this student",
            )

        return student

    # --------------------------------------------------------
    # Staff
    # --------------------------------------------------------

    if is_staff(role):
        return student

    raise HTTPException(
        status_code=403,
        detail="You do not have access to this student",
    )


# ============================================================
# ROLE CONFIGURATION ENDPOINT
# ============================================================

@router.get("/role-config")
async def get_role_chat_config(
    current_user: User = Depends(get_current_user),
):
    """
    Get role-based chatbot configuration including greeting, theme, and suggestion chips.
    """
    role = get_user_role(current_user)
    config = get_role_config(role)
    
    return success_response({
        "role": config.role,
        "greeting_title": config.greeting_title,
        "greeting_subtitle": config.greeting_subtitle,
        "theme_color": config.theme_color,
        "suggestion_chips": [
            {"label": chip.label, "action_tag": chip.action_tag}
            for chip in config.suggestion_chips
        ]
    })


# ============================================================
# PROCESS QUERY (LLM-based)
# ============================================================

async def _process_chatbot_query(
    request: ChatbotQueryRequest,
    db: AsyncSession,
    current_user: User,
) -> dict:
    """
    Core chatbot query processing logic.
    Shared between /process-query and /api/ai/chat endpoints.
    """
    start_time = time.time()

    try:
        # Build chatbot context
        context = await context_service.build_context(
            current_user,
            db,
            conversation_history=[message.model_dump() for message in request.conversation_history],
        )

        logger.info(
            "Chatbot request | user_id=%s | role=%s | "
            "organization_id=%s | query=%r",
            current_user.id,
            context.role,
            context.organization_id,
            request.query,
        )

        # A client-selected student is useful for parents with more than one
        # child, but it must be constrained to the context built from the
        # authenticated user rather than trusted as an arbitrary UUID.
        accessible_student_ids = {
            student["id"] for student in context.accessible_students
        }
        student_id = None
        if request.student_id:
            try:
                requested_student_id = UUID(request.student_id)
                if str(requested_student_id) in accessible_student_ids:
                    student_id = requested_student_id
                else:
                    logger.warning(
                        "Ignoring inaccessible chatbot student_id | user_id=%s | student_id=%s",
                        current_user.id,
                        request.student_id,
                    )
            except ValueError:
                logger.warning("Ignoring invalid chatbot student_id: %s", request.student_id)

        # Detect intent using LLM
        raw_intent = await intent_service.detect_intent_with_fallback(
            query=request.query,
            context=context,
        )

        logger.info(
            "Intent detected | user_id=%s | intent=%s | confidence=%.2f",
            current_user.id,
            raw_intent.intent,
            raw_intent.confidence,
        )

        # Resolve references (student, teacher)
        teacher_id = None

        if raw_intent.search_text:
            if raw_intent.student_id:
                # LLM provided a student ID - validate it
                try:
                    candidate_student_id = UUID(raw_intent.student_id)
                    if str(candidate_student_id) in accessible_student_ids:
                        student_id = candidate_student_id
                    else:
                        logger.warning("Ignoring inaccessible student_id from LLM")
                except ValueError:
                    logger.warning(f"Invalid student_id from LLM: {raw_intent.student_id}")
            else:
                # Resolve from search text
                resolved_student_id = await context_service.resolve_student_reference(
                    search_text=raw_intent.search_text,
                    context=context,
                    db=db,
                )
                if resolved_student_id and str(resolved_student_id) in accessible_student_ids:
                    student_id = resolved_student_id

            if raw_intent.teacher_id:
                try:
                    teacher_id = UUID(raw_intent.teacher_id)
                except ValueError:
                    logger.warning(f"Invalid teacher_id from LLM: {raw_intent.teacher_id}")
            else:
                teacher_id = await context_service.resolve_teacher_reference(
                    search_text=raw_intent.search_text,
                    context=context,
                    db=db,
                )

        # For a single child, answer data questions directly without making a
        # parent repeat the child's name each time.
        if student_id is None and len(accessible_student_ids) == 1:
            student_id = UUID(next(iter(accessible_student_ids)))

        # Resolve date range
        date_range = None
        if raw_intent.period:
            resolver = DateResolutionService(context.current_date) if raw_intent.intent == "CANTEEN" else date_resolver
            date_range = resolver.resolve_period(raw_intent.period)

        # Build resolved intent
        resolved_intent = ResolvedIntent(
            intent=raw_intent.intent,
            student_id=student_id,
            teacher_id=teacher_id,
            subject=raw_intent.subject,
            date_range=date_range,
            operation=raw_intent.operation,
            search_text=raw_intent.search_text,
            confidence=raw_intent.confidence,
            raw_intent=raw_intent,
        )

        logger.info(
            "Intent resolved | user_id=%s | student_id=%s | teacher_id=%s | date_range=%s",
            current_user.id,
            student_id,
            teacher_id,
            date_range.description if date_range else None,
        )

        # Dispatch to handler
        handler_response = await handler_dispatcher.dispatch(
            intent=resolved_intent,
            current_user=current_user,
            db=db,
        )

        execution_time = time.time() - start_time

        logger.info(
            "Chatbot response | user_id=%s | intent=%s | execution_time=%.2fs | success=True",
            current_user.id,
            raw_intent.intent,
            execution_time,
        )

        suggested_actions = handler_response.suggested_actions
        if raw_intent.operation == "details" and not suggested_actions and raw_intent.intent != "CANTEEN":
            detail_action = detail_action_for_intent(raw_intent.intent)
            suggested_actions = [detail_action] if detail_action else []

        # Create audit log entry
        try:
            # Format session ID as SES-{ROLE}-{USER_ID_SUFFIX} e.g., SES-PAR-882
            role_prefix_map = {
                "parent": "PAR",
                "teacher": "TEA",
                "super_admin": "SUP",
                "owner": "OWN",
                "admin": "ADM",
                "manager": "MGR",
                "accountant": "FIN",
                "canteen_staff": "CAN",
            }
            sender_role = get_user_role(current_user)
            role_code = role_prefix_map.get(sender_role, "USR")
            session_id = f"SES-{role_code.upper()}-{str(current_user.id)[:3]}"
            
            sentiment = analyze_sentiment(request.query)
            topic_category = map_intent_to_topic_category(raw_intent.intent)
            token_count = estimate_token_count(request.query + handler_response.message)
            latency_ms = int(execution_time * 1000)

            audit_log = AiChatAuditLogModel(
                session_id=session_id,
                user_id=current_user.id,
                organization_id=organization_id_of(current_user),
                user_query=request.query,
                ai_response=handler_response.message,
                detected_intent=raw_intent.intent,
                topic_category=topic_category,
                sentiment=sentiment,
                token_count=token_count,
                latency_ms=latency_ms,
                meta_data={
                    "confidence": raw_intent.confidence,
                    "student_id": str(student_id) if student_id else None,
                    "teacher_id": str(teacher_id) if teacher_id else None,
                    "operation": raw_intent.operation,
                    "sender_role": sender_role,
                }
            )
            db.add(audit_log)
            await db.commit()
        except Exception as log_error:
            logger.error(f"Failed to create audit log: {log_error}")
            # Don't fail the request if audit logging fails

        return {
            "intent": raw_intent.intent,
            "response_markdown": handler_response.message,
            "suggested_actions": suggested_actions,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat(),
        }

    except AppException:
        raise
    except Exception as e:
        execution_time = time.time() - start_time

        logger.exception(
            "Chatbot error | user_id=%s | execution_time=%.2fs | error=%s",
            current_user.id,
            execution_time,
            str(e),
        )

        raise HTTPException(
            status_code=500,
            detail="Chatbot işlemi sırasında beklenmeyen bir hata oluştu.",
        )


@router.post("/ai/chat")
async def handle_chat_message(
    request: ChatbotQueryRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Main chatbot endpoint matching specification format.
    
    1. Kullanıcı rolünü ve şubesini al
    2. İlgili veri tabanından canlı verileri (not, yoklama, kantin) topla (RAG)
    3. Yanıtı üret ve Audit Log tablosuna kaydet
    """
    result = await _process_chatbot_query(request, db, current_user)
    return success_response(result)

@router.post("/process-query")
async def process_query(
    request: ChatbotQueryRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Main chatbot endpoint using LLM-based intent detection.

    IMPORTANT:
    - Role is determined from authenticated user whenever possible
    - request.role is not trusted for authorization
    - All entity IDs are validated against database and user permissions
    """
    result = await _process_chatbot_query(request, db, current_user)
    return success_response(result)


# ============================================================
# GET STUDENT TEACHERS
# ============================================================

@router.get(
    "/students/{student_id}/teachers"
)
async def get_student_teachers(
    student_id: UUID,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Return teachers assigned to a student.

    Access is checked against current user's role.
    """

    student = await verify_student_access(
        db,
        current_user,
        student_id,
    )

    classroom_result = await db.execute(
        select(ClassRoom)
        .where(
            ClassRoom.id == student.class_id
        )
    )

    classroom = classroom_result.scalar_one_or_none()

    assignments_result = await db.execute(
        select(
            StudentTeacherAssignment,
            UserModel,
        )
        .join(
            UserModel,
            StudentTeacherAssignment.teacher_id
            == UserModel.id,
        )
        .where(
            StudentTeacherAssignment.student_id
            == student_id
        )
    )

    assignments = assignments_result.all()

    teachers = []

    for assignment, teacher in assignments:

        role_description = (
            f"{assignment.subject_name or 'Ders'} Öğretmeni"
        )

        if assignment.is_primary_adviser:

            role_description = (
                f"{assignment.subject_name or 'Ders'} "
                "& Rehber Öğretmeni"
            )

        teachers.append(
            TeacherInfo(
                teacher_id=teacher.id,
                full_name=safe_name(
                    teacher.first_name,
                    teacher.last_name,
                ),
                subject=assignment.subject_name or "",
                role_description=role_description,
                avatar_color_hex="#2563EB",
                is_online=False,
                office_hours=(
                    assignment.office_hours
                    or "08:30 - 17:30"
                ),
            )
        )

    return success_response(
        {
            "success": True,
            "student_id": str(student_id),
            "student_name": safe_name(
                student.first_name,
                student.last_name,
            ),
            "class_name": (
                classroom.name
                if classroom
                else ""
            ),
            "teachers": teachers,
        }
    )


# ============================================================
# CONNECT TEACHER
# ============================================================

@router.post(
    "/chat/conversations/connect-teacher", status_code=201,
    dependencies=[Depends(PermissionChecker("parent.send_message"))],
)
async def connect_teacher(
    request: ChatConversationCreate,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Create or reuse a parent-teacher conversation.

    Security:
    - Current user must be parent.
    - Student must belong to parent.
    - Teacher must be assigned to student.
    - Student must belong to same organization.
    """

    actual_role = get_user_role(
        current_user
    )

    if not is_parent(actual_role):

        raise HTTPException(
            status_code=403,
            detail="Only parents can start teacher conversations.",
        )

    # --------------------------------------------------------
    # Verify student
    # --------------------------------------------------------

    student = await verify_student_access(
        db,
        current_user,
        request.student_id,
    )

    # --------------------------------------------------------
    # Parent
    # --------------------------------------------------------

    from app.infrastructure.models.models import (
        Parent,
        StudentParent,
    )

    parent_result = await db.execute(
        select(Parent).where(
            Parent.user_id == current_user.id
        )
    )

    parent = parent_result.scalar_one_or_none()

    if not parent:

        raise HTTPException(
            status_code=403,
            detail="Parent record not found.",
        )

    # --------------------------------------------------------
    # Verify parent/student relation
    # --------------------------------------------------------

    relation_result = await db.execute(
        select(StudentParent).where(
            and_(
                StudentParent.parent_id == parent.id,
                StudentParent.student_id == request.student_id,
            )
        )
    )

    relation = relation_result.scalar_one_or_none()

    if not relation:

        raise HTTPException(
            status_code=403,
            detail="Student does not belong to this parent.",
        )

    # --------------------------------------------------------
    # Verify teacher assignment
    # --------------------------------------------------------

    assignment_result = await db.execute(
        select(
            StudentTeacherAssignment
        ).where(
            and_(
                StudentTeacherAssignment.student_id
                == request.student_id,
                StudentTeacherAssignment.teacher_id
                == request.teacher_id,
            )
        )
    )

    assignment = (
        assignment_result.scalar_one_or_none()
    )

    if not assignment:

        raise HTTPException(
            status_code=403,
            detail="Teacher is not assigned to this student.",
        )

    # --------------------------------------------------------
    # Verify teacher exists
    # --------------------------------------------------------

    teacher_result = await db.execute(
        select(UserModel).where(
            and_(
                UserModel.id == request.teacher_id,
                UserModel.organization_id
                == current_user.organization_id,
            )
        )
    )

    teacher = teacher_result.scalar_one_or_none()

    if not teacher:

        raise HTTPException(
            status_code=404,
            detail="Teacher not found.",
        )

    teacher_name = safe_name(
        teacher.first_name,
        teacher.last_name,
    )

    # --------------------------------------------------------
    # Existing conversation
    # --------------------------------------------------------

    existing_result = await db.execute(
        select(ChatConversation).where(
            and_(
                ChatConversation.parent_id
                == current_user.id,

                ChatConversation.teacher_id
                == request.teacher_id,

                ChatConversation.student_id
                == request.student_id,

                ChatConversation.is_active == True,
            )
        ).order_by(ChatConversation.created_at, ChatConversation.id).limit(1)
    )

    conversation = (
        existing_result.scalar_one_or_none()
    )

    now = datetime.now()

    if not conversation:

        conversation = ChatConversation(
            student_id=request.student_id,
            parent_id=current_user.id,
            teacher_id=request.teacher_id,
            subject_context=(
                f"{teacher_name} - Birebir İletişim"
            ),
            last_message=request.initial_message,
            last_message_at=now,
            teacher_unread_count=1,
            created_via=request.created_via,
        )

        db.add(conversation)

        await db.flush()

    else:

        conversation.last_message = (
            request.initial_message
        )

        conversation.last_message_at = now

        conversation.teacher_unread_count = (
            (conversation.teacher_unread_count or 0)
            + 1
        )

    # --------------------------------------------------------
    # Message
    # --------------------------------------------------------

    message = ChatMessage(
        conversation_id=conversation.id,
        sender_id=current_user.id,
        sender_role="PARENT",
        recipient_id=request.teacher_id,
        content=request.initial_message,
        is_read=False,
        sent_at=now,
    )

    db.add(message)

    await db.commit()

    await db.refresh(
        conversation
    )

    role_description = (
        assignment.subject_name
        or "Öğretmen"
    )

    if assignment.is_primary_adviser:

        role_description = (
            f"{assignment.subject_name or 'Ders'} "
            "& Rehber Öğretmeni"
        )

    return success_response(
        {
            "success": True,
            "conversation_id": str(
                conversation.id
            ),
            "participant_name": teacher_name,
            "participant_role": role_description,
            "student_id": str(
                student.id
            ),
            "last_message": request.initial_message,
            "last_message_time": (
                conversation.last_message_at.strftime(
                    "%H:%M"
                )
                if conversation.last_message_at
                else "Şimdi"
            ),
            "status": "ACTIVE",
        },
    )


# ============================================================
# AI CHAT AUDIT LOGS (Super Admin Only)
# ============================================================

def normalize_audit_role(role: str) -> str:
    value = normalize_role(role)
    return "super_admin" if value.replace("_", "").replace("-", "").replace(" ", "") == "superadmin" else value


@router.get("/ai/audit-logs")
async def get_audit_logs(
    role: Optional[str] = Query(None, max_length=50, description="Kayıt anındaki gönderici rolü"),
    topic: Optional[str] = None,
    feedback_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(require_ai_workspace_admin),
):
    """
    Get AI chat audit logs with filtering options.
    Only accessible by super admins.
    
    Süper Admin: Chat Loglarını ve Niyet İstatistiklerini Getir
    """
    # Build base query
    query = select(AiChatAuditLogModel).order_by(AiChatAuditLogModel.created_at.desc(), AiChatAuditLogModel.id.desc())
    
    # Apply filters
    if role and role.strip():
        recorded = func.lower(func.trim(AiChatAuditLogModel.meta_data["sender_role"].as_string()))
        compact = func.replace(func.replace(func.replace(recorded, "_", ""), "-", ""), " ", "")
        recorded = case((compact == "superadmin", "super_admin"), else_=recorded)
        query = query.where(recorded == normalize_audit_role(role))
    
    if topic:
        query = query.where(AiChatAuditLogModel.topic_category == topic)
    
    if feedback_status:
        query = query.where(AiChatAuditLogModel.feedback_status == feedback_status)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Enrich with user information
    enriched_logs = []
    for log in logs:
        # Get user details
        if log.user_id == current_user.id:
            user = current_user
        else:
            user_result = await db.execute(select(UserModel).where(UserModel.id == log.user_id))
            user = user_result.scalar_one_or_none()
        
        sender_name = f"{user.first_name} {user.last_name}" if user else "Bilinmeyen"
        captured_role = (log.meta_data or {}).get("sender_role") if isinstance(log.meta_data, dict) else None
        sender_role = normalize_audit_role(captured_role) if isinstance(captured_role, str) and captured_role.strip() else "UNKNOWN"
        
        log_dict = {
            "id": str(log.id),
            "session_id": log.session_id,
            "user_id": str(log.user_id),
            "organization_id": str(log.organization_id),
            "user_query": log.user_query,
            "ai_response": log.ai_response,
            "detected_intent": log.detected_intent,
            "topic_category": log.topic_category,
            "sentiment": log.sentiment,
            "quality_rating": log.quality_rating,
            "feedback_status": log.feedback_status,
            "corrected_response": log.corrected_response,
            "token_count": log.token_count,
            "latency_ms": log.latency_ms,
            "is_fine_tuning_ready": log.is_fine_tuning_ready,
            "meta_data": log.meta_data,
            "created_at": log.created_at,
            "updated_at": log.updated_at,
            "sender_name": sender_name,
            "sender_role": sender_role,
        }
        enriched_logs.append(log_dict)
    
    return success_response({
        "success": True,
        "logs": enriched_logs,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.put("/ai/audit-logs/{log_id}/verify")
async def update_audit_log_feedback(
    log_id: str,
    feedback: FeedbackPayload,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(require_ai_workspace_admin),
):
    """
    Update audit log feedback (RLHF - Reinforcement Learning from Human Feedback).
    Only accessible by super admins.
    
    Süper Admin: İnsan Düzeltmesi (RLHF) Kaydet
    """
    try:
        log_uuid = UUID(log_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid log ID")
    
    result = await db.execute(
        select(AiChatAuditLogModel).where(AiChatAuditLogModel.id == log_uuid)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    # Update feedback fields
    log.quality_rating = feedback.quality_rating
    log.feedback_status = feedback.feedback_status
    log.corrected_response = feedback.corrected_response
    log.is_fine_tuning_ready = feedback.is_fine_tuning_ready
    log.updated_by = current_user.id
    
    await db.commit()
    await db.refresh(log)
    
    return success_response({
        "success": True,
        "message": "Feedback updated successfully",
        "log_id": str(log.id),
    })


@router.get("/ai/export-dataset")
async def export_fine_tuning_dataset(
    format: str = "jsonl",
    feedback_status: Optional[str] = None,
    is_fine_tuning_ready: Optional[bool] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(require_ai_workspace_admin),
):
    """
    Export fine-tuning dataset in various formats.
    Only accessible by super admins.
    
    Süper Admin: Fine-Tuning JSONL İndir
    
    Supported formats:
    - jsonl: OpenAI/Gemini JSONL format (Chat Completion)
    - alpaca: Stanford Alpaca format (Instruction Tuning)
    - llama: Meta LLaMA 3 chat template
    - csv: Tabular CSV format for BI and Excel
    """
    try:
        format = format.lower().strip()
        if format not in {"jsonl", "alpaca", "llama", "csv"}:
            raise HTTPException(status_code=400, detail="Unsupported export format")
        dataset = await DatasetExportService.export_dataset(
            db=db,
            format=format,
            organization_id=current_user.organization_id,
            feedback_status=feedback_status,
            is_fine_tuning_ready=is_fine_tuning_ready,
        )
        
        if not dataset:
            raise HTTPException(status_code=404, detail="No logs found for export")
        
        # Set appropriate content type and filename
        content_type_map = {
            "jsonl": "application/json",
            "alpaca": "application/json",
            "llama": "text/plain",
            "csv": "text/csv",
        }
        
        content_type = content_type_map.get(format.lower(), "application/json")
        filename = f"scs360_finetuning_dataset.{format.lower()}"
        
        return Response(
            content=dataset,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Dataset export error: {e}")
        raise HTTPException(status_code=500, detail="Dataset export failed")


# ============================================================
# ANALYTICS DASHBOARD ENDPOINTS (Super Admin Only)
# ============================================================

@router.get("/ai/analytics/overview")
async def get_analytics_overview(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(require_ai_workspace_admin),
):
    """Recorded metrics for the explicitly selected institution; zero is unrated."""
    try:
        log = AiChatAuditLogModel
        scope = log.organization_id == current_user.organization_id
        rated = case((log.quality_rating.between(1, 5), log.quality_rating), else_=None)
        metrics = (await db.execute(select(
            func.count(log.id), func.avg(log.latency_ms), func.avg(rated), func.count(rated),
            func.sum(case((log.is_fine_tuning_ready.is_(True), 1), else_=0)),
        ).where(scope))).one()

        async def distribution(column):
            label = func.coalesce(cast(column, String), "UNKNOWN")
            result = await db.execute(select(label, func.count(log.id)).where(scope).group_by(label))
            return {row[0]: row[1] for row in result.all()}

        return success_response({
            "success": True,
            "overview": {
                "total_logs": metrics[0],
                "avg_latency_ms": round(metrics[1], 2) if metrics[1] is not None else None,
                "avg_quality_rating": round(metrics[2], 2) if metrics[2] is not None else None,
                "quality_rated_count": metrics[3],
                "finetuning_ready_count": metrics[4] or 0,
            },
            "distributions": {
                "sentiment": await distribution(log.sentiment),
                "topic": await distribution(log.topic_category),
                "intent": await distribution(log.detected_intent),
                "feedback_status": await distribution(log.feedback_status),
            },
        })
    except Exception as e:
        logger.error(f"Analytics overview error: {e}")
        raise HTTPException(status_code=503, detail="Analytics overview is temporarily unavailable")


@router.get("/ai/analytics/trends")
async def get_analytics_trends(
    days: int = Query(30, ge=1, le=366),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(require_ai_workspace_admin),
):
    """The requested UTC calendar days, including today up to the current instant."""
    try:
        now = datetime.now(UTC)
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
        log = AiChatAuditLogModel
        # PostgreSQL DATE(timestamptz) otherwise uses the connection's timezone.
        timestamp = func.timezone("UTC", log.created_at) if db.get_bind().dialect.name == "postgresql" else log.created_at
        day = func.date(timestamp)
        result = await db.execute(select(day, log.sentiment, func.count(log.id)).where(
            log.organization_id == current_user.organization_id,
            log.created_at >= start_date, log.created_at <= now,
        ).group_by(day, log.sentiment).order_by(day, log.sentiment))
        daily_counts = {}
        sentiment_trends = {}
        for date_value, sentiment, count in result.all():
            date_str = str(date_value)
            daily_counts[date_str] = daily_counts.get(date_str, 0) + count
            sentiment_trends.setdefault(date_str, {})[sentiment] = count
        return success_response({
            "success": True,
            "period_days": days,
            "timezone": "UTC",
            "daily_trends": [{"date": day, "count": count} for day, count in daily_counts.items()],
            "sentiment_trends": sentiment_trends,
        })
    except Exception as e:
        logger.error(f"Analytics trends error: {e}")
        raise HTTPException(status_code=503, detail="Analytics trends is temporarily unavailable")


@router.get("/ai/analytics/intent-performance")
async def get_intent_performance(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(require_ai_workspace_admin),
):
    """Measured latency and rated quality by recorded intent, within one institution."""
    try:
        log = AiChatAuditLogModel
        intent = func.coalesce(log.detected_intent, "UNKNOWN")
        rated = case((log.quality_rating.between(1, 5), log.quality_rating), else_=None)
        performance_result = await db.execute(select(
            intent, func.count(log.id), func.avg(log.latency_ms), func.avg(rated),
            func.sum(case((log.feedback_status == "VERIFIED", 1), else_=0)), func.count(rated),
        ).where(log.organization_id == current_user.organization_id)
            .group_by(intent).order_by(func.count(log.id).desc(), intent))
        return success_response({
            "success": True,
            "intent_performance": [{
                "intent": row[0],
                "count": row[1],
                "avg_latency_ms": round(row[2], 2) if row[2] is not None else None,
                "avg_quality_rating": round(row[3], 2) if row[3] is not None else None,
                "quality_rated_count": row[5],
                "verified_count": row[4] or 0,
                "verification_rate": round((row[4] / row[1] * 100), 2) if row[1] > 0 else 0,
            } for row in performance_result.all()],
        })
    except Exception as e:
        logger.error(f"Intent performance error: {e}")
        raise HTTPException(status_code=503, detail="Intent performance is temporarily unavailable")


# ============================================================
# CONVERSATION HISTORY ENDPOINTS
# ============================================================

@router.get("/ai/conversation/history/{session_id}")
async def get_conversation_history(
    session_id: str = Path(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Get conversation history for a session.
    Accessible by authenticated users for their own sessions.
    """
    try:
        # Verify user has access to this session
        result = await db.execute(
            select(AiChatAuditLogModel)
            .where(AiChatAuditLogModel.session_id == session_id)
            .where(AiChatAuditLogModel.user_id == current_user.id)
            .where(AiChatAuditLogModel.organization_id == current_user.organization_id)
            .limit(1)
        )
        has_access = result.scalar_one_or_none()
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied to this conversation")
        
        history = await conversation_history_service.get_conversation_history(
            db=db,
            session_id=session_id,
            limit=limit,
            user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
        
        return success_response({
            "success": True,
            "session_id": session_id,
            "history": history,
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Conversation history error: {e}")
        raise HTTPException(status_code=503, detail="Conversation history is temporarily unavailable")


@router.get("/ai/conversation/summary/{session_id}")
async def get_session_summary(
    session_id: str = Path(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Get summary statistics for a conversation session.
    Accessible by authenticated users for their own sessions.
    """
    try:
        # Verify user has access to this session
        result = await db.execute(
            select(AiChatAuditLogModel)
            .where(AiChatAuditLogModel.session_id == session_id)
            .where(AiChatAuditLogModel.user_id == current_user.id)
            .where(AiChatAuditLogModel.organization_id == current_user.organization_id)
            .limit(1)
        )
        has_access = result.scalar_one_or_none()
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied to this conversation")
        
        summary = await conversation_history_service.get_session_summary(
            db=db,
            session_id=session_id,
            user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
        
        return success_response({
            "success": True,
            "summary": summary,
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session summary error: {e}")
        raise HTTPException(status_code=503, detail="Conversation summary is temporarily unavailable")


@router.get("/ai/conversation/my-stats")
async def get_my_conversation_stats(
    db: AsyncSession = Depends(get_db, scope="function"),
    current_user: User = Depends(get_current_user),
):
    """
    Get conversation statistics for the current user.
    Accessible by authenticated users.
    """
    try:
        stats = await conversation_history_service.get_user_conversation_stats(
            db=db,
            user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
        
        return success_response({
            "success": True,
            "stats": stats,
        })
    
    except Exception as e:
        logger.error(f"User conversation stats error: {e}")
        raise HTTPException(status_code=503, detail="Conversation statistics are temporarily unavailable")
