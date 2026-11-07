from app.core.security import (
    create_access_token,
    hash_password,
    verify_access_token,
    verify_password,
)


def test_password_hashing():
    hashed = hash_password("Admin123*")
    assert verify_password("Admin123*", hashed)
    assert not verify_password("wrong", hashed)


def test_new_passwords_keep_the_entire_unicode_password_and_old_bcrypt_still_works():
    from passlib.hash import bcrypt
    original = "Ç" * 80 + "ilk-son-ek"
    hashed = hash_password(original)
    assert hashed.startswith("$bcrypt-sha256$")
    assert verify_password(original, hashed)
    assert not verify_password("Ç" * 80 + "farklı-son-ek", hashed)
    legacy = bcrypt.hash("Legacy123!")
    assert verify_password("Legacy123!", legacy)
    assert not verify_password("wrong", legacy)


def test_malformed_password_hash_is_not_an_internal_server_error():
    for value in (None, "", "damaged-hash", "$2b$12$malformed"):
        assert not verify_password("password", value)


def test_password_input_rejects_oversize_before_hashing():
    import pytest
    from pydantic import ValidationError
    from app.application.schemas.auth import LoginRequest, ResetPasswordRequest
    for schema, body in ((LoginRequest, {"email": "user@example.com", "password": "x" * 4097}),
        (ResetPasswordRequest, {"token": "test", "new_password": "x" * 4097})):
        with pytest.raises(ValidationError):
            schema(**body)


def test_access_token_has_expected_type():
    token = create_access_token("00000000-0000-0000-0000-000000000001")
    payload = verify_access_token(token)

    assert payload is not None
    assert payload["type"] == "access"


def test_refresh_like_token_is_not_accepted_as_access_token():
    import jwt

    from app.core.security import settings

    token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000001", "type": "refresh"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    assert verify_access_token(token) is None


def test_access_token_rejects_missing_expiry_and_wrong_algorithm():
    import jwt
    from app.core.security import settings
    from datetime import UTC, datetime, timedelta
    no_expiry = jwt.encode({"sub": "user", "type": "access"}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    assert verify_access_token(no_expiry) is None
    other_algorithm = "HS512" if settings.JWT_ALGORITHM != "HS512" else "HS256"
    wrong_algorithm = jwt.encode({"sub": "user", "type": "access", "exp": datetime.now(UTC) + timedelta(minutes=1)},
        settings.JWT_SECRET_KEY, algorithm=other_algorithm)
    assert verify_access_token(wrong_algorithm) is None
