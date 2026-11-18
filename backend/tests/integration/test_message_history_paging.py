from datetime import UTC, datetime, timedelta
from uuid import UUID

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.security import create_access_token
from app.infrastructure.models.models import ChatMessage


async def test_history_cursor_uses_timestamp_and_uuid_tiebreaker(materials_client):
    client, sessions, fixture = materials_client
    teacher, parent = fixture["teacher"], fixture["user"]
    now = datetime(2026, 11, 19, 9, tzinfo=UTC)
    older, tied_first, tied_last = (UUID(int=value) for value in (30, 10, 20))
    async with sessions() as db:
        db.add_all([
            ChatMessage(id=key, sender_id=parent.id, recipient_id=teacher.id, sender_role="PARENT",
                        sent_at=stamp, content=str(key.int))
            for key, stamp in [(older, now - timedelta(minutes=1)), (tied_first, now), (tied_last, now)]
        ])
        await db.commit()
    route = f"/api/messages/conversation/{parent.id}"
    auth = {"Authorization": "Bearer " + create_access_token(teacher.id)}
    for cursor, expected in [(None, tied_last), (tied_last, tied_first), (tied_first, older)]:
        params = {"limit": 1}
        if cursor:
            params["before_id"] = str(cursor)
        result = await client.get(route, headers=auth, params=params)
        assert result.status_code == 200, result.text
        assert [row["id"] for row in result.json()["data"]] == [str(expected)]
    result = await client.get(route, headers=auth, params={"before_id": str(older)})
    assert result.status_code == 200 and result.json()["data"] == []
    assert (await client.get(route, headers=auth, params={"before_id": str(UUID(int=99))})).status_code == 404
