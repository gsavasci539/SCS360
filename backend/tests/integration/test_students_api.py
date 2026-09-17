"""Integration tests for students API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_students_requires_auth(client: AsyncClient):
    response = await client.get("/api/students")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
