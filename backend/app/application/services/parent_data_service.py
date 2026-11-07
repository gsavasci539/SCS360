"""Student-related portal reads backed by real, relationship-scoped records."""
from collections import defaultdict
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select

from app.core.exceptions import NotFoundException
from app.core.student_access import require_parent_child_access, parent_contacts_query
from app.infrastructure.models.models import (
    Announcement, AnnouncementAudience, AnnouncementStatus, AnnouncementRecipient,
    ChatConversation, ChatMessage, ClassRoom, ClassTeacher, DailyDevelopmentReport,
    Grade, Homework, HomeworkSubmission, Student, StudentTeacherAssignment, User, Parent, StudentParent,
)


def enum_value(value):
    return value.value if hasattr(value, "value") else value


async def child(db, user, student_id):
    identifier = UUID(str(student_id))
    parent = await require_parent_child_access(db, user.id, identifier)
    student = (await db.execute(select(Student).where(Student.id == identifier,
        Student.organization_id == parent.organization_id,
        Student.organization_id == user.organization_id, Student.deleted_at.is_(None)))).scalar_one_or_none()
    if student is None:
        raise NotFoundException("Öğrenci bulunamadı")
    return parent, student


async def grades(db, user, student_id):
    from app.application.services.academic_records import records, numeric, normalized_score
    _, student = await child(db, user, student_id)
    rows = await records(db, student.organization_id, [student.id])
    return [{"id": str(row.id), "subject": row.subject, "exam_type": row.grade_type,
        "score": numeric(row.score), "max_score": numeric(row.max_score), "grade_scale": row.grade_scale,
        "exam_date": row.exam_date.isoformat(), "status": row.status, "source": row.source,
        "exam_id": str(row.exam_id) if row.exam_id else None,
        "valid_numeric_score": normalized_score(row) is not None} for row in rows]


async def schedule(db, user, student_id):
    from app.infrastructure.models.models import Timetable, TimetableSlot, ClassroomAssignment
    _, student = await child(db, user, student_id)
    if student.class_id is None:
        return []
    from app.infrastructure.models.models import OperationalRecord
    saved = (await db.execute(select(OperationalRecord).where(OperationalRecord.kind == "CLASS_SCHEDULE",
        OperationalRecord.class_id == student.class_id))).scalar_one_or_none()
    if saved:
        return [{"day_of_week": day.get("day"), "lessons": [{"subject": period.get("subject"),
            "start_time": str(period.get("time", "")).split(" - ")[0],
            "end_time": str(period.get("time", "")).split(" - ")[-1], "teacher": period.get("teacher_name")}
            for period in day.get("periods", [])]} for day in saved.data.get("schedule", [])]
    rows = (await db.execute(select(TimetableSlot, ClassroomAssignment, User).select_from(TimetableSlot)
        .join(Timetable, Timetable.slot_id == TimetableSlot.id)
        .outerjoin(ClassroomAssignment, ClassroomAssignment.id == Timetable.classroom_assignment_id)
        .outerjoin(User, User.id == ClassroomAssignment.teacher_id)
        .where(Timetable.class_id == student.class_id, Timetable.is_active.is_(True))
        .order_by(TimetableSlot.day, TimetableSlot.start_time))).all()
    days = defaultdict(list)
    for slot, assignment, teacher in rows:
        days[slot.day].append({"subject": "Teneffüs" if slot.is_break else "Ders",
            "subject_id": str(assignment.subject_id) if assignment and assignment.subject_id else None,
            "start_time": slot.start_time.strftime("%H:%M"), "end_time": slot.end_time.strftime("%H:%M"),
            "teacher": f"{teacher.first_name} {teacher.last_name}" if teacher else None})
    return [{"day_of_week": day, "lessons": lessons} for day, lessons in days.items()]


async def homework(db, user, student_id):
    _, student = await child(db, user, student_id)
    if student.class_id is None:
        return []
    rows = (await db.execute(select(Homework, HomeworkSubmission)
        .outerjoin(HomeworkSubmission, and_(HomeworkSubmission.homework_id == Homework.id,
            HomeworkSubmission.student_id == student.id))
        .where(Homework.organization_id == student.organization_id, Homework.class_id == student.class_id,
            Homework.deleted_at.is_(None), Homework.status == "ACTIVE")
        .order_by(Homework.due_date))).all()
    return [{"id": str(row.id), "subject": row.subject, "title": row.title, "description": row.description,
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "status": submission.status if submission else "PENDING",
        "score": float(submission.score) if submission and submission.score is not None else None,
        "attachment_url": row.attachment_url} for row, submission in rows]


async def materials(db, user, student_id):
    from app.domain.entities.materials import CourseMaterial
    from app.application.services.material_file_service import visible_to_child
    _, student = await child(db, user, student_id)
    rows = (await db.execute(select(CourseMaterial).where(visible_to_child(student))
        .order_by(CourseMaterial.created_at.desc()))).scalars()
    return [{"id": str(row.id), "title": row.title, "subject": row.unit_topic, "type": row.material_type,
        "file_name": row.file_name,
        "file_url": f"/api/parent/child/{student.id}/materials/{row.id}/download",
        "description": row.description} for row in rows]


async def communications(db, user, student_id):
    _, student = await child(db, user, student_id)
    conversations = select(ChatConversation.id).where(ChatConversation.student_id == student.id,
        ChatConversation.parent_id == user.id)
    rows = (await db.execute(select(ChatMessage, User).join(User, User.id == ChatMessage.sender_id)
        .where(ChatMessage.conversation_id.in_(conversations),
            or_(ChatMessage.sender_id == user.id, ChatMessage.recipient_id == user.id))
        .order_by(ChatMessage.created_at.desc()).limit(100))).all()
    return [{"id": str(row.id), "teacher_name": f"{sender.first_name} {sender.last_name}",
        "date": row.created_at.date().isoformat(), "subject": "Sohbet", "message": row.content} for row, sender in rows]


async def announcements(db, user, student_id):
    parent, student = await child(db, user, student_id)
    contacts = parent_contacts_query(user.id, user.organization_id).join(StudentParent, StudentParent.parent_id == Parent.id).where(
        StudentParent.student_id == student.id).with_only_columns(Parent.id)
    received = select(AnnouncementRecipient.announcement_id).where(AnnouncementRecipient.parent_id.in_(contacts),
        or_(AnnouncementRecipient.student_id.is_(None), AnnouncementRecipient.student_id == student.id))
    rows = (await db.execute(select(Announcement).where(
        Announcement.organization_id == student.organization_id, Announcement.deleted_at.is_(None),
        Announcement.status == AnnouncementStatus.SENT,
        or_(Announcement.id.in_(received), Announcement.audience == AnnouncementAudience.ALL_PARENTS,
            and_(Announcement.audience == AnnouncementAudience.BRANCH_PARENTS, Announcement.branch_id == student.branch_id),
            and_(Announcement.audience == AnnouncementAudience.CLASS_PARENTS, Announcement.class_id == student.class_id) if student.class_id else False,
            and_(Announcement.audience == AnnouncementAudience.SINGLE_STUDENT, Announcement.student_id == student.id)))
        .order_by(Announcement.created_at.desc()).limit(100))).scalars()
    return [{"id": str(row.id), "title": row.title, "content": row.content,
        "category": enum_value(row.audience), "date": (row.sent_at or row.created_at).date().isoformat()} for row in rows]


async def activities(db, user, student_id):
    from app.domain.entities.clubs import ClubMembership, SchoolClub
    _, student = await child(db, user, student_id)
    rows = (await db.execute(select(SchoolClub).join(ClubMembership, ClubMembership.club_id == SchoolClub.id)
        .where(ClubMembership.student_id == student.id, ClubMembership.status == "ACTIVE",
            SchoolClub.branch_id == student.branch_id, SchoolClub.is_active.is_(True)))).scalars()
    return [{"id": str(row.id), "name": row.club_name, "type": "Kulüp", "day": row.meeting_day,
        "time": row.meeting_time.strftime("%H:%M") if row.meeting_time else None,
        "location": row.meeting_location} for row in rows]


async def weekly_reports(db, user, student_id):
    _, student = await child(db, user, student_id)
    rows = (await db.execute(select(DailyDevelopmentReport, User)
        .outerjoin(User, User.id == DailyDevelopmentReport.recorded_by)
        .where(DailyDevelopmentReport.student_id == student.id)
        .order_by(DailyDevelopmentReport.date.desc()).limit(60))).all()
    weeks = {}
    for row, teacher in rows:
        week = row.date.isocalendar()
        key = (week.year, week.week)
        entry = weeks.setdefault(key, {"id": f"{week.year}-{week.week}", "week_title": f"{week.year} / {week.week}. Hafta",
            "report_date": row.date.isoformat(), "teacher_name": None, "summary": [], "behavior": [], "social": []})
        if teacher:
            entry["teacher_name"] = f"{teacher.first_name} {teacher.last_name}"
        if row.teacher_notes:
            entry["summary"].append(row.teacher_notes)
        if row.mood:
            entry["behavior"].append(row.mood)
        entry["social"].extend(row.activities or [])
    return [dict(entry, **{field: " · ".join(entry[field]) for field in ("summary", "behavior", "social")}) for entry in weeks.values()]


async def teachers(db, user, student_id):
    from app.infrastructure.models.models import ClassroomAssignment
    _, student = await child(db, user, student_id)
    assigned = select(ClassTeacher.user_id).where(ClassTeacher.class_id == student.class_id) if student.class_id else select(User.id).where(False)
    direct = select(StudentTeacherAssignment.teacher_id).where(StudentTeacherAssignment.student_id == student.id)
    adviser = select(ClassRoom.teacher_id).where(ClassRoom.id == student.class_id) if student.class_id else select(User.id).where(False)
    lessons = select(ClassroomAssignment.teacher_id).where(ClassroomAssignment.class_id == student.class_id) if student.class_id else select(User.id).where(False)
    existing = select(ChatConversation.teacher_id).where(ChatConversation.student_id == student.id,
        ChatConversation.parent_id == user.id, ChatConversation.is_active.is_(True))
    rows = (await db.execute(select(User).where(User.organization_id == student.organization_id, User.deleted_at.is_(None),
        User.status == "ACTIVE",
        or_(User.id.in_(assigned), User.id.in_(direct), User.id.in_(adviser), User.id.in_(lessons), User.id.in_(existing))))).scalars()
    return [{"id": str(row.id), "teacher_id": str(row.id), "name": f"{row.first_name} {row.last_name}",
        "full_name": f"{row.first_name} {row.last_name}", "first_name": row.first_name, "last_name": row.last_name} for row in rows]


async def conversation(db, user, student_id, teacher_id, *, create=False):
    from app.core.student_access import require_teacher_for_student
    _, student = await child(db, user, student_id)
    teacher_id = UUID(str(teacher_id))
    row = (await db.execute(select(ChatConversation).where(
        ChatConversation.student_id == student.id, ChatConversation.parent_id == user.id,
        ChatConversation.teacher_id == teacher_id, ChatConversation.is_active.is_(True))
        .order_by(ChatConversation.created_at).limit(1))).scalar_one_or_none()
    if row is None:
        await require_teacher_for_student(db, student, teacher_id)
    if row is None and create:
        row = ChatConversation(student_id=student.id, parent_id=user.id, teacher_id=teacher_id,
            subject_context="Veli-öğretmen iletişimi", created_via="DIRECT")
        db.add(row)
        await db.flush()
    return student, row


async def send_chat(db, user, student_id, teacher_id, content):
    student, thread = await conversation(db, user, student_id, teacher_id, create=True)
    message = ChatMessage(conversation_id=thread.id, sender_id=user.id, sender_role="PARENT",
        recipient_id=UUID(str(teacher_id)), class_id=student.class_id, content=content, is_read=False)
    db.add(message)
    thread.last_message, thread.last_message_at = content, datetime.now(UTC)
    thread.teacher_unread_count = (thread.teacher_unread_count or 0) + 1
    await db.flush()
    return {"id": str(message.id), "message_id": str(message.id), "sender_id": str(user.id),
        "receiver_id": str(teacher_id), "content": content, "sent_at": message.sent_at.isoformat(),
        "is_current_user": True}


async def chat_history(db, user, student_id, teacher_id):
    _, thread = await conversation(db, user, student_id, teacher_id)
    if thread is None:
        return []
    rows = (await db.execute(select(ChatMessage, User).join(User, User.id == ChatMessage.sender_id)
        .where(ChatMessage.conversation_id == thread.id).order_by(ChatMessage.sent_at))).all()
    thread.parent_unread_count = 0
    for message, _ in rows:
        if message.recipient_id == user.id:
            message.is_read = True
    return [{"id": str(row.id), "sender_id": str(row.sender_id), "receiver_id": str(row.recipient_id),
        "content": row.content, "is_read": row.is_read, "sent_at": row.sent_at.isoformat(),
        "sender_name": f"{sender.first_name} {sender.last_name}", "is_current_user": row.sender_id == user.id}
        for row, sender in rows]
