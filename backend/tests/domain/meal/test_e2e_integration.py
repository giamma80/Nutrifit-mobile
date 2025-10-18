"""End-to-end integration test for meal domain - V2 sempre attivo."""

import pytest

from domain.meal.integration import (
    get_meal_query_service,
    get_meal_service,
    is_meal_domain_v2_enabled,
    meal_domain_health_check,
)


@pytest.mark.asyncio
async def test_meal_domain_e2e_integration() -> None:
    """Test end-to-end meal domain integration - V2 sempre attivo."""
    # V2 è sempre abilitato
    assert is_meal_domain_v2_enabled()

    # I servizi sono sempre disponibili
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

    # Health check mostra stato sempre abilitato
    health = await meal_domain_health_check()
    assert health["meal_domain_v2"] == "enabled"
    assert health["feature_flag"] == "always_enabled"

    # Verify services are properly wired
    services = health["services"]
    assert services["meal_service"] == "available"
    assert services["query_service"] == "available"

    # Verify adapters are configured
    adapters = health["adapters"]
    assert adapters["repository"] == "in_memory"
    assert adapters["product_lookup"] == "stub"
    assert adapters["nutrition_calculator"] == "stub"
    assert adapters["events"] == "logging"


@pytest.mark.asyncio
async def test_meal_service_basic_operations() -> None:
    """Test basic meal service operations."""
    meal_service = get_meal_service()
    query_service = get_meal_query_service()

    assert meal_service is not None
    assert query_service is not None

    # Test that we can access service methods
    assert hasattr(meal_service, "create_meal")
    assert hasattr(query_service, "find_meal_by_id")
    assert hasattr(query_service, "find_meals_by_user")


@pytest.mark.asyncio
async def test_services_consistency() -> None:
    """Test that services are consistently available."""
    # Multiple calls should return the same services
    service1 = get_meal_service()
    service2 = get_meal_service()
    query1 = get_meal_query_service()
    query2 = get_meal_query_service()

    assert service1 is service2  # Singleton pattern
    assert query1 is query2  # Singleton pattern

    # Services should always be available
    assert service1 is not None
    assert query1 is not None

    # V2 should always be enabled
    assert is_meal_domain_v2_enabled() is True
