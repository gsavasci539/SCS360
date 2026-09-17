from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import PermissionChecker
from app.core.responses import success_response
from app.domain.entities.user import User
from app.core.tenant import TenantContext

router = APIRouter(prefix="/api/teacher", tags=["Teacher"])


@router.get("/my-classes")
async def get_teacher_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get classes assigned to the current teacher"""
    try:
        print(f"Current user ID: {current_user.id}")
        from app.infrastructure.models.models import ClassTeacher, ClassRoom, Student
        from sqlalchemy import func as sa_func
        
        result = await db.execute(
            select(ClassTeacher, ClassRoom)
            .join(ClassRoom, ClassTeacher.class_id == ClassRoom.id)
            .where(ClassTeacher.user_id == current_user.id)
        )
        
        classes_data = []
        for class_teacher, cls in result:
            # Count students in this class
            count_result = await db.execute(
                select(sa_func.count(Student.id)).where(Student.class_id == cls.id)
            )
            student_count = count_result.scalar() or 0
            
            classes_data.append({
                "id": str(cls.id),
                "name": cls.name,
                "student_count": student_count
            })
        
        print(f"Found {len(classes_data)} classes for user {current_user.id}")
        return success_response(classes_data)
    except Exception as e:
        print(f"Error in my-classes: {e}")
        import traceback
        traceback.print_exc()
        return success_response([])


@router.get("/today-schedule")
async def get_teacher_today_schedule(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get today's schedule for the current teacher"""
    try:
        print(f"Getting today's schedule for user {current_user.id}")
        from app.infrastructure.models.models import Timetable, TimetableSlot, ClassroomAssignment, ClassRoom
        print("Imports successful")
        
        today = datetime.utcnow().date()
        day_of_week = today.strftime("%A").upper()
        print(f"Day of week: {day_of_week}")
        
        # Get teacher's classroom assignments
        user_id_clean = str(current_user.id).replace('-', '')
        assignment_result = await db.execute(
            select(ClassroomAssignment).where(ClassroomAssignment.teacher_id == user_id_clean)
        )
        assignments = assignment_result.scalars().all()
        
        print(f"Found {len(assignments)} classroom assignments")
        
        if not assignments:
            print("No assignments found, returning empty")
            return success_response([])
        
        assignment_ids = [a.id for a in assignments]
        print(f"Assignment IDs: {assignment_ids}")
        
        # Get today's timetable entries for these assignments
        result = await db.execute(
            select(Timetable, TimetableSlot, ClassroomAssignment, ClassRoom)
            .select_from(Timetable)
            .join(TimetableSlot, Timetable.slot_id == TimetableSlot.id)
            .join(ClassroomAssignment, Timetable.classroom_assignment_id == ClassroomAssignment.id)
            .join(ClassRoom, Timetable.class_id == ClassRoom.id)
            .where(
                and_(
                    ClassroomAssignment.id.in_(assignment_ids),
                    TimetableSlot.day == day_of_week,
                    Timetable.is_active == True
                )
            )
        )
        
        schedule_data = []
        for timetable, slot, assignment, cls in result:
            schedule_data.append({
                "timetable_id": str(timetable.id),
                "day": slot.day,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "class_name": cls.name,
                "room_number": assignment.room_number or "Belirtilmedi",
                "subject_id": assignment.subject_id or "Ders"
            })
        
        print(f"Returning {len(schedule_data)} schedule items")
        return success_response(schedule_data)
    except Exception as e:
        print(f"Error in today-schedule: {e}")
        import traceback
        traceback.print_exc()
        return success_response([])


@router.get("/pending-tasks")
async def get_teacher_pending_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pending tasks for the current teacher"""
    try:
        print(f"Getting pending tasks for user {current_user.id}")
        from app.infrastructure.models.models import AttendanceRecord, DailyDevelopmentReport, ClassTeacher, ClassRoom
        from sqlalchemy import or_
        
        today = datetime.utcnow().date()
        
        # Get teacher's classes
        user_id_clean = str(current_user.id).replace('-', '')
        class_result = await db.execute(
            select(ClassTeacher, ClassRoom)
            .join(ClassRoom, ClassTeacher.class_id == ClassRoom.id)
            .where(ClassTeacher.user_id == user_id_clean)
        )
        
        tasks_data = []
        
        for class_teacher, cls in class_result:
            class_id_clean = str(cls.id).replace('-', '')
            
            # Check if attendance is taken for today
            attendance_result = await db.execute(
                select(AttendanceRecord).where(
                    and_(
                        AttendanceRecord.class_id == class_id_clean,
                        AttendanceRecord.attendance_date == today
                    )
                )
            )
            attendance_records = attendance_result.scalars().all()
            
            if not attendance_records:
                tasks_data.append({
                    "task_id": f"attendance_{cls.id}",
                    "task_type": "attendance",
                    "class_name": cls.name,
                    "class_id": str(cls.id),
                    "due_date": today.isoformat(),
                    "priority": "high"
                })
            
            # Check if daily report is submitted for today
            report_result = await db.execute(
                select(DailyDevelopmentReport).where(
                    and_(
                        DailyDevelopmentReport.class_id == class_id_clean,
                        DailyDevelopmentReport.date == today
                    )
                )
            )
            report_records = report_result.scalars().all()
            
            if not report_records:
                tasks_data.append({
                    "task_id": f"daily_report_{cls.id}",
                    "task_type": "daily_report",
                    "class_name": cls.name,
                    "class_id": str(cls.id),
                    "due_date": today.isoformat(),
                    "priority": "medium"
                })
        
        print(f"Returning {len(tasks_data)} tasks")
        return success_response({"tasks": tasks_data})
    except Exception as e:
        print(f"Error in pending-tasks: {e}")
        import traceback
        traceback.print_exc()
        return success_response({"tasks": []})


@router.get("/class/{class_id}/students")
async def get_class_students(
    class_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get students in a specific class for the teacher"""
    try:
        print(f"Getting students for class {class_id}")
        print(f"Current user ID: {current_user.id}")
        from app.infrastructure.models.models import Student, StudentParent, Parent, ClassRoom, ClassTeacher
        
        # Verify teacher has access to this class
        class_id_clean = class_id.replace('-', '')
        user_id_clean = str(current_user.id).replace('-', '')
        print(f"Checking teacher access - user_id_clean: {user_id_clean}, class_id_clean: {class_id_clean}")
        
        class_teacher_result = await db.execute(
            select(ClassTeacher).where(
                and_(
                    ClassTeacher.user_id == user_id_clean,
                    ClassTeacher.class_id == class_id_clean
                )
            )
        )
        class_teacher = class_teacher_result.scalar_one_or_none()
        
        print(f"Class teacher result: {class_teacher}")
        
        if not class_teacher:
            print(f"Teacher {current_user.id} has no access to class {class_id}")
            return success_response([])
        
        print(f"Teacher has access to class, fetching students...")
        
        # Get students in this class
        class_id_clean = class_id.replace('-', '')
        print(f"Searching for students with class_id: {class_id_clean}")
        student_result = await db.execute(
            select(Student).where(Student.class_id == class_id_clean)
        )
        students = student_result.scalars().all()
        
        print(f"Found {len(students)} students in class {class_id}")
        
        if not students:
            print("No students found, checking all students in DB...")
            all_students = await db.execute(select(Student))
            all_students_list = all_students.scalars().all()
            print(f"Total students in DB: {len(all_students_list)}")
            for s in all_students_list[:5]:
                print(f"  Student: {s.first_name} {s.last_name}, class_id: {s.class_id}")
        
        students_data = []
        for student in students:
            # Get primary parent
            parent_result = await db.execute(
                select(StudentParent, Parent)
                .join(Parent, StudentParent.parent_id == Parent.id)
                .where(
                    and_(
                        StudentParent.student_id == student.id,
                        StudentParent.is_primary == True
                    )
                )
            )
            parent_data = parent_result.first()
            
            parent_name = None
            if parent_data:
                parent = parent_data[1]
                parent_name = f"{parent.first_name} {parent.last_name}"
            
            students_data.append({
                "student_id": str(student.id),
                "student_name": f"{student.first_name} {student.last_name}",
                "parent_name": parent_name
            })
        
        print(f"Returning {len(students_data)} students with parents")
        return success_response(students_data)
    except Exception as e:
        print(f"Error in get_class_students: {e}")
        import traceback
        traceback.print_exc()
        return success_response([])


@router.get("/chat/{student_id}")
async def get_chat_messages(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat messages between teacher and parent for a student"""
    try:
        from app.infrastructure.models.models import ChatMessage
        
        result = await db.execute(
            select(ChatMessage).where(
                and_(
                    ChatMessage.student_id == student_id,
                    or_(
                        ChatMessage.sender_id == current_user.id,
                        ChatMessage.receiver_id == current_user.id
                    )
                )
            ).order_by(ChatMessage.created_at)
        )
        messages = result.scalars().all()
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                "id": str(msg.id),
                "sender_id": str(msg.sender_id),
                "receiver_id": str(msg.receiver_id),
                "student_id": str(msg.student_id),
                "message": msg.message,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            })
        
        return success_response(messages_data)
    except Exception as e:
        return success_response([])


@router.post("/chat/{student_id}")
async def send_chat_message(
    student_id: str,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a chat message from teacher to parent"""
    try:
        from app.infrastructure.models.models import ChatMessage, StudentParent, Parent
        import uuid
        
        message_text = request.get("message", "")
        if not message_text:
            return success_response({"error": "Message is required"})
        
        # Get primary parent for this student
        parent_result = await db.execute(
            select(StudentParent, Parent)
            .join(Parent, StudentParent.parent_id == Parent.id)
            .where(
                and_(
                    StudentParent.student_id == student_id,
                    StudentParent.is_primary == True
                )
            )
        )
        parent_data = parent_result.first()
        
        if not parent_data:
            return success_response({"error": "Parent not found"})
        
        student_parent, parent = parent_data
        
        # Create chat message
        chat_message = ChatMessage(
            id=str(uuid.uuid4()),
            sender_id=current_user.id,
            receiver_id=parent.id,
            student_id=student_id,
            message=message_text,
            created_at=datetime.utcnow()
        )
        
        db.add(chat_message)
        await db.commit()
        
        return success_response({"success": True})
    except Exception as e:
        await db.rollback()
        return success_response({"error": str(e)})