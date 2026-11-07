import asyncio
from datetime import date
from uuid import UUID

import pytest
from sqlalchemy import select

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.core.security import create_access_token
from app.domain.entities.clubs import ClubEvent, ClubMembership, SchoolClub, StudentCertificate
from app.infrastructure.models.models import Permission, Role, User


async def test_club_pagination_is_stable_searchable_and_avoids_per_row_queries(clubs_client):
    from sqlalchemy import event
    client, sessions, data = clubs_client
    async with sessions() as db:
        clubs = [SchoolClub(branch_id=data["branch"].id, club_name=f"Kulüp {index:03}",
            advisor_teacher_id=data["teacher"].id) for index in range(30)]
        db.add_all(clubs)
        await db.flush()
        db.add_all([ClubEvent(club_id=club.id, event_name=f"Sergi {index:03}", event_date=date(2027, 1, 1)) for index, club in enumerate(clubs)])
        db.add_all([StudentCertificate(student_id=data["children"][0].id, title=f"Belge {index:03}",
            certificate_type="PARTICIPATION", issue_date=date(2026, 11, 3), issued_by=data["manager"].id) for index in range(30)])
        await db.commit()
    headers = auth(data["manager"])
    engine = sessions.kw["bind"].sync_engine
    statements = []
    def record(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)
    event.listen(engine, "before_cursor_execute", record)
    try:
        response = await client.get("/api/clubs", headers=headers, params={"limit": 25})
        assert response.status_code == 200 and len(response.json()["data"]) == 25
        assert len(statements) < 15, len(statements)
        assert response.json()["data"][0]["advisor_name"] == "Teacher Test"
    finally:
        event.remove(engine, "before_cursor_execute", record)
    for path in ("/api/clubs", "/api/clubs/events", "/api/clubs/certificates",
        f'/api/parent/child/{data["children"][0].id}/certificates'):
        actor = auth(data["user"]) if "/parent/" in path else headers
        first = (await client.get(path, headers=actor, params={"limit": 20})).json()["data"]
        second = (await client.get(path, headers=actor, params={"limit": 20, "offset": 20})).json()["data"]
        assert len(first) == 20 and len(second) == 10
        assert len({row["id"] for row in first + second}) == 30
    for path, field in (("/api/clubs", "club_name"), ("/api/clubs/events", "event_name")):
        rows = (await client.get(path, headers=headers, params={"search": "025"})).json()["data"]
        assert len(rows) == 1 and rows[0][field].endswith("025")


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


@pytest.fixture
async def clubs_client(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        permissions = [Permission(code=code, name=code, module="clubs") for code in ("clubs.read", "clubs.write")]
        role = Role(name="Club manager", slug="org_admin", organization_id=data["org"].id, permissions=permissions)
        manager = User(organization_id=data["org"].id, first_name="Manager", last_name="Club", password_hash="unused",
            email="clubs@test.invalid", roles=[role])
        foreign_club = SchoolClub(branch_id=data["other_branch"].id, club_name="Foreign club")
        db.add_all([manager, foreign_club])
        await db.flush()
        foreign_event = ClubEvent(club_id=foreign_club.id, event_name="Foreign private event", event_date=date.today())
        db.add(foreign_event)
        await db.commit()
    yield client, sessions, {**data, "manager": manager, "foreign_club": foreign_club, "foreign_event": foreign_event}


async def make_club(client, data, capacity=1):
    body = {"branch_id": str(data["branch"].id), "club_name": "Sanat atölyesi", "max_members": capacity,
        "advisor_teacher_id": str(data["teacher"].id)}
    response = await client.post("/api/clubs/clubs", headers=auth(data["manager"]), json=body)
    assert response.status_code == 200, response.text
    return response.json()["data"], body


async def enroll(client, data, club_id, student):
    return await client.post("/api/clubs/memberships", headers=auth(data["manager"]),
        json={"club_id": club_id, "student_id": str(student.id)})


async def test_club_capacity_enrollment_reactivation_and_real_member_counts(clubs_client):
    client, sessions, data = clubs_client
    club, body = await make_club(client, data)
    first = await enroll(client, data, club["id"], data["children"][0])
    assert first.status_code == 200, first.text
    assert (await enroll(client, data, club["id"], data["children"][0])).status_code == 200
    assert (await enroll(client, data, club["id"], data["children"][1])).status_code == 409
    assert (await client.get("/api/clubs", headers=auth(data["manager"]))).json()["data"][0]["current_members"] == 1
    left = await client.delete('/api/clubs/memberships/' + first.json()["data"]["id"], headers=auth(data["manager"]))
    assert left.status_code == 200, left.text
    assert (await enroll(client, data, club["id"], data["children"][1])).status_code == 200
    async with sessions() as db:
        rows = (await db.execute(select(ClubMembership).where(ClubMembership.club_id == UUID(club["id"])))) .scalars().all()
        assert len(rows) == 2 and sum(row.status == "ACTIVE" for row in rows) == 1
        assert all(row.joined_date is not None for row in rows)
    another, another_body = await make_club(client, data, 2)
    invalid_advisor = await client.put('/api/clubs/clubs/' + another["id"], headers=auth(data["manager"]),
        json={**another_body, "advisor_teacher_id": str(data["user"].id)})
    assert invalid_advisor.status_code == 422
    for student in data["children"]:
        assert (await enroll(client, data, another["id"], student)).status_code == 200
    response = await client.put('/api/clubs/clubs/' + another["id"], headers=auth(data["manager"]), json={**another_body, "max_members": 1})
    assert response.status_code == 422


async def test_concurrent_enrollment_cannot_exceed_capacity_or_duplicate_a_member(clubs_client):
    client, sessions, data = clubs_client
    club, _ = await make_club(client, data)
    responses = await asyncio.gather(*[enroll(client, data, club["id"], student) for student in data["children"]])
    assert sorted(row.status_code for row in responses) == [200, 409], [row.text for row in responses]
    club, _ = await make_club(client, data, 2)
    responses = await asyncio.gather(*[enroll(client, data, club["id"], data["children"][0]) for _ in range(2)])
    assert [row.status_code for row in responses] == [200, 200], [row.text for row in responses]
    async with sessions() as db:
        assert len((await db.execute(select(ClubMembership).where(ClubMembership.club_id == UUID(club["id"])))) .scalars().all()) == 1


async def test_club_events_do_not_leak_across_institutions_and_certificates_return_real_pdf(clubs_client):
    client, sessions, data = clubs_client
    response = await client.get("/api/clubs/events", headers=auth(data["manager"]))
    assert response.status_code == 200 and response.json()["data"] == []
    response = await client.post("/api/clubs/events", headers=auth(data["manager"]),
        json={"club_id": str(data["foreign_club"].id), "event_name": "Unauthorized", "event_date": "2027-01-01"})
    assert response.status_code == 404
    club, _ = await make_club(client, data)
    event = await client.post("/api/clubs/events", headers=auth(data["manager"]),
        json={"club_id": club["id"], "event_name": "Sanat sergisi", "event_date": "2027-01-01"})
    assert event.status_code == 200, event.text
    body = {"student_id": str(data["children"][0].id), "title": "Sanat atölyesi katılım belgesi",
        "certificate_type": "PARTICIPATION", "description": "Yaratıcı çalışmalarını tamamladı.", "event_id": event.json()["data"]["id"]}
    assert (await client.post("/api/clubs/certificates", headers=auth(data["manager"]), json=body)).status_code == 422
    assert (await enroll(client, data, club["id"], data["children"][0])).status_code == 200
    awarded = await client.post("/api/clubs/certificates", headers=auth(data["manager"]), json=body)
    assert awarded.status_code == 200, awarded.text
    result = awarded.json()["data"]
    downloaded = await client.get(result["pdf_url"], headers=auth(data["manager"]))
    assert downloaded.status_code == 200 and downloaded.content.startswith(b"%PDF-"), downloaded.text[:100]
    assert downloaded.headers["cache-control"] == "private, no-store"
    assert (await client.get(result["pdf_url"])).status_code == 401
    parent_path = f'/api/parent/child/{data["children"][0].id}/certificates'
    parent_list = await client.get(parent_path, headers=auth(data["user"]))
    assert parent_list.status_code == 200 and parent_list.json()["data"][0]["id"] == result["id"]
    assert (await client.get(parent_list.json()["data"][0]["pdf_url"], headers=auth(data["user"]))).status_code == 200
    wrong_child = f'/api/parent/child/{data["children"][1].id}/certificates/{result["id"]}/pdf'
    assert (await client.get(wrong_child, headers=auth(data["user"]))).status_code == 404
    async with sessions() as db:
        record = await db.get(StudentCertificate, UUID(result["id"]))
        assert record.issue_date is not None and record.issued_by == data["manager"].id


async def test_club_options_and_statistics_match_scoped_database_records(clubs_client):
    client, sessions, data = clubs_client
    metadata = await client.get("/api/clubs/options", headers=auth(data["manager"]),
        params={"branch_id": str(data["branch"].id), "search": "Child0"})
    assert metadata.status_code == 200, metadata.text
    result = metadata.json()["data"]
    assert len(result["students"]) == 1 and result["students"][0]["id"] == str(data["children"][0].id)
    assert result["student_count"] == 1 and len(result["branches"]) == 1
    assert result["teachers"][0]["id"] == str(data["teacher"].id)
    assert (await client.get("/api/clubs/options", headers=auth(data["user"]))).status_code == 403
    club, _ = await make_club(client, data, 2)
    for student in data["children"]:
        assert (await enroll(client, data, club["id"], student)).status_code == 200
    event = await client.post("/api/clubs/events", headers=auth(data["manager"]),
        json={"club_id": club["id"], "event_name": "Upcoming", "event_date": "2027-01-01"})
    assert event.status_code == 200
    stats = await client.get("/api/ai/clubs-analysis", headers=auth(data["manager"]))
    assert stats.status_code == 200, stats.text
    result = stats.json()["data"]
    assert result["total_clubs"] == 1 and result["active_clubs"] == 1
    assert result["total_members"] == 2 and result["upcoming_events"] == 1
    assert result["source"] == "DATABASE_AND_RULES"
