from dataclasses import dataclass, field
from uuid import UUID


# The first deployed roles used plural resource names (``students.read``),
# while a number of earlier endpoints and frontend guards still use the
# singular spelling (``student.read``).  Keep the permission vocabulary
# compatible while the database roles are migrated.
PERMISSION_ALIASES: dict[str, str] = {
    "user.read": "users.read",
    "user.write": "users.write",
    "student.read": "students.read",
    "student.write": "students.write",
    "parent.read": "parents.read",
    "parent.write": "parents.write",
    "class.read": "classes.read",
    "class.write": "classes.write",
    "announcement.read": "announcements.read",
    "announcement.write": "announcements.write",
}


@dataclass
class TenantContext:
    user_id: UUID
    organization_id: UUID | None = None
    branch_ids: list[UUID] = field(default_factory=list)
    class_ids: list[UUID] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)
    role_slugs: set[str] = field(default_factory=set)
    is_super_admin: bool = False

    def has_permission(self, permission: str) -> bool:
        if self.is_super_admin:
            return True
        return permission in self.permissions or PERMISSION_ALIASES.get(permission) in self.permissions

    def has_any_permission(self, permissions: list[str]) -> bool:
        if self.is_super_admin:
            return True
        return any(self.has_permission(permission) for permission in permissions)

    def can_access_branch(self, branch_id: UUID | None) -> bool:
        if self.is_super_admin:
            return True
        if branch_id is None:
            return True
        if not self.branch_ids:
            return True
        return branch_id in self.branch_ids

    def can_access_organization(self, organization_id: UUID | None) -> bool:
        if self.is_super_admin:
            return True
        if organization_id is None:
            return True
        return self.organization_id == organization_id
