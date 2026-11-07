from datetime import date

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.domain.entities.surveys import Survey, SurveyQuestion, SurveyResponse
from app.domain.entities.consents import ConsentDocument
from app.infrastructure.models.models import Permission, Role, User


async def test_survey_and_consent_owners_questions_and_responses_are_tenant_scoped(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        role = Role(name="Forms", slug="org_admin", organization_id=data["org"].id,
            permissions=[Permission(code=code, name=code, module="forms") for code in ("survey.read", "survey.write", "consent.read", "consent.write")])
        manager = User(organization_id=data["org"].id, first_name="Forms", last_name="Manager", email="forms@example.com", password_hash="unused", roles=[role])
        foreign = User(organization_id=data["stranger"].organization_id, first_name="Foreign", last_name="Owner", email="other@forms.example.com", password_hash="unused")
        db.add_all([manager, foreign]); await db.flush()
        survey = Survey(organization_id=foreign.organization_id, title="Foreign private survey", start_date=date(2026, 1, 1), end_date=date(2030, 1, 1), created_by=foreign.id)
        document = ConsentDocument(organization_id=foreign.organization_id, title="Foreign private document", document_type="TEST", effective_date=date(2026, 1, 1), created_by=foreign.id)
        db.add_all([survey, document]); await db.flush()
        db.add_all([SurveyQuestion(survey_id=survey.id, question_text="Private foreign question", question_type="TEXT"),
            SurveyResponse(survey_id=survey.id, response_data={"private": "Private foreign answer"})])
        await db.commit()
    headers = {"Authorization": "Bearer " + create_access_token(manager.id)}
    for path in ("/api/surveys/surveys", "/api/surveys/questions", "/api/surveys/responses", "/api/consents/documents"):
        response = await client.get(path, headers=headers)
        assert response.status_code == 200 and response.json()["data"] == [], response.text
    denied = await client.post("/api/surveys/questions", headers=headers,
        json={"survey_id": str(survey.id), "question_text": "Unauthorized", "question_type": "TEXT"})
    assert denied.status_code in {403, 404}, denied.text
    own = await client.post("/api/surveys/surveys", headers=headers,
        json={"title": "Own survey", "start_date": "2026-01-01", "end_date": "2030-01-01"})
    assert own.status_code == 200, own.text
    document = await client.post("/api/consents/documents", headers=headers,
        json={"title": "Own document", "document_type": "TEST", "content": "Test", "effective_date": "2026-11-03"})
    assert document.status_code == 200, document.text
    for path in ("/api/surveys/surveys", "/api/consents/documents"):
        rows = (await client.get(path, headers=headers)).json()["data"]
        assert len(rows) == 1 and rows[0]["title"].startswith("Own")
