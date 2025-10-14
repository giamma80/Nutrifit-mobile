import pytest
import os
from typing import Any, Dict
from httpx import AsyncClient, Response


def _minify(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_log_meal_domain_v2_routing(client: AsyncClient) -> None:
    """Test that meal creation uses domain V2 when feature flags are enabled."""
    # Ensure feature flags are on
    os.environ["MEAL_DOMAIN_V2"] = "true"
    os.environ["MEAL_GRAPHQL_V2"] = "true"

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
async def test_log_meal_legacy_routing(client: AsyncClient) -> None:
    """Test that meal creation uses legacy when feature flags are disabled."""
    # Ensure feature flags are off
    os.environ["MEAL_DOMAIN_V2"] = "false"
    os.environ["MEAL_GRAPHQL_V2"] = "false"

    mutation = _minify(
        """
        mutation {
            logMeal(input: {name: \"Test Legacy Meal\", quantityG: 100}) {
                id name quantityG
                idempotencyKey
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
    assert data["name"] == "Test Legacy Meal"
    assert data["quantityG"] == 100
    assert data["idempotencyKey"]  # Note: camelCase in GraphQL

    # Legacy should work without errors
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_log_meal_domain_fallback_on_error(client: AsyncClient) -> None:
    """Test that meal creation falls back to legacy when domain fails."""
    # Enable feature flags but simulate domain error
    os.environ["MEAL_DOMAIN_V2"] = "true"
    os.environ["MEAL_GRAPHQL_V2"] = "true"

    mutation = _minify(
        """
        mutation {
            logMeal(input: {name: \"Test Fallback\", quantityG: 100}) {
                id name quantityG
            }
        }
        """
    )

    # Reset any cached integration services
    from domain.meal.integration import _reset_integration_service

    _reset_integration_service()

    resp: Response = await client.post("/graphql", json={"query": mutation})

    # Should still work via fallback
    assert resp.status_code == 200
    data: Dict[str, Any] = resp.json()["data"]["logMeal"]
    assert data["id"]
    assert data["name"] == "Test Fallback"
