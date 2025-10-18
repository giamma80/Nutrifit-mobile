"""GraphQL meal resolver with V2 domain integration."""

from __future__ import annotations

from typing import Any, Optional

from strawberry import Info
from graphql import GraphQLError

from graphql.types_meal import MealEntry, LogMealInput, UpdateMealInput
from domain.meal.integration import get_meal_integration_service


class GraphQLMealResolver:
    """GraphQL resolver with V2 domain integration - always active."""

    def __init__(self) -> None:
        # V2 domain is always active
        pass

    async def log_meal(self, info: Info[Any, Any], input: LogMealInput) -> MealEntry:
        """Log meal using V2 domain."""
        return await self._log_meal_domain(info, input)

    async def update_meal(self, info: Info[Any, Any], input: UpdateMealInput) -> MealEntry:
        """Update meal using V2 domain."""
        return await self._update_meal_domain(info, input)

    async def delete_meal(self, info: Info[Any, Any], id: str) -> bool:
        """Delete meal using V2 domain."""
        return await self._delete_meal_domain(info, id)

    async def _log_meal_domain(self, info: Info[Any, Any], input: LogMealInput) -> MealEntry:
        """Create meal using domain service."""
        if input.quantity_g <= 0:
            raise GraphQLError("INVALID_QUANTITY: quantity_g deve essere > 0")

        # Get domain service
        meal_service = get_meal_integration_service().get_meal_service()
        if not meal_service:
            raise GraphQLError("DOMAIN_ERROR: Meal service not available")

        import datetime as dt
        import dataclasses

        # Parse timestamp if provided
        if input.timestamp:
            try:
                ts_str = input.timestamp.replace("Z", "+00:00")
                ts_datetime = dt.datetime.fromisoformat(ts_str)
            except ValueError:
                ts_datetime = dt.datetime.utcnow()
        else:
            ts_datetime = dt.datetime.utcnow()

        user_id = input.user_id or "default"

        # Generate idempotency key if not provided
        base_ts_for_key = input.timestamp or ""
        idempotency_key = input.idempotency_key or (
            f"{input.name.lower()}|{round(input.quantity_g, 3)}|"
            f"{base_ts_for_key}|{input.barcode or ''}|{user_id}"
        )

        try:
            # Create domain meal
            meal = await meal_service.create_meal(
                user_id=user_id,
                name=input.name,
                quantity_g=input.quantity_g,
                timestamp=ts_datetime,
                barcode=input.barcode,
                idempotency_key=idempotency_key,
                auto_enrich=True,  # Enable nutritional enrichment
                image_url=getattr(input, "photo_url", None),  # Use photo_url field
            )

            # Get nutrients from domain meal
            nutrients = meal.nutrients if hasattr(meal, "nutrients") else None

            # Create meal record for GraphQL response
            from repository.meals import MealRecord

            meal_record = MealRecord(
                id=str(meal.id),
                user_id=str(meal.user_id),
                name=meal.name,
                quantity_g=meal.quantity_g,
                timestamp=meal.timestamp.isoformat() + "Z",
                barcode=meal.barcode,
                idempotency_key=meal.idempotency_key,
                nutrient_snapshot_json=meal.nutrient_snapshot_json,
                calories=nutrients.calories if nutrients else None,
                protein=nutrients.protein if nutrients else None,
                carbs=nutrients.carbs if nutrients else None,
                fat=nutrients.fat if nutrients else None,
                fiber=nutrients.fiber if nutrients else None,
                sugar=nutrients.sugar if nutrients else None,
                sodium=nutrients.sodium if nutrients else None,
                image_url=meal.image_url,  # Use image_url from domain
            )

            return MealEntry(**dataclasses.asdict(meal_record))

        except Exception as e:
            # V2 domain error - no fallback
            import logging

            logger = logging.getLogger("graphql.meal_resolver")
            logger.error(f"Domain meal creation failed: {e}")
            raise GraphQLError(f"DOMAIN_ERROR: {e}")

    async def _update_meal_domain(self, info: Info[Any, Any], input: UpdateMealInput) -> MealEntry:
        """Update meal using domain service."""
        # Get domain service
        meal_service = get_meal_integration_service().get_meal_service()
        if not meal_service:
            raise GraphQLError("DOMAIN_ERROR: Meal service not available")

        import datetime as dt

        # Parse timestamp if provided
        if input.timestamp:
            try:
                ts_str = input.timestamp.replace("Z", "+00:00")
                ts_datetime = dt.datetime.fromisoformat(ts_str)
            except ValueError:
                ts_datetime = None
        else:
            ts_datetime = None

        try:
            # Update meal through domain service
            updated_meal = await meal_service.update_meal(
                meal_id=input.id,
                name=input.name,
                quantity_g=input.quantity_g,
                timestamp=ts_datetime,
                barcode=input.barcode,
                recalculate_nutrients=True,
            )

            if not updated_meal:
                raise GraphQLError("NOT_FOUND: meal id inesistente")

            # Check user access if provided
            if input.user_id and str(updated_meal.user_id) != input.user_id:
                raise GraphQLError("FORBIDDEN: user mismatch")

            # Convert to GraphQL response
            import dataclasses
            from repository.meals import MealRecord

            nutrients = updated_meal.nutrients if hasattr(updated_meal, "nutrients") else None

            meal_record = MealRecord(
                id=str(updated_meal.id),
                user_id=str(updated_meal.user_id),
                name=updated_meal.name,
                quantity_g=updated_meal.quantity_g,
                timestamp=updated_meal.timestamp.isoformat() + "Z",
                barcode=updated_meal.barcode,
                idempotency_key=updated_meal.idempotency_key,
                nutrient_snapshot_json=updated_meal.nutrient_snapshot_json,
                calories=nutrients.calories if nutrients else None,
                protein=nutrients.protein if nutrients else None,
                carbs=nutrients.carbs if nutrients else None,
                fat=nutrients.fat if nutrients else None,
                fiber=nutrients.fiber if nutrients else None,
                sugar=nutrients.sugar if nutrients else None,
                sodium=nutrients.sodium if nutrients else None,
                image_url=updated_meal.image_url,
            )

            return MealEntry(**dataclasses.asdict(meal_record))

        except Exception as e:
            # V2 domain error - no fallback
            import logging

            logger = logging.getLogger("graphql.meal_resolver")
            logger.error(f"Domain meal update failed: {e}")
            raise GraphQLError(f"DOMAIN_ERROR: {e}")

    async def _delete_meal_domain(self, info: Info[Any, Any], id: str) -> bool:
        """Delete meal using domain service."""
        # Get domain service
        meal_service = get_meal_integration_service().get_meal_service()
        if not meal_service:
            raise GraphQLError("DOMAIN_ERROR: Meal service not available")

        try:
            return await meal_service.delete_meal(meal_id=id)

        except Exception as e:
            # V2 domain error - no fallback
            import logging

            logger = logging.getLogger("graphql.meal_resolver")
            logger.error(f"Domain meal deletion failed: {e}")
            raise GraphQLError(f"DOMAIN_ERROR: {e}")


# Singleton pattern for GraphQL resolver
_meal_resolver: Optional[GraphQLMealResolver] = None


def get_meal_resolver() -> GraphQLMealResolver:
    """Get singleton meal resolver."""
    global _meal_resolver
    if _meal_resolver is None:
        _meal_resolver = GraphQLMealResolver()
    return _meal_resolver
