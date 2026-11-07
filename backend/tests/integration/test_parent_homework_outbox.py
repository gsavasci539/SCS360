from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4
import os

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.services import homework_service, parent_data_service, outbox_service
from app.core.database import Base
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.tenant import TenantContext
from app.infrastructure.models.models import (
    Organization, Branch, ClassRoom, Student, Parent, StudentParent, User, Grade, SubjectType, GradeType,
    HomeworkSubmission, NotificationJob, NotificationRecipient, NotificationChannel, NotificationStatus,
)
from app.infrastructure.notifications.outbox_worker import process_pending_jobs
from app.infrastructure.notifications.base import ProviderResult
from app.routers.homework import HomeworkCreate


@pytest.fixture(params=["sqlite", "postgresql"])
async def portal_db(tmp_path, request):
    cleanup_engine, schema = None, None
    if request.param == "postgresql":
        url = os.getenv("TEST_POSTGRES_URL")
        if not url:
            pytest.skip("TEST_POSTGRES_URL must point at a disposable acceptance database")
        if "scs360_acceptance" not in url:
            raise RuntimeError("PostgreSQL acceptance tests require a disposable scs360_acceptance database")
        schema = "acceptance_" + uuid4().hex
        cleanup_engine = create_async_engine(url)
        async with cleanup_engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    else:
        engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'clean.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        org = Organization(name="Acceptance")
        foreign = Organization(name="Other")
        db.add_all([org, foreign]); await db.flush()
        branch = Branch(name="School", organization_id=org.id)
        other_branch = Branch(name="Other School", organization_id=foreign.id)
        db.add_all([branch, other_branch]); await db.flush()
        user = User(email="parent@test.invalid", password_hash="unused", first_name="Parent", last_name="Test", organization_id=org.id)
        teacher = User(email="teacher@test.invalid", password_hash="unused", first_name="Teacher", last_name="Test", organization_id=org.id)
        db.add_all([user, teacher]); await db.flush()
        from app.infrastructure.models.models import Permission, Role, UserRole
        permissions = {code: Permission(code=code, name=code, module=code.split('.')[0]) for code in (
            "messaging.read", "messaging.send",
            "material.read", "material.write",
            "parent.send_excuse",
            "parent.view_children", "parent.send_message", "parent.make_payment", "homework.read", "homework.write",
            "daily_reports.read", "daily_reports.write", "canteen.read", "students.read")}
        parent_role = Role(name="Parent", slug="parent", organization_id=org.id,
            permissions=[permissions[code] for code in ("parent.view_children", "parent.send_message", "parent.make_payment", "parent.send_excuse")])
        teacher_role = Role(name="Teacher", slug="teacher", organization_id=org.id,
            permissions=[permission for code, permission in permissions.items() if not code.startswith("parent.")])
        db.add_all([parent_role, teacher_role]); await db.flush()
        db.add_all([UserRole(user_id=user.id, role_id=parent_role.id), UserRole(user_id=teacher.id, role_id=teacher_role.id)])
        classroom = ClassRoom(name="A", organization_id=org.id, branch_id=branch.id, teacher_id=teacher.id)
        other_class = ClassRoom(name="B", organization_id=org.id, branch_id=branch.id)
        db.add_all([classroom, other_class]); await db.flush()
        children = [Student(first_name=f"Child{i}", last_name="Test", organization_id=org.id,
            branch_id=branch.id, class_id=classroom.id) for i in range(2)]
        stranger = Student(first_name="Other", last_name="Child", organization_id=foreign.id, branch_id=other_branch.id)
        parent = Parent(user_id=user.id, organization_id=org.id, first_name="Parent", last_name="Test")
        db.add_all([*children, stranger, parent]); await db.flush()
        db.add_all([StudentParent(student_id=child.id, parent_id=parent.id) for child in children])
        # Even a corrupt cross-organization relationship must not grant access.
        db.add(StudentParent(student_id=stranger.id, parent_id=parent.id))
        await db.commit()
        data = dict(user=user, teacher=teacher, children=children, stranger=stranger, org=org,
            branch=branch, other_branch=other_branch, classroom=classroom, other_class=other_class)
    try:
        yield sessions, data
    finally:
        await engine.dispose()
        if cleanup_engine:
            async with cleanup_engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            await cleanup_engine.dispose()


@pytest.mark.asyncio
async def test_parent_reads_real_records_no_fallback_and_denies_cross_tenant(portal_db):
    sessions, data = portal_db
    async with sessions() as db:
        for name in ("grades", "schedule", "homework", "materials", "communications", "announcements", "activities", "weekly_reports"):
            service = getattr(parent_data_service, name)
            assert await service(db, data["user"], data["children"][0].id) == []
            with pytest.raises(ForbiddenException):
                await service(db, data["user"], data["stranger"].id)
        child = data["children"][0]
        db.add(Grade(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=child.class_id,
            student_id=child.id, subject=SubjectType.MATHEMATICS, grade_type=GradeType.EXAM,
            exam_date=date.today(), score=87, max_score=100))
        await db.commit()
    async with sessions() as db:
        assert (await parent_data_service.grades(db, data["user"], child.id))[0]["score"] == 87
        assert await parent_data_service.grades(db, data["user"], data["children"][1].id) == []


@pytest.mark.asyncio
async def test_chat_is_per_child_and_persists_across_sessions(portal_db):
    from app.application.services import teacher_chat_service
    sessions, data = portal_db
    async with sessions() as db:
        await parent_data_service.send_chat(db, data["user"], data["children"][0].id, data["teacher"].id, "Only first child")
        await db.commit()
    async with sessions() as db:
        first = await parent_data_service.chat_history(db, data["user"], data["children"][0].id, data["teacher"].id)
        assert len(first) == 1 and first[0]["content"] == "Only first child"
        assert await parent_data_service.chat_history(db, data["user"], data["children"][1].id, data["teacher"].id) == []
    tenant = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id,
        branch_ids=[data["branch"].id], role_slugs={"teacher"})
    async with sessions() as db:
        db.info["tenant_context"] = tenant
        db.info["accessible_student_ids"] = {child.id for child in data["children"]}
        history = await teacher_chat_service.history(db, tenant, data["children"][0].id, data["user"].id)
        assert len(history) == 1 and history[0]["is_current_user"] is False
        await teacher_chat_service.send(db, tenant, data["children"][0].id, "Teacher reply", data["user"].id)
        with pytest.raises((ForbiddenException, NotFoundException)):
            await teacher_chat_service.send(db, tenant, data["stranger"].id, "Forbidden reply")
        await db.commit()
    async with sessions() as db:
        history = await parent_data_service.chat_history(db, data["user"], data["children"][0].id, data["teacher"].id)
        assert [message["content"] for message in history] == ["Only first child", "Teacher reply"]
        assert await parent_data_service.chat_history(db, data["user"], data["children"][1].id, data["teacher"].id) == []


@pytest.mark.asyncio
async def test_direct_teacher_assignment_grants_only_the_assigned_student(portal_db):
    from app.core.student_access import accessible_student_ids, require_teacher_for_student
    from app.infrastructure.models.models import StudentTeacherAssignment
    sessions, data = portal_db
    async with sessions() as db:
        student = Student(organization_id=data["org"].id, branch_id=data["branch"].id,
            class_id=data["other_class"].id, first_name="Direct", last_name="Assignment")
        db.add(student); await db.flush()
        db.add(StudentTeacherAssignment(student_id=student.id, teacher_id=data["teacher"].id, subject_name="Math"))
        await db.commit()
        tenant = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id, role_slugs={"teacher"})
        ids = await accessible_student_ids(db, tenant)
        assert student.id in ids and data["stranger"].id not in ids
        await require_teacher_for_student(db, student, data["teacher"].id)


@pytest.mark.asyncio
async def test_homework_persists_and_teacher_class_scope_is_enforced(portal_db):
    sessions, data = portal_db
    tenant = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id,
        branch_ids=[data["branch"].id], role_slugs={"teacher"})
    async with sessions() as db:
        created = await homework_service.save(db, tenant, HomeworkCreate(title="Real assignment", class_id=data["classroom"].id))
        with pytest.raises(ForbiddenException):
            await homework_service.save(db, tenant, HomeworkCreate(title="Forbidden", class_id=data["other_class"].id))
        await db.commit()
    async with sessions() as db:
        assert (await homework_service.get(db, tenant, UUID(created["id"]))).title == "Real assignment"
        assert (await parent_data_service.homework(db, data["user"], data["children"][0].id))[0]["title"] == "Real assignment"
        outsider = TenantContext(user_id=uuid4(), organization_id=uuid4())
        with pytest.raises(NotFoundException):
            await homework_service.get(db, outsider, UUID(created["id"]))


@pytest.mark.asyncio
async def test_outbox_retry_is_durable_and_success_requires_provider_confirmation(portal_db):
    sessions, data = portal_db
    tenant = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id, branch_ids=[data["branch"].id])
    async with sessions() as db:
        job = NotificationJob(organization_id=data["org"].id, branch_id=data["branch"].id,
            channel=NotificationChannel.EMAIL, body="Test", subject="Actual job", scheduled_at=datetime.now(UTC)-timedelta(seconds=1))
        db.add(job); await db.flush()
        recipient = NotificationRecipient(notification_job_id=job.id, recipient_address="test@invalid.local")
        db.add(recipient); await db.commit()
        job_id, recipient_id = job.id, recipient.id
    class Delivery:
        def __init__(self, success): self.success = success
        async def dispatch(self, *args): return ProviderResult(success=self.success, message="Simulated provider result")
    await process_pending_jobs(sessions, Delivery(False))
    async with sessions() as db:
        rows = await outbox_service.records(db, tenant)
        assert rows[0]["status"] == "FAILED" and rows[0]["sent_at"] is None
        retry = await outbox_service.retry(db, tenant, recipient_id)
        assert retry["status"] == "PENDING" and retry["sent_at"] is None
        with pytest.raises(NotFoundException):
            await outbox_service.get(db, TenantContext(user_id=uuid4(), organization_id=uuid4()), recipient_id)
        await db.commit()
    await process_pending_jobs(sessions, Delivery(True))
    async with sessions() as db:
        assert (await outbox_service.records(db, tenant))[0]["status"] == "SENT"
        assert (await db.get(NotificationJob, job_id)).status == NotificationStatus.SENT


@pytest.mark.asyncio
async def test_checkout_verifies_provider_result_and_callback_is_idempotent(portal_db):
    import hashlib
    import hmac
    from types import SimpleNamespace
    from decimal import Decimal
    from sqlalchemy import func
    from app.application.services import online_payment_service as payments
    from app.core.exceptions import AppException
    from app.infrastructure.models.models import Debt, DebtType, Payment, Receipt
    from app.routers.payments import IyzicoPaymentRequest

    sessions, data = portal_db
    tenant = TenantContext(user_id=data["user"].id, organization_id=data["org"].id, role_slugs={"parent"})
    class Gateway(payments.IyzicoGateway):
        def __init__(self):
            super().__init__(SimpleNamespace(IYZICO_SECRET_KEY="isolated-test-secret", IYZICO_ORGANIZATION_ID=str(data["org"].id), IYZICO_PAYMENT_ENABLED=True))
            self.result = {}
        def configured(self): pass
        async def initialize(self, payload):
            self.payload = payload
            self.result = {"status": "success", "paymentStatus": "SUCCESS", "paymentId": "provider-123",
                "currency": "TRY", "basketId": payload["basketId"], "conversationId": payload["conversationId"],
                "price": "25.0", "paidPrice": "25.00", "token": "random-test-token", "fraudStatus": 1}
            self.sign()
            initial = {"status": "success", "conversationId": payload["conversationId"], "token": self.result["token"],
                "paymentPageUrl": "https://sandbox-api.iyzipay.com/checkoutform/test"}
            initial["signature"] = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(),
                f"{payload['conversationId']}:{initial['token']}".encode(), hashlib.sha256).hexdigest()
            return initial
        def sign(self):
            fields = ("paymentStatus", "paymentId", "currency", "basketId", "conversationId", "paidPrice", "price", "token")
            values = [str(self.result[field]) if field not in {"paidPrice", "price"} else
                format(Decimal(self.result[field]).normalize(), 'f') for field in fields]
            self.result["signature"] = hmac.new(self.settings.IYZICO_SECRET_KEY.encode(), ":".join(values).encode(), hashlib.sha256).hexdigest()
        async def retrieve(self, token, conversation_id):
            assert str(conversation_id) == self.result["conversationId"]
            return self.result
    gateway = Gateway()
    async with sessions() as db:
        child = data["children"][0]
        debt = Debt(organization_id=data["org"].id, branch_id=data["branch"].id, student_id=child.id,
            debt_type=DebtType.EDUCATION, amount=100, paid_amount=0, due_date=date.today())
        db.add(debt); await db.flush()
        body = IyzicoPaymentRequest(debt_id=debt.id, amount="25.00", buyer={"identityNumber": "test-id",
            "registrationAddress": "Test billing address", "city": "Istanbul", "country": "Turkey"})
        result = await payments.initialize(db, tenant, data["user"], body, "127.0.0.1", gateway)
        assert result["status"] == "PENDING"
        await db.commit()
        debt_id = debt.id
    async with sessions() as db:
        gateway.result["signature"] = "forged"
        with pytest.raises(AppException, match="doğrulanamadı"):
            await payments.reconcile(db, "random-test-token", gateway)
        assert (await db.get(Debt, debt_id)).paid_amount == 0
        gateway.sign()
        for fraud, expected in [(0, "REVIEW"), (-1, "FAILED"), (None, "REVIEW")]:
            gateway.result["fraudStatus"] = fraud
            checked = await payments.reconcile(db, "random-test-token", gateway)
            assert checked["status"] == expected
            assert (await db.get(Debt, debt_id)).paid_amount == 0
            assert (await db.execute(select(func.count()).select_from(Payment))).scalar_one() == 0
        gateway.result["fraudStatus"] = 1
        first = await payments.reconcile(db, "random-test-token", gateway)
        await db.commit()
        assert first["status"] == "SUCCESS"
    async with sessions() as db:
        repeated = await payments.reconcile(db, "random-test-token", gateway)
        assert repeated["payment_id"] == first["payment_id"]
        assert (await db.get(Debt, debt_id)).paid_amount == 25
        assert (await db.execute(select(func.count()).select_from(Payment))).scalar_one() == 1
        assert (await db.execute(select(func.count()).select_from(Receipt))).scalar_one() == 1


@pytest.mark.asyncio
async def test_empty_jobs_fail_and_live_lease_is_not_taken_by_other_worker(portal_db):
    sessions, data = portal_db
    async with sessions() as db:
        job = NotificationJob(organization_id=data["org"].id, channel=NotificationChannel.EMAIL,
            body="No recipients", scheduled_at=datetime.now(UTC)-timedelta(seconds=1))
        locked = NotificationJob(organization_id=data["org"].id, channel=NotificationChannel.EMAIL,
            body="Already claimed", scheduled_at=datetime.now(UTC)-timedelta(seconds=1),
            locked_until=datetime.now(UTC)+timedelta(minutes=5), lock_token=uuid4())
        db.add_all([job, locked]); await db.commit()
        empty_id, locked_id = job.id, locked.id
    class NoDelivery:
        async def dispatch(self, *args): raise AssertionError("No messages may be sent")
    await process_pending_jobs(sessions, NoDelivery())
    async with sessions() as db:
        assert (await db.get(NotificationJob, empty_id)).status == NotificationStatus.FAILED
        assert (await db.get(NotificationJob, locked_id)).lock_token is not None


@pytest.mark.asyncio
async def test_real_jwt_role_checks_and_session_boundaries_http(portal_db, monkeypatch, tmp_path):
    from httpx import ASGITransport, AsyncClient
    from app.core.security import create_access_token
    from app.core.database import get_db
    from app.main import app
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "PRIVATE_UPLOAD_DIR", str(tmp_path / "private"))
    monkeypatch.setattr(get_settings(), "MAX_UPLOAD_SIZE_MB", 1)
    sessions, data = portal_db
    async def database():
        async with sessions() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = database
    parent = {"Authorization": "Bearer " + create_access_token(data["user"].id)}
    teacher = {"Authorization": "Bearer " + create_access_token(data["teacher"].id)}
    async with sessions() as db:
        admin = User(email="admin@test.invalid", password_hash="unused", first_name="Admin", last_name="Test",
            organization_id=data["org"].id, is_super_admin=True, branches=[await db.get(Branch, data["branch"].id)])
        db.add(admin); await db.commit()
        admin_id = admin.id
    admin_headers = {"Authorization": "Bearer " + create_access_token(admin_id)}
    try:
        async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=True), base_url="http://acceptance") as client:
            own = await client.get(f'/api/parent/child/{data["children"][0].id}/grades', headers=parent)
            assert own.status_code == 200, own.text
            denied = await client.get(f'/api/parent/child/{data["stranger"].id}/grades', headers=parent)
            assert denied.status_code == 403, denied.text
            forbidden = await client.post('/api/homework', headers=parent, json={"title": "No access"})
            assert forbidden.status_code == 403
            homework = await client.post('/api/homework', headers=teacher,
                json={"title": "HTTP persisted", "class_id": str(data["classroom"].id)})
            assert homework.status_code == 200, homework.text
            homework_id = homework.json()["data"]["id"]
            content = b"%PDF-1.4\nAcceptance homework file\n%%EOF"
            form = {"student_id": str(data["children"][0].id), "submission_text": "Actual file submission"}
            uploaded = await client.post(f'/api/homework/{homework_id}/submit-file', headers=parent,
                data=form, files={"file": ("homework.pdf", content, "application/pdf")})
            assert uploaded.status_code == 200, uploaded.text
            submission_id = uploaded.json()["data"]["id"]
            download_url = "/api" + uploaded.json()["data"]["attachment_url"]
            downloaded = await client.get(download_url, headers=teacher)
            assert downloaded.status_code == 200 and downloaded.content == content, downloaded.text
            assert downloaded.headers["cache-control"] == "private, no-store"
            assert (tmp_path / "private" / "homework" / submission_id).read_bytes() == content
            denied_upload = await client.post(f'/api/homework/{homework_id}/submit-file', headers=parent,
                data={"student_id": str(data["stranger"].id)}, files={"file": ("homework.pdf", content)})
            assert denied_upload.status_code == 403, denied_upload.text
            bad_type = await client.post(f'/api/homework/{homework_id}/submit-file', headers=parent,
                data=form, files={"file": ("program.exe", content)})
            assert bad_type.status_code == 422, bad_type.text
            oversized = await client.post(f'/api/homework/{homework_id}/submit-file', headers=parent,
                data=form, files={"file": ("large.pdf", b"X" * (1024 * 1024 + 1))})
            assert oversized.status_code == 413, oversized.text
            graded = await client.put(f'/api/homework/submissions/{submission_id}/grade', headers=teacher,
                json={"score": 0, "teacher_feedback": "Actual feedback"})
            assert graded.status_code == 200 and graded.json()["data"]["score"] == 0, graded.text
            repeated = await client.post(f'/api/homework/{homework_id}/submit-file', headers=parent,
                data=form, files={"file": ("changed.pdf", b"new")})
            assert repeated.status_code == 409 and (tmp_path / "private" / "homework" / submission_id).read_bytes() == content
            wrong_class = await client.post('/api/homework', headers=teacher,
                json={"title": "No access", "class_id": str(data["other_class"].id)})
            assert wrong_class.status_code == 403, wrong_class.text
            report = await client.post('/api/daily-reports', headers=teacher,
                json={"student_id": str(data["children"][0].id), "date": date.today().isoformat(), "teacher_notes": "Real note"})
            assert report.status_code == 200, report.text
            wallet = await client.get(f'/api/canteen/student/{data["children"][0].id}/wallet', headers=teacher)
            assert wallet.status_code == 200, wallet.text
            assert wallet.json()["data"]["balance"] == 0
            bad_wallet = await client.get(f'/api/canteen/student/{data["stranger"].id}/wallet', headers=teacher)
            assert bad_wallet.status_code in {403, 404}, bad_wallet.text
            fcm = await client.patch(f'/api/users/{data["user"].id}/fcm-token', headers=parent, json={"token": "test-device-token-12345"})
            assert fcm.status_code == 200, fcm.text
            wrong_fcm = await client.patch(f'/api/users/{data["teacher"].id}/fcm-token', headers=parent, json={"token": "test-device-token-12345"})
            assert wrong_fcm.status_code == 403
            student_id = data["children"][0].id
            sent = await client.post(f'/api/parent/child/{student_id}/chat/{data["teacher"].id}',
                headers=parent, json={"message": "Parent HTTP message"})
            assert sent.status_code == 200, sent.text
            teacher_url = f'/api/teacher/chat/{student_id}?parent_id={data["user"].id}'
            inbox = await client.get(teacher_url, headers=teacher)
            assert inbox.status_code == 200 and inbox.json()["data"][0]["content"] == "Parent HTTP message", inbox.text
            reply = await client.post(teacher_url, headers=teacher, json={"message": "Teacher HTTP reply"})
            assert reply.status_code == 200, reply.text
            parent_inbox = await client.get(f'/api/parent/child/{student_id}/chat/{data["teacher"].id}', headers=parent)
            assert parent_inbox.status_code == 200 and parent_inbox.json()["data"][-1]["content"] == "Teacher HTTP reply", parent_inbox.text
            conversations = await client.get('/api/messages/conversations', headers=teacher)
            assert conversations.status_code == 200 and len(conversations.json()["data"]) == 1, conversations.text
            admin_reply = await client.post(f'/api/admin/chat/{student_id}?parent_id={data["user"].id}',
                headers=admin_headers, json={"message": "Admin reply"})
            assert admin_reply.status_code == 200, admin_reply.text
            contacts = await client.get(f'/api/parent/child/{student_id}/teachers', headers=parent)
            assert contacts.status_code == 200 and str(admin_id) in {item["id"] for item in contacts.json()["data"]}, contacts.text
            admin_thread = await client.get(f'/api/parent/child/{student_id}/chat/{admin_id}', headers=parent)
            assert admin_thread.status_code == 200 and admin_thread.json()["data"][0]["content"] == "Admin reply", admin_thread.text
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.asyncio
async def test_appointment_availability_uses_school_timezone(portal_db):
    from datetime import time
    from app.infrastructure.models.models import Appointment, TimeSlot
    from app.routers.appointments import get_teacher_available_slots
    sessions, data = portal_db
    day = date(2026, 11, 3)
    tenant = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id, role_slugs={"teacher"})
    async with sessions() as db:
        db.add_all([TimeSlot(teacher_id=data["teacher"].id, date=day, start_time=time(10), end_time=time(10, 30)),
            TimeSlot(teacher_id=data["teacher"].id, date=day, start_time=time(11), end_time=time(11, 30)),
            Appointment(organization_id=data["org"].id, teacher_id=data["teacher"].id,
                student_id=data["children"][0].id, parent_id=data["user"].id,
                slot_datetime=datetime(2026, 11, 3, 7, tzinfo=UTC), duration_minutes=30, status="CONFIRMED")])
        await db.commit()
    async with sessions() as db:
        result = await get_teacher_available_slots(teacher_id=data["teacher"].id, date=day, db=db, tenant=tenant)
        assert [slot["start_time"] for slot in result["data"]] == ["11:00"]
        from app.application.services import appointment_service
        records = await appointment_service.records(db, tenant)
        assert records[0]["appointment_date"] == "2026-11-03" and records[0]["appointment_time"] == "10:00"


@pytest.mark.asyncio
async def test_imports_persist_valid_rows_and_roll_back_only_bad_rows(portal_db):
    from app.application.services.import_service import import_rows
    from app.infrastructure.models.models import LibraryBook
    sessions, data = portal_db
    tenant = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id, branch_ids=[data["branch"].id])
    async with sessions() as db:
        result = await import_rows(db, tenant, "students", [
            {"first_name": "Imported", "last_name": "One", "student_number": "IMPORT-1", "class_id": str(data["classroom"].id)},
            {"first_name": "Invalid", "last_name": "Branch", "branch_id": str(data["other_branch"].id)},
            {"first_name": "Imported", "last_name": "Two", "student_number": "IMPORT-2"},
        ])
        assert result["imported"] == 2 and len(result["errors"]) == 1
        books = await import_rows(db, tenant, "library", [{"title": "Real book", "author": "Writer", "quantity": "3"}])
        assert books["imported"] == 1
        await db.commit()
    async with sessions() as db:
        assert (await db.execute(select(Student).where(Student.student_number.like("IMPORT-%")))).scalars().all().__len__() == 2
        assert (await db.execute(select(LibraryBook).where(LibraryBook.title == "Real book"))).scalar_one().total_copies == 3


@pytest.mark.asyncio
async def test_wallet_has_no_fictional_balance_and_blocks_overspend(portal_db):
    from app.application.services import canteen_wallet_service as wallets
    from app.routers.operations import CanteenRestrictionUpdate
    from app.core.exceptions import ConflictException
    sessions, data = portal_db
    tenant = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id, branch_ids=[data["branch"].id])
    child = data["children"][0]
    async with sessions() as db:
        assert wallets.serialize(*(await wallets.wallet(db, tenant, child.id)))["balance"] == 0
        with pytest.raises(ConflictException):
            await wallets.purchase(db, tenant, child.id, price=10, name="Snack")
        assert (await wallets.topup(db, tenant, child.id, 100, "CASH"))["balance"] == 100
        await wallets.restrictions(db, tenant, CanteenRestrictionUpdate(student_id=str(child.id), daily_limit=30))
        first = await wallets.purchase(db, tenant, child.id, price=20, name="Snack")
        assert first["balance"] == 80 and first["today_spent"] == 20
        with pytest.raises(ConflictException):
            await wallets.purchase(db, tenant, child.id, price=20, name="Second snack")
        await db.commit()
    async with sessions() as db:
        assert wallets.serialize(*(await wallets.wallet(db, tenant, child.id)))["balance"] == 80
        cash = await wallets.purchase(db, tenant, child.id, price=5, name="Paid cash", payment_method="CASH")
        assert cash["balance"] == 80 and cash["today_spent"] == 25


@pytest.mark.asyncio
async def test_session_scope_generates_valid_queries_for_every_mapped_entity(portal_db):
    sessions, data = portal_db
    async with sessions() as db:
        db.info["tenant_context"] = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id,
            branch_ids=[data["branch"].id])
        db.info["accessible_student_ids"] = None
        for mapper in Base.registry.mappers:
            try:
                await db.execute(select(mapper.class_).limit(1))
            except Exception as exc:
                pytest.fail(f"Scope query for {mapper.class_.__name__} failed: {exc}")
        assert (await db.execute(select(Student).where(Student.id == data["stranger"].id))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_branch_scope_blocks_reads_updates_and_super_admin_escalation(portal_db):
    from sqlalchemy import update
    sessions, data = portal_db
    async with sessions() as db:
        branch = Branch(organization_id=data["org"].id, name="Unassigned branch")
        db.add(branch); await db.flush()
        student = Student(organization_id=data["org"].id, branch_id=branch.id, first_name="Restricted", last_name="Branch")
        db.add(student); await db.commit()
        restricted_id = student.id
    async with sessions() as db:
        db.info["tenant_context"] = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id,
            branch_ids=[data["branch"].id])
        db.info["accessible_student_ids"] = None
        assert (await db.execute(select(Student).where(Student.id == restricted_id))).scalar_one_or_none() is None
        changed = await db.execute(update(Student).where(Student.id == restricted_id).values(first_name="Forbidden mutation"))
        assert changed.rowcount == 0
        teacher = await db.get(User, data["teacher"].id)
        teacher.is_super_admin = True
        with pytest.raises(ForbiddenException):
            await db.flush()
        await db.rollback()
    async with sessions() as db:
        assert (await db.get(Student, restricted_id)).first_name == "Restricted"
        assert (await db.get(User, data["teacher"].id)).is_super_admin is False


@pytest.mark.asyncio
async def test_notification_retry_resets_failed_recipients_but_preserves_sent(portal_db):
    from app.routers.dashboard_reports import retry_notification
    from app.core.exceptions import ConflictException
    sessions, data = portal_db
    tenant = TenantContext(user_id=data["teacher"].id, organization_id=data["org"].id)
    async with sessions() as db:
        job = NotificationJob(organization_id=data["org"].id, channel=NotificationChannel.EMAIL,
            body="Test", status=NotificationStatus.FAILED, retry_count=3)
        db.add(job); await db.flush()
        failed = NotificationRecipient(notification_job_id=job.id, recipient_address="failed@test.invalid", status=NotificationStatus.FAILED)
        sent = NotificationRecipient(notification_job_id=job.id, recipient_address="sent@test.invalid", status=NotificationStatus.SENT)
        db.add_all([failed, sent]); await db.flush()
        await retry_notification(job.id, tenant, db)
        assert job.status == NotificationStatus.PENDING and job.retry_count == 0
        assert failed.status == NotificationStatus.PENDING and sent.status == NotificationStatus.SENT
        job.locked_until = datetime.now(UTC) + timedelta(minutes=1)
        with pytest.raises(ConflictException):
            await retry_notification(job.id, tenant, db)
