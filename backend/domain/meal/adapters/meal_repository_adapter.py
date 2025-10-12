"""Meal repository adapter - bridges domain model to legacy repository.

Converts between Meal domain objects and MealRecord repository objects,
maintaining separation of concerns and enabling gradual migration.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from domain.meal.model import Meal, MealId, ScaledNutrients, UserId
from domain.meal.port import MealRepositoryPort
from repository.meals import MealRecord, MealRepository


class MealRepositoryAdapter(MealRepositoryPort):
    """Adapter that bridges Meal domain to legacy MealRepository.
    
    Handles conversion between domain objects and repository records,
    preserving business logic isolation while enabling legacy integration.
    """

    def __init__(self, legacy_repo: MealRepository) -> None:
        self._legacy_repo = legacy_repo

    async def save(self, meal: Meal) -> None:
        """Save domain meal by converting to repository record."""
        # Check if meal exists to decide update vs create
        existing_record = self._legacy_repo.get(meal.id.value)
        
        if existing_record:
            # Update existing record
            updates = self._meal_to_update_fields(meal)
            self._legacy_repo.update(meal.id.value, **updates)
        else:
            # Create new record
            record = self._meal_to_record(meal)
            self._legacy_repo.add(record)

    async def find_by_id(self, meal_id: MealId) -> Optional[Meal]:
        """Find meal by ID, converting from repository record."""
        record = self._legacy_repo.get(meal_id.value)
        return self._record_to_meal(record) if record else None

    async def find_by_user_id(
        self,
        user_id: UserId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Meal]:
        """Find meals for user with pagination."""
        # Legacy repo doesn't support offset, so we fetch more and slice
        records = self._legacy_repo.list(
            user_id=user_id.value,
            limit=limit + offset,
            after=None,
            before=None,
        )
        
        # Apply offset manually
        sliced_records = records[offset:offset + limit]
        
        return [
            self._record_to_meal(record)
            for record in sliced_records
            if record is not None
        ]

    async def find_by_idempotency_key(
        self,
        user_id: UserId,
        idempotency_key: str,
    ) -> Optional[Meal]:
        """Find meal by idempotency key for deduplication."""
        record = self._legacy_repo.find_by_idempotency(
            user_id.value,
            idempotency_key
        )
        return self._record_to_meal(record) if record else None

    async def delete(self, meal_id: MealId) -> bool:
        """Delete meal from storage."""
        return self._legacy_repo.delete(meal_id.value)

    async def exists(self, meal_id: MealId) -> bool:
        """Check if meal exists in storage."""
        return self._legacy_repo.get(meal_id.value) is not None

    def _meal_to_record(self, meal: Meal) -> MealRecord:
        """Convert domain Meal to repository MealRecord."""
        return MealRecord(
            id=meal.id.value,
            user_id=meal.user_id.value,
            name=meal.name,
            quantity_g=meal.quantity_g,
            timestamp=meal.timestamp.isoformat(),
            barcode=meal.barcode,
            idempotency_key=meal.idempotency_key,
            nutrient_snapshot_json=meal.nutrient_snapshot_json,
            # Extract individual nutrients for legacy compatibility
            calories=meal.nutrients.calories if meal.nutrients else None,
            protein=meal.nutrients.protein if meal.nutrients else None,
            carbs=meal.nutrients.carbs if meal.nutrients else None,
            fat=meal.nutrients.fat if meal.nutrients else None,
            fiber=meal.nutrients.fiber if meal.nutrients else None,
            sugar=meal.nutrients.sugar if meal.nutrients else None,
            sodium=meal.nutrients.sodium if meal.nutrients else None,
        )

    def _meal_to_update_fields(self, meal: Meal) -> dict:
        """Convert domain Meal to update fields dict."""
        fields = {
            "name": meal.name,
            "quantity_g": meal.quantity_g,
            "timestamp": meal.timestamp.isoformat(),
            "barcode": meal.barcode,
            "idempotency_key": meal.idempotency_key,
            "nutrient_snapshot_json": meal.nutrient_snapshot_json,
        }
        
        # Add individual nutrients
        if meal.nutrients:
            fields.update({
                "calories": meal.nutrients.calories,
                "protein": meal.nutrients.protein,
                "carbs": meal.nutrients.carbs,
                "fat": meal.nutrients.fat,
                "fiber": meal.nutrients.fiber,
                "sugar": meal.nutrients.sugar,
                "sodium": meal.nutrients.sodium,
            })
        else:
            # Clear nutrients if none provided
            fields.update({
                "calories": None,
                "protein": None,
                "carbs": None,
                "fat": None,
                "fiber": None,
                "sugar": None,
                "sodium": None,
            })
        
        return fields

    def _record_to_meal(self, record: MealRecord) -> Meal:
        """Convert repository MealRecord to domain Meal."""
        # Parse timestamp
        timestamp = datetime.fromisoformat(
            record.timestamp.replace('Z', '+00:00')
        )
        
        # Build nutrients if any are present
        nutrients = None
        if any([
            record.calories is not None,
            record.protein is not None,
            record.carbs is not None,
            record.fat is not None,
            record.fiber is not None,
            record.sugar is not None,
            record.sodium is not None,
        ]):
            nutrients = ScaledNutrients(
                calories=record.calories,
                protein=record.protein,
                carbs=record.carbs,
                fat=record.fat,
                fiber=record.fiber,
                sugar=record.sugar,
                sodium=record.sodium,
            )
        
        return Meal(
            id=MealId.from_string(record.id),
            user_id=UserId.from_string(record.user_id),
            name=record.name,
            quantity_g=record.quantity_g,
            timestamp=timestamp,
            nutrients=nutrients,
            barcode=record.barcode,
            idempotency_key=record.idempotency_key,
            nutrient_snapshot_json=record.nutrient_snapshot_json,
        )
