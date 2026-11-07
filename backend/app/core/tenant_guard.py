"""Apply tenant boundaries to ORM reads and writes, including legacy routers.

Endpoint permissions still decide which feature is available. These session
guards prevent a missed WHERE clause from crossing an organization or branch.
"""
from sqlalchemy import String, and_, cast, event, or_, select
from sqlalchemy.orm import Session, with_loader_criteria
from sqlalchemy.sql import visitors

from app.core.database import Base
from app.core.exceptions import ForbiddenException
from app.core.teaching import teacher_class_condition
from app.core.student_access import uses_relationship_scope


def scope_filters(tenant, student_ids):
    tables = Base.metadata.tables
    branches, students, classes, users = [tables[name] for name in ("branches", "students", "classes", "users")]
    branch_query = select(branches.c.id).where(branches.c.organization_id == tenant.organization_id, branches.c.deleted_at.is_(None))
    if tenant.branch_ids:
        branch_query = branch_query.where(branches.c.id.in_(tenant.branch_ids))
    student_query = select(students.c.id).where(students.c.organization_id == tenant.organization_id,
        students.c.branch_id.in_(branch_query), students.c.deleted_at.is_(None))
    if student_ids is not None:
        student_query = student_query.where(students.c.id.in_(student_ids))
    class_query = select(classes.c.id).where(classes.c.organization_id == tenant.organization_id,
        classes.c.branch_id.in_(branch_query))
    if student_ids is not None:
        linked_classes = select(students.c.class_id).where(students.c.id.in_(student_query))
        allowed = classes.c.id.in_(linked_classes)
        if "teacher" in tenant.role_slugs:
            allowed = or_(allowed, teacher_class_condition(classes.c, tenant.user_id))
        class_query = class_query.where(allowed)
    user_query = select(users.c.id).where(users.c.organization_id == tenant.organization_id)
    return branch_query, student_query, class_query, user_query


def references(column, query):
    # Some historical auxiliary tables use VARCHAR UUIDs even on PostgreSQL.
    if isinstance(column.type, String):
        query = query.with_only_columns(cast(query.selected_columns[0], String))
    return column.in_(query)


def staff_scope(tenant, branches, users):
    """Payroll rows inherit the staff member's actual branch assignments."""
    if not tenant.branch_ids:
        return users
    tables = Base.metadata.tables
    links, classes, teaching, lessons = [tables[name] for name in ("user_branches", "classes", "class_teachers", "classroom_assignments")]
    assignments, students = tables["student_teacher_assignments"], tables["students"]
    identifier = tables["users"].c.id
    return users.where(or_(identifier == tenant.user_id,
        identifier.in_(select(links.c.user_id).where(links.c.branch_id.in_(branches))),
        identifier.in_(select(classes.c.teacher_id).where(classes.c.branch_id.in_(branches))),
        identifier.in_(select(teaching.c.user_id).join(classes, classes.c.id == teaching.c.class_id).where(classes.c.branch_id.in_(branches))),
        identifier.in_(select(lessons.c.teacher_id).join(classes, classes.c.id == lessons.c.class_id).where(classes.c.branch_id.in_(branches))),
        identifier.in_(select(assignments.c.teacher_id).join(students, students.c.id == assignments.c.student_id)
            .where(students.c.branch_id.in_(branches), students.c.deleted_at.is_(None)))))


def criteria(model, tenant, student_ids):
    table = model.__table__
    columns = table.c
    branch_query, student_query, class_query, user_query = scope_filters(tenant, student_ids)
    filters = []
    if table.name == "organizations":
        filters.append(model.id == tenant.organization_id)
    if "organization_id" in columns:
        expression = model.organization_id == str(tenant.organization_id) if tenant.organization_id else model.organization_id.is_(None)
        if table.name == "roles":
            expression = or_(expression, model.organization_id.is_(None))
        filters.append(expression)
    if table.name == "branches":
        filters.append(model.id.in_(branch_query))
    if table.name == "users" and tenant.branch_ids:
        links = Base.metadata.tables["user_branches"]
        classroom = Base.metadata.tables["classes"]
        teaching = Base.metadata.tables["class_teachers"]
        lessons = Base.metadata.tables["classroom_assignments"]
        direct_teaching = Base.metadata.tables["student_teacher_assignments"]
        parents = Base.metadata.tables["parents"]
        student_parents = Base.metadata.tables["student_parents"]
        filters.append(or_(model.id == tenant.user_id,
            model.id.in_(select(links.c.user_id).where(links.c.branch_id.in_(branch_query))),
            model.id.in_(select(classroom.c.teacher_id).where(classroom.c.branch_id.in_(branch_query))),
            model.id.in_(select(teaching.c.user_id).join(classroom, classroom.c.id == teaching.c.class_id)
                .where(classroom.c.branch_id.in_(branch_query))),
            model.id.in_(select(lessons.c.teacher_id).join(classroom, classroom.c.id == lessons.c.class_id)
                .where(classroom.c.branch_id.in_(branch_query))),
            model.id.in_(select(direct_teaching.c.teacher_id).where(direct_teaching.c.student_id.in_(student_query))),
            model.id.in_(select(parents.c.user_id).join(student_parents, student_parents.c.parent_id == parents.c.id)
                .where(student_parents.c.student_id.in_(student_query), parents.c.organization_id == tenant.organization_id))))
    if table.name == "parents" and (tenant.branch_ids or student_ids is not None):
        links = Base.metadata.tables["student_parents"]
        filters.append(or_(model.user_id == tenant.user_id,
            model.id.in_(select(links.c.parent_id).where(links.c.student_id.in_(student_query)))))
    if "branch_id" in columns:
        filters.append(or_(references(model.branch_id, branch_query), model.branch_id.is_(None)))
    if table.name == "students":
        filters.append(model.id.in_(student_query))
    if table.name == "digital_id_tokens":
        filters.append(references(model.student_id, student_query))
    if table.name == "gate_logs":
        # Unattributable legacy events remain available only to the root user.
        filters.append(or_(references(model.student_id, student_query),
            references(model.user_id, staff_scope(tenant, branch_query, user_query)), references(model.branch_id, branch_query)))
    if "student_id" in columns:
        filters.append(or_(references(model.student_id, student_query), model.student_id.is_(None)))
    if table.name == "classes":
        filters.append(model.id.in_(class_query))
    if "class_id" in columns:
        class_filter = or_(references(model.class_id, class_query), model.class_id.is_(None))
        if table.name == "course_materials":
            classes = Base.metadata.tables["classes"]
            institution_classes = select(classes.c.id).where(classes.c.organization_id == tenant.organization_id)
            class_filter = or_(class_filter, and_(model.visibility == "PUBLIC", references(model.class_id, institution_classes)))
        filters.append(class_filter)
    if "teacher_id" in columns:
        filters.append(or_(references(model.teacher_id, user_query), model.teacher_id.is_(None)))
    if table.name in {"tutoring_sessions", "tutoring_requests", "teacher_availability"}:
        filters.append(or_(references(model.teacher_id, staff_scope(tenant, branch_query, user_query)), model.teacher_id.is_(None)))
        if uses_relationship_scope(tenant) and "teacher" in tenant.role_slugs:
            filters.append(or_(model.teacher_id == tenant.user_id, model.teacher_id.is_(None)) if table.name == "tutoring_requests" else model.teacher_id == tenant.user_id)
    if "advisor_teacher_id" in columns:
        filters.append(or_(references(model.advisor_teacher_id, user_query), model.advisor_teacher_id.is_(None)))
    if table.name == "course_materials":
        # Old unowned materials cannot be attributed safely to any institution.
        filters.append(or_(references(model.class_id, class_query),
            references(model.teacher_id, user_query), references(model.created_by, user_query)))
    if table.name == "broadcast_jobs":
        filters.append(references(model.created_by, user_query))
        filters.append(or_(references(model.target_branch_id, branch_query), model.target_branch_id.is_(None)))
        filters.append(or_(references(model.target_class_id, class_query), model.target_class_id.is_(None)))
    if table.name in {"surveys", "consent_documents"} and "organization_id" not in columns:
        filters.append(references(model.created_by, user_query))
    if "staff_id" in columns:
        filters.append(or_(references(model.staff_id, staff_scope(tenant, branch_query, user_query)), model.staff_id.is_(None)))
    if table.name in {"guidance_sessions", "guidance_notes"} and not tenant.has_permission("guidance.read_confidential"):
        filters.append(or_(model.confidentiality_level == "STANDARD", model.counselor_id == tenant.user_id))
    # Tables scoped only through a route, job, or book inherit its ownership.
    relations = [("route_id", "bus_routes"), ("notification_job_id", "notification_jobs"),
        ("book_id", "library_books"), ("homework_id", "homework"),
        ("club_id", "school_clubs"), ("event_id", "club_events"),
        ("survey_id", "surveys"), ("consent_document_id", "consent_documents"), ("authorization_id", "pickup_authorizations"), ("schedule_id", "medication_schedules")]
    if table.name in {"asset_assignments", "maintenance_requests"}:
        relations.append(("item_id", "inventory_items"))
        filters.append(or_(references(model.assigned_to, user_query), model.assigned_to.is_(None)))
    if table.name == "inventory_items":
        relations.append(("location_id", "inventory_locations"))
    for field, target in relations:
        if field in columns and target in Base.metadata.tables:
            related = Base.metadata.tables[target]
            statement = select(related.c.id)
            if "organization_id" in related.c:
                statement = statement.where(related.c.organization_id == tenant.organization_id)
            elif "branch_id" in related.c:
                statement = statement.where(related.c.branch_id.in_(branch_query))
            elif target == "club_events":
                clubs = Base.metadata.tables["school_clubs"]
                statement = statement.where(related.c.club_id.in_(select(clubs.c.id).where(clubs.c.branch_id.in_(branch_query))))
            elif target in {"surveys", "consent_documents"}:
                statement = statement.where(related.c.created_by.in_(user_query))
            elif target == "pickup_authorizations":
                statement = statement.where(related.c.student_id.in_(student_query))
            elif target == "medication_schedules":
                statement = statement.where(related.c.student_id.in_(student_query), related.c.student_id == model.student_id).correlate_except(related)
            filters.append(or_(references(getattr(model, field), statement), getattr(model, field).is_(None)))
    return and_(*filters) if filters else None


@event.listens_for(Session, "do_orm_execute")
def filter_tenant_statements(state):
    tenant = state.session.info.get("tenant_context")
    if tenant is None or tenant.is_super_admin or not state.is_orm_statement:
        return
    ids = state.session.info.get("accessible_student_ids")
    options = []
    mappers = set(state.all_mappers)
    for node in visitors.iterate(state.statement):
        mapper = getattr(node, "_annotations", {}).get("parentmapper")
        if mapper is not None:
            mappers.add(mapper)
    for mapper in mappers:
        condition = criteria(mapper.class_, tenant, ids)
        if condition is not None:
            options.append(with_loader_criteria(mapper.class_, condition, include_aliases=True, propagate_to_loaders=False))
    state.statement = state.statement.options(*options)


@event.listens_for(Session, "before_flush")
def validate_tenant_writes(session, context, instances):
    tenant = session.info.get("tenant_context")
    if tenant is None or tenant.is_super_admin:
        return
    branches, students, classes, users = scope_filters(tenant, session.info.get("accessible_student_ids"))
    staff = staff_scope(tenant, branches, users)
    clubs_table = Base.metadata.tables["school_clubs"]
    events_table = Base.metadata.tables["club_events"]
    clubs = select(clubs_table.c.id).where(clubs_table.c.branch_id.in_(branches))
    events = select(events_table.c.id).where(events_table.c.club_id.in_(clubs))
    inventory = Base.metadata.tables["inventory_items"]
    locations_table = Base.metadata.tables["inventory_locations"]
    items = select(inventory.c.id).where(inventory.c.branch_id.in_(branches))
    locations = select(locations_table.c.id).where(locations_table.c.branch_id.in_(branches))
    survey_table = Base.metadata.tables["surveys"]
    consent_table = Base.metadata.tables["consent_documents"]
    surveys = select(survey_table.c.id).where(survey_table.c.organization_id == tenant.organization_id)
    consents = select(consent_table.c.id).where(consent_table.c.organization_id == tenant.organization_id)
    for row in set(session.new) | set(session.dirty) | set(session.deleted):
        columns = row.__table__.c
        if row.__table__.name in {"tutoring_sessions", "tutoring_requests", "teacher_availability"}:
            if uses_relationship_scope(tenant) and "teacher" in tenant.role_slugs and row.teacher_id not in {None, tenant.user_id}:
                raise ForbiddenException("Yalnız kendi etüt kayıtlarınızı değiştirebilirsiniz")
            if row.teacher_id is not None and not session.execute(select(staff.exists().where(staff.selected_columns[0] == row.teacher_id))).scalar():
                raise ForbiddenException("Öğretmen erişilebilir şubeye bağlı değil")
        if row.__table__.name == "users" and getattr(row, "is_super_admin", False):
            raise ForbiddenException("Süper yönetici hesaplarını yalnızca süper yönetici değiştirebilir")
        if row.__table__.name == "roles" and getattr(row, "organization_id", None) is None:
            raise ForbiddenException("Sistem rollerini yalnızca süper yönetici değiştirebilir")
        if row.__table__.name == "role_permissions":
            roles = Base.metadata.tables["roles"]
            owner = session.execute(select(roles.c.organization_id).where(roles.c.id == row.role_id)).scalar_one_or_none()
            if owner != tenant.organization_id:
                raise ForbiddenException("Başka kurumun veya sistem rolünün yetkileri değiştirilemez")
        if "organization_id" in columns:
            value = getattr(row, "organization_id", None)
            if value is not None and str(value).replace("-", "") != str(tenant.organization_id).replace("-", ""):
                raise ForbiddenException("Başka bir kuruma kayıt yazılamaz")
        extra = []
        if row.__table__.name in {"asset_assignments", "maintenance_requests"}:
            extra = [("item_id", items), ("assigned_to", users), ("reported_by", users)]
        elif row.__table__.name == "inventory_items":
            extra = [("location_id", locations)]
        elif row.__table__.name in {"surveys", "consent_documents"} and row in session.new:
            extra = [("created_by", users)]
        elif row.__table__.name in {"guidance_sessions", "guidance_notes"}:
            extra = [("counselor_id", staff)]
        elif row.__table__.name == "behavioral_incidents":
            extra = [("reported_by", users)]
        elif row.__table__.name == "pickup_authorizations":
            extra = [("created_by", users)] if row in session.new else []
        elif row.__table__.name == "pickup_logs":
            authorizations = Base.metadata.tables["pickup_authorizations"]
            allowed = select(authorizations.c.id).where(authorizations.c.student_id.in_(students), authorizations.c.student_id == row.student_id)
            extra = [("authorization_id", allowed), ("verified_by", users)]
            if row in session.new and row.authorization_id is None:
                raise ForbiddenException("Teslim kaydı için aynı öğrenciye ait yetki gerekir")
        elif row.__table__.name == "medication_logs":
            schedules = Base.metadata.tables["medication_schedules"]
            allowed = select(schedules.c.id).where(schedules.c.student_id.in_(students), schedules.c.student_id == row.student_id)
            extra = [("schedule_id", allowed), ("given_by", users)]
        elif row.__table__.name == "medication_schedules":
            extra = [("updated_by", users)] + ([("created_by", users)] if row in session.new else [])
        elif row.__table__.name == "health_records":
            extra = [("updated_by", users)]
        elif row.__table__.name == "infirmary_visits" and row in session.new:
            extra = [("examined_by", users)]
        elif row.__table__.name == "gate_logs" and row in session.new:
            if row.student_id is None and row.user_id is None and row.branch_id is None:
                raise ForbiddenException("Kapı kaydı erişilebilir bir kuruma bağlanmalı")
            extra = [("verified_by", users), ("user_id", staff)]
        for field, allowed in [("branch_id", branches), ("student_id", students), ("class_id", classes),
            ("teacher_id", users), ("staff_id", staff), ("advisor_teacher_id", users),
            ("target_branch_id", branches), ("target_class_id", classes), ("club_id", clubs), ("event_id", events),
            ("survey_id", surveys), ("consent_document_id", consents)] + extra:
            value = getattr(row, field, None)
            if field in columns and value is not None:
                if tenant.platform_admin and str(value).replace("-", "") == str(tenant.user_id).replace("-", "") and field in {
                    "created_by", "updated_by", "assigned_by", "verified_by", "reported_by", "given_by", "examined_by"
                }:
                    continue  # Preserve the real platform actor, without broadening staff visibility.
                # Core selects avoid recursively applying this ORM event.
                if session.execute(select(allowed.exists().where(allowed.selected_columns[0] == value))).scalar() is not True:
                    raise ForbiddenException("İlişkili kayıt bu kurum veya erişim kapsamına ait değil")
