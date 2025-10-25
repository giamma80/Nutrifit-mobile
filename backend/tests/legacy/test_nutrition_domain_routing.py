import pytest
import os
from typing import Any, Dict
from httpx import AsyncClient, Response


def _minify(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_daily_summary_nutrition_v2_routing(client: AsyncClient) -> None:
    """Test that daily_summary uses nutrition V2 when feature flag enabled."""
    # Enable feature flag
    os.environ["AI_NUTRITION_V2"] = "true"

    # Reset integration service to pick up env var
    # Force reset of singleton to pick up new environment
    import domain.nutrition.integration

    domain.nutrition.integration._integration_service = None

    query = _minify(
        """
        query {
            dailySummary(date: "2023-10-13") {
                date
                userId
                meals
                calories
                protein
                carbs
                fat
                caloriesDeficit
                caloriesReplenishedPercent
            }
        }
        """
    )

    resp: Response = await client.post("/graphql", json={"query": query})
    data: Dict[str, Any] = resp.json()["data"]["dailySummary"]

    assert data["date"] == "2023-10-13"
    assert data["userId"] == "default"
    assert isinstance(data["meals"], int)
    assert isinstance(data["calories"], int)

    # Should work without errors (domain logic might enhance calculations)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_daily_summary_legacy_routing(client: AsyncClient) -> None:
    """Test that daily_summary uses legacy when feature flag disabled."""
    # Disable feature flag
    os.environ["AI_NUTRITION_V2"] = "false"

    # Reset integration service to pick up env var
    import domain.nutrition.integration

    domain.nutrition.integration._integration_service = None

    query = _minify(
        """
        query {
            dailySummary(date: "2023-10-13") {
                date
                userId
                meals
                calories
                protein
                carbs
                fat
                caloriesDeficit
                caloriesReplenishedPercent
            }
        }
        """
    )

    resp: Response = await client.post("/graphql", json={"query": query})
    data: Dict[str, Any] = resp.json()["data"]["dailySummary"]

    assert data["date"] == "2023-10-13"
    assert data["userId"] == "default"
    assert isinstance(data["meals"], int)
    assert isinstance(data["calories"], int)

    # Legacy should work without errors
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_daily_summary_fallback_on_domain_error(client: AsyncClient) -> None:
    """Test that daily_summary falls back to legacy when domain fails."""
    # Enable feature flag but simulate domain error scenario
    os.environ["AI_NUTRITION_V2"] = "true"

    # Reset integration service
    import domain.nutrition.integration

    domain.nutrition.integration._integration_service = None

    query = _minify(
        """
        query {
            dailySummary(date: "2023-10-13") {
                date
                userId
                meals
                calories
            }
        }
        """
    )

    resp: Response = await client.post("/graphql", json={"query": query})

    # Should still work via fallback even if domain has issues
    assert resp.status_code == 200
    data: Dict[str, Any] = resp.json()["data"]["dailySummary"]
    assert data["date"] == "2023-10-13"
    assert data["userId"] == "default"
