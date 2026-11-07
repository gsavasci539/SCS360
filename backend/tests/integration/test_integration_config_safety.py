"""Exercise the registered settings routes on disposable SQLite and PostgreSQL."""
import asyncio

from sqlalchemy import select
from test_material_files import materials_client  # noqa: F401
from test_parent_homework_outbox import portal_db  # noqa: F401
from test_settings_canonical_models import auth, settings_client  # noqa: F401

from app.infrastructure.models.models import IntegrationSetting


async def stored(sessions):
    async with sessions() as db:
        return (await db.execute(select(IntegrationSetting))).scalar_one()


async def test_nested_credentials_are_masked_without_changing_public_json_types(settings_client):
    client, sessions, data = settings_client
    config = {"apiKey": "private-camel-key", "AUTHORIZATION": "private-bearer", "awsAccessKeyId": "private-aws-id",
        "credentials": {"login": "private-login"},
        "options": {"enabled": False, "zero": 0, "labels": [None, "public"],
            "auth": {"clientSecret": "private-client", "private-key": "private-pem"}},
        "accounts": [{"name": "public-name", "accessToken": "private-access", "password": "private-password"}]}
    saved = await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "config": config, "is_active": False})
    assert saved.status_code == 200, saved.text
    response = await client.get("/api/settings/integrations", headers=auth(data["reader"]))
    assert response.status_code == 200, response.text
    assert "private-" not in response.text
    visible = response.json()["data"][0]["config"]
    assert visible["apiKey"] == visible["AUTHORIZATION"] == visible["credentials"] == "***"
    assert visible["awsAccessKeyId"] == "***"
    assert visible["options"] == {"enabled": False, "zero": 0, "labels": [None, "public"], "auth": "***"}
    assert visible["accounts"] == [{"name": "public-name", "accessToken": "***", "password": "***"}]
    assert (await stored(sessions)).config == config
    assert (await client.get("/api/settings/integrations", headers=auth(data["foreign_writer"]))).json()["data"] == []
    assert (await client.put("/api/settings/integrations", headers=auth(data["reader"]),
        json={"provider": "SMTP", "config": {"host": "blocked"}})).status_code == 403
    assert (await client.get("/api/settings/integrations", headers=auth(data["user"]))).status_code == 403


async def test_masked_roundtrip_and_narrow_patch_keep_credentials_options_and_inactive_state(settings_client):
    client, sessions, data = settings_client
    original = {"host": "smtp.example.invalid", "password": "private-pass", "apiKey": "private-api",
        "options": {"clientSecret": "private-nested", "retry": 0, "enabled": False, "note": None},
        "accounts": [{"label": "account", "token": "private-list"}],
        "auth": {"username": "old-user", "password": "private-auth", "options": {"tls": True}},
        "credentials": {"apiKey": "private-credentials", "region": "old-region"}}
    assert (await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "is_active": False, "config": original})).status_code == 200
    view = (await client.get("/api/settings/integrations", headers=auth(data["writer"]))).json()["data"][0]
    assert (await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "config": view["config"]})).status_code == 200
    assert (await stored(sessions)).config == original
    changed = await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "config": {"host": "new.example.invalid", "password": "  ",
            "apiKey": "***", "options": {"clientSecret": "", "retry": 2}}})
    assert changed.status_code == 200, changed.text
    row = await stored(sessions)
    expected = original | {"host": "new.example.invalid", "options": original["options"] | {"retry": 2}}
    assert row.config == expected and row.is_active is False
    updated = await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "config": {"options": {"clientSecret": "replacement-secret"}}})
    assert updated.status_code == 200 and "replacement-secret" not in updated.text
    assert (await stored(sessions)).config["options"]["clientSecret"] == "replacement-secret"
    nested_patch = await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "config": {"auth": {"username": "new-user", "password": "***"},
            "credentials": {"region": "new-region", "apiKey": None}}})
    assert nested_patch.status_code == 200, nested_patch.text
    row = await stored(sessions)
    assert row.config["auth"] == original["auth"] | {"username": "new-user"}
    assert row.config["credentials"] == original["credentials"] | {"region": "new-region"}


async def test_masked_array_edits_and_masks_without_stored_secrets_are_rejected_atomically(settings_client):
    client, sessions, data = settings_client
    original = {"host": "keep.example.invalid", "accounts": [{"name": "one", "token": "private-one"}]}
    assert (await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "config": original})).status_code == 200
    for patch in ({"host": "must-not-save", "accounts": [{"name": "changed", "token": "***"}]},
        {"accounts": [{"name": "one", "token": "***"}, {"token": "***"}]},
        {"newSecret": "***"}, {"accounts": [{"name": "one", "token": ""}]}):
        rejected = await client.put("/api/settings/integrations", headers=auth(data["writer"]),
            json={"provider": "SMTP", "config": patch})
        assert rejected.status_code == 422, rejected.text
        assert (await stored(sessions)).config == original
    rejected_new = await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "TWILIO", "config": {"apiKey": "***"}})
    assert rejected_new.status_code == 422, rejected_new.text


async def test_malformed_legacy_root_requires_review_and_cannot_be_silently_replaced(settings_client):
    client, sessions, data = settings_client
    async with sessions() as db:
        row = IntegrationSetting(organization_id=data["org"].id, provider="SMTP", config={}, is_active=False)
        db.add(row)
        await db.commit()
        identifier = row.id
    for legacy in ([{"apiKey": "legacy-private"}], None, "legacy-private", 42, False):
        async with sessions() as db:
            row = await db.get(IntegrationSetting, identifier)
            row.config = legacy
            await db.commit()
        response = await client.get("/api/settings/integrations", headers=auth(data["reader"]))
        assert response.status_code == 200, response.text
        view = response.json()["data"][0]
        assert view["requires_review"] is True and view["config"] is None
        assert "legacy-private" not in response.text
        rejected = await client.put("/api/settings/integrations", headers=auth(data["writer"]),
            json={"provider": "SMTP", "config": {"host": "must-not-replace"}, "is_active": True})
        assert rejected.status_code == 422, rejected.text
        row = await stored(sessions)
        assert row.config == legacy and row.is_active is False


async def test_invalid_config_and_non_boolean_activation_return_422_without_records(settings_client):
    client, sessions, data = settings_client
    for payload in ({"provider": "SMTP", "config": []}, {"provider": "SMTP", "config": None},
        {"provider": "SMTP", "config": "private-invalid"},
        *({"provider": "SMTP", "config": {}, "is_active": active} for active in (None, "false", 0, 1, [], {}))):
        response = await client.put("/api/settings/integrations", headers=auth(data["writer"]), json=payload)
        assert response.status_code == 422, response.text
        assert "private-invalid" not in response.text
    assert (await client.get("/api/settings/integrations", headers=auth(data["reader"]))).json()["data"] == []
    saved = await client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "config": {"host": "not-activated.example.invalid"}})
    assert saved.status_code == 200, saved.text
    assert (await stored(sessions)).is_active is False


async def test_simultaneous_first_provider_patches_preserve_both_changes_in_one_record(settings_client):
    client, sessions, data = settings_client
    replies = await asyncio.gather(*(client.put("/api/settings/integrations", headers=auth(data["writer"]),
        json={"provider": "SMTP", "config": patch}) for patch in ({"host": "smtp.example.invalid"}, {"port": 2525})))
    assert [reply.status_code for reply in replies] == [200, 200], [reply.text for reply in replies]
    row = await stored(sessions)
    assert row.config == {"host": "smtp.example.invalid", "port": 2525} and row.is_active is False
