import pytest
from typing import Any, Dict
from httpx import AsyncClient, Response


def _minify(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_log_meal_basic(client: AsyncClient) -> None:
    mutation = _minify(
        """
        mutation {
            logMeal(input: {name: \"Mela\", quantityG: 150}) {
                id name quantityG
                idempotencyKey nutrientSnapshotJson
                calories protein
            }
        }
        """
    )
    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]
    assert data["id"]
    assert data["name"] == "Mela"
    assert data["quantityG"] == 150
    assert data["idempotencyKey"]
    # nutrientSnapshotJson non ancora popolato lato backend
    # deve risultare None/null in JSON
    assert data["nutrientSnapshotJson"] is None


@pytest.mark.asyncio
async def test_log_meal_idempotent(client: AsyncClient) -> None:
    mutation = _minify(
        'mutation { logMeal(input: {name: "Banana", quantityG: 100, '
        'timestamp: "2025-09-21T10:00:00Z"}) { id name quantityG } }'
    )
    r1: Response = await client.post("/graphql", json={"query": mutation})
    r2: Response = await client.post("/graphql", json={"query": mutation})
    d1: Dict[str, Any] = r1.json()["data"]["logMeal"]
    d2: Dict[str, Any] = r2.json()["data"]["logMeal"]
    assert d1["id"] == d2["id"], "Idempotenza fallita"


@pytest.mark.asyncio
async def test_log_meal_with_barcode_enrichment(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    class DummyDTO:
        barcode: str
        name: str
        brand: str
        category: str
        nutrients: dict[str, float]

        def __init__(self) -> None:
            self.barcode = "123456"
            self.name = "Protein Bar"
            self.brand = "BrandX"
            self.category = "en:protein-bars"
            self.nutrients = {"calories": 200, "protein": 20.0}

    async def fake_fetch(barcode: str) -> DummyDTO:  # noqa: ARG001
        return DummyDTO()

    from openfoodfacts import adapter

    monkeypatch.setattr(adapter, "fetch_product", fake_fetch)

    mutation = _minify(
        'mutation { logMeal(input: {name: "Bar", quantityG: 50, '
        'barcode: "123456"}) { id name quantityG idempotencyKey '
        "calories protein } }"
    )
    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]
    assert data["calories"] == 100
    assert data["protein"] == 10.0


@pytest.mark.asyncio
async def test_log_meal_invalid_quantity(client: AsyncClient) -> None:
    mutation = _minify(
        'mutation { logMeal(input: {name: "Bad", quantityG: -5}) { id } }'
    )
    resp: Response = await client.post("/graphql", json={"query": mutation})
    err: Any = resp.json().get("errors")
    assert err and any("INVALID_QUANTITY" in e.get("message", "") for e in err)


@pytest.mark.asyncio
async def test_log_meal_with_explicit_idempotency_key(
    client: AsyncClient,
) -> None:
    mutation = _minify(
        'mutation { logMeal(input: {name: "Yogurt", quantityG: 120, '
        'idempotencyKey: "meal:yogurt:120:static"}) { id idempotencyKey '
        "quantityG } }"
    )
    r1: Response = await client.post("/graphql", json={"query": mutation})
    r2: Response = await client.post("/graphql", json={"query": mutation})
    d1: Dict[str, Any] = r1.json()["data"]["logMeal"]
    d2: Dict[str, Any] = r2.json()["data"]["logMeal"]
    assert d1["id"] == d2["id"]
    assert d1["idempotencyKey"] == "meal:yogurt:120:static"
