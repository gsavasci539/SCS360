"""Branch isolation unit tests."""

import uuid

from sqlalchemy.dialects import sqlite

from app.core.tenant_guard import scope_filters
from app.core.branch_scope import ensure_assigned_branch
from app.core.exceptions import ForbiddenException
from app.core.tenant import TenantContext


def test_tenant_can_access_branch():
    branch_id = uuid.uuid4()
    tenant = TenantContext(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        branch_ids=[branch_id],
        role_slugs={"branch_manager"},
        permissions={"branch.read"},
        is_super_admin=False,
    )
    assert tenant.can_access_branch(branch_id) is True
    assert tenant.can_access_branch(uuid.uuid4()) is False


def test_super_admin_accesses_all_branches():
    tenant = TenantContext(
        user_id=uuid.uuid4(),
        organization_id=None,
        branch_ids=[],
        role_slugs={"super_admin"},
        permissions=set(),
        is_super_admin=True,
    )
    assert tenant.can_access_branch(uuid.uuid4()) is True


def test_unassigned_regular_user_fails_closed_for_branch_access():
    tenant = TenantContext(user_id=uuid.uuid4(), organization_id=uuid.uuid4(),
        branch_ids=[], role_slugs={"staff"})
    assert tenant.can_access_branch(uuid.uuid4()) is False
    assert tenant.can_access_branch(None) is True
    branch_query, _, _, _ = scope_filters(tenant, None)
    sql = str(branch_query.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
    assert "0 = 1" in sql


def test_relationship_scoped_user_gets_only_branches_of_accessible_students():
    organization_id, student_id = uuid.uuid4(), uuid.uuid4()
    tenant = TenantContext(user_id=uuid.uuid4(), organization_id=organization_id,
        branch_ids=[], role_slugs={"teacher"})
    branch_query, _, _, _ = scope_filters(tenant, {student_id})
    sql = str(branch_query.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
    assert "students.branch_id" in sql
    assert "students.organization_id" in sql
    assert str(student_id) in sql


def test_platform_workspace_and_owner_are_explicit_institution_wide_branch_scopes():
    owner = TenantContext(user_id=uuid.uuid4(), organization_id=uuid.uuid4(),
        branch_ids=[], role_slugs={"owner"})
    platform = TenantContext(user_id=uuid.uuid4(), organization_id=uuid.uuid4(),
        branch_ids=[], platform_admin=True)
    assert owner.has_institution_wide_branch_access
    assert platform.has_institution_wide_branch_access
    assert owner.can_access_branch(uuid.uuid4())
    assert platform.can_access_branch(uuid.uuid4())


def test_institution_admin_is_wide_but_branch_manager_without_assignments_is_not():
    admin = TenantContext(user_id=uuid.uuid4(), organization_id=uuid.uuid4(),
        branch_ids=[], role_slugs={"org_admin"})
    branch_manager = TenantContext(user_id=uuid.uuid4(), organization_id=uuid.uuid4(),
        branch_ids=[], role_slugs={"branch_manager"})
    assert admin.can_access_branch(uuid.uuid4())
    assert not branch_manager.can_access_branch(uuid.uuid4())


def test_branch_bound_routes_reject_unassigned_non_admin_users():
    unassigned = TenantContext(user_id=uuid.uuid4(), organization_id=uuid.uuid4(),
        branch_ids=[], role_slugs={"staff"})
    branch_manager = TenantContext(user_id=uuid.uuid4(), organization_id=uuid.uuid4(),
        branch_ids=[], role_slugs={"branch_manager"})
    for tenant in (unassigned, branch_manager):
        try:
            ensure_assigned_branch(tenant)
        except ForbiddenException:
            continue
        raise AssertionError("unassigned user unexpectedly entered branch-bound route")
