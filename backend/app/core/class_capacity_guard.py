"""Serialize class roster changes across API, import and legacy ORM paths."""
from collections import defaultdict
from uuid import UUID, uuid4

from sqlalchemy import event, func, inspect, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, ValidationException
from app.core.branch_lifecycle import enforce_branch_lifecycle
from app.infrastructure.models.models import Branch, ClassRoom, Organization, Student, User


def identifier(value):
    return UUID(str(value)) if value is not None else None


def old(state, field, current):
    values = state.attrs[field].history.deleted
    return values[0] if values else current


@event.listens_for(Session, "before_flush")
def enforce_class_capacity(session, context, instances):
    if session.info.get("tenant_context") is None:
        return
    rows = set(session.new) | set(session.dirty) | set(session.deleted)
    deltas, additions, changed_classes, changed_students, touched = defaultdict(int), [], {}, [], set()
    branch_admissions, branch_changes = [], []
    for row in rows:
        state = inspect(row)
        if isinstance(row, Branch) and (row in session.deleted or state.attrs.deleted_at.history.has_changes()
                or state.attrs.is_active.history.has_changes()):
            branch_changes.append(row)
        if isinstance(row, ClassRoom):
            if row not in session.deleted and row.deleted_at is None and (row in session.new
                    or state.attrs.branch_id.history.has_changes() or state.attrs.organization_id.history.has_changes()
                    or state.attrs.deleted_at.history.has_changes()):
                branch_admissions.append(row)
            if row not in session.new and (state.attrs.capacity.history.has_changes()
                    or state.attrs.deleted_at.history.has_changes() or row in session.deleted):
                changed_classes[identifier(row.id)] = row
            continue
        if not isinstance(row, Student):
            continue
        # Relationship-based assignment must obey the same rule as class_id.
        relation = state.attrs.class_room.history
        if relation.has_changes():
            classroom = relation.added[0] if relation.added else None
            if classroom is not None and classroom.id is None:
                classroom.id = uuid4()
            row.class_id = classroom.id if classroom is not None else None
        current = identifier(row.class_id)
        previous = None if row in session.new else identifier(old(state, "class_id", row.class_id))
        was_counted = row not in session.new and old(state, "deleted_at", row.deleted_at) is None
        counted = row not in session.deleted and row.deleted_at is None
        branch_changed = identifier(old(state, "branch_id", row.branch_id)) != identifier(row.branch_id)
        org_changed = identifier(old(state, "organization_id", row.organization_id)) != identifier(row.organization_id)
        if counted and (row in session.new or not was_counted or branch_changed or org_changed or previous != current):
            branch_admissions.append(row)
        if previous != current or was_counted != counted or branch_changed or org_changed:
            touched.update({previous, current} - {None})
            if row not in session.new:
                changed_students.append(row)
        if previous and was_counted:
            deltas[previous] -= 1
        if current and counted:
            deltas[current] += 1
            if row in session.new or previous != current or not was_counted or branch_changed or org_changed:
                additions.append(row)
    affected = touched | set(changed_classes)
    if not affected and not branch_admissions and not branch_changes:
        return  # An unrelated edit never rewrites or blocks a legacy roster.

    # Lock organizations before classes, including every pending quota resource.
    # subscription_guard runs after this listener and reuses the same locks.
    organizations = set()
    for row in rows:
        if isinstance(row, (Student, ClassRoom, User, Branch)):
            organizations.add(identifier(row.organization_id))
            if row not in session.new:
                organizations.add(identifier(old(inspect(row), "organization_id", row.organization_id)))
    org_table, classes, students = Organization.__table__, ClassRoom.__table__, Student.__table__
    for org in sorted(organizations - {None}, key=str):
        session.execute(org_table.update().where(org_table.c.id == org).values(updated_at=org_table.c.updated_at))
    enforce_branch_lifecycle(session, branch_admissions, branch_changes)
    if changed_students:
        actual = {row.id: row for row in session.execute(select(students).where(
            students.c.id.in_([row.id for row in changed_students]))).mappings()}
        for student in changed_students:
            stored, state = actual.get(student.id), inspect(student)
            if stored is None or any(identifier(stored[name]) != identifier(old(state, name, getattr(student, name)))
                    for name in ("class_id", "branch_id", "organization_id")) or (
                    (stored.deleted_at is None) != (old(state, "deleted_at", student.deleted_at) is None)):
                raise ConflictException("Öğrencinin sınıf veya şube kaydı değişti; kaydı yenileyip tekrar deneyin")
    for class_id in sorted(affected, key=str):
        session.execute(classes.update().where(classes.c.id == class_id).values(updated_at=classes.c.updated_at))
    saved = {row.id: row for row in session.execute(select(classes).where(classes.c.id.in_(affected))).mappings()}
    pending = {identifier(row.id): row for row in session.new if isinstance(row, ClassRoom) and row.id}
    for class_id in sorted(affected, key=str):
        row = changed_classes.get(class_id) or pending.get(class_id) or saved.get(class_id)
        if row is None:
            raise ValidationException("Sınıf kaydı bulunamadı")
        count = session.execute(select(func.count()).select_from(students).where(
            students.c.class_id == class_id, students.c.deleted_at.is_(None))).scalar_one()
        final_count = count + deltas.get(class_id, 0)
        if class_id in changed_classes and ((row in session.deleted if isinstance(row, ClassRoom) else False) or row.deleted_at is not None):
            if final_count > 0:
                raise ConflictException("Öğrencileri başka sınıfa aktarmadan sınıf silinemez")
        capacity = row.capacity if row.capacity is not None else 20
        if final_count > capacity and (deltas.get(class_id, 0) > 0 or class_id in changed_classes):
            raise ConflictException("Sınıf kontenjanı yetersiz; kayıtlı öğrenci sayısından daha düşük kontenjan belirlenemez")
    for student in additions:
        class_id = identifier(student.class_id)
        classroom = changed_classes.get(class_id) or pending.get(class_id) or saved.get(class_id)
        if classroom is None or classroom.deleted_at is not None or classroom.is_active is False:
            raise ConflictException("Bu sınıf yeni öğrenci kaydı almıyor")
        if identifier(student.organization_id) != identifier(classroom.organization_id) or identifier(student.branch_id) != identifier(classroom.branch_id):
            raise ValidationException("Öğrenci ve sınıf aynı kurum ve şubeye bağlı olmalıdır")
