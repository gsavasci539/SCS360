"""Persist imports with per-row savepoints and the same tenant rules as CRUD."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.application.services.operations_service import identifier
from app.core.exceptions import AppException, ForbiddenException, ValidationException
from app.core.student_access import require_student_access
from app.domain.entities.canteen import CanteenProduct
from app.domain.services.debt_calculator import DebtCalculator
from app.infrastructure.models.models import Branch, ClassRoom, Debt, DebtType, Organization, Parent, ParentRelationType, Student, StudentParent, GenderType
from app.infrastructure.repositories.base import BaseRepository


def required(row, key):
    value = row.get(key)
    if value is None or str(value).strip() == "":
        raise ValidationException(f"{key} alanı gerekli")
    return str(value).strip()


def when(value):
    if isinstance(value, datetime): return value.date()
    if isinstance(value, date): return value
    return date.fromisoformat(str(value)[:10])


async def branch_for(db, tenant, row):
    repo = BaseRepository(db, tenant)
    if row.get("branch_id"):
        return await repo.get_by_id(identifier(row["branch_id"]), Branch)
    statement = repo._branch_filter(repo._org_filter(select(Branch), Branch), Branch).where(Branch.deleted_at.is_(None))
    if row.get("branch_name"):
        statement = statement.where(Branch.name == row["branch_name"])
    branches = (await db.execute(statement.limit(2))).scalars().all()
    if len(branches) != 1:
        raise ValidationException("Şube kimliği veya benzersiz şube adı gerekli")
    return branches[0]


async def student_for(db, tenant, row):
    repo = BaseRepository(db, tenant)
    if row.get("student_id"):
        student = await repo.get_by_id(identifier(row["student_id"]), Student)
    else:
        statement = repo._branch_filter(repo._org_filter(select(Student), Student), Student).where(
            Student.student_number == required(row, "student_number"), Student.deleted_at.is_(None))
        student = (await db.execute(statement)).scalar_one_or_none()
        if student is None:
            raise ValidationException("Öğrenci numarası kurumda bulunamadı")
    await require_student_access(db, tenant, student.id)
    return student


async def persist_row(db, tenant, kind, row):
    repo = BaseRepository(db, tenant)
    if kind == "students":
        branch = await branch_for(db, tenant, row)
        classroom = None
        if row.get("class_id"):
            classroom = await repo.get_by_id(identifier(row["class_id"]), ClassRoom)
        elif row.get("class_name"):
            classroom = (await db.execute(select(ClassRoom).where(ClassRoom.branch_id == branch.id,
                ClassRoom.name == row["class_name"], ClassRoom.deleted_at.is_(None)))).scalar_one_or_none()
            if classroom is None: raise ValidationException("Sınıf bu şubede bulunamadı")
        if classroom and classroom.branch_id != branch.id:
            raise ValidationException("Sınıf ile şube eşleşmiyor")
        record = Student(organization_id=branch.organization_id, branch_id=branch.id,
            class_id=classroom.id if classroom else None, first_name=required(row, "first_name"),
            last_name=required(row, "last_name"), student_number=row.get("student_number"),
            gender=GenderType(str(row["gender"]).upper()) if row.get("gender") else None,
            birth_date=when(row.get("birth_date") or row.get("date_of_birth")) if row.get("birth_date") or row.get("date_of_birth") else None,
            created_by=tenant.user_id)
    elif kind == "parents":
        if not tenant.organization_id: raise ValidationException("Kurum bilgisi gerekli")
        record = Parent(organization_id=tenant.organization_id, first_name=required(row, "first_name"),
            last_name=required(row, "last_name"), relation_type=ParentRelationType(str(row.get("relation_type", "GUARDIAN")).upper()),
            phone=row.get("phone"), email=row.get("email"), address=row.get("address"), created_by=tenant.user_id)
        db.add(record); await db.flush()
        if row.get("student_id") or row.get("student_number"):
            student = await student_for(db, tenant, row)
            db.add(StudentParent(student_id=student.id, parent_id=record.id))
    elif kind == "classes":
        branch = await branch_for(db, tenant, row)
        capacity = int(row.get("capacity", 20))
        if not 1 <= capacity <= 10000: raise ValidationException("Sınıf kapasitesi geçersiz")
        record = ClassRoom(organization_id=branch.organization_id, branch_id=branch.id,
            name=required(row, "name"), capacity=capacity, academic_year=row.get("academic_year"), created_by=tenant.user_id)
    elif kind == "organizations":
        if not tenant.is_super_admin: raise ForbiddenException("Kurum içe aktarma için süper yönetici gerekli")
        record = Organization(name=required(row, "name"), legal_name=row.get("legal_name"),
            phone=row.get("phone"), email=row.get("email"), address=row.get("address"), created_by=tenant.user_id)
    elif kind == "branches":
        organization_id = identifier(row["organization_id"]) if row.get("organization_id") else tenant.organization_id
        if not organization_id: raise ValidationException("Kurum kimliği gerekli")
        await repo.get_by_id(organization_id, Organization)
        record = Branch(organization_id=organization_id, name=required(row, "name"), code=row.get("code"),
            phone=row.get("phone"), email=row.get("email"), address=row.get("address"), created_by=tenant.user_id)
    elif kind == "library":
        from app.application.services import library_service
        from app.application.schemas.common import LibraryBookCreate
        return await library_service.create_book(db, tenant, LibraryBookCreate(title=required(row, "title"),
            author=required(row, "author"), isbn=row.get("isbn"), category=row.get("category") or "Genel",
            total_copies=int(row.get("quantity", row.get("total_copies", 1)))))
    elif kind == "canteen":
        branch = await branch_for(db, tenant, row)
        price = Decimal(required(row, "price"))
        if not price.is_finite() or price <= 0: raise ValidationException("Fiyat pozitif olmalı")
        record = CanteenProduct(branch_id=branch.id, name=required(row, "name"), price=price,
            category=row.get("category"), description=row.get("description"), created_by=tenant.user_id)
    elif kind == "debts":
        student = await student_for(db, tenant, row)
        amount = Decimal(required(row, "amount"))
        if not amount.is_finite() or amount <= 0: raise ValidationException("Borç tutarı pozitif olmalı")
        due = when(required(row, "due_date"))
        record = Debt(organization_id=student.organization_id, branch_id=student.branch_id, student_id=student.id,
            debt_type=DebtType(required(row, "debt_type").upper()), amount=amount, paid_amount=0,
            due_date=due, description=row.get("description"), created_by=tenant.user_id,
            status=DebtCalculator.calculate_status(amount, Decimal(0), due))
    else:
        raise ValidationException("Desteklenmeyen içe aktarma türü")
    db.add(record); await db.flush()
    if kind == "organizations":
        from app.domain.entities.saas import OrganizationSubscription
        db.add(OrganizationSubscription(organization_id=record.id, admin_status="ACTIVE"))
        await db.flush()
    return {"id": str(record.id)}


async def import_rows(db, tenant, kind, rows):
    imported, errors = [], []
    for index, row in enumerate(rows, 1):
        try:
            async with db.begin_nested():
                result = await persist_row(db, tenant, kind, row)
            imported.append(result)
        except AppException as exc:
            errors.append(f"Satır {index}: {exc.message}")
        except IntegrityError:
            errors.append(f"Satır {index}: Tekrarlanan kayıt veya geçersiz ilişki")
        except (ValueError, TypeError, ArithmeticError):
            errors.append(f"Satır {index}: Alan biçimi veya zorunlu bilgiler geçersiz")
    return {"imported": len(imported), "errors": errors, "data": imported}
