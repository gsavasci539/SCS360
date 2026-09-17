"""Branch isolation unit tests."""

import uuid
from unittest.mock import MagicMock

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
        class_ids=[],
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
        class_ids=[],
    )
    assert tenant.can_access_branch(uuid.uuid4()) is True
