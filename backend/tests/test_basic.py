import pytest
from typing import Any, Dict
from httpx import AsyncClient, Response


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    resp: Response = await client.get("/health")
    body: Dict[str, Any] = resp.json()
    assert resp.status_code == 200
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_graphql_hello(client: AsyncClient) -> None:
    query: Dict[str, str] = {"query": "{ hello }"}
    resp: Response = await client.post("/graphql", json=query)
    data: Dict[str, Any] = resp.json()["data"]
    hello: str = data["hello"]
    assert hello.startswith("nutrifit-backend")
