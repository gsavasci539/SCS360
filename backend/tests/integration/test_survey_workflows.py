import asyncio
import pytest
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from app.infrastructure.models.models import UserRole

from test_material_files import materials_client, headers  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.dates import school_today
from app.domain.entities.surveys import Survey, SurveyParticipation, SurveyQuestion, SurveyResponse
from app.infrastructure.models.models import Permission, Role, RolePermission, User


async def setup(client, sessions, data, *, grant_parent=True, anonymous=False, audience="PARENTS"):
    async with sessions() as db:
        manager = User(organization_id=data["org"].id, first_name="Survey", last_name="Manager", email="manager@survey.invalid", password_hash="unused",
            roles=[Role(name="Survey manager", slug="org_admin", organization_id=data["org"].id,
                permissions=[Permission(code=code, name=code, module="surveys") for code in ("surveys.read", "surveys.write")])])
        db.add(manager)
        if grant_parent:
            permission = Permission(code="parent.respond_survey", name="Survey participation", module="parent")
            db.add(permission); await db.flush()
            role = (await db.execute(select(Role).where(Role.slug == "parent"))).scalar_one()
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        await db.commit()
    payload = {"title": "Veli geri bildirimi", "description": "Gerçek sorular", "start_date": str(school_today()),
        "end_date": str(school_today() + timedelta(days=7)), "is_anonymous": anonymous, "target_audience": audience}
    response = await client.post("/api/surveys/surveys", headers=headers(manager), json=payload)
    assert response.status_code == 200, response.text
    survey = response.json()["data"]
    questions = []
    for kind, options in (("RATING", None), ("MULTIPLE_CHOICE", ["Evet", "Hayır"]), ("TEXT", None)):
        response = await client.post("/api/surveys/questions", headers=headers(manager), json={"survey_id": survey["id"], "question_text": "Soru " + kind, "question_type": kind, "options": options, "is_required": kind != "TEXT"})
        assert response.status_code == 200, response.text
        questions.append(response.json()["data"])
    return manager, survey, questions, payload


def parent_path(data, survey):
    return f'/api/parent/child/{data["children"][0].id}/surveys/{survey["id"]}/respond'


async def publish(client, manager, survey):
    response = await client.post(f'/api/surveys/surveys/{survey["id"]}/publish', headers=headers(manager))
    assert response.status_code == 200, response.text


async def test_survey_publish_validation_freeze_and_real_results(materials_client):
    client, sessions, data = materials_client
    manager, survey, questions, payload = await setup(client, sessions, data)
    assert (await client.post("/api/surveys/surveys", headers=headers(manager), json={**payload, "end_date": str(school_today() - timedelta(days=1))})).status_code == 422
    assert (await client.post("/api/surveys/questions", headers=headers(manager), json={"survey_id": survey["id"], "question_text": "Bad choice", "question_type": "MULTIPLE_CHOICE", "options": ["Same", "Same"]})).status_code == 422
    await publish(client, manager, survey)
    assert (await client.put(f'/api/surveys/surveys/{survey["id"]}', headers=headers(manager), json={**payload, "is_anonymous": True})).status_code == 409
    assert (await client.delete("/api/surveys/questions/" + questions[0]["id"], headers=headers(manager))).status_code == 409
    values = {questions[0]["id"]: 4, questions[1]["id"]: "Evet", questions[2]["id"]: "Faydalı etkinlik"}
    response = await client.post(parent_path(data, survey), headers=headers(data["user"]), json={"response_data": values})
    assert response.status_code == 200, response.text
    listing = (await client.get("/api/surveys/responses", headers=headers(manager))).json()["data"]
    assert listing[0]["survey_title"] == payload["title"] and listing[0]["respondent_name"] == "Parent Test"
    assert listing[0]["answers"][0]["question_text"].startswith("Soru")
    assert "ip_address" not in listing[0]
    results = (await client.get(f'/api/surveys/surveys/{survey["id"]}/results', headers=headers(manager))).json()["data"]
    rating = next(item for item in results["question_results"] if item["question_type"] == "RATING")
    assert rating["average_rating"] == 4 and results["total_responses"] == 1
    summary = (await client.get("/api/surveys/summary", headers=headers(manager))).json()["data"]
    assert summary["total_surveys"] == 1 and summary["total_responses"] == 1
    assert (await client.get("/api/ai/surveys-analysis", headers=headers(manager))).json()["data"] == summary


async def test_survey_answers_are_validated_and_simultaneous_participation_is_single(materials_client):
    client, sessions, data = materials_client
    manager, survey, questions, _ = await setup(client, sessions, data, anonymous=True)
    await publish(client, manager, survey)
    path = parent_path(data, survey)
    values = {questions[0]["id"]: 5, questions[1]["id"]: "Evet"}
    for invalid in ({}, {**values, str(uuid4()): "Foreign question"}, {**values, questions[0]["id"]: True},
                    {**values, questions[0]["id"]: "NaN"}, {**values, questions[0]["id"]: 99999999999999999999999999999},
                    {**values, questions[1]["id"]: {"option": "Evet"}}):
        response = await client.post(path, headers=headers(data["user"]), json={"response_data": invalid})
        assert response.status_code == 422, response.text
    responses = await asyncio.gather(*[client.post(path, headers=headers(data["user"]), json={"response_data": values}) for _ in range(2)])
    assert sorted(response.status_code for response in responses) == [200, 409], [response.text for response in responses]
    async with sessions() as db:
        record = (await db.execute(select(SurveyResponse))).scalar_one()
        assert record.respondent_id is None and record.ip_address is None
        assert (await db.execute(select(func.count(SurveyParticipation.id)))).scalar() == 1
    own = (await client.get(path.rsplit("/", 2)[0], headers=headers(data["user"]))).json()["data"]
    assert own[0]["submitted"] is True


async def test_parent_survey_permissions_audience_dates_and_child_scope(materials_client):
    client, sessions, data = materials_client
    manager, survey, questions, _ = await setup(client, sessions, data, grant_parent=False, audience="STAFF")
    await publish(client, manager, survey)
    path = parent_path(data, survey)
    assert (await client.get(path.rsplit("/", 2)[0], headers=headers(data["user"]))).json()["data"] == []
    assert (await client.post(path, headers=headers(data["user"]), json={"response_data": {}})).status_code == 403
    assert (await client.get("/api/surveys/responses", headers=headers(data["user"]))).status_code == 403
    assert (await client.get(f'/api/parent/child/{data["stranger"].id}/surveys', headers=headers(data["user"]))).status_code == 403
    async with sessions() as db:
        permission = Permission(code="parent.respond_survey", name="Respond", module="parent")
        db.add(permission); await db.flush()
        role = (await db.execute(select(Role).where(Role.slug == "parent"))).scalar_one()
        db.add(RolePermission(role_id=role.id, permission_id=permission.id)); await db.commit()
    assert (await client.post(path, headers=headers(data["user"]), json={"response_data": {}})).status_code == 404
    async with sessions() as db:
        row = (await db.execute(select(Survey))).scalar_one()
        row.target_audience = "PARENTS"; row.start_date = school_today() + timedelta(days=1); await db.commit()
    assert (await client.post(path, headers=headers(data["user"]), json={"response_data": {}})).status_code == 409


async def test_legacy_anonymous_identity_and_invalid_values_never_leak_or_crash(materials_client):
    client, sessions, data = materials_client
    manager, survey, questions, _ = await setup(client, sessions, data, anonymous=True)
    async with sessions() as db:
        db.add(SurveyResponse(survey_id=UUID(survey["id"]), respondent_id=data["user"].id,
            response_data={questions[0]["id"]: "NaN", questions[1]["id"]: {"unhashable": True}}, ip_address="127.0.0.1"))
        await db.commit()
    response = await client.get("/api/surveys/responses", headers=headers(manager))
    assert response.status_code == 200, response.text
    record = response.json()["data"][0]
    assert record["respondent_id"] is None and record["respondent_name"] is None and "ip_address" not in record
    filtered = await client.get("/api/surveys/responses", headers=headers(manager), params={"respondent_id": str(data["user"].id)})
    assert filtered.json()["data"] == []
    results = await client.get(f'/api/surveys/surveys/{survey["id"]}/results', headers=headers(manager))
    assert results.status_code == 200, results.text
    assert all(item["response_count"] == 0 for item in results.json()["data"]["question_results"])
    assert sum(item["invalid_count"] for item in results.json()["data"]["question_results"]) == 2
    assert (await client.get(f'/api/surveys/surveys/{uuid4()}/results', headers=headers(manager))).status_code == 404


async def test_staff_can_participate_without_management_or_parent_permissions(materials_client):
    client, sessions, data = materials_client
    manager, survey, questions, _ = await setup(client, sessions, data, audience="STAFF")
    await publish(client, manager, survey)
    async with sessions() as db:
        permission = Permission(code="surveys.respond", name="Staff participation", module="surveys")
        db.add(permission); await db.flush()
        role_id = (await db.execute(select(UserRole.role_id).where(UserRole.user_id == data["teacher"].id))).scalar_one()
        db.add(RolePermission(role_id=role_id, permission_id=permission.id)); await db.commit()
    listing = await client.get("/api/surveys/my-surveys", headers=headers(data["teacher"]))
    assert listing.status_code == 200 and listing.json()["data"][0]["id"] == survey["id"], listing.text
    assert (await client.get("/api/surveys/responses", headers=headers(data["teacher"]))).status_code == 403
    assert (await client.post("/api/surveys/responses", headers=headers(data["teacher"]), json={"survey_id": survey["id"], "response_data": {questions[0]["id"]: 3, questions[1]["id"]: "Hayır"}})).status_code == 200
    assert (await client.get("/api/surveys/my-surveys", headers=headers(data["teacher"]))).json()["data"][0]["submitted"] is True
    assert (await client.get("/api/surveys/my-surveys", headers=headers(data["user"]))).status_code == 403


async def test_legacy_nonfinite_sqlite_answers_are_flagged_without_rewriting_data(materials_client):
    client, sessions, data = materials_client
    manager, survey, questions, _ = await setup(client, sessions, data)
    if sessions.kw["bind"].dialect.name != "sqlite":
        async with sessions() as db:
            db.add(SurveyResponse(survey_id=UUID(survey["id"]), response_data={questions[0]["id"]: float("nan")}))
            with pytest.raises(DBAPIError):
                await db.commit()
            await db.rollback()
        return
    async with sessions() as db:
        db.add(SurveyResponse(survey_id=UUID(survey["id"]), response_data={questions[0]["id"]: float("nan")}))
        await db.commit()
    response = await client.get("/api/surveys/responses", headers=headers(manager))
    assert response.status_code == 200, response.text
    assert response.json()["data"][0]["response_data"][questions[0]["id"]] is None
    async with sessions() as db:
        from math import isnan
        assert isnan((await db.execute(select(SurveyResponse))).scalar_one().response_data[questions[0]["id"]])
