import pytest
import httpx

from backend.openfoodfacts.adapter import fetch_product, ProductNotFound

 
@pytest.mark.asyncio
async def test_fetch_product_success(monkeypatch):
    sample = {
        "status": 1,
        "product": {
            "product_name": "Test Bar",
            "brands": "BrandX",
            "categories_tags": ["en:protein-bars"],
            "nutriments": {
                "energy-kcal_100g": 400,
                "proteins_100g": 30,
                "carbohydrates_100g": 35,
                "fat_100g": 12,
                "fiber_100g": 5,
                "sugars_100g": 10,
                "sodium_100g": 200,
            },
        },
    }

    class MockResp:
        def __init__(self, status_code, data):
            self.status_code = status_code
            self._data = data

        def json(self):
            return self._data

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            return MockResp(200, sample)

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: MockClient())

    dto = await fetch_product("123456")
    assert dto.name == "Test Bar"
    assert dto.nutrients["calories"] == 400
    assert dto.nutrients["protein"] == 30

 
@pytest.mark.asyncio
async def test_fetch_product_not_found(monkeypatch):
    sample = {"status": 0}

    class MockResp:
        def __init__(self, status_code, data):
            self.status_code = status_code
            self._data = data

        def json(self):
            return self._data

    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url):
            return MockResp(200, sample)

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: MockClient())

    with pytest.raises(ProductNotFound):
        await fetch_product("999999")
