import pytest
import httpx

from openfoodfacts.adapter import (
    fetch_product,
    ProductNotFound,
    OpenFoodFactsError,
)

 
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


@pytest.mark.asyncio
async def test_kj_fallback(monkeypatch):
    sample = {
        "status": 1,
        "product": {
            "product_name": "KJ Energy",
            "nutriments": {
                # manca energy-kcal_100g ma c'è energy_100g (kJ)
                "energy_100g": 1046,  # ~250 kcal
                "proteins_100g": 10,
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
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def get(self, url): return MockResp(200, sample)

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: MockClient())
    dto = await fetch_product("kjfallback")
    # 1046 / 4.184 ≈ 250.0
    assert dto.nutrients["calories"] == 250
    assert dto.nutrients["protein"] == 10


@pytest.mark.asyncio
async def test_salt_to_sodium(monkeypatch):
    sample = {
        "status": 1,
        "product": {
            "product_name": "Salty",
            "nutriments": {
                # manca sodium_100g ma presente salt_100g
                "salt_100g": 1.5,  # => 1.5 * 400 = 600 mg
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
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def get(self, url): return MockResp(200, sample)

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: MockClient())
    dto = await fetch_product("saltconv")
    assert dto.nutrients["sodium"] == 600


@pytest.mark.asyncio
async def test_invalid_nutrient_ignored(monkeypatch):
    sample = {
        "status": 1,
        "product": {
            "product_name": "Weird",
            "nutriments": {
                "energy-kcal_100g": 100,
                "proteins_100g": "abc",  # non numerico → ignorato
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
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def get(self, url): return MockResp(200, sample)

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: MockClient())
    dto = await fetch_product("weird")
    assert dto.nutrients["calories"] == 100
    assert "protein" not in dto.nutrients


@pytest.mark.asyncio
async def test_http_404(monkeypatch):
    class MockResp:
        def __init__(self, status_code, data):
            self.status_code = status_code
            self._data = data

        def json(self):
            return self._data

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def get(self, url): return MockResp(404, {})

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: MockClient())
    with pytest.raises(ProductNotFound):
        await fetch_product("404code")


@pytest.mark.asyncio
async def test_http_500(monkeypatch):
    class MockResp:
        def __init__(self, status_code, data):
            self.status_code = status_code
            self._data = data

        def json(self):
            return self._data

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def get(self, url): return MockResp(500, {})

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: MockClient())
    with pytest.raises(OpenFoodFactsError):
        await fetch_product("500code")
