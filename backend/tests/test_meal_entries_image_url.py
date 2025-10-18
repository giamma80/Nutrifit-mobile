import pytest
import os
from typing import Any, Dict, List
from httpx import AsyncClient, Response


def _minify(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_meal_entries_returns_image_url(client: AsyncClient) -> None:
    """Test that mealEntries query returns imageUrl for meals with images."""
    # Domain V2 is always active
    os.environ["MEAL_DOMAIN_V2"] = "true"

    # Reset integration service to pick up env vars
    from domain.meal.integration import _reset_integration_service

    _reset_integration_service()

    # Test image URL
    test_image_url = "https://example.com/test-meal-entries.jpg"

    # First create a meal with image using logMeal
    create_mutation = _minify(
        f"""
        mutation {{
            logMeal(input: {{
                name: "Meal with Image for Query",
                quantityG: 100,
                photoUrl: "{test_image_url}"
            }}) {{
                id
                imageUrl
            }}
        }}
        """
    )

    create_resp: Response = await client.post("/graphql", json={"query": create_mutation})
    create_data: Dict[str, Any] = create_resp.json()["data"]["logMeal"]

    assert create_resp.status_code == 200
    assert create_data["imageUrl"] == test_image_url
    created_meal_id = create_data["id"]

    # Now query mealEntries to verify imageUrl is returned
    query = _minify(
        """
        query {
            mealEntries(limit: 20) {
                id
                name
                quantityG
                imageUrl
            }
        }
        """
    )

    query_resp: Response = await client.post("/graphql", json={"query": query})
    query_data: Dict[str, Any] = query_resp.json()["data"]
    meal_entries: List[Dict[str, Any]] = query_data["mealEntries"]

    assert query_resp.status_code == 200

    # Find our created meal
    created_meal = next((meal for meal in meal_entries if meal["id"] == created_meal_id), None)

    assert created_meal is not None
    assert created_meal["name"] == "Meal with Image for Query"
    assert created_meal["quantityG"] == 100
    assert created_meal["imageUrl"] == test_image_url  # This should work now!


@pytest.mark.asyncio
async def test_meal_entries_null_image_url_for_meals_without_image(
    client: AsyncClient,
) -> None:
    """Test that mealEntries returns null imageUrl for meals without images."""
    # Domain V2 is always active
    os.environ["MEAL_DOMAIN_V2"] = "true"

    # Reset integration service
    from domain.meal.integration import _reset_integration_service

    _reset_integration_service()

    # Create a meal WITHOUT image
    create_mutation = _minify(
        """
        mutation {
            logMeal(input: {
                name: "Meal without Image",
                quantityG: 50
            }) {
                id
                imageUrl
            }
        }
        """
    )

    create_resp: Response = await client.post("/graphql", json={"query": create_mutation})
    create_data: Dict[str, Any] = create_resp.json()["data"]["logMeal"]

    assert create_resp.status_code == 200
    assert create_data["imageUrl"] is None  # No photoUrl provided
    created_meal_id = create_data["id"]

    # Query mealEntries
    query = _minify(
        """
        query {
            mealEntries(limit: 20) {
                id
                name
                imageUrl
            }
        }
        """
    )

    query_resp: Response = await client.post("/graphql", json={"query": query})
    meal_entries: List[Dict[str, Any]] = query_resp.json()["data"]["mealEntries"]

    # Find our meal
    created_meal = next((meal for meal in meal_entries if meal["id"] == created_meal_id), None)

    assert created_meal is not None
    assert created_meal["name"] == "Meal without Image"
    assert created_meal["imageUrl"] is None  # Should be null as expected
