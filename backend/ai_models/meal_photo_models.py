"""Shared dataclasses per AI meal photo analysis to avoid circular imports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List


@dataclass(slots=True)
class MealPhotoItemPredictionRecord:
    label: str
    confidence: float
    display_name: Optional[str] = None
    quantity_g: Optional[float] = None
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    enrichment_source: Optional[str] = None
    calorie_corrected: Optional[bool] = None


@dataclass(slots=True)
class MealPhotoAnalysisRecord:
    id: str
    user_id: str
    status: str  # PENDING | COMPLETED | FAILED
    created_at: str
    source: str  # stub|heuristic|model|fallback (string semplice per ora)
    items: List[MealPhotoItemPredictionRecord]
    raw_json: Optional[str] = None
    idempotency_key_used: Optional[str] = None
    dish_name: Optional[str] = None
    photo_url: Optional[str] = None
