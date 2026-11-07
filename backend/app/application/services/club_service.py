"""Scoped club enrollment, events and student awards."""
from sqlalchemy import func, select, update

from app.core.dates import school_today
from app.core.exceptions import ConflictException, ValidationException
from app.domain.entities.clubs import ClubEvent, ClubMembership, SchoolClub, StudentCertificate
from app.infrastructure.models.models import Branch, Organization, Role, Student, User, UserRole
from app.infrastructure.repositories.base import BaseRepository


def count_members(club_id):
    table = ClubMembership.__table__
    # Capacity counts all members of the already-authorized club, even when a
    # teacher can see personal details for only some students in that club.
    students, clubs, branches = Student.__table__, SchoolClub.__table__, Branch.__table__
    return (select(func.count(func.distinct(table.c.student_id))).select_from(table.join(students, students.c.id == table.c.student_id)
        .join(clubs, clubs.c.id == table.c.club_id).join(branches, branches.c.id == clubs.c.branch_id))
        .where(table.c.club_id == club_id, table.c.status == "ACTIVE", students.c.deleted_at.is_(None),
            students.c.status == "ACTIVE", students.c.branch_id == clubs.c.branch_id,
            students.c.organization_id == branches.c.organization_id).scalar_subquery())


async def validate_club(db, tenant, body):
    repo = BaseRepository(db, tenant)
    branch = await repo.get_by_id(body.branch_id, Branch)
    if body.advisor_teacher_id:
        teacher = await repo.get_by_id(body.advisor_teacher_id, User)
        teaching_role = (await db.execute(select(UserRole.user_id).join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id == teacher.id, Role.slug == "teacher", Role.deleted_at.is_(None),
                (Role.organization_id.is_(None) | (Role.organization_id == branch.organization_id))).limit(1))).first()
        if teacher.organization_id != branch.organization_id or getattr(teacher.status, "value", teacher.status) != "ACTIVE" or not teaching_role:
            raise ValidationException("Danışman, kurumun aktif öğretmenlerinden biri olmalı")
    if not body.club_name.strip():
        raise ValidationException("Kulüp adı gerekli")


async def save_club(db, tenant, body, club_id=None):
    await validate_club(db, tenant, body)
    if club_id:
        club = await BaseRepository(db, tenant).get_by_id(club_id, SchoolClub, for_update=True)
        current = (await db.execute(select(count_members(club.id)))).scalar_one()
        if current > body.max_members:
            raise ValidationException("Kapasite aktif üye sayısından az olamaz")
        if club.branch_id != body.branch_id:
            table = ClubMembership.__table__
            has_history = (await db.execute(select(table.c.id).where(table.c.club_id == club.id).limit(1))).first()
            event_history = (await db.execute(select(ClubEvent.id).where(ClubEvent.club_id == club.id).limit(1))).first()
            if has_history or event_history:
                raise ValidationException("Üyelik veya etkinlik kaydı bulunan kulüp başka şubeye taşınamaz")
        club.current_members = current
        for key, value in body.model_dump().items():
            setattr(club, key, value)
    else:
        club = SchoolClub(**body.model_dump(), current_members=0, is_active=True)
        db.add(club)
    await db.flush()
    return {"id": str(club.id), "club_name": club.club_name, "max_members": club.max_members,
        "current_members": club.current_members, "created_at": club.created_at.isoformat()}


async def enroll(db, tenant, body):
    repo = BaseRepository(db, tenant)
    club = await repo.get_by_id(body.club_id, SchoolClub, for_update=True)
    student = await repo.get_by_id(body.student_id, Student)
    if not club.is_active:
        raise ValidationException("Kulüp aktif değil")
    if student.branch_id != club.branch_id:
        raise ValidationException("Öğrenci ve kulüp aynı şubede olmalı")
    if getattr(student.status, "value", student.status) != "ACTIVE":
        raise ValidationException("Öğrenci aktif değil")
    existing = (await db.execute(select(ClubMembership).where(ClubMembership.club_id == club.id,
        ClubMembership.student_id == student.id).order_by(ClubMembership.created_at).limit(1))).scalar_one_or_none()
    if existing is None or existing.status != "ACTIVE":
        table = ClubMembership.__table__
        active = select(table.c.id).where(table.c.club_id == club.id, table.c.student_id == student.id,
            table.c.status == "ACTIVE").exists()
        claimed = await db.execute(update(SchoolClub).where(SchoolClub.id == club.id, SchoolClub.is_active.is_(True),
            count_members(club.id) < SchoolClub.max_members, ~active)
            .values(current_members=count_members(club.id) + 1).execution_options(synchronize_session=False))
        if claimed.rowcount != 1:
            existing = (await db.execute(select(ClubMembership).where(ClubMembership.club_id == club.id,
                ClubMembership.student_id == student.id, ClubMembership.status == "ACTIVE").limit(1))).scalar_one_or_none()
            if existing is None:
                raise ConflictException("Kulüp kapasitesi dolu")
        if existing is None:
            existing = ClubMembership(club_id=club.id, student_id=student.id, joined_date=school_today(), status="ACTIVE")
            db.add(existing)
    existing.status, existing.role, existing.notes = "ACTIVE", body.role, body.notes
    await db.flush()
    return {"id": str(existing.id), "club_id": str(club.id), "student_id": str(student.id), "status": existing.status}


async def leave(db, tenant, membership_id):
    repo = BaseRepository(db, tenant)
    row = await repo.get_by_id(membership_id, ClubMembership)
    club = await repo.get_by_id(row.club_id, SchoolClub, for_update=True)
    await db.refresh(row, with_for_update=True)
    row.status = "INACTIVE"
    await db.flush()
    await db.execute(update(SchoolClub).where(SchoolClub.id == club.id).values(current_members=count_members(club.id)))
    return {"id": str(row.id), "status": row.status}


async def save_event(db, tenant, body):
    club = await BaseRepository(db, tenant).get_by_id(body.club_id, SchoolClub)
    if not club.is_active or not body.event_name.strip():
        raise ValidationException("Aktif kulüp ve etkinlik adı gerekli")
    row = ClubEvent(**body.model_dump())
    db.add(row)
    await db.flush()
    return {"id": str(row.id), "event_name": row.event_name, "event_date": row.event_date.isoformat(),
        "created_at": row.created_at.isoformat()}


async def certificate(db, tenant, body):
    repo = BaseRepository(db, tenant)
    student = await repo.get_by_id(body.student_id, Student)
    if body.template_id not in {None, "scs360"}:
        raise ValidationException("Desteklenen belge şablonu SCS360")
    if body.event_id:
        event = await repo.get_by_id(body.event_id, ClubEvent)
        club = await repo.get_by_id(event.club_id, SchoolClub)
        if student.branch_id != club.branch_id:
            raise ValidationException("Öğrenci etkinliğin şubesine kayıtlı değil")
        membership = (await db.execute(select(ClubMembership.id).where(ClubMembership.club_id == club.id,
            ClubMembership.student_id == student.id, ClubMembership.joined_date <= event.event_date).limit(1))).first()
        if membership is None:
            raise ValidationException("Etkinlik belgesi için öğrencinin kulüp üyeliği gerekli")
    if not body.title.strip() or not body.certificate_type.strip():
        raise ValidationException("Belge başlığı ve türü gerekli")
    row = StudentCertificate(**body.model_dump(), issue_date=school_today(), issued_by=tenant.user_id)
    db.add(row)
    await db.flush()
    row.pdf_url = f"/api/clubs/certificates/{row.id}/pdf"
    await db.flush()
    return {"id": str(row.id), "title": row.title, "certificate_type": row.certificate_type,
        "issue_date": row.issue_date.isoformat(), "pdf_url": row.pdf_url, "created_at": row.created_at.isoformat()}


async def certificate_context(db, tenant, certificate_id):
    repo = BaseRepository(db, tenant)
    row = await repo.get_by_id(certificate_id, StudentCertificate)
    student = await repo.get_by_id(row.student_id, Student)
    branch = await repo.get_by_id(student.branch_id, Branch)
    organization = await repo.get_by_id(student.organization_id, Organization)
    issuer = (await db.execute(select(User).where(User.id == row.issued_by))).scalar_one_or_none() if row.issued_by else None
    return {"id": str(row.id), "title": row.title, "certificate_type": row.certificate_type,
        "description": row.description or "", "student_name": f"{student.first_name} {student.last_name}",
        "organization_name": organization.legal_name or organization.name, "branch_name": branch.name,
        "issue_date": row.issue_date.strftime("%d.%m.%Y"),
        "issuer_name": f"{issuer.first_name} {issuer.last_name}" if issuer else ""}


async def statistics(db):
    clubs = (await db.execute(select(SchoolClub))).scalars().all()
    ids = [club.id for club in clubs]
    active_ids = [club.id for club in clubs if club.is_active]
    memberships, students, club_table = ClubMembership.__table__, Student.__table__, SchoolClub.__table__
    branches = Branch.__table__
    query = (select(func.count(func.distinct(students.c.id)))
        .select_from(memberships.join(students, students.c.id == memberships.c.student_id)
            .join(club_table, club_table.c.id == memberships.c.club_id).join(branches, branches.c.id == club_table.c.branch_id))
        .where(memberships.c.club_id.in_(active_ids), memberships.c.status == "ACTIVE", students.c.deleted_at.is_(None),
            students.c.status == "ACTIVE", students.c.branch_id == club_table.c.branch_id,
            students.c.organization_id == branches.c.organization_id))
    members = (await db.execute(query)).scalar_one() if active_ids else 0
    upcoming = (await db.execute(select(func.count(ClubEvent.id)).where(ClubEvent.club_id.in_(ids),
        ClubEvent.event_date >= school_today()))).scalar_one() if ids else 0
    recommendations = []
    if not clubs:
        recommendations.append("İlk kulübü oluşturup öğrencilerin üyeliklerini ekleyin.")
    elif not members:
        recommendations.append("Aktif öğrenci üyeliği bulunmuyor; kulüp kayıtlarını kontrol edin.")
    if active_ids and not upcoming:
        recommendations.append("Aktif kulüpler için yaklaşan etkinlik kaydı bulunmuyor.")
    return {"total_clubs": len(clubs), "active_clubs": len(active_ids), "total_members": members,
        "upcoming_events": upcoming, "source": "DATABASE_AND_RULES", "recommendations": recommendations}
