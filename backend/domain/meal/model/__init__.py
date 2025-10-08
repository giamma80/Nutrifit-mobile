"""Domain models per meal analysis.

Value objects e DTOs per il dominio dell'analisi dei pasti.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List


@dataclass(slots=True)
class MealItem:
    """Item nutrizionale identificato nell'analisi foto pasto."""

    label: str
    confidence: float
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
class MealAnalysisResult:
    """Risultato completo dell'analisi foto pasto."""

    items: List[MealItem]
    source: str  # adapter utilizzato (gpt4v, stub, etc.)
    dish_name: Optional[str] = None
    total_calories: Optional[int] = None
    analysis_errors: Optional[List[str]] = None
    fallback_reason: Optional[str] = None


@dataclass(slots=True)
class MealAnalysisRequest:
    """Richiesta di analisi foto pasto."""

    user_id: str
    photo_id: Optional[str]
    photo_url: Optional[str]
    now_iso: str
    normalization_mode: str = "off"


__all__ = [
    "MealItem",
    "MealAnalysisResult",
    "MealAnalysisRequest",
]
