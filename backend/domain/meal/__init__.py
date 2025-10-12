"""Meal domain - DDD implementation for meal management.

Complete domain layer with aggregates, services, ports, and value objects
following Domain-Driven Design principles.
"""

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
]
