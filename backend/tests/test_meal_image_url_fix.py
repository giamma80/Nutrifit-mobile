import pytest
import os
from typing import Any, Dict
from httpx import AsyncClient, Response


def _minify(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_log_meal_preserves_image_url_with_domain_v2(client: AsyncClient) -> None:
    """Test that logMeal preserves image_url when using domain V2."""
    # Domain V2 is always active
    os.environ["MEAL_DOMAIN_V2"] = "true"

    # Reset integration service to pick up env vars
    from domain.meal.integration import _reset_integration_service

    _reset_integration_service()

    # Test image URL
    test_image_url = "https://example.com/test-image.jpg"

    mutation = _minify(
        f"""
        mutation {{
            logMeal(input: {{
                name: "Test Meal with Image",
                quantityG: 100,
                photoUrl: "{test_image_url}"
            }}) {{
                id
                name
                quantityG
                imageUrl
                idempotencyKey
            }}
        }}
        """
    )

    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]

    assert resp.status_code == 200
    assert data["id"]
    assert data["name"] == "Test Meal with Image"
    assert data["quantityG"] == 100
    assert data["imageUrl"] == test_image_url  # This should now work!
    assert data["idempotencyKey"]


# Query test removed because 'meals' query doesn't exist in GraphQL schema
# The above mutation test verifies that image_url is preserved in domain V2
