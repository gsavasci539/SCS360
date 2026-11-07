from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.application.services.online_payment_service import IyzicoGateway
from app.core.exceptions import AppException
from app.infrastructure.models.models import Debt, DebtType, PaymentCheckout


async def test_student_checkout_summary_and_status_keep_child_and_institution_scope(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        own = Debt(organization_id=data["org"].id, branch_id=data["branch"].id, student_id=data["children"][0].id, debt_type=DebtType.EDUCATION, amount=100, paid_amount=25, due_date=date.today())
        other = Debt(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id, student_id=data["stranger"].id, debt_type=DebtType.EDUCATION, amount=200, paid_amount=0, due_date=date.today())
        db.add_all([own, other]); await db.flush()
        attempt = PaymentCheckout(organization_id=own.organization_id, debt_id=own.id, created_by=data["user"].id, amount=75, currency="TRY", token_hash="scope-test-only", status="PENDING")
        db.add(attempt); await db.commit()
    auth = headers(data["user"])
    response = await client.get(f"/api/payments/iyzico/debts/{own.id}", headers=auth)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["remaining_amount"] == "75.00"
    assert response.json()["data"]["online_payment_available"] is False
    assert (await client.get(f"/api/payments/iyzico/debts/{other.id}", headers=auth)).status_code in {403, 404}
    status = await client.get(f"/api/payments/iyzico/checkouts/{attempt.id}", headers=auth)
    assert status.status_code == 200 and "token_hash" not in status.text
    assert (await client.get(f"/api/payments/iyzico/checkouts/{attempt.id}", headers=headers(data["teacher"]))).status_code == 403


def test_legacy_school_merchant_is_explicitly_bound_and_never_available_to_new_saas_schools():
    school = uuid4(); other = uuid4()
    settings = SimpleNamespace(APP_ENV="test", IYZICO_API_KEY="isolated", IYZICO_SECRET_KEY="isolated", IYZICO_BASE_URL="https://sandbox-api.iyzipay.com",
        IYZICO_CALLBACK_URL="http://127.0.0.1/api/payments/iyzico/callback", IYZICO_ORGANIZATION_ID=str(school), IYZICO_PAYMENT_ENABLED=True)
    gateway = IyzicoGateway(settings)
    assert gateway.available_for(school) is True and gateway.available_for(other) is False
    with pytest.raises(AppException): gateway.require_organization(other)
    settings.IYZICO_ORGANIZATION_ID = ""
    assert gateway.available_for(school) is False
    settings.IYZICO_ORGANIZATION_ID = str(school); settings.IYZICO_PAYMENT_ENABLED = False
    assert gateway.available_for(school) is False
