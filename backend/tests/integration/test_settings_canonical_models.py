"""Registered settings preserve JSON/permissions on fresh and legacy physical layouts."""
from uuid import UUID

import pytest
from sqlalchemy import inspect, select, text
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401

from app.core.security import create_access_token
from app.domain.entities.app_setting import AppSetting as ExportedAppSetting
from app.domain.entities.integration_setting import IntegrationSetting as ExportedIntegrationSetting
from app.infrastructure.models.models import AppSetting, IntegrationSetting, Permission, Role, User


@pytest.fixture
async def settings_client(materials_client):  # noqa: F811 - imported pytest fixture injection
    client, sessions, data = materials_client
    async with sessions() as db:
        read = Permission(code="settings.read", name="Read settings", module="settings")
        write = Permission(code="settings.write", name="Write settings", module="settings")
        writer_role = Role(name="Settings writer", slug="settings_writer", organization_id=data["org"].id, permissions=[read, write])
        reader_role = Role(name="Settings reader", slug="settings_reader", organization_id=data["org"].id, permissions=[read])
        foreign_role = Role(name="Other school settings", slug="settings_writer", organization_id=data["stranger"].organization_id, permissions=[read, write])
        people = {
            "writer": User(organization_id=data["org"].id, first_name="Settings", last_name="Writer", email="settings-writer@test.invalid", password_hash="unused", roles=[writer_role]),
            "reader": User(organization_id=data["org"].id, first_name="Settings", last_name="Reader", email="settings-reader@test.invalid", password_hash="unused", roles=[reader_role]),
            "foreign_writer": User(organization_id=data["stranger"].organization_id, first_name="Other", last_name="Writer", email="other-settings@test.invalid", password_hash="unused", roles=[foreign_role]),
        }
        db.add_all(people.values())
        await db.commit()
    return client, sessions, data | people


def auth(user):
    return {"Authorization": "Bearer " + create_access_token(user.id)}


async def test_domain_exports_canonical_identity_and_fresh_schema_has_no_shadow_fields(settings_client):
    _, sessions, _ = settings_client
    assert ExportedAppSetting is AppSetting
    assert ExportedIntegrationSetting is IntegrationSetting
    async with sessions() as db:
        for model, shadow in ((AppSetting, {"key", "value"}),
            (IntegrationSetting, {"integration_type", "provider_name", "settings"})):
            columns = await db.run_sync(lambda session, name=model.__tablename__: {value["name"] for value in inspect(session.connection()).get_columns(name)})
            assert not shadow & columns
            assert not shadow & set(model.__table__.c.keys())


async def test_registered_settings_roundtrip_json_and_native_read_write_institution_guards(settings_client):
    client, _, data = settings_client
    payload = {"nested": {"text": "Türkçe", "flags": [True, False, None], "amount": "25.00"}, "zero": 0, "disabled": False}
    saved = await client.put("/api/settings", headers=auth(data["writer"]), json=payload)
    assert saved.status_code == 200, saved.text
    assert (await client.get("/api/settings", headers=auth(data["reader"]))).json()["data"] == payload
    assert (await client.put("/api/settings", headers=auth(data["reader"]), json={"zero": 99})).status_code == 403
    assert (await client.get("/api/settings", headers=auth(data["user"]))).status_code == 403
    other = await client.put("/api/settings", headers=auth(data["foreign_writer"]), json={"other_school_only": "separate"})
    assert other.status_code == 200, other.text
    assert (await client.get("/api/settings", headers=auth(data["writer"]))).json()["data"] == payload
    assert (await client.get("/api/settings", headers=auth(data["foreign_writer"]))).json()["data"] == {"other_school_only": "separate"}


async def test_registered_integration_config_persists_types_masks_secrets_and_denies_writes(settings_client):
    client, sessions, data = settings_client
    config = {"host": "smtp.example.invalid", "port": 587, "options": {"enabled": False, "labels": ["test", None]},
        "password": "placeholder-password", "api_key": "placeholder-api-key", "access_token": "placeholder-token", "client_secret": "placeholder-secret"}
    saved = await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "config": config, "is_active": False})
    assert saved.status_code == 200, saved.text
    reply = await client.get("/api/settings/integrations", headers=auth(data["reader"]))
    assert reply.status_code == 200, reply.text
    rows = reply.json()["data"]
    assert len(rows) == 1 and rows[0]["provider"] == "SMTP" and rows[0]["is_active"] is False
    assert rows[0]["config"] == config | {key: "***" for key in ("password", "api_key", "access_token", "client_secret")}
    assert (await client.put("/api/settings/integrations", headers=auth(data["reader"]), json={"provider": "SMTP", "config": {}})).status_code == 403
    assert (await client.get("/api/settings/integrations", headers=auth(data["user"]))).status_code == 403
    assert (await client.get("/api/settings/integrations", headers=auth(data["foreign_writer"]))).json()["data"] == []
    async with sessions() as db:
        stored = (await db.execute(select(IntegrationSetting))).scalar_one()
        assert stored.config == config and stored.organization_id == data["org"].id


async def test_existing_legacy_column_layout_updates_preserve_ids_json_and_single_rows(settings_client):
    client, sessions, data = settings_client
    setting_id = UUID("d9999999-0000-4000-8000-000000000001")
    integration_id = UUID("d9999999-0000-4000-8000-000000000002")
    async with sessions() as db:
        # Disposable acceptance DB only: reproduce the known old physical layout
        # even when this regression is run against pre-fix polluted metadata.
        for table, shadow in (("app_settings", ("key", "value")),
            ("integration_settings", ("integration_type", "provider_name", "settings"))):
            columns = await db.run_sync(lambda session, name=table: {value["name"] for value in inspect(session.connection()).get_columns(name)})
            for column in shadow:
                if column in columns:
                    await db.execute(text(f'ALTER TABLE "{table}" DROP COLUMN "{column}"'))
        db.add(AppSetting(id=setting_id, organization_id=data["org"].id, setting_key="legacy", setting_value={"numbers": [0, 1], "active": False}))
        db.add(IntegrationSetting(id=integration_id, organization_id=data["org"].id, provider="SMTP", config={"port": 25}, is_active=False))
        await db.commit()
    assert (await client.get("/api/settings", headers=auth(data["writer"]))).json()["data"] == {"legacy": {"numbers": [0, 1], "active": False}}
    updated = await client.put("/api/settings", headers=auth(data["writer"]), json={"legacy": {"numbers": [0, 1, 2], "active": True}})
    assert updated.status_code == 200, updated.text
    integrated = await client.put("/api/settings/integrations", headers=auth(data["writer"]), json={"provider": "SMTP", "config": {"port": 587}, "is_active": False})
    assert integrated.status_code == 200, integrated.text
    async with sessions() as db:
        settings = (await db.execute(select(AppSetting))).scalars().all()
        integrations = (await db.execute(select(IntegrationSetting))).scalars().all()
        assert len(settings) == len(integrations) == 1
        assert settings[0].id == setting_id and settings[0].setting_value == {"numbers": [0, 1, 2], "active": True}
        assert integrations[0].id == integration_id and integrations[0].config == {"port": 587}
