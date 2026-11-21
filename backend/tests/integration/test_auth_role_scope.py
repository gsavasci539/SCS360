import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from app.application.services.auth_service import AuthService
from app.core.exceptions import UnauthorizedException
from app.core.security import hash_password, hash_token, verify_access_token
from app.infrastructure.models.models import Branch, PasswordResetToken, Permission, RefreshToken, Role, User, UserBranch, UserRole


async def test_login_refresh_and_me_ignore_deleted_roles_and_foreign_branch_links(materials_client):
    client, sessions, data = materials_client
    async with sessions() as db:
        teacher = await db.get(User, data["teacher"].id)
        teacher.email, teacher.password_hash = "teacher@auth.example.com", hash_password("RoleScope-Test-2026!")
        foreign_branch = await db.get(Branch, data["other_branch"].id)
        deleted_branch = Branch(organization_id=data["org"].id, name="Deleted branch", deleted_at=datetime.now(UTC))
        removed = Role(organization_id=data["org"].id, name="Removed role", slug="removed-role", deleted_at=datetime.now(UTC),
            permissions=[Permission(code="settings.write", name="Removed permission", module="settings")])
        foreign = Role(organization_id=foreign_branch.organization_id, name="Foreign role", slug="foreign-role",
            permissions=[Permission(code="security.write", name="Foreign permission", module="security")])
        db.add_all([removed, foreign, deleted_branch])
        await db.flush()
        db.add_all([UserRole(user_id=teacher.id, role_id=row.id) for row in (removed, foreign)])
        db.add_all([UserBranch(user_id=teacher.id, branch_id=row.id) for row in (data["branch"], foreign_branch, deleted_branch)])
        await db.commit()
    response = await client.post("/api/auth/login", json={"email": "teacher@auth.example.com", "password": "RoleScope-Test-2026!"})
    assert response.status_code == 200, response.text
    session = response.json()["data"]
    assert {row["slug"] for row in session["user"]["roles"]} == {"teacher"}
    assert session["user"]["branch_ids"] == [str(data["branch"].id)]
    assert {"settings.write", "security.write"}.isdisjoint(session["user"]["permissions"])
    claims = verify_access_token(session["access_token"])
    assert {"settings.write", "security.write"}.isdisjoint(claims["permissions"])
    headers = {"Authorization": "Bearer " + session["access_token"]}
    me = await client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["data"]["roles"] == session["user"]["roles"]
    assert me.json()["data"]["branch_ids"] == session["user"]["branch_ids"]
    assert (await client.get("/api/hardware/devices", headers=headers)).status_code == 403
    refreshed = await client.post("/api/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["data"]["user"]["branch_ids"] == session["user"]["branch_ids"]
    assert refreshed.json()["data"]["user"]["permissions"] == session["user"]["permissions"]
    assert {"settings.write", "security.write"}.isdisjoint(verify_access_token(refreshed.json()["data"]["access_token"])["permissions"])
    async with sessions() as db:
        teacher = (await db.execute(select(User).where(User.id == data["teacher"].id))).scalar_one()
        assert teacher.email == "teacher@auth.example.com"


async def test_own_profile_and_password_save_without_changing_scope(materials_client):
    from app.core.security import create_access_token, verify_password

    client, sessions, data = materials_client
    actor = data["teacher"]
    old_password, new_password = "temporary current", "temporary new"
    old_reset, new_reset, refresh = (str(uuid4()) for _ in range(3))
    canonical_email = "profile@auth.example.com"
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    async with sessions() as db:
        user = await db.get(User, actor.id)
        user.password_hash = hash_password(old_password)
        db.add(UserBranch(user_id=actor.id, branch_id=data["branch"].id))
        db.add(PasswordResetToken(user_id=actor.id, token_hash=hash_token(old_reset), expires_at=expires_at))
        db.add(RefreshToken(user_id=actor.id, token_hash=hash_token(refresh), family_id=uuid4(), expires_at=expires_at))
        await db.commit()

    headers = {"Authorization": "Bearer " + create_access_token(actor.id)}
    before = (await client.get("/api/auth/me", headers=headers)).json()["data"]
    profile = {"first_name": " Sample ", "last_name": " Person ", "email": canonical_email.upper(), "phone": " "}
    assert (await client.put("/api/auth/me", headers=headers, json={**profile, "organization_id": str(uuid4())})).status_code == 422
    assert (await client.put("/api/auth/me", headers=headers, json=profile)).status_code == 422
    saved = await client.put("/api/auth/me", headers=headers, json={**profile, "current_password": old_password})
    assert saved.status_code == 200, saved.text
    assert saved.json()["data"] == {"id": str(actor.id), "email": canonical_email}
    current = (await client.get("/api/auth/me", headers=headers)).json()["data"]
    assert (current["first_name"], current["last_name"], current["email"], current["phone"]) == ("Sample", "Person", canonical_email, None)
    for key in ("id", "organization_id", "branch_ids", "roles", "permissions"):
        assert current[key] == before[key]
    assert (await client.post("/api/auth/reset-password", json={"token": old_reset, "new_password": new_password})).status_code == 422

    async with sessions() as db:
        db.add(PasswordResetToken(user_id=actor.id, token_hash=hash_token(new_reset), expires_at=expires_at))
        await db.commit()
    assert (await client.post("/api/auth/change-password", headers=headers, json={
        "current_password": "incorrect", "new_password": new_password,
    })).status_code == 422
    changed = await client.post("/api/auth/change-password", headers=headers, json={
        "current_password": old_password, "new_password": new_password,
    })
    assert changed.status_code == 200, changed.text
    assert changed.json()["data"] == {"id": str(actor.id)}
    assert (await client.post("/api/auth/reset-password", json={"token": new_reset, "new_password": old_password})).status_code == 422
    assert (await client.post("/api/auth/refresh", json={"refresh_token": refresh})).status_code == 401
    async with sessions() as db:
        user = await db.get(User, actor.id)
        assert verify_password(new_password, user.password_hash)
        assert not verify_password(old_password, user.password_hash)


async def test_parallel_refresh_does_not_fork_a_token_family(portal_db):
    sessions, data = portal_db
    secret, family = str(uuid4()), uuid4()
    async with sessions() as db:
        db.add(RefreshToken(user_id=data["teacher"].id, token_hash=hash_token(secret), family_id=family,
            expires_at=datetime.now(UTC) + timedelta(hours=1)))
        await db.commit()
    async def refresh():
        async with sessions() as db:
            try:
                result = await AuthService(db).refresh(secret, None, None)
                await db.commit()
                return result
            except UnauthorizedException:
                return None
    results = await asyncio.gather(refresh(), refresh())
    assert sum(row is not None for row in results) == 1
    async with sessions() as db:
        rows = (await db.execute(select(RefreshToken).where(RefreshToken.family_id == family))).scalars().all()
        assert len(rows) == 2
        assert all(row.revoked_at is not None for row in rows)


async def test_only_stale_branch_links_do_not_expand_access_to_the_whole_organization(materials_client):
    from app.core.security import create_access_token
    client, sessions, data = materials_client
    async with sessions() as db:
        db.add(UserBranch(user_id=data["teacher"].id, branch_id=data["other_branch"].id))
        await db.commit()
    headers = {"Authorization": "Bearer " + create_access_token(data["teacher"].id)}
    response = await client.get("/api/students", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["items"] == []
    assert (await client.get(f'/api/students/{data["children"][0].id}', headers=headers)).status_code == 404
