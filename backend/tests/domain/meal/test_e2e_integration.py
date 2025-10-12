"""End-to-end integration test for meal domain."""

import os
from unittest.mock import patch

import pytest

from domain.meal.integration import (
    _reset_integration_service,
    get_meal_query_service,
    get_meal_service,
    is_meal_domain_v2_enabled,
    meal_domain_health_check,
)


@pytest.mark.asyncio
async def test_meal_domain_e2e_integration():
    """Test end-to-end meal domain integration with feature flag."""
    # Test with feature disabled (default)
    with patch.dict(os.environ, {}, clear=True):
        _reset_integration_service()
        assert not is_meal_domain_v2_enabled()
        assert get_meal_service() is None
        assert get_meal_query_service() is None

        health = await meal_domain_health_check()
        assert health["meal_domain_v2"] == "disabled"

    # Test with feature enabled
    with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
        _reset_integration_service()
        assert is_meal_domain_v2_enabled()

        meal_service = get_meal_service()
        query_service = get_meal_query_service()
        assert meal_service is not None
        assert query_service is not None

        # Test basic query service functionality (using stub adapters)
        user_id = "test-user-123"
        meals = await query_service.find_meals_by_user(user_id)
        assert isinstance(meals, list)

        # Test meal existence check
        meal_exists = await query_service.meal_exists("non-existent-meal")
        assert isinstance(meal_exists, bool)

        # Health check should show enabled state
        health = await meal_domain_health_check()
        assert health["meal_domain_v2"] == "enabled"
        assert health["services"]["meal_service"] == "available"
        assert health["services"]["query_service"] == "available"
        assert health["adapters"]["repository"] == "in_memory"


if __name__ == "__main__":
    import asyncio

    async def main():
        print("Testing meal domain integration...")
        await test_meal_domain_e2e_integration()
        print("✅ All integration tests passed!")

    asyncio.run(main())
