import pytest
from typing import Any, Dict
from httpx import AsyncClient, Response


class DummyDTO:
    def __init__(self, barcode: str):
        self.barcode = barcode
        self.name = "Bar Test"
        self.brand = "BrandX"
        self.category = "en:protein-bars"
        self.nutrients = {"calories": 123, "protein": 10.5}


@pytest.mark.asyncio
async def test_product_success(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_fetch(barcode: str) -> DummyDTO:
        return DummyDTO(barcode)

    from openfoodfacts import adapter

    monkeypatch.setattr(adapter, "fetch_product", fake_fetch)
    query = '{ product(barcode: "123") { barcode name calories protein } }'
    resp: Response = await client.post("/graphql", json={"query": query})
    data: Dict[str, Any] = resp.json()["data"]["product"]
    assert data["barcode"] == "123"
    assert data["calories"] == 123
    assert data["protein"] == 10.5


@pytest.mark.asyncio
async def test_product_not_found(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from openfoodfacts import adapter
    from openfoodfacts.adapter import ProductNotFound

    async def fake_fetch(barcode: str) -> DummyDTO:
        raise ProductNotFound(barcode)

    monkeypatch.setattr(adapter, "fetch_product", fake_fetch)
    resp: Response = await client.post(
        "/graphql",
        json={"query": '{ product(barcode: "404") { barcode } }'},
    )
    data: Dict[str, Any] = resp.json()["data"]
    assert data["product"] is None


@pytest.mark.asyncio
async def test_product_cache_hit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from openfoodfacts import adapter

    calls = {"n": 0}

    async def fake_fetch(barcode: str) -> DummyDTO:
        calls["n"] += 1
        return DummyDTO(barcode)

    monkeypatch.setattr(adapter, "fetch_product", fake_fetch)
    q = '{ product(barcode: "999") { barcode name } }'
    await client.post("/graphql", json={"query": q})
    await client.post("/graphql", json={"query": q})
    assert calls["n"] == 1, "Seconda richiesta dovrebbe usare cache"
