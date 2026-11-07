import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,payload,status", [
    ("GET", "/api/auth/me", None, 401),
    ("GET", "/api/nonexistent-contract-route", None, 404),
    ("POST", "/api/auth/login", {}, 422),
])
async def test_errors_keep_http_status_and_share_mobile_envelope(client, method, path, payload, status):
    response = await client.request(method, path, json=payload)
    assert response.status_code == status
    body = response.json()
    assert body["success"] is False
    assert isinstance(body["message"], str)
    assert isinstance(body["errors"], list)
    assert body["request_id"] == response.headers["X-Request-ID"]
    if status == 401:
        assert response.headers["WWW-Authenticate"] == "Bearer"
