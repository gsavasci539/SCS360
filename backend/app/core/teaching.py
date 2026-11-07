"""The supported database relationships that assign a teacher to a class."""
from sqlalchemy import or_, select

from app.infrastructure.models.models import ClassRoom, ClassTeacher, ClassroomAssignment


def teacher_class_condition(class_model, user_id):
    links, lessons = ClassTeacher.__table__, ClassroomAssignment.__table__
    return or_(class_model.teacher_id == user_id,
        class_model.id.in_(select(links.c.class_id).where(links.c.user_id == user_id)),
        class_model.id.in_(select(lessons.c.class_id).where(lessons.c.teacher_id == user_id)))


def teacher_classes_query(user_id):
    return select(ClassRoom).where(ClassRoom.deleted_at.is_(None), teacher_class_condition(ClassRoom, user_id))
