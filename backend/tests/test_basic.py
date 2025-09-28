import pytest


@pytest.mark.asyncio
async def test_health(client) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_graphql_hello(client) -> None:
    query = {"query": "{ hello }"}
    resp = await client.post("/graphql", json=query)
    data = resp.json()["data"]
    assert data["hello"].startswith("nutrifit-backend")
