"""Context service for resolving references and building chatbot context."""

import logging
from app.core.dates import school_today
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.chatbot.intent_schemas import ChatbotContext
from app.domain.entities.user import User
from app.infrastructure.models.models import (
    Parent,
    Student,
    StudentParent,
    StudentTeacherAssignment,
    User as UserModel,
)

logger = logging.getLogger(__name__)


class ContextService:
    """Service for building and resolving chatbot context."""

    async def build_context(
        self,
        current_user: User,
        db: AsyncSession,
        conversation_history: Optional[list[dict]] = None,
    ) -> ChatbotContext:
        """
        Build chatbot context for the current user.

        Args:
            current_user: Authenticated user
            db: Database session
            conversation_history: Optional conversation history

        Returns:
            ChatbotContext: Context with accessible entities
        """
        # Get user role
        role = "parent" if getattr(db.info.get("tenant_context"), "parent_portal", False) else self._get_user_role(current_user)

        # Get accessible students based on role
        accessible_students = await self._get_accessible_students(
            current_user, role, db
        )

        # Get accessible teachers based on role
        accessible_teachers = await self._get_accessible_teachers(
            current_user, role, db
        )

        return ChatbotContext(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            role=role,
            accessible_students=accessible_students,
            accessible_teachers=accessible_teachers,
            current_date=school_today(),
            conversation_history=conversation_history or [],
        )

    def _get_user_role(self, user: User) -> str:
        """Extract user role from user object."""
        # Try roles attribute first
        if hasattr(user, "roles") and user.roles:
            first_role = user.roles[0]
            if hasattr(first_role, "slug"):
                return first_role.slug
            return str(first_role)

        # Fallback to role attribute
        if hasattr(user, "role"):
            role = user.role
            if hasattr(role, "value"):
                return role.value
            return str(role)

        return "unknown"

    async def _get_accessible_students(
        self,
        user: User,
        role: str,
        db: AsyncSession,
    ) -> list[dict]:
        """Get list of students the user can access."""
        tenant = db.info.get("tenant_context")
        allowed = ["students.read", "academic.read", "attendance.read", "teacher.view_classes", "finance.read", "finance.write",
            "parent.view_children", "parent.view_finances", "parent.view_attendance"]
        if tenant is None or not tenant.has_any_permission(allowed):
            return []
        query = select(Student).where(Student.organization_id == user.organization_id, Student.deleted_at.is_(None))
        if role == "parent":
            from app.core.student_access import parent_student_ids
            identifiers = await parent_student_ids(db, user.id, user.organization_id)
            query = query.where(Student.id.in_(identifiers))
        rows = (await db.execute(query.order_by(Student.first_name, Student.id))).scalars().all()
        return [{"id": str(student.id), "first_name": student.first_name, "last_name": student.last_name,
            "student_number": student.student_number, "class_id": str(student.class_id) if student.class_id else None} for student in rows]

    async def _get_accessible_teachers(
        self,
        user: User,
        role: str,
        db: AsyncSession,
    ) -> list[dict]:
        """Get list of teachers the user can access."""
        accessible_teachers = []

        try:
            if role == "parent":
                # Parents can access teachers assigned to their children
                parent_result = await db.execute(
                    select(Parent).where(Parent.user_id == user.id)
                )
                parent = parent_result.scalar_one_or_none()

                if parent:
                    # Get student IDs
                    students_result = await db.execute(
                        select(StudentParent.student_id)
                        .where(StudentParent.parent_id == parent.id)
                    )
                    student_ids = {s[0] for s in students_result.all()}

                    if student_ids:
                        # Get teacher assignments for these students
                        assignments_result = await db.execute(
                            select(StudentTeacherAssignment)
                            .where(StudentTeacherAssignment.student_id.in_(student_ids))
                        )
                        assignments = assignments_result.scalars().all()

                        teacher_ids = {a.teacher_id for a in assignments}

                        if teacher_ids:
                            teachers_result = await db.execute(
                                select(UserModel)
                                .where(UserModel.id.in_(teacher_ids))
                                .where(UserModel.deleted_at.is_(None))
                            )
                            teachers = teachers_result.scalars().all()

                            for teacher in teachers:
                                accessible_teachers.append({
                                    "id": str(teacher.id),
                                    "first_name": teacher.first_name,
                                    "last_name": teacher.last_name,
                                })

            elif role in ["admin", "super_admin", "teacher"]:
                # Admins and teachers can see all teachers in their organization
                if user.organization_id:
                    teachers_result = await db.execute(
                        select(UserModel)
                        .where(UserModel.organization_id == user.organization_id)
                        .where(UserModel.deleted_at.is_(None))
                        .limit(100)  # Limit for context size
                    )
                    teachers = teachers_result.scalars().all()

                    for teacher in teachers:
                        accessible_teachers.append({
                            "id": str(teacher.id),
                            "first_name": teacher.first_name,
                            "last_name": teacher.last_name,
                        })

        except Exception as e:
            logger.exception(f"Error getting accessible teachers: {e}")

        return accessible_teachers

    async def resolve_student_reference(
        self,
        search_text: Optional[str],
        context: ChatbotContext,
        db: AsyncSession,
    ) -> Optional[UUID]:
        """
        Resolve student reference from search text.

        Args:
            search_text: Name or identifier to search for
            context: Chatbot context
            db: Database session

        Returns:
            UUID of resolved student or None
        """
        if not search_text:
            return None

        search_lower = search_text.lower()

        # First, try to match against accessible students in context
        for student in context.accessible_students:
            full_name = f"{student['first_name']} {student['last_name']}".lower()
            if (
                search_lower in full_name
                or search_lower in student['first_name'].lower()
                or search_lower in student['last_name'].lower()
                or (student.get('student_number') and search_lower in student['student_number'].lower())
            ):
                return UUID(student['id'])

        # If not found in context, try database search with organization filtering
        try:
            if context.organization_id:
                students_result = await db.execute(
                    select(Student)
                    .where(Student.organization_id == context.organization_id)
                    .where(Student.deleted_at.is_(None))
                )
                students = students_result.scalars().all()

                for student in students:
                    full_name = f"{student.first_name} {student.last_name}".lower()
                    if (
                        search_lower in full_name
                        or search_lower in student.first_name.lower()
                        or search_lower in student.last_name.lower()
                        or (student.student_number and search_lower in student.student_number.lower())
                    ):
                        return student.id

        except Exception as e:
            logger.exception(f"Error resolving student reference: {e}")

        return None

    async def resolve_teacher_reference(
        self,
        search_text: Optional[str],
        context: ChatbotContext,
        db: AsyncSession,
    ) -> Optional[UUID]:
        """
        Resolve teacher reference from search text.

        Args:
            search_text: Name to search for
            context: Chatbot context
            db: Database session

        Returns:
            UUID of resolved teacher or None
        """
        if not search_text:
            return None

        search_lower = search_text.lower()

        # Try to match against accessible teachers in context
        for teacher in context.accessible_teachers:
            full_name = f"{teacher['first_name']} {teacher['last_name']}".lower()
            if (
                search_lower in full_name
                or search_lower in teacher['first_name'].lower()
                or search_lower in teacher['last_name'].lower()
            ):
                return UUID(teacher['id'])

        return None
