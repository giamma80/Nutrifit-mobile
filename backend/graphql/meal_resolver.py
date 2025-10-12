"""GraphQL meal resolver with domain integration and feature flag support."""

from __future__ import annotations

import os
from typing import Any, Optional

from strawberry import Info
from graphql import GraphQLError

from graphql.types_meal import MealEntry, LogMealInput, UpdateMealInput
from domain.meal.integration import (
    get_meal_integration_service,
    is_meal_domain_v2_enabled,
)


class GraphQLMealResolver:
    """GraphQL resolver with domain integration and feature flag control."""

    def __init__(self) -> None:
        self._feature_enabled = self._check_feature_flag()

    def _check_feature_flag(self) -> bool:
        """Check MEAL_GRAPHQL_V2 feature flag."""
        return os.getenv("MEAL_GRAPHQL_V2", "false").lower() == "true"

    async def log_meal(self, info: Info[Any, Any], input: LogMealInput) -> MealEntry:
        """Log meal with feature flag routing."""
        if self._feature_enabled and is_meal_domain_v2_enabled():
            return await self._log_meal_domain(info, input)
        else:
            return await self._log_meal_legacy(info, input)

    async def update_meal(self, info: Info[Any, Any], input: UpdateMealInput) -> MealEntry:
        """Update meal with feature flag routing."""
        # For now, always use legacy until domain methods implemented
        return await self._update_meal_legacy(info, input)

    async def delete_meal(self, info: Info[Any, Any], id: str) -> bool:
        """Delete meal with feature flag routing."""
        # For now, always use legacy until domain methods implemented
        return await self._delete_meal_legacy(info, id)

    async def _log_meal_legacy(self, info: Info[Any, Any], input: LogMealInput) -> MealEntry:
        """Legacy meal creation logic with nutrient enrichment."""
        if input.quantity_g <= 0:
            raise GraphQLError("INVALID_QUANTITY: quantity_g deve essere > 0")

        # Import required modules locally to avoid circular imports
        import uuid
        import datetime as dt
        import dataclasses
        from typing import Dict, Optional, cast
        from repository.meals import meal_repo, MealRecord
        from nutrients import NUTRIENT_FIELDS
        from graphql.types_meal import enrich_from_product as _enrich_from_product
        from cache import cache
        from openfoodfacts import adapter
        from graphql.types_product import Product, map_product as _map_product

        # Constants
        DEFAULT_USER_ID = "default"
        PRODUCT_CACHE_TTL_S = 3600

        ts = input.timestamp or dt.datetime.utcnow().isoformat() + "Z"
        user_id = input.user_id or DEFAULT_USER_ID

        # Idempotency key logic matching app.py
        base_ts_for_key = input.timestamp or ""
        idempotency_key = input.idempotency_key or (
            f"{input.name.lower()}|{round(input.quantity_g, 3)}|"
            f"{base_ts_for_key}|{input.barcode or ''}|{user_id}"
        )

        existing = meal_repo.find_by_idempotency(user_id, idempotency_key)
        if existing:
            return MealEntry(**dataclasses.asdict(existing))

        # Initialize nutrients
        nutrients: Dict[str, Optional[float]] = {k: None for k in NUTRIENT_FIELDS}

        # Nutrient enrichment from barcode
        prod: Optional[Product] = None
        if input.barcode:
            key = f"product:{input.barcode}"
            prod_cached = cache.get(key)
            if prod_cached:
                prod = cast(Product, prod_cached)
            else:
                try:
                    from typing import cast

                    dto = await adapter.fetch_product(input.barcode)
                    prod = _map_product(cast(Any, dto))
                    cache.set(key, prod, PRODUCT_CACHE_TTL_S)
                except adapter.ProductNotFound:
                    prod = None
                except adapter.OpenFoodFactsError:
                    prod = None

        if prod:
            nutrients = _enrich_from_product(prod, input.quantity_g)

        meal = MealRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=input.name,
            quantity_g=input.quantity_g,
            timestamp=ts,
            barcode=input.barcode,
            idempotency_key=idempotency_key,
            nutrient_snapshot_json=(
                __import__("json").dumps(
                    {k: nutrients[k] for k in NUTRIENT_FIELDS},
                    sort_keys=True,
                )
                if prod
                else None
            ),
            calories=(
                nutrients["calories"]
                if nutrients["calories"] is None
                else int(nutrients["calories"])
            ),
            protein=nutrients["protein"],
            carbs=nutrients["carbs"],
            fat=nutrients["fat"],
            fiber=nutrients["fiber"],
            sugar=nutrients["sugar"],
            sodium=nutrients["sodium"],
        )

        meal_repo.add(meal)
        return MealEntry(**dataclasses.asdict(meal))

    async def _log_meal_domain(self, info: Info[Any, Any], input: LogMealInput) -> MealEntry:
        """Create meal using domain service."""
        if input.quantity_g <= 0:
            raise GraphQLError("INVALID_QUANTITY: quantity_g deve essere > 0")

        # Get domain service
        meal_service = get_meal_integration_service().get_meal_service()
        if not meal_service:
            raise GraphQLError("DOMAIN_ERROR: Meal service not available")

        # For now return legacy implementation
        # Domain implementation will be completed later
        return await self._log_meal_legacy(info, input)

    async def _update_meal_legacy(self, info: Info[Any, Any], input: UpdateMealInput) -> MealEntry:
        """Legacy meal update logic."""
        from repository.meals import meal_repo

        rec = meal_repo.get(input.id)
        if not rec:
            raise GraphQLError("NOT_FOUND: meal id inesistente")

        if input.user_id and input.user_id != rec.user_id:
            raise GraphQLError("FORBIDDEN: user mismatch")

        from typing import Dict, Any

        update_fields: Dict[str, Any] = {}
        if input.name is not None:
            update_fields["name"] = input.name
        if input.quantity_g is not None:
            update_fields["quantity_g"] = input.quantity_g
        if input.timestamp is not None:
            update_fields["timestamp"] = input.timestamp
        if input.barcode is not None:
            update_fields["barcode"] = input.barcode

        updated = meal_repo.update(input.id, **update_fields)
        assert updated is not None

        return MealEntry(
            id=updated.id,
            user_id=updated.user_id,
            name=updated.name,
            quantity_g=updated.quantity_g,
            timestamp=updated.timestamp,
            barcode=updated.barcode,
            idempotency_key=updated.idempotency_key,
            nutrient_snapshot_json=updated.nutrient_snapshot_json,
            calories=updated.calories,
            protein=updated.protein,
            carbs=updated.carbs,
            fat=updated.fat,
            fiber=updated.fiber,
            sugar=updated.sugar,
            sodium=updated.sodium,
        )

    async def _delete_meal_legacy(self, info: Info[Any, Any], id: str) -> bool:
        """Legacy meal delete logic."""
        from repository.meals import meal_repo

        return meal_repo.delete(id)


# Singleton instance
_meal_resolver: Optional[GraphQLMealResolver] = None


def get_meal_resolver() -> GraphQLMealResolver:
    """Get singleton meal resolver."""
    global _meal_resolver
    if _meal_resolver is None:
        _meal_resolver = GraphQLMealResolver()
    return _meal_resolver
