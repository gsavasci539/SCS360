from datetime import UTC, datetime

from sqlalchemy import select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.security import create_access_token
from app.infrastructure.models.models import Appointment, Permission, Role


async def test_literal_my_appointments_route_returns_only_current_teachers_records(materials_client):
    client, sessions, data = materials_client
    teacher, other, student = data["teacher"], data["user"], data["children"][0]
    async with sessions() as db:
        role = await db.scalar(select(Role).where(Role.slug == "teacher", Role.organization_id == data["org"].id))
        await db.refresh(role, ["permissions"])
        role.permissions.append(Permission(code="appointments.read", name="Read appointments", module="appointments"))
        own = Appointment(organization_id=data["org"].id, teacher_id=teacher.id, parent_id=other.id,
            student_id=student.id, slot_datetime=datetime(2027, 1, 3, 10, tzinfo=UTC))
        another = Appointment(organization_id=data["org"].id, teacher_id=other.id, parent_id=other.id,
            student_id=student.id, slot_datetime=datetime(2027, 1, 3, 12, tzinfo=UTC))
        db.add_all([own, another])
        await db.commit()
        own_id = str(own.id)

    headers = {"Authorization": "Bearer " + create_access_token(teacher.id)}
    result = await client.get("/api/appointments/my-appointments", headers=headers,
        params={"start_date": "2027-01-03", "end_date": "2027-01-03"})
    assert result.status_code == 200, result.text
    assert [row["id"] for row in result.json()["data"]] == [own_id]
    assert result.json()["data"][0]["appointment_time"] == "13:00"
    detail = await client.get(f"/api/appointments/{own_id}", headers=headers)
    assert detail.status_code == 200 and detail.json()["data"]["id"] == own_id
