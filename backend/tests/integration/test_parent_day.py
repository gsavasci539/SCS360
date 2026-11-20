from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.core.config import get_settings
from app.application.services import parent_day_service
from app.infrastructure.models.models import AttendanceRecord, AttendanceStatus, DailyDevelopmentReport, OperationalRecord
from app.infrastructure.models.models import Permission, Role, UserBranch
from app.domain.entities.health import MedicationLog, MedicationSchedule, InfirmaryVisit
from app.domain.entities.bus import BusRoute, BusAttendance
from app.domain.entities.pickup import PickupLog


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


async def grant_attendance_read(db):
    role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "parent"))).scalar_one()
    code = "parent.view_attendance"
    role.permissions.append(Permission(code=code, name=code, module="parent"))


async def test_parent_financial_invoices_discover_only_owned_open_checkouts(materials_client):  # noqa: F811
    from decimal import Decimal
    from app.infrastructure.models.models import Debt, DebtType, Parent, PaymentCheckout, StudentParent, User, UserRole

    client, sessions, data = materials_client
    first, sibling = data["children"]
    foreign = data["stranger"]
    owner = data["user"]

    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "parent"))).scalar_one()
        role.permissions.append(Permission(code="parent.view_finances", name="Parent finance", module="parent"))
        other = User(email="guardian2@test.invalid", password_hash="unused", first_name="Other",
            last_name="Guardian", organization_id=first.organization_id)
        db.add(other)
        await db.flush()
        other_parent = Parent(user_id=other.id, organization_id=first.organization_id, first_name="Other", last_name="Guardian")
        db.add_all([other_parent, UserRole(user_id=other.id, role_id=role.id)])
        await db.flush()
        db.add(StudentParent(student_id=first.id, parent_id=other_parent.id))

        debts = [Debt(student_id=child.id, organization_id=child.organization_id, branch_id=child.branch_id,
            debt_type=DebtType.EDUCATION, amount=Decimal("50.00"), paid_amount=Decimal("0.00"),
            due_date=date(2026, 11, 20)) for child in (first, first, sibling, foreign)]
        first_debt, second_debt, sibling_debt, foreign_debt = debts
        db.add_all(debts)
        await db.flush()
        own_checkout = PaymentCheckout(debt_id=first_debt.id, created_by=owner.id, organization_id=first.organization_id,
            amount=Decimal("25.10"), status="REVIEW")
        other_checkout = PaymentCheckout(debt_id=second_debt.id, created_by=other.id, organization_id=first.organization_id,
            amount=Decimal("10.00"), status="PENDING")
        db.add_all([own_checkout, other_checkout, *[
            PaymentCheckout(debt_id=debt.id, created_by=owner.id, organization_id=organization_id,
                amount=Decimal("50.00"), status=status)
            for debt, organization_id, status in (
                (second_debt, first.organization_id, "FAILED"),
                (second_debt, foreign.organization_id, "PENDING"),
                (sibling_debt, first.organization_id, "PENDING"),
            )
        ]])
        await db.commit()

    def invoice_url(student):
        return f"/api/parent/child/{student.id}/financial-invoices"

    def checkout_url(checkout):
        return f"/api/parent/payments/checkouts/{checkout.id}"

    response = await client.get(invoice_url(first), headers=auth(owner))
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    invoices = {row["debt_id"]: row["open_checkout"] for row in response.json()["data"]["invoices"]}
    assert invoices == {str(first_debt.id): {
        "debt_id": str(first_debt.id), "request_id": str(own_checkout.id), "amount": "25.10",
    }, str(second_debt.id): None}
    status = await client.get(checkout_url(own_checkout), headers=auth(owner))
    assert status.status_code == 200 and status.json()["data"]["status"] == "REVIEW"
    assert (await client.get(checkout_url(other_checkout), headers=auth(owner))).status_code == 403
    assert (await client.get(checkout_url(own_checkout), headers=auth(other))).status_code == 403
    assert (await client.get(invoice_url(foreign), headers=auth(owner))).status_code == 403
    assert str(foreign_debt.id) not in invoices

    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "parent"))).scalar_one()
        role.permissions = [permission for permission in role.permissions if permission.code != "parent.make_payment"]
        await db.commit()

    finance_only = await client.get(invoice_url(first), headers=auth(owner))
    assert finance_only.status_code == 200 and all(row["open_checkout"] is None for row in finance_only.json()["data"]["invoices"])
    assert (await client.get(checkout_url(own_checkout), headers=auth(owner))).status_code == 403


async def test_parent_receipts_require_a_matching_student_debt_and_institution(materials_client):  # noqa: F811
    from decimal import Decimal

    from app.infrastructure.models.models import (
        Debt,
        DebtType,
        Parent,
        Payment,
        PaymentMethod,
        Receipt,
        User,
        UserRole,
    )

    client, sessions, data = materials_client
    first, sibling = data["children"]
    foreign = data["stranger"]
    parent = auth(data["user"])

    async with sessions() as db:
        def make_debt(student):
            return Debt(student_id=student.id, organization_id=student.organization_id, branch_id=student.branch_id,
                debt_type=DebtType.EDUCATION, amount=Decimal("100.25"), paid_amount=Decimal("50.25"),
                due_date=date(2026, 11, 20))

        first_debt, sibling_debt, foreign_debt = [make_debt(child) for child in (first, sibling, foreign)]
        db.add_all([first_debt, sibling_debt, foreign_debt])
        await db.flush()

        async def make_receipt(debt, number, issued_day, branch_id=None):
            payment = Payment(debt_id=debt.id, student_id=debt.student_id, organization_id=debt.organization_id,
                branch_id=debt.branch_id, amount=Decimal("25.10"), payment_method=PaymentMethod.CASH,
                received_by=data["teacher"].id)
            db.add(payment)
            await db.flush()
            receipt = Receipt(student_id=debt.student_id, organization_id=debt.organization_id,
                payment_id=payment.id, branch_id=branch_id or debt.branch_id, receipt_number=number,
                issued_at=datetime(2026, 11, issued_day, tzinfo=UTC), remaining_debt=Decimal("50.00"),
                issued_by=data["teacher"].id)
            db.add(receipt)
            return receipt

        first_receipt = await make_receipt(first_debt, "TEST-01", 20)
        older_receipt = await make_receipt(first_debt, "TEST-02", 19)
        sibling_receipt = await make_receipt(sibling_debt, "TEST-03", 20)
        foreign_receipt = await make_receipt(foreign_debt, "TEST-04", 20)
        wrong_branch = await make_receipt(first_debt, "TEST-05", 20, data["other_branch"].id)
        other_actor = User(email="other-guardian@test.invalid", first_name="Other", last_name="Guardian",
            password_hash="unused", organization_id=first.organization_id)
        db.add(other_actor)
        await db.flush()
        role_id = await db.scalar(select(Role.id).where(Role.slug == "parent"))
        db.add_all([UserRole(user_id=other_actor.id, role_id=role_id),
            Parent(user_id=other_actor.id, organization_id=first.organization_id, first_name="Other", last_name="Guardian")])
        await db.commit()

    def path(student, debt):
        return f"/api/parent/child/{student.id}/debts/{debt.id}/receipts"

    own = path(first, first_debt)
    assert (await client.get(own, headers=parent)).status_code == 403
    async with sessions() as db:
        role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "parent"))).scalar_one()
        role.permissions = [Permission(code="parent.view_finances", name="Parent finance", module="parent")]
        await db.commit()

    response = await client.get(own, headers=parent, params={"page_size": 1})
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["student_id"] == str(first.id) and payload["debt_id"] == str(first_debt.id)
    assert payload["total"] == 2
    assert payload["items"][0]["id"] == str(first_receipt.id) and payload["items"][0]["amount"] == "25.10"
    page_two = await client.get(own, headers=parent, params={"page": 2, "page_size": 1})
    assert page_two.json()["data"]["items"][0]["id"] == str(older_receipt.id)

    pdf = await client.get(f"{own}/{first_receipt.id}/pdf", headers=parent)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert pdf.headers["content-type"] == "application/pdf" and pdf.headers["cache-control"] == "private, no-store"
    assert (await client.get(path(sibling, first_debt), headers=parent)).status_code == 404
    for receipt in (sibling_receipt, wrong_branch):
        assert (await client.get(f"{own}/{receipt.id}/pdf", headers=parent)).status_code == 404
    assert (await client.get(f"{path(foreign, foreign_debt)}/{foreign_receipt.id}/pdf", headers=parent)).status_code == 403
    assert (await client.get(own, headers=auth(other_actor))).status_code == 403
    assert (await client.get(f"{own}/{first_receipt.id}/pdf", headers=auth(other_actor))).status_code == 403
    assert (await client.get(f"/api/receipts/{first_receipt.id}", headers=parent)).status_code == 403


async def test_child_options_follow_module_permissions_and_relationships(materials_client):  # noqa: F811
    client, sessions, data = materials_client
    parent = auth(data["user"])
    children_path = "/api/parent/my-children"
    options_path = f"{children_path}/options"
    assert (await client.get(children_path, headers=parent)).status_code == 200
    assert (await client.get(options_path, headers=parent, params={"module": "attendance"})).status_code == 403
    assert (await client.get(options_path, headers=parent, params={"module": "profile"})).status_code == 422

    for module, code, detail, params in (
        ("attendance", "parent.view_attendance", "attendance", {"year": 2026, "month": 11}),
        ("finances", "parent.view_finances", "financial-invoices", {}),
    ):
        async with sessions() as db:
            role = (await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.slug == "parent"))).scalar_one()
            role.permissions = [Permission(code=code, name=code, module="parent")]
            await db.commit()
        assert (await client.get(children_path, headers=parent)).status_code == 403
        response = await client.get(options_path, headers=parent, params={"module": module})
        assert response.status_code == 200, response.text
        assert response.json()["data"] == [
            {"student_id": str(child.id), "first_name": child.first_name, "last_name": child.last_name}
            for child in data["children"]
        ]
        other_module = "finances" if module == "attendance" else "attendance"
        assert (await client.get(options_path, headers=parent, params={"module": other_module})).status_code == 403
        for key, status in (("children", 200), ("stranger", 403)):
            child = data[key][0] if key == "children" else data[key]
            result = await client.get(f"/api/parent/child/{child.id}/{detail}", headers=parent, params=params)
            assert result.status_code == status, result.text


async def test_parent_timeline_reads_real_child_events_and_school_day_boundaries(materials_client, monkeypatch):
    client, sessions, data = materials_client
    monkeypatch.setattr(get_settings(), "BUSINESS_TIMEZONE", "Europe/Istanbul")
    day = date(2026, 11, 3)
    student = data["children"][0]
    async with sessions() as db:
        await grant_attendance_read(db)
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
            student_id=student.id, attendance_date=day, status=AttendanceStatus.PRESENT, check_in_time=time(8, 30), recorded_by=data["teacher"].id))
        db.add(DailyDevelopmentReport(student_id=student.id, class_id=student.class_id, date=day, meal_status="ALL",
            activities=["Kitap okuma"], teacher_notes="Kalıcı öğretmen notu", recorded_by=data["teacher"].id,
            updated_at=datetime(2026, 11, 3, 10, tzinfo=UTC)))
        prescription = MedicationSchedule(student_id=student.id, medication_name="Test talimatı", dosage="Test dozu",
            frequency="Günde bir", start_date=day)
        other_prescription = MedicationSchedule(student_id=data["children"][1].id, medication_name="Başka çocuğun kaydı",
            dosage="Gizli", frequency="Günde bir", start_date=day)
        route = BusRoute(branch_id=data["branch"].id, route_name="Test güzergâhı")
        db.add_all([prescription, other_prescription, route])
        await db.flush()
        for instant in (datetime(2026, 11, 2, 20, 59, tzinfo=UTC), datetime(2026, 11, 2, 22, 30, tzinfo=UTC),
            datetime(2026, 11, 3, 21, tzinfo=UTC)):
            db.add(MedicationLog(student_id=student.id, schedule_id=prescription.id, scheduled_time=time(1, 30),
                given_time=instant, status="GIVEN", given_by=data["teacher"].id))
        # Corrupt auxiliary relationship must not reveal a sibling's prescription.
        db.add(MedicationLog(student_id=student.id, schedule_id=other_prescription.id, scheduled_time=time(1),
            given_time=datetime(2026, 11, 3, 9, tzinfo=UTC), status="GIVEN"))
        db.add(InfirmaryVisit(student_id=student.id, branch_id=data["branch"].id, visit_date=day, visit_time=time(11),
            complaint="Test revir kaydı", examined_by=data["teacher"].id))
        db.add(BusAttendance(route_id=route.id, student_id=student.id, date=day, pickup_time=time(7, 45), dropoff_time=time(16, 30)))
        db.add(PickupLog(student_id=student.id, pickup_person_name="Yetkili veli", verified_by=data["teacher"].id,
            pickup_time=datetime(2026, 11, 3, 14, tzinfo=UTC)))
        await db.commit()
    path = f"/api/parent/child/{student.id}/timeline"
    response = await client.get(path, headers=auth(data["user"]), params={"date": str(day)})
    assert response.status_code == 200, response.text
    events = response.json()["data"]["events"]
    assert [row["type"] for row in events] == ["MEDICATION", "BUS_PICKUP", "ATTENDANCE", "INFIRMARY", "DAILY_REPORT", "BUS_DROPOFF", "PICKUP"]
    assert events[0]["time"] == "01:30" and events[0]["timestamp"].endswith("+03:00")
    assert "Başka çocuğun kaydı" not in response.text
    assert all(row["detail_url"].startswith("/parent/") for row in events)
    response = await client.get(f'/api/parent/child/{data["children"][1].id}/timeline', headers=auth(data["user"]), params={"date": str(day)})
    assert response.json()["data"]["events"] == []
    assert (await client.get(f'/api/parent/child/{data["stranger"].id}/timeline', headers=auth(data["user"]))).status_code == 403


async def test_today_status_uses_school_date_and_saved_class_schedule(materials_client, monkeypatch):
    client, sessions, data = materials_client
    day = date(2026, 11, 3)
    monkeypatch.setattr(parent_day_service, "school_today", lambda: day)
    student = data["children"][0]
    async with sessions() as db:
        await grant_attendance_read(db)
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
            student_id=student.id, attendance_date=day, status=AttendanceStatus.PRESENT, check_in_time=time(8), recorded_by=data["teacher"].id))
        db.add(OperationalRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
            created_by=data["teacher"].id, kind="CLASS_SCHEDULE", data={"schedule": [
                {"day": "SALI", "periods": [{"subject": "Türkçe", "time": "09:00 - 09:40", "teacher_name": "Öğretmen"}]},
                {"day": "MONDAY", "periods": [{"subject": "Başka gün", "time": "10:00 - 10:40"}]}]}))
        await db.commit()
    response = await client.get(f'/api/parent/child/{student.id}/today-status', headers=auth(data["user"]))
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["date"] == str(day) and result["attendance"]["status"] == "PRESENT"
    assert result["today_schedule"] == [{"subject": "Türkçe", "start_time": "09:00", "end_time": "09:40", "teacher": "Öğretmen"}]
    assert (await client.get(f'/api/parent/child/{data["stranger"].id}/today-status', headers=auth(data["user"]))).status_code == 403


async def test_date_only_records_do_not_invent_an_event_time(materials_client):
    client, sessions, data = materials_client
    day = date(2026, 11, 3)
    student = data["children"][0]
    async with sessions() as db:
        await grant_attendance_read(db)
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=student.class_id,
            student_id=student.id, attendance_date=day, status=AttendanceStatus.ABSENT, recorded_by=data["teacher"].id))
        await db.commit()
    response = await client.get(f'/api/parent/child/{student.id}/timeline', headers=auth(data["user"]), params={"date": str(day)})
    row = response.json()["data"]["events"][0]
    assert row["time"] is None and row["timestamp"] is None and row["status"] == "ABSENT"


async def test_created_daily_report_is_visible_only_for_the_linked_child_and_date(materials_client, monkeypatch):
    client, _, data = materials_client
    day = date(2026, 11, 3)
    monkeypatch.setattr(parent_day_service, "school_today", lambda: day)
    student, sibling = data["children"]
    parent = auth(data["user"])
    observations = {"sleep_status": "30 dk", "mood": "Sakin", "activities": ["Kitap okuma", "Çizim"],
        "teacher_notes": "Kayıtlı gözlem"}
    created = await client.post("/api/daily-reports", headers=auth(data["teacher"]), json={"student_id": str(student.id),
        "class_id": str(student.class_id), "date": str(day), "meal_breakfast": "Tümünü Yedi", **observations})
    assert created.status_code == 200, created.text
    expected = {**observations, "meal_status": "Kahvaltı: Tümünü Yedi"}

    child_path = f"/api/parent/child/{student.id}"
    today = await client.get(f"{child_path}/today-status", headers=parent)
    assert today.status_code == 200, today.text
    assert today.json()["data"]["daily_report"] == expected
    timeline = await client.get(f"{child_path}/timeline", headers=parent, params={"date": str(day)})
    assert timeline.status_code == 200, timeline.text
    today_events = timeline.json()["data"]["events"]
    assert [(event["type"], event["details"]) for event in today_events] == [("DAILY_REPORT", expected)]
    previous = await client.get(f"{child_path}/timeline", headers=parent, params={"date": "2026-11-02"})
    assert previous.json()["data"]["events"] == []
    other = await client.get(f"/api/parent/child/{sibling.id}/today-status", headers=parent)
    assert other.json()["data"]["daily_report"] is None
    forbidden = await client.get(f'/api/parent/child/{data["stranger"].id}/timeline', headers=parent)
    assert forbidden.status_code == 403


async def test_parent_attendance_requires_permission_in_all_daily_views(materials_client, monkeypatch):
    client, sessions, data = materials_client
    sibling, child = data["children"]
    parent = auth(data["user"])
    day = date(2025, 10, 7)
    monkeypatch.setattr(parent_day_service, "school_today", lambda: day)
    child_path = f"/api/parent/child/{child.id}"
    path = f"{child_path}/attendance"
    period = {"year": day.year, "month": day.month}

    async with sessions() as db:
        db.add(DailyDevelopmentReport(student_id=child.id, class_id=child.class_id, date=day,
            teacher_notes="Kayıtlı gözlem", recorded_by=data["teacher"].id))
        db.add_all([AttendanceRecord(student_id=student.id, class_id=student.class_id,
            organization_id=student.organization_id, branch_id=student.branch_id, attendance_date=record_day,
            status=AttendanceStatus.PRESENT, recorded_by=data["teacher"].id, notes=note)
            for student, record_day, note in [(child, day, "Seçilen çocuk"),
                (child, date(2025, 11, 7), "Farklı ay"), (sibling, date(2025, 10, 8), "Kardeş")]])
        await db.commit()

    assert (await client.get(path, headers=parent, params=period)).status_code == 403
    today = await client.get(f"{child_path}/today-status", headers=parent)
    assert today.status_code == 200, today.text
    assert "attendance" not in today.json()["data"]
    assert today.json()["data"]["daily_report"]["teacher_notes"] == "Kayıtlı gözlem"
    timeline = await client.get(f"{child_path}/timeline", headers=parent, params={"date": str(day)})
    assert timeline.status_code == 200, timeline.text
    assert [event["type"] for event in timeline.json()["data"]["events"]] == ["DAILY_REPORT"]

    async with sessions() as db:
        await grant_attendance_read(db)
        await db.commit()

    today = await client.get(f"{child_path}/today-status", headers=parent)
    assert today.json()["data"]["attendance"]["status"] == "PRESENT"
    no_record = await client.get(f"/api/parent/child/{sibling.id}/today-status", headers=parent)
    assert no_record.json()["data"]["attendance"] is None
    timeline = await client.get(f"{child_path}/timeline", headers=parent, params={"date": str(day)})
    entry = next(event for event in timeline.json()["data"]["events"] if event["type"] == "ATTENDANCE")
    assert entry["details"]["notes"] == "Seçilen çocuk"

    response = await client.get(path, headers=parent, params=period)
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert (payload["student_id"], payload["year"], payload["month"]) == (str(child.id), 2025, 10)
    assert payload["calendar"]["7"]["note"] == "Seçilen çocuk" and payload["calendar"]["8"]["status"] is None
    assert payload["summary"]["total"] == 1
    assert (await client.get(f'/api/parent/child/{data["stranger"].id}/attendance', headers=parent, params=period)).status_code == 403


async def test_teacher_with_assigned_branch_can_read_daily_reports_without_server_error(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        db.add(UserBranch(user_id=data["teacher"].id, branch_id=data["branch"].id))
        db.add(DailyDevelopmentReport(student_id=data["children"][0].id, class_id=data["classroom"].id,
            date=date(2026, 11, 3), teacher_notes="Şube kapsamındaki rapor", recorded_by=data["teacher"].id))
        await db.commit()
    response = await client.get("/api/daily-reports", headers=auth(data["teacher"]))
    assert response.status_code == 200, response.text
    assert "Şube kapsamındaki rapor" in response.text
