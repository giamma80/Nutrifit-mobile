"""Meal domain - DDD implementation for meal management.

Complete domain layer with aggregates, services, ports, and value objects
following Domain-Driven Design principles. Includes integration layer for
feature flag controlled service composition.
"""

from .integration import (
    MealIntegrationService,
    get_meal_integration_service,
    get_meal_query_service,
    get_meal_service,
    is_meal_domain_v2_enabled,
    meal_domain_health_check,
)
from .model import (
    Meal,
    MealId,
    NutrientProfile,
    ProductInfo,
    ScaledNutrients,
    UserId,
)
from .port import (
    MealEventPort,
    MealRepositoryPort,
    NutritionCalculatorPort,
    ProductLookupPort,
)
from .service import MealQueryService, MealService

__all__ = [
    # Domain Models
    "Meal",
    "MealId",
    "NutrientProfile",
    "ProductInfo",
    "ScaledNutrients",
    "UserId",
    # Ports
    "MealEventPort",
    "MealRepositoryPort",
    "NutritionCalculatorPort",
    "ProductLookupPort",
    # Services
    "MealService",
    "MealQueryService",
    # Integration
    "MealIntegrationService",
    "get_meal_integration_service",
    "get_meal_service",
    "get_meal_query_service",
    "is_meal_domain_v2_enabled",
    "meal_domain_health_check",
]
