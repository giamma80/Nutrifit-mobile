"""Test integration layer for meal domain."""

import pytest

from domain.meal.integration import (
    MealIntegrationService,
    get_meal_integration_service,
    get_meal_query_service,
    get_meal_service,
    is_meal_domain_v2_enabled,
    meal_domain_health_check,
)


class TestMealIntegrationService:
    """Test meal integration service - sempre attivo in V2."""

    def test_service_always_enabled(self) -> None:
        """Test that meal domain v2 is always enabled."""
        service = MealIntegrationService()

        assert service.is_enabled()
        assert service.get_meal_service() is not None
        assert service.get_query_service() is not None

    def test_service_initialization_success(self) -> None:
        """Test successful service initialization."""
        service = MealIntegrationService()

        # Verify all services are properly initialized
        meal_service = service.get_meal_service()
        query_service = service.get_query_service()

        assert meal_service is not None
        assert query_service is not None
        assert hasattr(meal_service, "create_meal")
        assert hasattr(query_service, "find_meal_by_id")
        assert hasattr(query_service, "find_meals_by_user")

    @pytest.mark.asyncio
    async def test_health_check_always_enabled(self) -> None:
        """Test health check - always enabled in V2."""
        service = MealIntegrationService()
        health = await service.health_check()

        assert health["meal_domain_v2"] == "enabled"
        assert health["feature_flag"] == "always_enabled"

        # Check services are available
        services = health["services"]
        assert services["meal_service"] == "available"
        assert services["query_service"] == "available"

        # Check adapters are configured
        adapters = health["adapters"]
        assert adapters["repository"] == "in_memory"
        assert adapters["product_lookup"] == "stub"
        assert adapters["nutrition_calculator"] == "stub"
        assert adapters["events"] == "logging"


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_is_meal_domain_v2_enabled_always_true(self) -> None:
        """Test that V2 is always enabled."""
        assert is_meal_domain_v2_enabled() is True

    def test_get_meal_service_always_available(self) -> None:
        """Test get_meal_service always returns service."""
        service = get_meal_service()
        assert service is not None
        assert hasattr(service, "create_meal")

    def test_get_meal_query_service_always_available(self) -> None:
        """Test get_meal_query_service always returns service."""
        service = get_meal_query_service()
        assert service is not None
        assert hasattr(service, "find_meal_by_id")

    @pytest.mark.asyncio
    async def test_meal_domain_health_check(self) -> None:
        """Test meal domain health check function."""
        health = await meal_domain_health_check()

        assert health["meal_domain_v2"] == "enabled"
        assert "services" in health
        assert "adapters" in health


class TestServiceComposition:
    """Test service composition and wiring."""

    def test_services_properly_wired(self) -> None:
        """Test that services are properly wired together."""
        integration_service = get_meal_integration_service()
        meal_service = get_meal_service()
        query_service = get_meal_query_service()

        # All services should be available
        assert integration_service is not None
        assert meal_service is not None
        assert query_service is not None

        # Services should be the same instances returned by integration
        assert meal_service is integration_service.get_meal_service()
        assert query_service is integration_service.get_query_service()

    def test_adapter_composition(self) -> None:
        """Test that adapters are properly composed."""
        service = get_meal_integration_service()

        # Service should be properly initialized
        assert service.is_enabled()

        # Should have all required services
        meal_service = service.get_meal_service()
        query_service = service.get_query_service()

        assert meal_service is not None
        assert query_service is not None
