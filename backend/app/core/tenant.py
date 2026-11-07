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
    "parent_notices.read": "students.read",
    "parent_notices.write": "students.write",
    "communication.read": "notification.read",
    "communication.write": "notification.write",
    "parent.view_daily_report": "parent.view_children",
    "parent.view_finance": "parent.view_finances",
    "outbox.read": "notification.read",
    "survey.read": "surveys.read", "survey.write": "surveys.write",
    "consent.read": "consents.read", "consent.write": "consents.write",
}


def effective_roles(user):
    return [role for role in user.roles if role.deleted_at is None and role.organization_id in {None, user.organization_id}]


def effective_branches(user):
    return [branch for branch in user.branches if branch.deleted_at is None and branch.organization_id == user.organization_id]


@dataclass
class TenantContext:
    user_id: UUID
    organization_id: UUID | None = None
    branch_ids: list[UUID] = field(default_factory=list)
    class_ids: list[UUID] = field(default_factory=list)
    permissions: set[str] = field(default_factory=set)
    role_slugs: set[str] = field(default_factory=set)
    is_super_admin: bool = False
    platform_admin: bool = False
    parent_portal: bool = False

    def has_permission(self, permission: str) -> bool:
        if permission == "super_admin":
            return self.is_super_admin
        if self.is_super_admin or self.platform_admin:
            return True
        if permission in self.permissions or PERMISSION_ALIASES.get(permission) in self.permissions:
            return True
        return any(alias in self.permissions and canonical == permission
                   for alias, canonical in PERMISSION_ALIASES.items())

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
