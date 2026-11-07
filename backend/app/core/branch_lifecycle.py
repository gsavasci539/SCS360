"""Preserve branch history while blocking new admissions after closure."""
from sqlalchemy import String, cast, func, select

from app.core.database import Base
from app.core.exceptions import ConflictException, ValidationException
from app.infrastructure.models.models import Branch


def enforce_branch_lifecycle(session, admissions, changes):
    """Called after sorted organization locks, before any class or quota locks."""
    identifiers = {row.branch_id for row in admissions}
    table = Branch.__table__
    stored = {row.id: row for row in session.execute(select(table).where(table.c.id.in_(identifiers))).mappings()} if identifiers else {}
    pending = {row.id: row for row in changes}
    for row in admissions:
        branch = pending.get(row.branch_id) or stored.get(row.branch_id)
        if branch is None or branch.deleted_at is not None or branch.is_active is False:
            raise ConflictException("Pasif veya silinmiş şube yeni öğrenci ve sınıf kaydı almıyor")
        if branch.organization_id != row.organization_id:
            raise ValidationException("Kayıt ve şube aynı kuruma bağlı olmalıdır")
    for branch in changes:
        if branch.deleted_at is None and branch not in session.deleted:
            continue
        for related in Base.metadata.tables.values():
            if "branch_id" not in related.c:
                continue
            # Older auxiliary tables store UUID strings with either spelling.
            matches = func.replace(cast(related.c.branch_id, String), "-", "") == branch.id.hex
            if session.execute(select(select(related).where(matches).exists())).scalar_one():
                raise ConflictException("Şubeye bağlı kayıtlar var; geçmişi korumak için silmek yerine şubeyi pasife alın")
