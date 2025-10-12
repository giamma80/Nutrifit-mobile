"""Test integration layer for meal domain."""

import os
from unittest.mock import patch

import pytest

from domain.meal.integration import (
    MealIntegrationService,
    _reset_integration_service,
    get_meal_integration_service,
    get_meal_query_service,
    get_meal_service,
    is_meal_domain_v2_enabled,
    meal_domain_health_check,
)


class TestMealIntegrationService:
    """Test meal integration service with feature flag control."""

    def test_feature_disabled_by_default(self):
        """Test that meal domain v2 is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            service = MealIntegrationService()

            assert not service.is_enabled()
            assert service.get_meal_service() is None
            assert service.get_query_service() is None

    def test_feature_enabled_with_flag(self):
        """Test that meal domain v2 can be enabled with flag."""
        with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
            service = MealIntegrationService()

            assert service.is_enabled()
            assert service.get_meal_service() is not None
            assert service.get_query_service() is not None

    def test_feature_flag_case_insensitive(self):
        """Test that feature flag is case insensitive."""
        for value in ["TRUE", "True", "true"]:
            with patch.dict(os.environ, {"MEAL_DOMAIN_V2": value}):
                service = MealIntegrationService()
                assert service.is_enabled()

    def test_feature_flag_false_values(self):
        """Test that various false values disable the feature."""
        for value in ["false", "FALSE", "False", "0", "no", ""]:
            with patch.dict(os.environ, {"MEAL_DOMAIN_V2": value}):
                service = MealIntegrationService()
                assert not service.is_enabled()

    @pytest.mark.asyncio
    async def test_health_check_disabled(self):
        """Test health check when feature is disabled."""
        with patch.dict(os.environ, {}, clear=True):
            service = MealIntegrationService()
            health = await service.health_check()

            assert health["meal_domain_v2"] == "disabled"
            assert health["feature_flag"] == "MEAL_DOMAIN_V2=false"

    @pytest.mark.asyncio
    async def test_health_check_enabled(self):
        """Test health check when feature is enabled."""
        with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
            service = MealIntegrationService()
            health = await service.health_check()

            assert health["meal_domain_v2"] == "enabled"
            assert health["feature_flag"] == "MEAL_DOMAIN_V2=true"

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

    def test_is_meal_domain_v2_enabled_default(self):
        """Test default state is disabled."""
        with patch.dict(os.environ, {}, clear=True):
            _reset_integration_service()
            assert not is_meal_domain_v2_enabled()

    def test_is_meal_domain_v2_enabled_true(self):
        """Test enabled state."""
        with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
            _reset_integration_service()
            assert is_meal_domain_v2_enabled()

    def test_get_meal_service_disabled(self):
        """Test get_meal_service returns None when disabled."""
        with patch.dict(os.environ, {}, clear=True):
            _reset_integration_service()
            assert get_meal_service() is None

    def test_get_meal_service_enabled(self):
        """Test get_meal_service returns service when enabled."""
        with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
            _reset_integration_service()
            service = get_meal_service()
            assert service is not None

    def test_get_meal_query_service_disabled(self):
        """Test get_meal_query_service returns None when disabled."""
        with patch.dict(os.environ, {}, clear=True):
            _reset_integration_service()
            assert get_meal_query_service() is None

    def test_get_meal_query_service_enabled(self):
        """Test get_meal_query_service returns service when enabled."""
        with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
            _reset_integration_service()
            service = get_meal_query_service()
            assert service is not None

    def test_singleton_behavior(self):
        """Test that get_meal_integration_service returns same instance."""
        with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
            _reset_integration_service()
            service1 = get_meal_integration_service()
            service2 = get_meal_integration_service()

            assert service1 is service2

    @pytest.mark.asyncio
    async def test_meal_domain_health_check(self):
        """Test global health check function."""
        with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
            _reset_integration_service()
            health = await meal_domain_health_check()

            assert health["meal_domain_v2"] == "enabled"
            assert "services" in health
            assert "adapters" in health


class TestServiceComposition:
    """Test service composition with adapters."""

    def test_services_properly_wired(self):
        """Test that services are properly wired with adapters."""
        with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
            service = MealIntegrationService()

            meal_service = service.get_meal_service()
            query_service = service.get_query_service()

            # Verify services are not None
            assert meal_service is not None
            assert query_service is not None

            # Verify services have proper types
            from domain.meal.service import MealService, MealQueryService

            assert isinstance(meal_service, MealService)
            assert isinstance(query_service, MealQueryService)

    def test_adapter_composition(self):
        """Test that adapters are properly composed."""
        with patch.dict(os.environ, {"MEAL_DOMAIN_V2": "true"}):
            service = MealIntegrationService()
            meal_service = service.get_meal_service()

            # Services should be available (adapter composition worked)
            assert meal_service is not None

            # Integration test: services should be usable
            # (detailed functionality tested in service tests)
