"""Test per la funzionalità image_url nei meal."""

from typing import Any, Dict
import pytest
from httpx import AsyncClient, Response


def _minify(s: str) -> str:
    """Remove newlines and extra spaces from GraphQL query."""
    return " ".join(s.split())


@pytest.mark.asyncio
async def test_log_meal_with_photo_url_ai_case(client: AsyncClient) -> None:
    """Test che photo_url dall'input (caso AI) venga salvato come image_url."""
    photo_url = "https://example.com/meal-photo.jpg"

    mutation = _minify(
        'mutation { logMeal(input: {name: "Pizza AI", quantityG: 200, '
        f'photoUrl: "{photo_url}"'
        "}) { id name quantityG imageUrl } }"
    )

    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]

    assert data["name"] == "Pizza AI"
    assert data["quantityG"] == 200
    assert data["imageUrl"] == photo_url


@pytest.mark.asyncio
async def test_log_meal_with_barcode_image_from_openfoodfacts(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    """Test che l'immagine da OpenFoodFacts (caso Barcode) venga salvata come image_url."""

    class DummyDTO:
        def __init__(self) -> None:
            self.barcode = "123456789"
            self.name = "Test Product"
            self.brand = "Test Brand"
            self.category = "test-category"
            self.nutrients = {"calories": 150, "protein": 10.0}
            self.image_url = "https://images.openfoodfacts.org/products/123/456/789/front.jpg"

    async def fake_fetch(barcode: str) -> DummyDTO:  # noqa: ARG001
        return DummyDTO()

    from openfoodfacts import adapter

    monkeypatch.setattr(adapter, "fetch_product", fake_fetch)

    mutation = _minify(
        'mutation { logMeal(input: {name: "Barcode Product", quantityG: 100, '
        'barcode: "123456789"}) { id name quantityG barcode imageUrl calories protein } }'
    )

    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]

    assert data["name"] == "Barcode Product"
    assert data["quantityG"] == 100
    assert data["barcode"] == "123456789"
    assert data["imageUrl"] == "https://images.openfoodfacts.org/products/123/456/789/front.jpg"
    assert data["calories"] == 150  # Nutrienti arricchiti
    assert data["protein"] == 10.0


@pytest.mark.asyncio
async def test_log_meal_photo_url_priority_over_barcode_image(
    monkeypatch: pytest.MonkeyPatch, client: AsyncClient
) -> None:
    """Test che photo_url abbia priorità su image_url da OpenFoodFacts."""

    class DummyDTO:
        def __init__(self) -> None:
            self.barcode = "999888777"
            self.name = "Dual Source Product"
            self.brand = "Test Brand"
            self.category = "test-category"
            self.nutrients = {"calories": 200, "protein": 15.0}
            self.image_url = "https://images.openfoodfacts.org/products/999/888/777/front.jpg"

    async def fake_fetch(barcode: str) -> DummyDTO:  # noqa: ARG001
        return DummyDTO()

    from openfoodfacts import adapter

    monkeypatch.setattr(adapter, "fetch_product", fake_fetch)

    user_photo_url = "https://user-upload.example.com/my-meal.jpg"

    mutation = _minify(
        'mutation { logMeal(input: {name: "Priority Test", quantityG: 150, '
        f'barcode: "999888777", photoUrl: "{user_photo_url}"'
        "}) { id name quantityG barcode imageUrl calories protein } }"
    )

    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]

    assert data["name"] == "Priority Test"
    assert data["quantityG"] == 150
    assert data["barcode"] == "999888777"
    # photo_url deve avere priorità su image_url da OpenFoodFacts
    assert data["imageUrl"] == user_photo_url
    assert data["calories"] == 300  # 200 * 1.5 (scaled per quantityG)
    assert data["protein"] == 22.5  # 15.0 * 1.5


@pytest.mark.asyncio
async def test_log_meal_no_image_sources(client: AsyncClient) -> None:
    """Test che senza photo_url e senza barcode, image_url sia None."""

    mutation = _minify(
        'mutation { logMeal(input: {name: "No Image Meal", quantityG: 100}) '
        "{ id name quantityG imageUrl } }"
    )

    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]

    assert data["name"] == "No Image Meal"
    assert data["quantityG"] == 100
    assert data["imageUrl"] is None


@pytest.mark.asyncio
async def test_meal_entries_includes_image_url(client: AsyncClient) -> None:
    """Test che la query mealEntries restituisca il campo imageUrl."""
    # Prima creiamo un meal con image_url
    photo_url = "https://example.com/test-meal.jpg"

    mutation = _minify(
        'mutation { logMeal(input: {name: "Test Query Meal", quantityG: 250, '
        f'photoUrl: "{photo_url}"'
        "}) { id } }"
    )

    resp: Response = await client.post("/graphql", json={"query": mutation})
    meal_id = resp.json()["data"]["logMeal"]["id"]

    # Ora queryamo mealEntries per verificare che image_url sia restituito
    query = _minify("query { mealEntries(limit: 10) { id name quantityG imageUrl } }")

    resp_query: Response = await client.post("/graphql", json={"query": query})
    meals = resp_query.json()["data"]["mealEntries"]

    # Trova il nostro meal
    test_meal = next((m for m in meals if m["id"] == meal_id), None)
    assert test_meal is not None
    assert test_meal["name"] == "Test Query Meal"
    assert test_meal["quantityG"] == 250
    assert test_meal["imageUrl"] == photo_url
