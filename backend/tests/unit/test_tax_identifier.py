import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from cryptography.fernet import Fernet

from app.core.tax_identifier import decrypt_tax_identifier, tax_identifier_fingerprint
from app.infrastructure.models import models


def test_organization_tax_identifier_column_uses_ciphertext_and_keyed_fingerprint(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(models, "get_settings", lambda: SimpleNamespace(ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY=key))
    value = "  TCKN-SENSITIVE-SENTINEL  "

    organization = models.Organization(name="Acceptance", tax_number=value)

    assert organization.tax_number_ciphertext != value
    assert value.strip() not in organization.tax_number_ciphertext
    assert organization.tax_number == value.strip()
    assert organization.tax_number_fingerprint == tax_identifier_fingerprint(value, key)
    assert organization.tax_number_fingerprint != tax_identifier_fingerprint(value, Fernet.generate_key().decode("ascii"))


def _load_migration():
    path = Path(__file__).parents[2] / "alembic" / "versions" / "041_encrypt_organization_tax_identifiers.py"
    spec = importlib.util.spec_from_file_location("organization_tax_migration_041", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_legacy_schema(connection, values):
    connection.exec_driver_sql("CREATE TABLE organizations (id TEXT PRIMARY KEY, tax_number TEXT)")
    connection.exec_driver_sql("INSERT INTO organizations(id, tax_number) VALUES (?, ?)", values[0])
    if len(values) > 1:
        connection.exec_driver_sql("INSERT INTO organizations(id, tax_number) VALUES (?, ?)", values[1])


def _run_migration(monkeypatch, connection, key):
    migration = _load_migration()
    context = MigrationContext.configure(connection)
    monkeypatch.setattr(migration, "op", Operations(context))
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration, "get_settings", lambda: SimpleNamespace(ORGANIZATION_TAX_NUMBER_ENCRYPTION_KEY=key))
    migration.upgrade()


def test_organization_tax_identifier_migration_encrypts_and_removes_plaintext(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    value = "TCKN-SENSITIVE-SENTINEL"
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        _prepare_legacy_schema(connection, [("org-1", value)])
        _run_migration(monkeypatch, connection, key)
        columns = {column["name"] for column in sa.inspect(connection).get_columns("organizations")}
        assert "tax_number" not in columns
        ciphertext, fingerprint = connection.exec_driver_sql(
            "SELECT tax_number_ciphertext, tax_number_fingerprint FROM organizations WHERE id='org-1'"
        ).one()
        assert value not in ciphertext
        assert decrypt_tax_identifier(ciphertext, key) == value
        assert fingerprint == tax_identifier_fingerprint(value, key)
    engine.dispose()


def test_organization_tax_identifier_migration_aborts_duplicate_fingerprints(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            _prepare_legacy_schema(connection, [("org-1", "same"), ("org-2", " same ")])
            with pytest.raises(RuntimeError, match="Duplicate organization tax identifiers"):
                _run_migration(monkeypatch, connection, key)
    finally:
        engine.dispose()
