"""Meal event adapter - handles domain event publishing.

Provides event publishing capabilities for meal domain events:
- Meal lifecycle events (created, updated, deleted)
- Nutrition calculation events
- Integration with event streaming systems
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from domain.meal.model import Meal
from domain.meal.port import MealEventPort

logger = logging.getLogger(__name__)


class LoggingMealEventAdapter(MealEventPort):
    """Event adapter that logs events for debugging and development.

    Simple implementation that logs all meal events with structured data.
    Useful for development, testing, and as fallback when other systems fail.
    """

    def __init__(self, log_level: int = logging.INFO) -> None:
        self._log_level = log_level
        self._logger = logging.getLogger("domain.meal.events")
        self._logger.setLevel(log_level)

    async def meal_created(self, meal: Meal) -> None:
        """Log meal created event."""
        self._logger.log(
            self._log_level,
            "meal.created",
            extra={
                "meal_id": meal.id.value,
                "user_id": meal.user_id.value,
                "meal_name": meal.name,  # Renamed to avoid LogRecord collision
                "quantity_g": meal.quantity_g,
                "has_nutrients": meal.has_nutritional_data(),
                "has_barcode": meal.has_barcode(),
                "timestamp": meal.timestamp.isoformat(),
            },
        )

    async def meal_updated(self, old_meal: Meal, new_meal: Meal) -> None:
        """Log meal updated event."""
        changes = self._calculate_changes(old_meal, new_meal)

        self._logger.log(
            self._log_level,
            "meal.updated",
            extra={
                "meal_id": new_meal.id.value,
                "user_id": new_meal.user_id.value,
                "changes": changes,
                "timestamp": new_meal.timestamp.isoformat(),
            },
        )

    async def meal_deleted(self, meal: Meal) -> None:
        """Log meal deleted event."""
        self._logger.log(
            self._log_level,
            "meal.deleted",
            extra={
                "meal_id": meal.id.value,
                "user_id": meal.user_id.value,
                "meal_name": meal.name,  # Renamed to avoid LogRecord collision
                "timestamp": meal.timestamp.isoformat(),
            },
        )

    async def nutrients_calculated(self, meal: Meal) -> None:
        """Log nutrients calculated event."""
        nutrients_summary = {}
        if meal.nutrients:
            nutrients_summary = {
                "calories": meal.nutrients.calories,
                "protein": meal.nutrients.protein,
                "carbs": meal.nutrients.carbs,
                "fat": meal.nutrients.fat,
            }

        self._logger.log(
            self._log_level,
            "meal.nutrients_calculated",
            extra={
                "meal_id": meal.id.value,
                "user_id": meal.user_id.value,
                "nutrients": nutrients_summary,
                "timestamp": meal.timestamp.isoformat(),
            },
        )

    def _calculate_changes(self, old_meal: Meal, new_meal: Meal) -> Dict[str, Any]:
        """Calculate what changed between two meal versions."""
        changes: Dict[str, Any] = {}

        if old_meal.name != new_meal.name:
            changes["name"] = {"old": old_meal.name, "new": new_meal.name}

        if old_meal.quantity_g != new_meal.quantity_g:
            changes["quantity_g"] = {
                "old": old_meal.quantity_g,
                "new": new_meal.quantity_g,
            }

        if old_meal.barcode != new_meal.barcode:
            changes["barcode"] = {
                "old": old_meal.barcode,
                "new": new_meal.barcode,
            }

        if old_meal.timestamp != new_meal.timestamp:
            changes["timestamp"] = {
                "old": old_meal.timestamp.isoformat(),
                "new": new_meal.timestamp.isoformat(),
            }

        # Check nutrients changes
        old_calories = old_meal.total_calories()
        new_calories = new_meal.total_calories()
        if old_calories != new_calories:
            changes["calories"] = {"old": old_calories, "new": new_calories}

        return changes


class NullMealEventAdapter(MealEventPort):
    """Null object pattern implementation that does nothing.

    Useful for testing or when event publishing is disabled.
    """

    async def meal_created(self, meal: Meal) -> None:
        """No-op implementation."""
        pass

    async def meal_updated(self, old_meal: Meal, new_meal: Meal) -> None:
        """No-op implementation."""
        pass

    async def meal_deleted(self, meal: Meal) -> None:
        """No-op implementation."""
        pass

    async def nutrients_calculated(self, meal: Meal) -> None:
        """No-op implementation."""
        pass


class CompositeMealEventAdapter(MealEventPort):
    """Composite adapter that publishes to multiple event handlers.

    Enables publishing the same event to multiple systems simultaneously,
    with error isolation between handlers.
    """

    def __init__(self, *adapters: MealEventPort) -> None:
        self._adapters = adapters

    async def meal_created(self, meal: Meal) -> None:
        """Publish to all adapters."""
        for adapter in self._adapters:
            try:
                await adapter.meal_created(meal)
            except Exception as e:
                logger.error(f"Event publishing failed for {adapter.__class__.__name__}: {e}")

    async def meal_updated(self, old_meal: Meal, new_meal: Meal) -> None:
        """Publish to all adapters."""
        for adapter in self._adapters:
            try:
                await adapter.meal_updated(old_meal, new_meal)
            except Exception as e:
                logger.error(f"Event publishing failed for {adapter.__class__.__name__}: {e}")

    async def meal_deleted(self, meal: Meal) -> None:
        """Publish to all adapters."""
        for adapter in self._adapters:
            try:
                await adapter.meal_deleted(meal)
            except Exception as e:
                logger.error(f"Event publishing failed for {adapter.__class__.__name__}: {e}")

    async def nutrients_calculated(self, meal: Meal) -> None:
        """Publish to all adapters."""
        for adapter in self._adapters:
            try:
                await adapter.nutrients_calculated(meal)
            except Exception as e:
                logger.error(f"Event publishing failed for {adapter.__class__.__name__}: {e}")
