import pytest
import os
from typing import Any, Dict
from httpx import AsyncClient, Response


def _minify(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_server_exact_scenario(client: AsyncClient) -> None:
    """Test the exact mutation used by the user on server."""
    # Domain V2 is always active
    os.environ["MEAL_DOMAIN_V2"] = "true"

    # Reset integration service to pick up env vars
    from domain.meal.integration import _reset_integration_service

    _reset_integration_service()

    # The EXACT mutation from user's message (NO photoUrl!)
    mutation = _minify(
        """
        mutation {
            logMeal(
                input: {
                    name: "SPAGHETTI N° 5",
                    quantityG: 1.5,
                    barcode: "8076800195057",
                    userId: "00004"
                }
            ) {
                barcode
                calories
                carbs
                fat
                fiber
                id
                idempotencyKey
                imageUrl
                name
                nutrientSnapshotJson
                protein
                quantityG
                sodium
                sugar
                timestamp
                userId
            }
        }
        """
    )

    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]

    print(f"Response imageUrl: {data['imageUrl']}")
    print(f"Full response: {data}")

    assert resp.status_code == 200
    assert data["name"] == "SPAGHETTI N° 5"
    assert data["barcode"] == "8076800195057"
    assert data["userId"] == "00004"

    # Should use OpenFoodFacts image when no photoUrl is provided but barcode exists
    assert data["imageUrl"] is not None  # Should get image from OpenFoodFacts
    assert "openfoodfacts.org" in data["imageUrl"]  # Verify it's from OpenFoodFacts


@pytest.mark.asyncio
async def test_server_scenario_with_photo_url(client: AsyncClient) -> None:
    """Test mutation WITH photoUrl to see if it works."""
    # Domain V2 is always active
    os.environ["MEAL_DOMAIN_V2"] = "true"

    # Reset integration service
    from domain.meal.integration import _reset_integration_service

    _reset_integration_service()

    # Same mutation but WITH photoUrl
    test_image_url = "https://example.com/server-test.jpg"
    mutation = _minify(
        f"""
        mutation {{
            logMeal(
                input: {{
                    name: "SPAGHETTI N° 5 WITH IMAGE",
                    quantityG: 1.5,
                    barcode: "8076800195057",
                    userId: "00004",
                    photoUrl: "{test_image_url}"
                }}
            ) {{
                barcode
                imageUrl
                name
                userId
            }}
        }}
        """
    )

    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]

    print(f"WITH photoUrl - imageUrl: {data['imageUrl']}")

    assert resp.status_code == 200
    assert data["imageUrl"] == test_image_url  # Should work!
