from __future__ import annotations

from typing import Optional, Dict
import strawberry

from nutrients import NUTRIENT_FIELDS
from .types_product import Product


@strawberry.type
class MealEntry:
    id: str
    user_id: str
    name: str
    quantity_g: float
    timestamp: str
    barcode: Optional[str] = None
    idempotency_key: Optional[str] = None
    nutrient_snapshot_json: Optional[str] = None
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    image_url: Optional[str] = strawberry.field(name="imageUrl", default=None)


@strawberry.type
class DailySummary:
    date: str
    user_id: str
    meals: int
    calories: int
    protein: Optional[float]
    carbs: Optional[float]
    fat: Optional[float]
    fiber: Optional[float]
    sugar: Optional[float]
    sodium: Optional[float]
    activity_steps: int = 0
    activity_calories_out: float = 0.0
    activity_events: int = 0
    calories_deficit: int = 0
    calories_replenished_percent: int = 0


@strawberry.input
class LogMealInput:
    name: str
    quantity_g: float
    timestamp: Optional[str] = None
    barcode: Optional[str] = None
    idempotency_key: Optional[str] = None
    user_id: Optional[str] = None
    photo_url: Optional[str] = None


@strawberry.input
class UpdateMealInput:
    id: str
    name: Optional[str] = None
    quantity_g: Optional[float] = None
    timestamp: Optional[str] = None
    barcode: Optional[str] = None
    user_id: Optional[str] = None


def enrich_from_product(prod: Product, quantity_g: float) -> Dict[str, Optional[float]]:
    factor = quantity_g / 100.0 if quantity_g else 1.0
    enriched: Dict[str, Optional[float]] = {}
    for f in NUTRIENT_FIELDS:
        value = getattr(prod, f)
        if value is not None:
            if f == "calories":
                enriched[f] = int(round(value * factor))
            else:
                enriched[f] = round(value * factor, 2)
        else:
            enriched[f] = None
    return enriched


__all__ = [
    "MealEntry",
    "DailySummary",
    "LogMealInput",
    "UpdateMealInput",
    "enrich_from_product",
]
