"""Meal domain adapters - infrastructure integrations.

Adapters that implement domain ports by bridging to external systems:
- Repository adapters for data persistence
- Product lookup adapters for barcode databases
- Nutrition calculation adapters for AI and legacy systems
- Event publishing adapters for domain events
"""

from .meal_event_adapter import (
    CompositeMealEventAdapter,
    LoggingMealEventAdapter,
    NullMealEventAdapter,
)
from .meal_repository_adapter import MealRepositoryAdapter
from .nutrition_calculator_adapter import (
    CompositeNutritionCalculatorAdapter,
    LegacyNutritionAdapter,
    StubNutritionCalculatorAdapter,
)
from .product_lookup_adapter import (
    OpenFoodFactsAdapter,
    StubProductLookupAdapter,
)

__all__ = [
    # Repository adapters
    "MealRepositoryAdapter",
    # Product lookup adapters
    "StubProductLookupAdapter",
    "OpenFoodFactsAdapter",
    # Nutrition calculation adapters
    "StubNutritionCalculatorAdapter",
    "LegacyNutritionAdapter",
    "CompositeNutritionCalculatorAdapter",
    # Event adapters
    "LoggingMealEventAdapter",
    "NullMealEventAdapter",
    "CompositeMealEventAdapter",
]
