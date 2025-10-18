import pytest
import os
from typing import Any, Dict
from httpx import AsyncClient, Response


def _minify(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_log_meal_domain_v2_routing(client: AsyncClient) -> None:
    """Test that meal creation uses domain V2 when feature flags are enabled."""
    # Domain V2 is always active
    os.environ["MEAL_DOMAIN_V2"] = "true"

    mutation = _minify(
        """
        mutation {
            logMeal(input: {name: \"Test Domain Meal\", quantityG: 100}) {
                id name quantityG
                idempotencyKey
                calories protein carbs fat
            }
        }
        """
    )

    # Reset any cached integration services to pick up new env vars
    from domain.meal.integration import _reset_integration_service

    _reset_integration_service()

    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]

    assert data["id"]
    assert data["name"] == "Test Domain Meal"
    assert data["quantityG"] == 100
    assert data["idempotencyKey"]

    # Domain should work without errors
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_log_meal_domain_v2_active(client: AsyncClient) -> None:
    """Test that meal creation uses domain V2 (always active)."""
    # Domain V2 is always active
    os.environ["MEAL_DOMAIN_V2"] = "true"

    mutation = _minify(
        """
        mutation {
            logMeal(input: {name: \"Test Domain V2\", quantityG: 100}) {
                id name quantityG
            }
        }
        """
    )

    # Reset any cached integration services
    from domain.meal.integration import _reset_integration_service

    _reset_integration_service()

    resp: Response = await client.post("/graphql", json={"query": mutation})

    # Should work with domain V2
    assert resp.status_code == 200
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]
    assert data["id"]
    assert data["name"] == "Test Domain V2"
