from app.core.dates import school_today
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.application.schemas.common import (
    AttendanceCreate,
    AttendanceUpdate,
    BulkAttendanceCreate,
    ClassCreate,
    ClassUpdate,
    ClassStudentAssign,
    ClassStudentsAssign,
    ClassTransferRequest,
    DebtCreate,
    DebtUpdate,
    ParentCreate,
    ExistingParentLink,
    PaymentCancel,
    PaymentCreate,
    StudentCreate,
    StudentUpdate,
)
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.core.permissions import PermissionChecker
from app.core.responses import paginate, success_response
from app.core.tenant import TenantContext
from app.domain.services.class_capacity import ClassCapacityChecker
from app.domain.services.debt_calculator import DebtCalculator
from app.infrastructure.models.models import (
    AttendanceRecord,
    AttendanceStatus,
    AuditAction,
    AuditLog,
    Branch,
    ClassRoom,
    ClassTeacher,
    Debt,
    DebtStatus,
    DebtType,
    GenderType,
    NotificationChannel,
    NotificationJob,
    Parent,
    ParentRelationType,
    Payment,
    PaymentMethod,
    Receipt,
    ReceiptStatus,
    Student,
    StudentParent,
    StudentStatus,
    User,
    UserStatus,
    Role,
)
from app.infrastructure.repositories.base import BaseRepository

router = APIRouter(tags=["Core Modules"])


def student_dict(s: Student, tenant: TenantContext) -> dict:
    data = {
        "id": str(s.id),
        "organization_id": str(s.organization_id),
        "branch_id": str(s.branch_id),
        "class_id": str(s.class_id) if s.class_id else None,
        "student_number": s.student_number,
        "first_name": s.first_name,
        "last_name": s.last_name,
        "gender": s.gender.value if s.gender else None,
        "birth_date": s.birth_date.isoformat() if s.birth_date else None,
        "date_of_birth": s.birth_date.isoformat() if s.birth_date else None,
        "enrollment_date": s.enrollment_date.isoformat(),
        "status": s.status.value,
        "photo_url": s.photo_url,
    }
    if tenant.has_permission("students.write"):
        data.update(address=s.address, notes=s.notes)
    if tenant.has_permission("health.read"):
        data["health_notes"] = s.health_notes
    return data


# ---------- STUDENTS ----------


@router.get("/api/students/organization-options")
async def student_organization_options(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None, max_length=150), organization_id: UUID | None = None,
    branch_id: UUID | None = None, selected_id: UUID | None = None, student_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("students.write")), db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.student_form_choices import choices
    return success_response(await choices(db, tenant, "organizations", page=page, page_size=page_size,
        search=search, organization_id=organization_id, branch_id=branch_id,
        selected_id=selected_id, student_id=student_id))


@router.get("/api/students/branch-options")
async def student_branch_options(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None, max_length=150), organization_id: UUID | None = None,
    branch_id: UUID | None = None, selected_id: UUID | None = None, student_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("students.write")), db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.student_form_choices import choices
    return success_response(await choices(db, tenant, "branches", page=page, page_size=page_size,
        search=search, organization_id=organization_id, branch_id=branch_id,
        selected_id=selected_id, student_id=student_id))


@router.get("/api/students/class-options")
async def student_class_options(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None, max_length=150), organization_id: UUID | None = None,
    branch_id: UUID | None = None, selected_id: UUID | None = None, student_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("students.write")), db: AsyncSession = Depends(get_db, scope="function"),
):
    from app.application.services.student_form_choices import choices
    return success_response(await choices(db, tenant, "classes", page=page, page_size=page_size,
        search=search, organization_id=organization_id, branch_id=branch_id,
        selected_id=selected_id, student_id=student_id))


@router.get("/api/students/{student_id}/form")
async def student_edit_form(
    student_id: UUID, tenant: TenantContext = Depends(PermissionChecker("students.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    student = await BaseRepository(db, tenant).get_by_id(student_id, Student)
    return success_response(student_dict(student, tenant))


@router.get("/api/students")
async def list_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    branch_id: UUID | None = None,
    class_id: UUID | None = None,
    status: str | None = None,
    unassigned: bool = False,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    query = select(Student).where(Student.deleted_at.is_(None))
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, Student)
    query = repo._branch_filter(query, Student)
    if branch_id:
        query = query.where(Student.branch_id == branch_id)
    if class_id:
        query = query.where(Student.class_id == class_id)
    if status:
        query = query.where(Student.status == status)
    if unassigned:
        query = query.where(Student.class_id.is_(None))
    if search:
        query = query.where(
            Student.first_name.ilike(f"%{search}%") | Student.last_name.ilike(f"%{search}%")
        )
    if "teacher" in tenant.role_slugs and tenant.class_ids:
        query = query.where(Student.class_id.in_(tenant.class_ids))
    query = query.order_by(Student.last_name, Student.first_name)
    items, total = await repo.paginate(query, page, page_size)
    return success_response(paginate([student_dict(s, tenant) for s in items], total, page, page_size))


@router.post("/api/students")
async def create_student(
    body: StudentCreate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    branch = await repo.require_related(UUID(body.branch_id), Branch)
    if body.health_notes is not None and not tenant.has_permission("health.write"):
        raise ForbiddenException("Sağlık notu için sağlık kayıtlarını düzenleme yetkisi gerekli")
    requested_org_id = UUID(body.organization_id)
    if requested_org_id != branch.organization_id:
        raise ValidationException("Şube ve organizasyon eşleşmiyor")
    class_id = UUID(body.class_id) if body.class_id else None
    if class_id:
        classroom = await repo.require_related(class_id, ClassRoom)
        if classroom.branch_id != branch.id:
            raise ValidationException("Sınıf seçilen şubeye ait değil")
    student = Student(
        organization_id=branch.organization_id,
        branch_id=branch.id,
        class_id=class_id,
        student_number=body.student_number,
        first_name=body.first_name,
        last_name=body.last_name,
        gender=GenderType(body.gender) if body.gender else None,
        birth_date=(
            date.fromisoformat(body.birth_date or body.date_of_birth)
            if (body.birth_date or body.date_of_birth)
            else None
        ),
        enrollment_date=(
            date.fromisoformat(body.enrollment_date) if body.enrollment_date else school_today()
        ),
        status=StudentStatus(body.status),
        health_notes=body.health_notes,
        notes=body.notes,
        address=body.address,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(student)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictException("Öğrenci numarası kurumda zaten kullanılıyor veya ilişki kaydı değişmiş") from None
    return success_response(student_dict(student, tenant), "Öğrenci oluşturuldu")


@router.get("/api/students/{student_id}")
async def get_student(
    student_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    student = await repo.get_by_id(student_id, Student)
    return success_response(student_dict(student, tenant))


@router.put("/api/students/{student_id}")
async def update_student(
    student_id: UUID,
    body: StudentUpdate,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    student = await repo.get_by_id(student_id, Student)
    data = body.model_dump(exclude_unset=True)
    if "health_notes" in data and not tenant.has_permission("health.write"):
        raise ForbiddenException("Sağlık notu için sağlık kayıtlarını düzenleme yetkisi gerekli")
    if "branch_id" in data and data["branch_id"]:
        data["branch_id"] = UUID(data["branch_id"])
        branch = await repo.require_related(data["branch_id"], Branch)
        if branch.organization_id != student.organization_id:
            raise ValidationException("Şube öğrencinin organizasyonuna ait değil")
    if "class_id" in data and data["class_id"]:
        data["class_id"] = UUID(data["class_id"])
        classroom = await repo.require_related(data["class_id"], ClassRoom)
        target_branch_id = data.get("branch_id", student.branch_id)
        if classroom.branch_id != target_branch_id:
            raise ValidationException("Sınıf öğrencinin şubesine ait değil")
    elif "class_id" not in data and "branch_id" in data and data["branch_id"] and student.class_id:
        current_classroom = await repo.require_related(student.class_id, ClassRoom)
        if current_classroom.branch_id != data["branch_id"]:
            raise ValidationException("Şube değişiminden önce sınıf atamasını kaldırın")
    if "gender" in data and data["gender"]:
        data["gender"] = GenderType(data["gender"])
    if "date_of_birth" in data:
        alias = data.pop("date_of_birth")
        if alias is not None or "birth_date" not in data:
            data["birth_date"] = alias
    if data.get("birth_date") is not None:
        data["birth_date"] = date.fromisoformat(data["birth_date"])
    if data.get("enrollment_date") is not None:
        data["enrollment_date"] = date.fromisoformat(data["enrollment_date"])
    if "status" in data and data["status"]:
        data["status"] = StudentStatus(data["status"])
    for k, v in data.items():
        setattr(student, k, v)
    student.updated_by = user.id
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictException("Öğrenci numarası kurumda zaten kullanılıyor veya ilişki kaydı değişmiş") from None
    return success_response(student_dict(student, tenant), "Öğrenci güncellendi")


@router.delete("/api/students/{student_id}")
async def delete_student(
    student_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    student = await repo.get_by_id(student_id, Student)
    student.status = StudentStatus.PASSIVE
    await repo.soft_delete(student)
    await db.flush()
    return success_response(message="Öğrenci pasife alındı")


@router.get("/api/students/{student_id}/parents")
async def get_student_parents(
    student_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("student.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    await repo.get_by_id(student_id, Student)
    result = await db.execute(
        select(Parent, StudentParent)
        .join(StudentParent, StudentParent.parent_id == Parent.id)
        .where(StudentParent.student_id == student_id, Parent.deleted_at.is_(None))
    )
    parents = []
    for parent, sp in result.all():
        parents.append(
            {
                "id": str(parent.id),
                "first_name": parent.first_name,
                "last_name": parent.last_name,
                "relation_type": parent.relation_type.value,
                "phone": parent.phone,
                "email": parent.email,
                "is_primary": sp.is_primary,
                "is_emergency": sp.is_emergency,
            }
        )
    return success_response(parents)


@router.post("/api/students/{student_id}/parents")
async def add_student_parent(
    student_id: UUID,
    body: ParentCreate | ExistingParentLink,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    student = await repo.get_by_id(student_id, Student)
    if isinstance(body, ExistingParentLink):
        parent = await repo.get_by_id(UUID(body.parent_id), Parent)
        if parent.organization_id != student.organization_id:
            raise ValidationException("Veli ve öğrenci aynı kuruma ait olmalıdır")
        existing = (await db.execute(select(StudentParent).where(
            StudentParent.student_id == student.id, StudentParent.parent_id == parent.id,
        ))).scalar_one_or_none()
        if existing is not None:
            raise ConflictException("Bu veli öğrenciye zaten bağlı")
        db.add(StudentParent(student_id=student.id, parent_id=parent.id,
            is_primary=body.is_primary, is_emergency=body.is_emergency))
        return success_response({"id": str(parent.id)}, "Veli bağlandı")
    parent = Parent(
        organization_id=student.organization_id,
        first_name=body.first_name,
        last_name=body.last_name,
        relation_type=ParentRelationType(body.relation_type),
        phone=body.phone,
        sms_phone=body.sms_phone,
        whatsapp_phone=body.whatsapp_phone,
        email=body.email,
        address=body.address,
        receive_notifications=body.receive_notifications,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(parent)
    await db.flush()
    db.add(
        StudentParent(
            student_id=student_id,
            parent_id=parent.id,
            is_primary=body.is_primary,
            is_emergency=body.is_emergency,
        )
    )
    return success_response({"id": str(parent.id)}, "Veli eklendi")


@router.delete("/api/students/{student_id}/parents/{parent_id}")
async def remove_student_parent(
    student_id: UUID,
    parent_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("student.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    await repo.get_by_id(student_id, Student)
    relation = (
        await db.execute(
            select(StudentParent).where(
                StudentParent.student_id == student_id, StudentParent.parent_id == parent_id
            )
        )
    ).scalar_one_or_none()
    if not relation:
        raise NotFoundException("Veli ilişkisi bulunamadı")
    await db.delete(relation)
    return success_response(message="Veli ilişkisi kaldırıldı")


# ---------- CLASSES ----------


def class_dict(c: ClassRoom, student_count: int = 0, teacher_name: str | None = None) -> dict:
    return {
        "id": str(c.id),
        "organization_id": str(c.organization_id),
        "branch_id": str(c.branch_id),
        "name": c.name,
        "code": c.code,
        "capacity": c.capacity,
        "student_count": student_count,
        "occupancy_rate": ClassCapacityChecker.occupancy_rate(student_count, c.capacity),
        "academic_year": c.academic_year,
        "is_active": c.is_active,
        "description": c.description,
        "teacher_id": str(c.teacher_id) if c.teacher_id else None,
        "teacher_name": teacher_name,
    }


def class_teacher_query(organization_id: UUID):
    return select(User).where(
        User.organization_id == organization_id, User.deleted_at.is_(None),
        User.is_super_admin.is_(False), User.status == UserStatus.ACTIVE,
        User.roles.any((Role.slug == "teacher") & Role.deleted_at.is_(None)
            & or_(Role.organization_id.is_(None), Role.organization_id == organization_id)),
    )


async def require_class_teacher(db, teacher_id, classroom):
    if not teacher_id:
        return None
    teacher = (await db.execute(class_teacher_query(classroom.organization_id).where(
        User.id == UUID(str(teacher_id)),
        or_(~User.branches.any(Branch.deleted_at.is_(None) & (Branch.organization_id == classroom.organization_id)),
            User.branches.any((Branch.id == classroom.branch_id) & Branch.deleted_at.is_(None))),
    ))).scalar_one_or_none()
    if teacher is None:
        raise ValidationException("Bu sınıf için etkin, aynı kuruma ve şubeye yetkili bir öğretmen seçin")
    return teacher


async def class_teacher_names(db, classrooms):
    # Resolve names in one minimal query; class readers need no user-directory permission.
    pairs = {(row.teacher_id, row.organization_id) for row in classrooms if row.teacher_id}
    if not pairs:
        return {}
    users = User.__table__
    rows = (await db.execute(select(users.c.id, users.c.first_name, users.c.last_name).where(
        users.c.deleted_at.is_(None), users.c.is_super_admin.is_(False),
        or_(*[(users.c.id == user_id) & (users.c.organization_id == org_id) for user_id, org_id in pairs]),
    ))).all()
    return {row.id: f"{row.first_name} {row.last_name}".strip() for row in rows}


@router.get("/api/classes/teacher-options")
async def class_teacher_options(
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=100),
    search: str | None = Query(None, max_length=150), branch_id: UUID | None = None,
    organization_id: UUID | None = None, selected_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    org_id = tenant.organization_id if not tenant.is_super_admin else organization_id
    if org_id is None:
        return success_response(paginate([], 0, page, page_size))
    query = class_teacher_query(org_id)
    if branch_id:
        branch = await BaseRepository(db, tenant).get_by_id(branch_id, Branch)
        if branch.organization_id != org_id:
            raise ValidationException("Şube ve kurum eşleşmiyor")
        query = query.where(or_(~User.branches.any(Branch.deleted_at.is_(None) & (Branch.organization_id == org_id)),
            User.branches.any((Branch.id == branch_id) & Branch.deleted_at.is_(None))))
    selected = (await db.execute(query.where(User.id == selected_id))).scalar_one_or_none() if selected_id else None
    if search:
        query = query.where((User.first_name + " " + User.last_name).ilike(f"%{search}%"))
    rows, total = await BaseRepository(db, tenant).paginate(query.order_by(User.first_name, User.last_name, User.id), page, page_size)
    choice = lambda row: {"id": str(row.id), "name": f"{row.first_name} {row.last_name}".strip()}
    return success_response({**paginate([choice(row) for row in rows], total, page, page_size), "selected": choice(selected) if selected else None})


@router.get("/api/classes")
async def list_classes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    branch_id: UUID | None = None,
    search: str | None = Query(None, max_length=150),
    tenant: TenantContext = Depends(PermissionChecker("class.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    query = select(ClassRoom).where(ClassRoom.deleted_at.is_(None))
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, ClassRoom)
    query = repo._branch_filter(query, ClassRoom)
    if branch_id:
        query = query.where(ClassRoom.branch_id == branch_id)
    if search:
        query = query.where(or_(ClassRoom.name.ilike(f"%{search}%"), ClassRoom.code.ilike(f"%{search}%")))
    items, total = await repo.paginate(query.order_by(ClassRoom.name), page, page_size)
    teacher_names = await class_teacher_names(db, items)
    data = []
    for c in items:
        count = (
            await db.execute(
                select(func.count())
                .select_from(Student)
                .where(Student.class_id == c.id, Student.deleted_at.is_(None))
            )
        ).scalar() or 0
        data.append(class_dict(c, count, teacher_names.get(c.teacher_id)))
    return success_response(paginate(data, total, page, page_size))


@router.post("/api/classes")
async def create_class(
    body: ClassCreate,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    branch = await repo.require_related(UUID(body.branch_id), Branch)
    if UUID(body.organization_id) != branch.organization_id:
        raise ValidationException("Şube ve organizasyon eşleşmiyor")
    classroom = ClassRoom(
        organization_id=branch.organization_id,
        branch_id=branch.id,
        name=body.name,
        code=body.code,
        description=body.description,
        capacity=body.capacity,
        academic_year=body.academic_year,
        is_active=body.is_active,
        created_by=user.id,
        updated_by=user.id,
    )
    teacher = await require_class_teacher(db, body.teacher_id, classroom)
    classroom.teacher_id = teacher.id if teacher else None
    db.add(classroom)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise ConflictException("Bu şubede aynı adlı sınıf zaten var") from exc
    return success_response(class_dict(classroom, teacher_name=f"{teacher.first_name} {teacher.last_name}".strip() if teacher else None), "Sınıf oluşturuldu")


@router.get("/api/classes/{class_id}")
async def get_class(
    class_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("class.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    classroom = await repo.get_by_id(class_id, ClassRoom)
    count = (
        await db.execute(
            select(func.count())
            .select_from(Student)
            .where(Student.class_id == class_id, Student.deleted_at.is_(None))
        )
    ).scalar() or 0
    names = await class_teacher_names(db, [classroom])
    return success_response(class_dict(classroom, count, names.get(classroom.teacher_id)))


@router.put("/api/classes/{class_id}")
async def update_class(
    class_id: UUID,
    body: ClassUpdate,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    classroom = await repo.get_by_id(class_id, ClassRoom)
    changes = body.model_dump(exclude_unset=True)
    for key in ("organization_id", "branch_id"):
        if key in changes and changes.pop(key) != str(getattr(classroom, key)):
            raise ValidationException("Sınıfın kurumu veya şubesi bu işlemle değiştirilemez")
    if "teacher_id" in changes and (UUID(changes["teacher_id"]) if changes["teacher_id"] else None) != classroom.teacher_id:
        teacher = await require_class_teacher(db, changes["teacher_id"], classroom)
        changes["teacher_id"] = teacher.id if teacher else None
    elif "teacher_id" in changes:
        changes["teacher_id"] = classroom.teacher_id
    for k, v in changes.items():
        setattr(classroom, k, v)
    classroom.updated_by = user.id
    try:
        await db.flush()
    except IntegrityError as exc:
        raise ConflictException("Bu şubede aynı adlı sınıf zaten var") from exc
    names = await class_teacher_names(db, [classroom])
    count = (await db.execute(select(func.count(Student.id)).where(Student.class_id == class_id, Student.deleted_at.is_(None)))).scalar() or 0
    return success_response(class_dict(classroom, count, names.get(classroom.teacher_id)), "Sınıf güncellendi")


@router.delete("/api/classes/{class_id}")
async def delete_class(
    class_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    classroom = await repo.get_by_id(class_id, ClassRoom)
    await repo.soft_delete(classroom)
    await db.flush()
    return success_response(message="Sınıf silindi")


@router.post("/api/classes/{class_id}/students")
async def assign_student_to_class(
    class_id: UUID,
    body: ClassStudentAssign,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    classroom = await repo.get_by_id(class_id, ClassRoom)
    student_id = body.student_id
    student = await repo.get_by_id(student_id, Student)
    if student.branch_id != classroom.branch_id:
        raise ValidationException("Öğrenci ve sınıf aynı şubede olmalıdır")
    student.class_id = class_id
    await db.flush()
    return success_response(message="Öğrenci sınıfa atandı")


@router.get("/api/classes/{class_id}/students")
async def list_class_students(
    class_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("class.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    await repo.get_by_id(class_id, ClassRoom)
    query = select(Student).where(Student.class_id == class_id, Student.deleted_at.is_(None))
    query = repo._org_filter(query, Student)
    query = repo._branch_filter(query, Student)
    students = (
        (await db.execute(query.order_by(Student.last_name, Student.first_name))).scalars().all()
    )
    return success_response([student_dict(student, tenant) for student in students])


@router.post("/api/classes/{class_id}/assign-students")
async def assign_students_to_class(
    class_id: UUID,
    body: ClassStudentsAssign,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    classroom = await repo.get_by_id(class_id, ClassRoom)
    student_ids = body.student_ids
    students = (
        list(
            (
                await db.execute(
                    repo._branch_filter(
                        repo._org_filter(
                            select(Student).where(
                                Student.id.in_(student_ids), Student.deleted_at.is_(None)
                            ),
                            Student,
                        ),
                        Student,
                    )
                )
            )
            .scalars()
            .all()
        )
        if student_ids
        else []
    )
    if len(students) != len(set(student_ids)):
        raise ValidationException("Geçersiz öğrenci kaydı")
    for student in students:
        if student.branch_id != classroom.branch_id:
            raise ValidationException("Öğrenci ve sınıf aynı şubede olmalıdır")
        student.class_id = class_id
    await db.flush()
    return success_response({"assigned": len(students)}, "Öğrenciler sınıfa atandı")


@router.post("/api/classes/{class_id}/transfer-students")
async def transfer_class_students(
    class_id: UUID, body: ClassTransferRequest,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    source = await repo.get_by_id(class_id, ClassRoom)
    target = await repo.get_by_id(body.target_class_id, ClassRoom)
    if source.organization_id != target.organization_id or source.branch_id != target.branch_id:
        raise ValidationException("Sınıf aktarımı aynı kurum ve şube içinde yapılmalıdır; şube değişimi için öğrenci kaydını düzenleyin")
    query = select(Student).where(Student.id.in_(body.student_ids), Student.class_id == class_id, Student.deleted_at.is_(None))
    rows = (await db.execute(repo._branch_filter(repo._org_filter(query, Student), Student))).scalars().all()
    if len(rows) != len(body.student_ids):
        raise ValidationException("Belirtilen öğrencilerin tümü kaynak sınıfta olmalıdır")
    for student in rows:
        student.class_id = body.target_class_id
        student.updated_by = tenant.user_id
    await db.flush()
    return success_response({"transferred_count": len(rows), "source_class_id": str(class_id), "target_class_id": str(body.target_class_id)}, "Öğrenciler sınıfa aktarıldı")


@router.delete("/api/classes/{class_id}/students/{student_id}")
async def remove_student_from_class(
    class_id: UUID,
    student_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    student = await repo.get_by_id(student_id, Student)
    if student.class_id != class_id:
        raise NotFoundException("Öğrenci bu sınıfta değil")
    student.class_id = None
    await db.flush()
    return success_response(message="Öğrenci sınıftan çıkarıldı")


@router.get("/api/classes/{class_id}/occupancy")
async def class_occupancy(
    class_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("class.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    classroom = await repo.get_by_id(class_id, ClassRoom)
    count = (
        await db.execute(
            select(func.count())
            .select_from(Student)
            .where(Student.class_id == class_id, Student.deleted_at.is_(None))
        )
    ).scalar() or 0
    return success_response(
        {
            "class_id": str(class_id),
            "capacity": classroom.capacity,
            "current_count": count,
            "available": max(0, classroom.capacity - count),
            "occupancy_rate": ClassCapacityChecker.occupancy_rate(count, classroom.capacity),
            "is_full": count >= classroom.capacity,
        }
    )


@router.post("/api/classes/{class_id}/teachers")
async def assign_teacher_to_class(
    class_id: UUID,
    body: dict,
    tenant: TenantContext = Depends(PermissionChecker("class.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    classroom = await repo.get_by_id(class_id, ClassRoom)
    teacher_id = UUID(body["user_id"])
    teacher = await repo.require_related(teacher_id, User)
    if teacher.organization_id != classroom.organization_id:
        raise ValidationException("Öğretmen sınıfın organizasyonuna ait değil")
    existing = await db.execute(
        select(ClassTeacher).where(
            ClassTeacher.class_id == class_id, ClassTeacher.user_id == teacher_id
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException("Öğretmen zaten bu sınıfa atanmış")
    db.add(ClassTeacher(class_id=class_id, user_id=teacher_id, assigned_by=user.id))
    return success_response(message="Öğretmen sınıfa atandı")


# ---------- ATTENDANCE ----------


@router.get("/api/attendance")
async def list_attendance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    class_id: UUID | None = None,
    attendance_date: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("attendance.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    query = select(AttendanceRecord).where(AttendanceRecord.deleted_at.is_(None))
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, AttendanceRecord)
    query = repo._branch_filter(query, AttendanceRecord)
    if class_id:
        query = query.where(AttendanceRecord.class_id == class_id)
    if attendance_date:
        query = query.where(AttendanceRecord.attendance_date == date.fromisoformat(attendance_date))
    items, total = await repo.paginate(
        query.order_by(AttendanceRecord.attendance_date.desc()), page, page_size
    )
    data = [
        {
            "id": str(a.id),
            "student_id": str(a.student_id),
            "class_id": str(a.class_id),
            "attendance_date": a.attendance_date.isoformat(),
            "status": a.status.value,
        }
        for a in items
    ]
    return success_response(paginate(data, total, page, page_size))


@router.post("/api/attendance")
async def create_attendance(
    body: AttendanceCreate,
    tenant: TenantContext = Depends(PermissionChecker("attendance.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    student = await repo.get_by_id(UUID(body.student_id), Student)
    classroom = await repo.require_related(UUID(body.class_id), ClassRoom)
    if classroom.branch_id != student.branch_id:
        raise ValidationException("Öğrenci ve sınıf aynı şubede olmalıdır")
    existing = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.student_id == student.id,
            AttendanceRecord.attendance_date == date.fromisoformat(body.attendance_date),
            AttendanceRecord.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictException("Bu öğrenci için aynı tarihte kayıt mevcut")
    record = AttendanceRecord(
        organization_id=student.organization_id,
        branch_id=student.branch_id,
        class_id=classroom.id,
        student_id=student.id,
        attendance_date=date.fromisoformat(body.attendance_date),
        status=AttendanceStatus(body.status),
        notes=body.notes,
        recorded_by=user.id,
    )
    db.add(record)
    await db.flush()
    return success_response({"id": str(record.id)}, "Yoklama kaydedildi")


@router.post("/api/attendance/bulk")
async def bulk_attendance(
    body: BulkAttendanceCreate,
    tenant: TenantContext = Depends(PermissionChecker("attendance.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    created = 0
    att_date = date.fromisoformat(body.attendance_date)
    repo = BaseRepository(db, tenant)
    classroom = await repo.require_related(UUID(body.class_id), ClassRoom)
    for rec in body.records:
        student_id = UUID(rec["student_id"])
        existing = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.attendance_date == att_date,
                AttendanceRecord.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            continue
        student = await repo.get_by_id(student_id, Student)
        if student.branch_id != classroom.branch_id:
            raise ValidationException("Öğrenci ve sınıf aynı şubede olmalıdır")
        db.add(
            AttendanceRecord(
                organization_id=student.organization_id,
                branch_id=student.branch_id,
                class_id=classroom.id,
                student_id=student_id,
                attendance_date=att_date,
                status=AttendanceStatus(rec["status"]),
                recorded_by=user.id,
            )
        )
        created += 1
    return success_response({"created": created}, f"{created} yoklama kaydı oluşturuldu")


@router.put("/api/attendance/{attendance_id}")
async def update_attendance(
    attendance_id: UUID,
    body: AttendanceUpdate,
    tenant: TenantContext = Depends(PermissionChecker("attendance.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    record = await repo.get_by_id(attendance_id, AttendanceRecord)
    if body.status:
        record.status = AttendanceStatus(body.status)
    if body.notes is not None:
        record.notes = body.notes
    if body.check_in_time:
        from datetime import time as dt_time

        parts = body.check_in_time.split(":")
        record.check_in_time = dt_time(int(parts[0]), int(parts[1]))
    return success_response({"id": str(record.id)}, "Yoklama güncellendi")


@router.delete("/api/attendance/{attendance_id}")
async def delete_attendance(
    attendance_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("attendance.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    record = await repo.get_by_id(attendance_id, AttendanceRecord)
    await repo.soft_delete(record)
    return success_response(message="Yoklama kaydı silindi")


@router.get("/api/attendance/reports/monthly")
async def monthly_attendance_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    class_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("attendance.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    query = select(AttendanceRecord).where(
        AttendanceRecord.attendance_date >= start,
        AttendanceRecord.attendance_date < end,
        AttendanceRecord.deleted_at.is_(None),
    )
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, AttendanceRecord)
    if class_id:
        query = query.where(AttendanceRecord.class_id == class_id)
    result = await db.execute(query)
    records = result.scalars().all()
    summary = {}
    for r in records:
        key = r.status.value
        summary[key] = summary.get(key, 0) + 1
    return success_response(
        {"year": year, "month": month, "summary": summary, "total": len(records)}
    )


# ---------- DEBTS & PAYMENTS ----------


@router.get("/api/debts/student-options")
async def debt_student_options(
    page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=100),
    search: str | None = Query(None, max_length=150), selected_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    # The finance form needs a student reference, never the full student profile.
    query = select(Student).where(Student.deleted_at.is_(None))
    repo = BaseRepository(db, tenant)
    query = repo._branch_filter(repo._org_filter(query, Student), Student)
    selected = (await db.execute(query.where(Student.id == selected_id))).scalar_one_or_none() if selected_id else None
    if search:
        query = query.where(or_((Student.first_name + " " + Student.last_name).ilike(f"%{search}%"), Student.student_number.ilike(f"%{search}%")))
    rows, total = await repo.paginate(query.order_by(Student.first_name, Student.last_name, Student.id), page, page_size)
    def choice(row):
        return {"id": str(row.id), "name": f"{row.first_name} {row.last_name}".strip() + (f" · {row.student_number}" if row.student_number else "")}
    return success_response({**paginate([choice(row) for row in rows], total, page, page_size), "selected": choice(selected) if selected else None})


@router.get("/api/debts")
async def list_debts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    student_id: UUID | None = None,
    status: str | None = None,
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    query = select(Debt).where(Debt.deleted_at.is_(None))
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, Debt)
    query = repo._branch_filter(query, Debt)
    if student_id:
        query = query.where(Debt.student_id == student_id)
    if status:
        query = query.where(Debt.status == status)
    items, total = await repo.paginate(query.order_by(Debt.due_date.desc()), page, page_size)
    # Legacy SQLite demo imports may contain malformed UUID primary keys.
    # SQLAlchemy represents those unreadable rows as ``None``; skip them so a
    # single bad historical record cannot take down the whole debt screen.
    valid_items = [debt for debt in items if debt is not None]
    data = [
        {
            "id": str(d.id),
            "student_id": str(d.student_id),
            "debt_type": d.debt_type.value,
            "amount": str(d.amount),
            "paid_amount": str(d.paid_amount),
            "remaining_amount": str(d.amount - d.paid_amount),
            "status": d.status.value,
            "due_date": d.due_date.isoformat(),
        }
        for d in valid_items
    ]
    return success_response(paginate(data, total, page, page_size))


@router.post("/api/debts")
async def create_debt(
    body: DebtCreate,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    student = await BaseRepository(db, tenant).get_by_id(UUID(body.student_id), Student)
    amount = Decimal(body.amount)
    if amount <= 0:
        raise ValidationException("Borç tutarı 0'dan büyük olmalıdır")
    due = date.fromisoformat(body.due_date)
    debt = Debt(
        organization_id=student.organization_id,
        branch_id=student.branch_id,
        student_id=student.id,
        debt_type=DebtType(body.debt_type),
        description=body.description,
        amount=amount,
        paid_amount=Decimal("0"),
        status=DebtCalculator.calculate_status(amount, Decimal("0"), due),
        due_date=due,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(debt)
    await db.flush()
    return success_response({"id": str(debt.id)}, "Borç tanımlandı")


@router.get("/api/debts/{debt_id}")
async def get_debt(
    debt_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    debt = await repo.get_by_id(debt_id, Debt)
    return success_response(
        {
            "id": str(debt.id),
            "student_id": str(debt.student_id),
            "debt_type": debt.debt_type.value,
            "description": debt.description,
            "amount": str(debt.amount),
            "paid_amount": str(debt.paid_amount),
            "remaining_amount": str(debt.amount - debt.paid_amount),
            "status": debt.status.value,
            "due_date": debt.due_date.isoformat(),
        }
    )


@router.put("/api/debts/{debt_id}")
async def update_debt(
    debt_id: UUID,
    body: DebtUpdate,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    debt = await repo.get_by_id(debt_id, Debt)
    if "student_id" in body.model_fields_set and body.student_id != str(debt.student_id):
        raise ValidationException("Borç tanımlandıktan sonra öğrencisi değiştirilemez")
    if "debt_type" in body.model_fields_set and body.debt_type != debt.debt_type.value:
        raise ValidationException("Borç tanımlandıktan sonra türü değiştirilemez")
    if debt.paid_amount > 0 and body.amount:
        raise ValidationException("Ödemesi olan borcun tutarı değiştirilemez")
    data = body.model_dump(exclude_unset=True)
    if "amount" in data and data["amount"]:
        amount = Decimal(data["amount"])
        if amount <= 0:
            raise ValidationException("Borç tutarı 0'dan büyük olmalıdır")
        debt.amount = amount
    if "due_date" in data and data["due_date"]:
        debt.due_date = date.fromisoformat(data["due_date"])
    if "description" in data:
        debt.description = data["description"]
    calculated_status = DebtCalculator.calculate_status(debt.amount, debt.paid_amount, debt.due_date)
    if "status" in data and data["status"] != calculated_status.value:
        raise ValidationException("Borç durumu tahsilat ve vade tarihinden hesaplanır; iptal için borç iptali işlemini kullanın")
    debt.status = calculated_status
    debt.updated_by = user.id
    return success_response({"id": str(debt.id)}, "Borç güncellendi")


@router.delete("/api/debts/{debt_id}")
async def delete_debt(
    debt_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    debt = await repo.get_by_id(debt_id, Debt)
    if debt.paid_amount > 0:
        raise ValidationException("Ödemesi olan borç silinemez")
    debt.status = DebtStatus.CANCELLED
    await repo.soft_delete(debt)
    return success_response(message="Borç iptal edildi")


@router.post("/api/debts/{debt_id}/recalculate-status")
async def recalculate_debt_status(
    debt_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    debt = await repo.get_by_id(debt_id, Debt)
    debt.status = DebtCalculator.calculate_status(debt.amount, debt.paid_amount, debt.due_date)
    return success_response({"status": debt.status.value}, "Borç durumu yeniden hesaplandı")


@router.get("/api/payments")
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    student_id: UUID | None = None,
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    query = select(Payment).where(Payment.cancelled_at.is_(None))
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, Payment)
    query = repo._branch_filter(query, Payment)
    if student_id:
        query = query.where(Payment.student_id == student_id)
    items, total = await repo.paginate(query.order_by(Payment.payment_date.desc()), page, page_size)
    data = [
        {
            "id": str(p.id),
            "student_id": str(p.student_id),
            "amount": str(p.amount),
            "payment_method": p.payment_method.value,
            "payment_date": p.payment_date.isoformat(),
            "cancelled": p.cancelled_at is not None,
        }
        for p in items
    ]
    return success_response(paginate(data, total, page, page_size))


@router.get("/api/payments/{payment_id}")
async def get_payment(
    payment_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    payment = await BaseRepository(db, tenant).get_by_id(payment_id, Payment)
    receipt = (
        await db.execute(select(Receipt).where(Receipt.payment_id == payment_id))
    ).scalar_one_or_none()
    return success_response(
        {
            "id": str(payment.id),
            "student_id": str(payment.student_id),
            "debt_id": str(payment.debt_id),
            "amount": str(payment.amount),
            "payment_method": payment.payment_method.value,
            "payment_date": payment.payment_date.isoformat(),
            "notes": payment.notes,
            "cancelled": payment.cancelled_at is not None,
            "cancel_reason": payment.cancel_reason,
            "receipt_id": str(receipt.id) if receipt else None,
            "receipt_number": receipt.receipt_number if receipt else None,
        }
    )


@router.get("/api/receipts")
async def list_receipts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tenant: TenantContext = Depends(PermissionChecker("receipt.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    query = select(Receipt).order_by(Receipt.issued_at.desc())
    repo = BaseRepository(db, tenant)
    query = repo._org_filter(query, Receipt)
    query = repo._branch_filter(query, Receipt)
    items, total = await repo.paginate(query, page, page_size)
    data = [
        {
            "id": str(r.id),
            "receipt_number": r.receipt_number,
            "payment_id": str(r.payment_id),
            "status": r.status.value,
            "issued_at": r.issued_at.isoformat(),
            "remaining_debt": str(r.remaining_debt),
        }
        for r in items
    ]
    return success_response(paginate(data, total, page, page_size))


@router.post("/api/payments")
async def take_payment(
    body: PaymentCreate,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    debt = await repo.get_by_id(UUID(body.debt_id), Debt, for_update=True)
    if debt.status == DebtStatus.CANCELLED:
        raise ValidationException("İptal edilmiş borca ödeme alınamaz")
    payment_amount = Decimal(body.amount)
    try:
        DebtCalculator.validate_payment(debt.amount, debt.paid_amount, payment_amount)
    except ValueError as e:
        raise ValidationException(str(e)) from e

    payment = Payment(
        organization_id=debt.organization_id,
        branch_id=debt.branch_id,
        student_id=debt.student_id,
        debt_id=debt.id,
        amount=payment_amount,
        payment_method=PaymentMethod(body.payment_method),
        notes=body.notes,
        received_by=user.id,
    )
    db.add(payment)
    await db.flush()

    debt.paid_amount = DebtCalculator.apply_payment(debt.amount, debt.paid_amount, payment_amount)
    debt.status = DebtCalculator.calculate_status(debt.amount, debt.paid_amount, debt.due_date)

    remaining_total = (
        await db.execute(
            select(func.coalesce(func.sum(Debt.amount - Debt.paid_amount), 0)).where(
                Debt.student_id == debt.student_id,
                Debt.deleted_at.is_(None),
                Debt.status != DebtStatus.CANCELLED,
            )
        )
    ).scalar()

    receipt_number = f"RCP-{datetime.now(UTC).strftime('%Y%m%d')}-{str(payment.id)[:6].upper()}"
    receipt = Receipt(
        organization_id=debt.organization_id,
        branch_id=debt.branch_id,
        student_id=debt.student_id,
        payment_id=payment.id,
        receipt_number=receipt_number,
        status=ReceiptStatus.ACTIVE,
        issued_by=user.id,
        remaining_debt=remaining_total,
    )
    db.add(receipt)

    job = NotificationJob(
        organization_id=debt.organization_id,
        branch_id=debt.branch_id,
        channel=NotificationChannel.EMAIL,
        template_code="payment_received",
        subject="Ödeme Bildirimi",
        body=f"Ödeme alındı: {payment_amount} TL - Makbuz: {receipt_number}",
        reference_type="payment",
        reference_id=payment.id,
        created_by=user.id,
    )
    db.add(job)
    await db.flush()

    db.add(
        AuditLog(
            organization_id=debt.organization_id,
            branch_id=debt.branch_id,
            user_id=user.id,
            action=AuditAction.PAYMENT,
            entity_type="payment",
            entity_id=payment.id,
            new_values={"amount": str(payment_amount), "debt_id": str(debt.id)},
        )
    )

    return success_response(
        {
            "payment_id": str(payment.id),
            "receipt_id": str(receipt.id),
            "receipt_number": receipt_number,
            "remaining_debt": str(remaining_total),
        },
        "Tahsilat alındı",
    )


@router.post("/api/payments/{payment_id}/cancel")
async def cancel_payment(
    payment_id: UUID,
    body: PaymentCancel,
    tenant: TenantContext = Depends(PermissionChecker("finance.write")),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    repo = BaseRepository(db, tenant)
    payment = await repo.get_by_id(payment_id, Payment, for_update=True)
    if payment.cancelled_at:
        raise ValidationException("Ödeme zaten iptal edilmiş")
    debt = await repo.get_by_id(payment.debt_id, Debt, for_update=True)
    payment.cancelled_at = datetime.now(UTC)
    payment.cancelled_by = user.id
    payment.cancel_reason = body.cancel_reason
    debt.paid_amount = DebtCalculator.reverse_payment(debt.paid_amount, payment.amount)
    debt.status = DebtCalculator.calculate_status(debt.amount, debt.paid_amount, debt.due_date)
    receipt_result = await db.execute(select(Receipt).where(Receipt.payment_id == payment.id))
    receipt = receipt_result.scalar_one_or_none()
    if receipt:
        receipt.status = ReceiptStatus.CANCELLED
    db.add(
        AuditLog(
            organization_id=payment.organization_id,
            user_id=user.id,
            action=AuditAction.CANCEL_PAYMENT,
            entity_type="payment",
            entity_id=payment.id,
        )
    )
    return success_response(message="Ödeme iptal edildi")


@router.get("/api/receipts/{receipt_id}")
async def get_receipt(
    receipt_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("receipt.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    receipt = await BaseRepository(db, tenant).get_by_id(receipt_id, Receipt)
    return success_response(
        {
            "id": str(receipt.id),
            "receipt_number": receipt.receipt_number,
            "payment_id": str(receipt.payment_id),
            "status": receipt.status.value,
            "issued_at": receipt.issued_at.isoformat(),
            "remaining_debt": str(receipt.remaining_debt),
        }
    )


@router.get("/api/students/{student_id}/payments")
async def student_payments(
    student_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("finance.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    await BaseRepository(db, tenant).get_by_id(student_id, Student)
    result = await db.execute(
        select(Payment)
        .where(Payment.student_id == student_id)
        .order_by(Payment.payment_date.desc())
    )
    payments = result.scalars().all()
    return success_response(
        [
            {
                "id": str(p.id),
                "amount": str(p.amount),
                "payment_method": p.payment_method.value,
                "payment_date": p.payment_date.isoformat(),
                "cancelled": p.cancelled_at is not None,
            }
            for p in payments
        ]
    )


@router.get("/api/students/{student_id}/attendance")
async def student_attendance(
    student_id: UUID,
    tenant: TenantContext = Depends(PermissionChecker("attendance.read")),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    await BaseRepository(db, tenant).get_by_id(student_id, Student)
    result = await db.execute(
        select(AttendanceRecord)
        .where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.deleted_at.is_(None),
        )
        .order_by(AttendanceRecord.attendance_date.desc())
    )
    records = result.scalars().all()
    return success_response(
        [
            {
                "id": str(r.id),
                "attendance_date": r.attendance_date.isoformat(),
                "status": r.status.value,
            }
            for r in records
        ]
    )
