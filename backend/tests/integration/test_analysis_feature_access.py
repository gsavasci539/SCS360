from sqlalchemy import select
from sqlalchemy.orm import selectinload

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.infrastructure.models.models import Permission, Role


async def test_analytics_do_not_turn_student_or_guardian_access_into_finance_staff_or_school_report_access(materials_client):
    client, sessions, data = materials_client
    for actor in (data["teacher"], data["user"]):
        for path in ("/ai-financial-predictions", "/payment-forecast", "/payroll-analysis", "/staff-analysis", "/organization-health", "/insights-report", "/risk-management"):
            response = await client.get("/api/ai" + path, headers=headers(actor))
            assert response.status_code == 403, (path, response.text)
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "teacher"))).scalar_one()
        role.permissions.append(Permission(code="academic.read", name="Academic", module="academic"))
        await db.commit()
    allowed = await client.get("/api/ai/academic-performance", headers=headers(data["teacher"]))
    assert allowed.status_code == 200, allowed.text
    # Granting one analysis domain cannot open a multi-domain school report.
    assert (await client.get("/api/ai/insights-report", headers=headers(data["teacher"])) ).status_code == 403
