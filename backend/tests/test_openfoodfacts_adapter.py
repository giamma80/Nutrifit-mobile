import pytest
import httpx
from typing import Any, Dict

from openfoodfacts.adapter import (
    fetch_product,
    ProductNotFound,
    OpenFoodFactsError,
)


@pytest.mark.asyncio
async def test_fetch_product_success(monkeypatch: pytest.MonkeyPatch) -> None:
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
        def __init__(self, status_code: int, data: Dict[str, Any]) -> None:
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> "MockResp":
            return MockResp(200, sample)

    # timeout arg passato da codice ma non rilevante nei test
    def _fake_async_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client)

    dto = await fetch_product("123456")
    assert dto.name == "Test Bar"
    assert dto.nutrients["calories"] == 400
    assert dto.nutrients["protein"] == 30


@pytest.mark.asyncio
async def test_fetch_product_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = {"status": 0}

    class MockResp:
        def __init__(self, status_code: int, data: Dict[str, Any]) -> None:
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> "MockResp":
            return MockResp(200, sample)

    def _fake_async_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client)

    with pytest.raises(ProductNotFound):
        await fetch_product("999999")


@pytest.mark.asyncio
async def test_kj_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
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
        def __init__(self, status_code: int, data: Dict[str, Any]) -> None:
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> "MockResp":
            return MockResp(200, sample)

    def _fake_async_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client)
    dto = await fetch_product("kjfallback")
    # 1046 / 4.184 ≈ 250.0
    assert dto.nutrients["calories"] == 250
    assert dto.nutrients["protein"] == 10


@pytest.mark.asyncio
async def test_salt_to_sodium(monkeypatch: pytest.MonkeyPatch) -> None:
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
        def __init__(self, status_code: int, data: Dict[str, Any]) -> None:
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> "MockResp":
            return MockResp(200, sample)

    def _fake_async_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client)
    dto = await fetch_product("saltconv")
    assert dto.nutrients["sodium"] == 600


@pytest.mark.asyncio
async def test_invalid_nutrient_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        def __init__(self, status_code: int, data: Dict[str, Any]) -> None:
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> MockResp:
            return MockResp(200, sample)

    def _fake_async_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client)
    dto = await fetch_product("weird")
    assert "calories" in dto.nutrients
    assert dto.nutrients.get("calories") == 100
    assert "protein" not in dto.nutrients


@pytest.mark.asyncio
async def test_http_404(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockResp:
        def __init__(self, status_code: int, data: Dict[str, Any]) -> None:
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> MockResp:
            return MockResp(404, {})

    def _fake_async_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client)
    with pytest.raises(ProductNotFound):
        await fetch_product("404code")


@pytest.mark.asyncio
async def test_http_500(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockResp:
        def __init__(self, status_code: int, data: Dict[str, Any]) -> None:
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> MockResp:
            return MockResp(500, {})

    def _fake_async_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client)
    with pytest.raises(OpenFoodFactsError):
        await fetch_product("500code")


# -------------------- Retry tests --------------------


def _sample_ok() -> Dict[str, Any]:
    return {
        "status": 1,
        "product": {
            "product_name": "Retry OK",
            "nutriments": {"energy-kcal_100g": 100},
        },
    }


@pytest.mark.asyncio
async def test_retry_transient_500_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    class MockResp:
        def __init__(self, status_code: int, data: Dict[str, Any]):
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> MockResp:
            calls["n"] += 1
            if calls["n"] == 1:
                return MockResp(500, {})
            return MockResp(200, _sample_ok())

    def _fake_client(timeout: Any) -> MockClient:  # noqa: D401
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client)
    dto = await fetch_product("retry500")
    assert "calories" in dto.nutrients
    assert dto.nutrients.get("calories") == 100
    assert calls["n"] == 2  # una retry


@pytest.mark.asyncio
async def test_retry_timeout_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    class MockResp:
        def __init__(self, status_code: int, data: Dict[str, Any]):
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> MockResp:
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ReadTimeout("boom")
            return MockResp(200, _sample_ok())

    def _fake_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client)
    dto = await fetch_product("retrytimeout")
    assert "calories" in dto.nutrients
    assert dto.nutrients.get("calories") == 100
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_retry_exhausted_500(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    class MockResp:
        def __init__(self, status_code: int, data: Dict[str, Any]):
            self.status_code = status_code
            self._data = data

        def json(self) -> Dict[str, Any]:
            return self._data

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> MockResp:
            calls["n"] += 1
            return MockResp(500, {})

    def _fake_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client)
    with pytest.raises(OpenFoodFactsError):
        await fetch_product("exh500")
    # MAX_RETRIES=3 => 3 tentativi
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_retry_exhausted_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    class MockClient:
        async def __aenter__(self) -> "MockClient":
            return self

        async def __aexit__(self, *args: Any) -> bool:
            return False

        async def get(self, url: str) -> Any:
            calls["n"] += 1
            raise httpx.ReadTimeout("timeout")

    def _fake_client(timeout: Any) -> MockClient:
        return MockClient()

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client)
    with pytest.raises(OpenFoodFactsError):
        await fetch_product("exhtimeout")
    assert calls["n"] == 3
