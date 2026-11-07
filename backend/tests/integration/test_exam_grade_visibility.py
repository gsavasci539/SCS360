from app.core.dates import school_today
from app.application.services.chatbot.intent_schemas import ChatbotIntent
from test_saas_platform import platform_client  # noqa: F401
from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401


async def test_real_exam_results_reach_parent_student_insights_chatbot_and_school_summary(platform_client, monkeypatch):
    from app.routers import chatbot
    async def intent(query, context):
        return ChatbotIntent(intent="GRADES", confidence=1)
    monkeypatch.setattr(chatbot.intent_service, "detect_intent_with_fallback", intent)
    client, sessions, data = platform_client
    root = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    exam = await client.post("/api/exams", headers=root, json={"class_id": str(data["classroom"].id),
        "title": "Gerçek Matematik Sınavı", "exam_type": "QUIZ", "exam_date": school_today().isoformat(), "max_score": 80})
    assert exam.status_code == 200, exam.text
    saved = await client.post("/api/exams/bulk-grade-entry", headers=root, json={"exam_id": exam.json()["data"]["id"],
        "grades": [{"student_id": str(child.id), "score": score} for child, score in zip(data["children"], [40, 0])]})
    assert saved.status_code == 200, saved.text
    parent = headers(data["user"]); child = data["children"][0]
    grades = await client.get(f"/api/parent/child/{child.id}/grades", headers=parent)
    assert grades.status_code == 200 and len(grades.json()["data"]) == 1, grades.text
    assert grades.json()["data"][0]["score"] == 40 and grades.json()["data"][0]["max_score"] == 80
    insights = await client.get(f"/api/parent/child/{child.id}/insights", headers=parent, params={"context": "academic"})
    assert insights.status_code == 200 and insights.json()["data"]["current_average"] == 50, insights.text
    answer = await client.post("/api/v1/chatbot/process-query", headers=parent, json={"query": "Notları göster", "role": "parent", "student_id": str(child.id)})
    assert answer.status_code == 200 and "Gerçek Matematik Sınavı" in answer.json()["data"]["response_markdown"], answer.text
    summary = await client.get("/api/ai/ai-academic-predictions", headers=root)
    assert summary.status_code == 200 and summary.json()["data"]["total_analyzed"] == 2, summary.text
    assert sorted(row["current_average"] for row in summary.json()["data"]["risk_students"]) == [0, 50]
    performance = await client.get("/api/ai/academic-performance", headers=root)
    assert performance.status_code == 200 and performance.json()["data"]["average_grade"] == 25, performance.text
    for student in data["children"]:
        moved = await client.put(f"/api/students/{student.id}", headers=root, json={"class_id": str(data["other_class"].id)})
        assert moved.status_code == 200, moved.text
    history = await client.get(f"/api/parent/child/{child.id}/grades", headers=parent)
    assert history.status_code == 200 and len(history.json()["data"]) == 1, history.text
    assert (await client.get(f'/api/parent/child/{data["stranger"].id}/grades', headers=parent)).status_code in {403, 404}


async def test_corrupt_foreign_exam_or_legacy_class_links_never_enter_own_child_records(platform_client):
    from app.domain.entities.exams import Exam, ExamResult
    from app.infrastructure.models.models import ClassRoom, Grade, GradeType, SubjectType
    client, sessions, data = platform_client
    async with sessions() as db:
        foreign = ClassRoom(organization_id=data["stranger"].organization_id, branch_id=data["other_branch"].id, name="Foreign class")
        db.add(foreign); await db.flush()
        exam = Exam(class_id=foreign.id, title="Foreign private exam", exam_type="QUIZ", exam_date=school_today(), max_score=100)
        db.add(exam); await db.flush()
        db.add(ExamResult(exam_id=exam.id, student_id=data["children"][0].id, score=80))
        db.add(Grade(organization_id=data["org"].id, branch_id=data["branch"].id, class_id=foreign.id,
            student_id=data["children"][0].id, subject=SubjectType.MATHEMATICS, grade_type=GradeType.EXAM, score=80, max_score=100, exam_date=school_today()))
        await db.commit()
    result = await client.get(f'/api/parent/child/{data["children"][0].id}/grades', headers=headers(data["user"]))
    assert result.status_code == 200 and result.json()["data"] == [], result.text
    scoped = {**headers(data["root"]), "X-SCS360-Organization-Id": str(data["org"].id)}
    result = await client.get("/api/ai/ai-academic-predictions", headers=scoped)
    assert result.status_code == 200 and result.json()["data"]["total_analyzed"] == 0, result.text
    assert "Foreign private exam" not in result.text
