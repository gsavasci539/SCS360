from fastapi import Request, Response

from app.application.services.auth_service import AuthService
from app.core.exceptions import ForbiddenException
from app.core.web_session import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    CSRF_HEADER,
    REFRESH_COOKIE,
    REMEMBER_COOKIE,
    clear_session_cookies,
    require_csrf,
    set_session_cookies,
    settings,
)


def make_request(*, origin: str = "https://panel.example.test", cookie: str = "", csrf: str = "") -> Request:
    headers = [(b"origin", origin.encode())]
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    if csrf:
        headers.append((CSRF_HEADER.lower().encode(), csrf.encode()))
    return Request({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "https", "path": "/api/students", "raw_path": b"/api/students",
        "query_string": b"", "headers": headers, "client": ("127.0.0.1", 1234), "server": ("panel.example.test", 443),
    })


def test_cookie_auth_mutation_requires_matching_csrf_and_allowed_origin(monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", "https://panel.example.test")

    require_csrf(make_request(cookie=f"{CSRF_COOKIE}=random", csrf="random"))

    for request in (
        make_request(cookie=f"{CSRF_COOKIE}=random", csrf="different"),
        make_request(cookie=f"{CSRF_COOKIE}=random"),
        make_request(origin="https://attacker.example", cookie=f"{CSRF_COOKIE}=random", csrf="random"),
    ):
        try:
            require_csrf(request)
        except ForbiddenException:
            continue
        raise AssertionError("invalid CSRF/origin request was accepted")


def test_session_cookies_hide_auth_tokens_and_scope_refresh_cookie(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    response = Response()
    set_session_cookies(response, "access", "refresh", "csrf", remember=True)
    headers = response.headers.getlist("set-cookie")

    access = next(value for value in headers if value.startswith(f"{ACCESS_COOKIE}="))
    refresh = next(value for value in headers if value.startswith(f"{REFRESH_COOKIE}="))
    csrf = next(value for value in headers if value.startswith(f"{CSRF_COOKIE}="))
    remember = next(value for value in headers if value.startswith(f"{REMEMBER_COOKIE}="))
    assert "HttpOnly" in access and "Secure" in access and "Path=/api" in access
    assert "HttpOnly" in refresh and "Secure" in refresh and "Path=/api/auth/web" in refresh
    assert "HttpOnly" not in csrf and "Secure" in csrf
    assert "HttpOnly" in remember and "Secure" in remember


def test_session_cookie_logout_clears_all_cookie_names(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    response = Response()
    clear_session_cookies(response)
    headers = response.headers.getlist("set-cookie")
    for name in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE, REMEMBER_COOKIE):
        assert any(value.startswith(f"{name}=") and "Max-Age=0" in value for value in headers)


async def test_web_login_and_refresh_keep_tokens_out_of_json_and_csrf_blocks_mutations(client, monkeypatch):
    monkeypatch.setattr(settings, "CORS_ORIGINS", "http://test")
    user = {
        "id": "user-id", "email": "user@example.com", "first_name": "A", "last_name": "B",
        "status": "ACTIVE", "is_super_admin": False, "organization_id": "org-id", "roles": [],
        "permissions": [], "branch_ids": [],
    }

    async def fake_login(self, email, password, ip, user_agent):
        return {"access_token": "access-one", "refresh_token": "refresh-one", "user": user}

    async def fake_refresh(self, refresh_token, ip, user_agent):
        assert refresh_token == "refresh-one"
        return {"access_token": "access-two", "refresh_token": "refresh-two", "user": user}

    monkeypatch.setattr(AuthService, "login", fake_login)
    login = await client.post("/api/auth/web/login", headers={"Origin": "http://test"}, json={
        "email": "user@example.com", "password": "password", "remember": True,
    })
    assert login.status_code == 200
    assert set(login.json()["data"]) == {"user", "csrf_token"}
    assert login.json()["data"]["user"] == user
    csrf_token = login.json()["data"]["csrf_token"]
    assert ACCESS_COOKIE in client.cookies and REFRESH_COOKIE in client.cookies

    blocked = await client.post("/api/auth/web/logout", headers={"Origin": "http://test", CSRF_HEADER: "wrong"})
    assert blocked.status_code == 403

    monkeypatch.setattr(AuthService, "refresh", fake_refresh)
    refreshed = await client.post("/api/auth/web/refresh", headers={
        "Origin": "http://test", CSRF_HEADER: csrf_token,
    }, json={})
    assert refreshed.status_code == 200
    assert set(refreshed.json()["data"]) == {"user", "csrf_token"}
    assert refreshed.json()["data"]["user"] == user
