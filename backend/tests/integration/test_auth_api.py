import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, database_available):
    response = await client.post(
        "/api/auth/login", json={"email": "invalid@test.com", "password": "wrong"}
    )
    assert response.status_code == 401
