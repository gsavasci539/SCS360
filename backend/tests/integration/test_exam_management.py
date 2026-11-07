import asyncio
from datetime import date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.domain.entities.exams import Exam, ExamResult
from app.infrastructure.models.models import AttendanceRecord, AttendanceStatus
from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


def scope(data):
    return {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}


def body(data, **values):
    return {"class_id": str(data["classroom"].id), "title": "Gerçek sınav", "exam_type": "QUIZ",
            "exam_date": "2026-10-20", "max_score": 80, **values}


async def create(client, data, **values):
    response = await client.post("/api/exams", headers=scope(data), json=body(data, **values))
    assert response.status_code == 200, response.text
    assert response.json()["message"] == "Sınav oluşturuldu", response.text
    return response.json()["data"]


async def save(client, data, exam, grades):
    return await client.post("/api/exams/bulk-grade-entry", headers=scope(data),
                             json={"exam_id": exam["id"], "grades": grades})


async def test_exam_time_and_actor_are_persisted_without_database_type_errors(platform_client):
    client, sessions, data = platform_client
    exam = await create(client, data, start_time="10:15", description="Gerçek açıklama")
    changed = await client.put(f'/api/exams/{exam["id"]}', headers=scope(data),
        json=body(data, start_time="11:30", title="Güncel sınav"))
    assert changed.status_code == 200, changed.text
    async with sessions() as db:
        stored = await db.get(Exam, UUID(exam["id"]))
        assert stored.start_time == time(11, 30)
        assert stored.created_by == data["root"].id and stored.updated_by == data["root"].id
    listed = await client.get("/api/exams", headers=scope(data))
    assert listed.status_code == 200 and listed.json()["data"][0]["start_time"] == "11:30:00", listed.text


async def test_invalid_exam_storage_values_are_rejected_before_writing(platform_client):
    client, sessions, data = platform_client
    for invalid in ({"title": "   "}, {"max_score": 0}, {"max_score": 1000}, {"max_score": 80.001},
                    {"weight": None}, {"weight": -1}, {"duration_minutes": 15.5}, {"exam_type": "invalid"},
                    {"description": "x" * 1001}, {"start_time": "10:15:00+03:00"}):
        response = await client.post("/api/exams", headers=scope(data), json=body(data, **invalid))
        assert response.status_code == 422, (invalid, response.text)
    async with sessions() as db:
        assert await db.scalar(select(func.count(Exam.id))) == 0


async def test_bulk_grades_validate_entire_batch_and_current_class_before_any_mutation(platform_client):
    client, sessions, data = platform_client
    exam = await create(client, data)
    first, second = data["children"]
    seeded = await save(client, data, exam, [{"student_id": str(first.id), "score": 40}])
    assert seeded.status_code == 200, seeded.text
    invalid_batches = [
        [{"student_id": str(first.id), "score": 0}, {"student_id": str(second.id), "score": 81}],
        [{"student_id": str(first.id), "score": 0}, {"student_id": "invalid", "score": 10}],
        [{"student_id": str(first.id), "score": 1}, {"student_id": str(first.id), "score": 2}],
        [], [{"student_id": str(first.id), "score": -1}],
        [{"student_id": str(first.id), "score": 10.001}],
        [{"student_id": str(first.id), "notes": "x" * 1001}],
        [{"student_id": str(first.id), "grade_scale": "x" * 11}],
    ]
    for grades in invalid_batches:
        invalid = await save(client, data, exam, grades)
        assert invalid.status_code == 422, invalid.text
    for grades in ([{"student_id": str(first.id), "score": 0}, {"student_id": str(data["stranger"].id), "score": 10}],):
        denied = await save(client, data, exam, grades)
        assert denied.status_code in {403, 404, 422}, denied.text
    moved = await client.put(f"/api/students/{second.id}", headers=scope(data), json={"class_id": str(data["other_class"].id)})
    assert moved.status_code == 200, moved.text
    denied = await save(client, data, exam, [{"student_id": str(second.id), "score": 30}])
    assert denied.status_code == 422, denied.text
    async with sessions() as db:
        results = (await db.execute(select(ExamResult))).scalars().all()
        assert len(results) == 1 and results[0].score == 40


async def test_zero_results_upsert_is_atomic_and_records_the_real_actor(platform_client):
    client, sessions, data = platform_client
    exam = await create(client, data)
    grades = [{"student_id": str(data["children"][0].id), "score": 0, "notes": "Gerçek sıfır"}]
    replies = await asyncio.gather(*[save(client, data, exam, grades) for _ in range(2)])
    assert [row.status_code for row in replies] == [200, 200], [row.text for row in replies]
    async with sessions() as db:
        results = (await db.execute(select(ExamResult))).scalars().all()
        assert len(results) == 1 and results[0].score == 0 and results[0].submitted_by == data["root"].id
    listed = await client.get(f'/api/exams/{exam["id"]}/results', headers=scope(data))
    assert listed.status_code == 200 and listed.json()["data"][0]["score"] == 0, listed.text
    existing = listed.json()["data"][0]
    mismatch = await client.put(f'/api/exams/results/{existing["id"]}', headers=scope(data), json={
        "exam_id": exam["id"], "student_id": str(data["children"][1].id), "score": 10})
    assert mismatch.status_code == 422, mismatch.text


async def test_cancel_retains_result_history_and_rejects_further_grading(platform_client):
    client, sessions, data = platform_client
    exam = await create(client, data)
    grades = [{"student_id": str(data["children"][0].id), "score": 40}]
    assert (await save(client, data, exam, grades)).status_code == 200
    cancelled = await client.delete(f'/api/exams/{exam["id"]}', headers=scope(data))
    assert cancelled.status_code == 200, cancelled.text
    again = await client.delete(f'/api/exams/{exam["id"]}', headers=scope(data))
    assert again.status_code == 200, again.text
    assert (await save(client, data, exam, grades)).status_code == 409
    async with sessions() as db:
        assert (await db.get(Exam, UUID(exam["id"]))).status == "CANCELLED"
        assert await db.scalar(select(func.count(ExamResult.id))) == 1
    summary = await client.get("/api/ai/academic-performance", headers=scope(data), params={"days": 365})
    assert summary.status_code == 200 and summary.json()["data"]["average_grade"] is None, summary.text


async def test_graded_exam_class_and_scale_are_immutable_and_duplicates_do_not_destroy_history(platform_client):
    client, sessions, data = platform_client
    exam = await create(client, data)
    grades = [{"student_id": str(data["children"][0].id), "score": 40}]
    assert (await save(client, data, exam, grades)).status_code == 200
    for updates in ({"max_score": 100}, {"class_id": str(data["other_class"].id)}):
        response = await client.put(f'/api/exams/{exam["id"]}', headers=scope(data), json=body(data, **updates))
        assert response.status_code == 409, response.text
    async with sessions() as db:
        db.add(ExamResult(exam_id=UUID(exam["id"]), student_id=data["children"][0].id, score=30))
        await db.commit()
    response = await save(client, data, exam, grades)
    assert response.status_code == 409, response.text
    async with sessions() as db:
        assert await db.scalar(select(func.count(ExamResult.id))) == 2


async def test_exam_write_requires_selected_school_and_foreign_exam_is_not_readable(platform_client):
    client, sessions, data = platform_client
    denied = await client.post("/api/exams", headers=headers(data["root"]), json=body(data))
    assert denied.status_code == 403, denied.text
    exam = await create(client, data)
    assert (await client.get(f'/api/exams/{uuid4()}/results', headers=scope(data))).status_code == 404
    assert (await client.post("/api/exams", headers=headers(data["user"]), json=body(data))).status_code == 403
    async with sessions() as db:
        assert await db.scalar(select(func.count(Exam.id))) == 1


async def test_exam_form_options_are_paged_searchable_and_do_not_hide_a_full_class(platform_client):
    from app.infrastructure.models.models import ClassRoom
    client, sessions, data = platform_client
    async with sessions() as db:
        classroom = await db.get(ClassRoom, data["classroom"].id)
        classroom.capacity = 2
        db.add_all([ClassRoom(organization_id=data["org"].id, branch_id=data["branch"].id,
            name=f"Seçenek {index:02}") for index in range(8)])
        await db.commit()
    reply = await client.get("/api/exams/class-options", headers=scope(data), params={"page_size": 2})
    assert reply.status_code == 200 and reply.json()["data"]["total"] == 10, reply.text
    assert len(reply.json()["data"]["items"]) == 2 and reply.json()["data"]["total_pages"] == 5
    search = await client.get("/api/exams/class-options", headers=scope(data), params={"search": "Seçenek 07"})
    assert search.status_code == 200 and len(search.json()["data"]["items"]) == 1, search.text
    full = await client.get("/api/exams/class-options", headers=scope(data), params={"search": "A"})
    assert full.status_code == 200 and str(data["classroom"].id) in [row["id"] for row in full.json()["data"]["items"]], full.text


async def test_write_only_exam_editor_gets_minimal_own_roster_without_granting_registry_reads(platform_client):
    from sqlalchemy.orm import selectinload
    from app.infrastructure.models.models import Permission, Role
    client, sessions, data = platform_client
    exam = await create(client, data)
    assert (await save(client, data, exam, [{"student_id": str(data["children"][0].id), "score": 0}])).status_code == 200
    async with sessions() as db:
        permission = Permission(code="exam.write", name="Exam write", module="exam")
        role = (await db.execute(select(Role).where(Role.organization_id == data["org"].id,
            Role.slug == "teacher").options(selectinload(Role.permissions)))).scalar_one()
        role.permissions = [permission]
        await db.commit()
    auth = headers(data["teacher"])
    reply = await client.get(f'/api/exams/{exam["id"]}/roster', headers=auth, params={"page_size": 1})
    assert reply.status_code == 200 and reply.json()["data"]["total"] == 2, reply.text
    assert len(reply.json()["data"]["items"]) == 1 and reply.json()["data"]["items"][0]["score"] == 0
    assert "organization_id" not in reply.json()["data"]["items"][0]
    options = await client.get("/api/exams/class-options", headers=auth)
    assert options.status_code == 200, options.text
    assert (await client.get("/api/students", headers=auth)).status_code == 403
    assert (await client.get("/api/classes", headers=auth)).status_code == 403
    foreign = await client.get(f"/api/exams/{uuid4()}/roster", headers=auth)
    assert foreign.status_code == 404, foreign.text


async def test_report_card_uses_actual_period_scale_ranking_and_attendance_including_zero(platform_client):
    client, sessions, data = platform_client
    first, second = data["children"]
    exam = await create(client, data)
    assert (await save(client, data, exam, [{"student_id": str(first.id), "score": 80}, {"student_id": str(second.id), "score": 0}])).status_code == 200
    old = await create(client, data, exam_date="2025-10-20")
    assert (await save(client, data, old, [{"student_id": str(second.id), "score": 80}])).status_code == 200
    async with sessions() as db:
        for index, status in enumerate((AttendanceStatus.ABSENT, AttendanceStatus.ABSENT)):
            db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id,
                class_id=data["classroom"].id, student_id=second.id, attendance_date=date(2026, 10, 20 + index),
                status=status, recorded_by=data["teacher"].id))
        db.add(AttendanceRecord(organization_id=data["org"].id, branch_id=data["branch"].id,
            class_id=data["classroom"].id, student_id=second.id, attendance_date=date(2026, 10, 22),
            status=AttendanceStatus.PRESENT, recorded_by=data["teacher"].id, deleted_at=datetime(2026, 10, 23)))
        await db.commit()
    response = await client.post("/api/exams/report-cards/generate", headers=scope(data), json={
        "student_id": str(second.id), "academic_year": "2026-2027", "semester": "FALL"})
    assert response.status_code == 200, response.text
    card = response.json()["data"]
    assert card["gpa"] == 0 and card["class_rank"] == 2 and card["total_students"] == 2, card
    assert card["attendance_rate"] == 0 and card["generated_by"] == str(data["root"].id), card
    listed = await client.get(f'/api/exams/report-cards/{second.id}', headers=scope(data))
    assert listed.status_code == 200 and listed.json()["data"][0]["gpa"] == 0, listed.text
    empty = await client.post("/api/exams/report-cards/generate", headers=scope(data), json={
        "student_id": str(second.id), "academic_year": "2026-2027", "semester": "SUMMER"})
    assert empty.status_code == 200 and empty.json()["data"]["gpa"] is None and empty.json()["data"]["attendance_rate"] is None, empty.text
    for invalid in ({"academic_year": "2026-2026"}, {"semester": "invalid"}, {"teacher_comments": "x" * 2001}):
        rejected = await client.post("/api/exams/report-cards/generate", headers=scope(data), json={
            "student_id": str(second.id), "academic_year": "2026-2027", "semester": "FALL", **invalid})
        assert rejected.status_code == 422, rejected.text


async def test_parent_sees_only_published_own_cards_and_attendance_requires_its_permission(platform_client):
    from app.domain.entities.exams import ReportCard
    client, sessions, data = platform_client
    child = data["children"][0]
    async with sessions() as db:
        card = ReportCard(student_id=child.id, academic_year="2026-2027", semester="FALL", gpa=0,
            attendance_rate=50, is_published=False, teacher_comments="Yayımlanacak yorum")
        foreign = ReportCard(student_id=data["stranger"].id, academic_year="2026-2027", semester="FALL", is_published=True)
        db.add_all([card, foreign]); await db.commit()
    auth = headers(data["user"])
    path = f"/api/parent/child/{child.id}/report-cards"
    draft = await client.get(path, headers=auth)
    assert draft.status_code == 200 and draft.json()["data"]["items"] == [], draft.text
    published = await client.put(f"/api/exams/report-cards/{card.id}/publish", headers=scope(data))
    assert published.status_code == 200, published.text
    visible = await client.get(path, headers=auth)
    assert visible.status_code == 200, visible.text
    rows = visible.json()["data"]["items"]
    assert len(rows) == 1 and rows[0]["gpa"] == 0 and rows[0]["attendance_rate"] is None, rows
    assert rows[0]["teacher_comments"] == "Yayımlanacak yorum" and "generated_by" not in rows[0]
    denied = await client.get(f'/api/parent/child/{data["stranger"].id}/report-cards', headers=auth)
    assert denied.status_code in {403, 404}, denied.text


async def test_legacy_nonfinite_scores_are_readable_without_rewriting_the_original_rows(platform_client):
    from decimal import Decimal
    from app.domain.entities.exams import ReportCard
    client, sessions, data = platform_client
    exam = await create(client, data)
    async with sessions() as db:
        invalid = Decimal("NaN") if db.bind.dialect.name == "postgresql" else Decimal("Infinity")
        result = ExamResult(exam_id=UUID(exam["id"]), student_id=data["children"][0].id, score=invalid)
        card = ReportCard(student_id=data["children"][0].id, academic_year="2026-2027", semester="FALL", gpa=invalid, attendance_rate=invalid)
        db.add_all([result, card]); await db.commit()
    for path in (f'/api/exams/{exam["id"]}/results', f'/api/exams/{exam["id"]}/roster', f'/api/exams/report-cards/{data["children"][0].id}'):
        response = await client.get(path, headers=scope(data))
        assert response.status_code == 200, response.text
        payload = response.json()["data"]
        rows = payload["items"] if isinstance(payload, dict) else payload
        row = rows[0]
        assert row.get("score") is None and row.get("gpa") is None and row.get("attendance_rate") is None, row
    async with sessions() as db:
        assert not (await db.get(ExamResult, result.id)).score.is_finite()
