"""Integration service for meal domain with existing GraphQL layer."""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional

from .service import MealService, MealQueryService

logger = logging.getLogger("domain.meal.integration")


class MealIntegrationService:
    """Integration layer for meal domain v2."""

    def __init__(self) -> None:
        self._meal_service: MealService
        self._query_service: MealQueryService

        try:
            self._initialize_services()
            logger.info("Meal domain V2 initialized")
        except Exception as e:
            logger.error(f"Failed to initialize meal V2: {e}")
            raise RuntimeError(f"Critical: Meal service failed to initialize: {e}")

    def _initialize_services(self) -> None:
        """Initialize meal domain services with adapters."""
        # Initialize adapters
        from domain.meal.adapters.meal_repository_adapter import MealRepositoryAdapter
        from domain.meal.adapters.nutrition_calculator_adapter import (
            StubNutritionCalculatorAdapter,
        )
        from domain.meal.adapters.product_lookup_adapter import OpenFoodFactsAdapter
        from domain.meal.adapters.meal_event_adapter import LoggingMealEventAdapter
        from repository.meals import meal_repo

        repository_adapter = MealRepositoryAdapter(meal_repo)

        # Use stub nutrition calculator (USDA integration is handled elsewhere)
        nutrition_calculator_adapter = StubNutritionCalculatorAdapter()

        # Use OpenFoodFacts for product lookup
        product_lookup_adapter = OpenFoodFactsAdapter()

        event_adapter = LoggingMealEventAdapter()

        # Initialize services
        self._meal_service = MealService(
            meal_repository=repository_adapter,
            nutrition_calculator=nutrition_calculator_adapter,
            product_lookup=product_lookup_adapter,
            event_publisher=event_adapter,
        )

        self._query_service = MealQueryService(meal_repository=repository_adapter)

    def get_meal_service(self) -> MealService:
        """Get meal service."""
        return self._meal_service

    def get_query_service(self) -> MealQueryService:
        """Get query service."""
        return self._query_service

    def is_enabled(self) -> bool:
        """Check if meal domain v2 is enabled."""
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Health check for meal domain services."""
        try:
            # Test basic service availability
            meal_service_available = self._meal_service is not None
            query_service_available = self._query_service is not None

            return {
                "meal_domain_v2": "enabled",
                "feature_flag": "always_enabled",
                "services": {
                    "meal_service": ("available" if meal_service_available else "unavailable"),
                    "query_service": ("available" if query_service_available else "unavailable"),
                },
                "adapters": {
                    "repository": "in_memory",
                    "product_lookup": "stub",
                    "nutrition_calculator": "stub",
                    "events": "logging",
                },
            }
        except Exception as e:
            return {
                "meal_domain_v2": "error",
                "feature_flag": "MEAL_DOMAIN_V2=true",
                "error": str(e),
            }


# Global integration service instance
_integration_service: Optional[MealIntegrationService] = None


def get_meal_integration_service() -> MealIntegrationService:
    """Get or create the global meal integration service."""
    global _integration_service
    if _integration_service is None:
        _integration_service = MealIntegrationService()
    return _integration_service


def _reset_integration_service() -> None:
    """Reset the global integration service (for testing only)."""
    global _integration_service
    _integration_service = None


# Convenience functions for service access
def get_meal_service() -> MealService:
    """Get meal service."""
    return get_meal_integration_service().get_meal_service()


def get_meal_query_service() -> MealQueryService:
    """Get meal query service."""
    return get_meal_integration_service().get_query_service()


def is_meal_domain_v2_enabled() -> bool:
    """Check if meal domain v2 is enabled - always True now."""
    return True


async def meal_domain_health_check() -> Dict[str, Any]:
    """Perform health check on meal domain services."""
    return await get_meal_integration_service().health_check()
