"""Meal application services - business logic coordination.

Application layer services that orchestrate domain operations,
manage transactions, and coordinate with external dependencies.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from ..model import Meal, MealId, UserId
from ..port import (
    MealEventPort,
    MealRepositoryPort,
    NutritionCalculatorPort,
    ProductLookupPort,
)


class MealService:
    """Core meal management service.

    Orchestrates meal CRUD operations with nutritional enrichment,
    event publishing, and business rule enforcement.
    """

    def __init__(
        self,
        meal_repository: MealRepositoryPort,
        nutrition_calculator: NutritionCalculatorPort,
        product_lookup: ProductLookupPort,
        event_publisher: MealEventPort,
    ) -> None:
        self._meal_repository = meal_repository
        self._nutrition_calculator = nutrition_calculator
        self._product_lookup = product_lookup
        self._event_publisher = event_publisher

    async def create_meal(
        self,
        user_id: str,
        name: str,
        quantity_g: float,
        timestamp: Optional[datetime] = None,
        barcode: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        auto_enrich: bool = True,
        image_url: Optional[str] = None,
    ) -> Meal:
        """Create new meal with optional nutritional enrichment."""
        # Convert to domain types
        user_id_vo = UserId.from_string(user_id)
        meal_id = MealId.generate()

        # Use current time if not provided
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Check for duplicate using idempotency key
        if idempotency_key:
            existing = await self._meal_repository.find_by_idempotency_key(
                user_id_vo, idempotency_key
            )
            if existing:
                return existing

        # Create initial meal
        meal = Meal(
            id=meal_id,
            user_id=user_id_vo,
            name=name,
            quantity_g=quantity_g,
            timestamp=timestamp,
            barcode=barcode,
            idempotency_key=idempotency_key,
            image_url=image_url,
        )

        # Enrich with nutritional data if requested
        if auto_enrich:
            meal = await self._enrich_meal_nutrients(meal)

        # Persist meal
        await self._meal_repository.save(meal)

        # Publish event
        await self._event_publisher.meal_created(meal)

        return meal

    async def get_meal(self, meal_id: str) -> Optional[Meal]:
        """Retrieve meal by ID."""
        meal_id_vo = MealId.from_string(meal_id)
        return await self._meal_repository.find_by_id(meal_id_vo)

    async def get_user_meals(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Meal]:
        """Get meals for specific user with pagination."""
        user_id_vo = UserId.from_string(user_id)
        return await self._meal_repository.find_by_user_id(user_id_vo, limit=limit, offset=offset)

    async def update_meal(
        self,
        meal_id: str,
        name: Optional[str] = None,
        quantity_g: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        barcode: Optional[str] = None,
        recalculate_nutrients: bool = True,
    ) -> Optional[Meal]:
        """Update existing meal with optional nutrient recalculation."""
        meal_id_vo = MealId.from_string(meal_id)

        # Find existing meal
        existing_meal = await self._meal_repository.find_by_id(meal_id_vo)
        if not existing_meal:
            return None

        # Apply basic updates
        updated_meal = existing_meal.update_basic_info(
            name=name,
            timestamp=timestamp,
            barcode=barcode,
        )

        # Apply quantity change if provided
        if quantity_g is not None:
            updated_meal = updated_meal.change_quantity(quantity_g)

        # Recalculate nutrients if needed
        if recalculate_nutrients and updated_meal.should_recalculate_nutrients(
            new_quantity_g=quantity_g,
            new_barcode=barcode,
        ):
            updated_meal = await self._enrich_meal_nutrients(updated_meal)

        # Persist changes
        await self._meal_repository.save(updated_meal)

        # Publish event
        await self._event_publisher.meal_updated(existing_meal, updated_meal)

        return updated_meal

    async def delete_meal(self, meal_id: str) -> bool:
        """Delete meal by ID."""
        meal_id_vo = MealId.from_string(meal_id)

        # Find meal for event
        meal = await self._meal_repository.find_by_id(meal_id_vo)

        # Delete meal
        deleted = await self._meal_repository.delete(meal_id_vo)

        # Publish event if meal existed
        if deleted and meal:
            await self._event_publisher.meal_deleted(meal)

        return deleted

    async def recalculate_nutrients(self, meal_id: str) -> Optional[Meal]:
        """Force recalculation of meal nutrients."""
        meal_id_vo = MealId.from_string(meal_id)

        # Find existing meal
        existing_meal = await self._meal_repository.find_by_id(meal_id_vo)
        if not existing_meal:
            return None

        # Recalculate nutrients
        enriched_meal = await self._enrich_meal_nutrients(existing_meal)

        # Persist if nutrients changed
        if enriched_meal.nutrients != existing_meal.nutrients:
            await self._meal_repository.save(enriched_meal)
            await self._event_publisher.nutrients_calculated(enriched_meal)

        return enriched_meal

    async def _enrich_meal_nutrients(self, meal: Meal) -> Meal:
        """Enrich meal with nutritional information."""
        try:
            # Try barcode lookup first
            if meal.has_barcode() and meal.barcode is not None:
                product_info = await self._product_lookup.lookup_by_barcode(meal.barcode)
                if product_info:
                    nutrients = product_info.enrich_meal_with_quantity(meal.quantity_g)
                    # Update nutrients but preserve user-provided image_url
                    # Priority: 1. user image_url, 2. product image_url, 3. None
                    updated_meal = meal.update_nutrients(nutrients)
                    if not meal.image_url and product_info.image_url:
                        from dataclasses import replace

                        updated_meal = replace(updated_meal, image_url=product_info.image_url)
                    return updated_meal

            # Fallback to nutrition calculator
            nutrient_profile = await self._nutrition_calculator.calculate_nutrients(
                meal.name, meal.quantity_g, meal.barcode
            )

            if nutrient_profile:
                nutrients = nutrient_profile.scale_to_quantity(meal.quantity_g)
                return meal.update_nutrients(nutrients)

        except Exception:
            # Log error but don't fail meal creation
            # TODO: Add proper logging
            pass

        return meal


class MealQueryService:
    """Read-only meal query service.

    Optimized for read operations and reporting.
    Separated from write operations for CQRS pattern.
    """

    def __init__(self, meal_repository: MealRepositoryPort) -> None:
        self._meal_repository = meal_repository

    async def find_meal_by_id(self, meal_id: str) -> Optional[Meal]:
        """Find meal by unique identifier."""
        meal_id_vo = MealId.from_string(meal_id)
        return await self._meal_repository.find_by_id(meal_id_vo)

    async def find_meals_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Meal]:
        """Find meals for user with pagination."""
        user_id_vo = UserId.from_string(user_id)
        return await self._meal_repository.find_by_user_id(user_id_vo, limit=limit, offset=offset)

    async def meal_exists(self, meal_id: str) -> bool:
        """Check if meal exists."""
        meal_id_vo = MealId.from_string(meal_id)
        return await self._meal_repository.exists(meal_id_vo)

    async def calculate_daily_totals(
        self, user_id: str, date: datetime
    ) -> dict[str, str | int | float]:
        """Calculate daily nutritional totals for user."""
        # This would filter meals by date and sum nutrients
        # Implementation depends on repository date filtering capabilities
        user_id_vo = UserId.from_string(user_id)
        meals = await self._meal_repository.find_by_user_id(user_id_vo)

        # Filter by date (simplified - would need date range filtering)
        daily_meals = [meal for meal in meals if meal.timestamp.date() == date.date()]

        # Sum nutrients
        total_calories = 0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0

        for meal in daily_meals:
            if meal.nutrients:
                if meal.nutrients.calories:
                    total_calories += meal.nutrients.calories
                if meal.nutrients.protein:
                    total_protein += meal.nutrients.protein
                if meal.nutrients.carbs:
                    total_carbs += meal.nutrients.carbs
                if meal.nutrients.fat:
                    total_fat += meal.nutrients.fat

        return {
            "date": date.date().isoformat(),
            "meal_count": len(daily_meals),
            "total_calories": total_calories,
            "total_protein": round(total_protein, 2),
            "total_carbs": round(total_carbs, 2),
            "total_fat": round(total_fat, 2),
        }


__all__ = [
    "MealService",
    "MealQueryService",
]
