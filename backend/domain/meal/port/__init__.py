"""Meal domain ports - output interfaces for external dependencies.

Defines contracts for persistence, external services, and integrations
following hexagonal architecture principles.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ..model import Meal, MealId, UserId, ProductInfo, NutrientProfile


class MealRepositoryPort(ABC):
    """Port for meal persistence operations."""

    @abstractmethod
    async def save(self, meal: Meal) -> None:
        """Save meal to storage."""
        ...

    @abstractmethod
    async def find_by_id(self, meal_id: MealId) -> Optional[Meal]:
        """Find meal by unique identifier."""
        ...

    @abstractmethod
    async def find_by_user_id(
        self,
        user_id: UserId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Meal]:
        """Find meals for specific user with pagination."""
        ...

    @abstractmethod
    async def find_by_idempotency_key(
        self,
        user_id: UserId,
        idempotency_key: str,
    ) -> Optional[Meal]:
        """Find meal by idempotency key for deduplication."""
        ...

    @abstractmethod
    async def delete(self, meal_id: MealId) -> bool:
        """Delete meal from storage. Returns True if meal existed."""
        ...

    @abstractmethod
    async def exists(self, meal_id: MealId) -> bool:
        """Check if meal exists in storage."""
        ...


class ProductLookupPort(ABC):
    """Port for external product information lookup."""

    @abstractmethod
    async def lookup_by_barcode(self, barcode: str) -> Optional[ProductInfo]:
        """Look up product information by barcode."""
        ...

    @abstractmethod
    async def search_products(self, query: str, limit: int = 10) -> List[ProductInfo]:
        """Search products by text query."""
        ...


class NutritionCalculatorPort(ABC):
    """Port for nutritional calculations and enrichment."""

    @abstractmethod
    async def calculate_nutrients(
        self,
        meal_name: str,
        quantity_g: float,
        barcode: Optional[str] = None,
    ) -> Optional[NutrientProfile]:
        """Calculate nutritional profile for meal."""
        ...

    @abstractmethod
    async def enrich_from_ai(
        self,
        meal_name: str,
        quantity_g: float,
    ) -> Optional[NutrientProfile]:
        """Use AI to estimate nutritional information."""
        ...


class MealEventPort(ABC):
    """Port for meal domain events."""

    @abstractmethod
    async def meal_created(self, meal: Meal) -> None:
        """Publish meal created event."""
        ...

    @abstractmethod
    async def meal_updated(self, old_meal: Meal, new_meal: Meal) -> None:
        """Publish meal updated event."""
        ...

    @abstractmethod
    async def meal_deleted(self, meal: Meal) -> None:
        """Publish meal deleted event."""
        ...

    @abstractmethod
    async def nutrients_calculated(self, meal: Meal) -> None:
        """Publish nutrients calculated event."""
        ...


__all__ = [
    "MealRepositoryPort",
    "ProductLookupPort",
    "NutritionCalculatorPort",
    "MealEventPort",
]
