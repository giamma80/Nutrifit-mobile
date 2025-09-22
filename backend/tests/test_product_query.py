import pytest
from httpx import AsyncClient
from app import app


class DummyDTO:
    def __init__(self, barcode: str):
        self.barcode = barcode
        self.name = "Bar Test"
        self.brand = "BrandX"
        self.category = "en:protein-bars"
        self.nutrients = {"calories": 123, "protein": 10.5}


@pytest.mark.asyncio
async def test_product_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(barcode: str) -> DummyDTO:
        return DummyDTO(barcode)

    from openfoodfacts import adapter

    monkeypatch.setattr(adapter, "fetch_product", fake_fetch)
    async with AsyncClient(app=app, base_url="http://test") as ac:
        query = '{ product(barcode: "123") { barcode name calories protein } }'
        resp = await ac.post("/graphql", json={"query": query})
        data = resp.json()["data"]["product"]
        assert data["barcode"] == "123"
        assert data["calories"] == 123
        assert data["protein"] == 10.5


@pytest.mark.asyncio
async def test_product_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    from openfoodfacts import adapter
    from openfoodfacts.adapter import ProductNotFound

    async def fake_fetch(barcode: str) -> DummyDTO:
        raise ProductNotFound(barcode)

    monkeypatch.setattr(adapter, "fetch_product", fake_fetch)
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(
            "/graphql",
            json={"query": '{ product(barcode: "404") { barcode } }'},
        )
        data = resp.json()["data"]
        assert data["product"] is None


@pytest.mark.asyncio
async def test_product_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    from openfoodfacts import adapter

    calls = {"n": 0}

    async def fake_fetch(barcode: str) -> DummyDTO:
        calls["n"] += 1
        return DummyDTO(barcode)

    monkeypatch.setattr(adapter, "fetch_product", fake_fetch)
    async with AsyncClient(app=app, base_url="http://test") as ac:
        q = '{ product(barcode: "999") { barcode name } }'
        await ac.post("/graphql", json={"query": q})
        await ac.post("/graphql", json={"query": q})
    assert calls["n"] == 1, "Seconda richiesta dovrebbe usare cache"
