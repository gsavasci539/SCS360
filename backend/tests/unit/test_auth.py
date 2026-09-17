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


def test_access_token_has_expected_type():
    token = create_access_token("00000000-0000-0000-0000-000000000001")
    payload = verify_access_token(token)

    assert payload is not None
    assert payload["type"] == "access"


def test_refresh_like_token_is_not_accepted_as_access_token():
    from jose import jwt

    from app.core.security import settings

    token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000001", "type": "refresh"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    assert verify_access_token(token) is None
