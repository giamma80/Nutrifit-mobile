from httpx import AsyncClient
import pytest
from app import app


@pytest.mark.asyncio
async def test_health() -> None:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_graphql_hello() -> None:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        query = {"query": "{ hello }"}
        resp = await ac.post("/graphql", json=query)
        data = resp.json()["data"]
        assert data["hello"].startswith("nutrifit-backend")
