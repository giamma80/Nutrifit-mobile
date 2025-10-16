"""Meal Analysis Application Service.

Coordina l'analisi foto pasti integrando adapter esistenti
con la nuova pipeline di normalizzazione domain-driven.
"""

from __future__ import annotations

import os
from typing import Any, List


from domain.meal.model import MealItem, MealAnalysisResult, MealAnalysisRequest
from domain.meal.pipeline.normalizer import (
    MealNormalizationPipeline,
    NormalizedMealItem,
)
from domain.meal.errors import MealAnalysisError


class MealAnalysisService:
    """Service per orchestrazione analisi foto pasti."""

    def __init__(
        self,
        legacy_adapter: Any,
        normalization_pipeline: MealNormalizationPipeline,
    ):
        self.legacy_adapter = legacy_adapter
        self.normalization_pipeline = normalization_pipeline

    async def analyze_meal_photo(self, request: MealAnalysisRequest) -> MealAnalysisResult:
        """Analizza foto pasto con pipeline integrata."""
        try:
            # Fase 1: Analisi via adapter legacy esistente
            legacy_items = await self.legacy_adapter.analyze_async(
                user_id=request.user_id,
                photo_id=request.photo_id,
                photo_url=request.photo_url,
                now_iso=request.now_iso,
                dish_hint=request.dish_hint,
            )

            # Converte da infrastructure a domain model
            meal_items = [self._convert_to_meal_item(item) for item in legacy_items]

            # Fase 2: Normalizzazione (se richiesta)
            if request.normalization_mode != "off":
                normalized_items = [self._convert_to_normalized_item(item) for item in meal_items]

                norm_result = self.normalization_pipeline.normalize(
                    items=normalized_items,
                    mode=request.normalization_mode,
                )

                # Applica back le modifiche se enforce
                if request.normalization_mode == "enforce":
                    meal_items = [
                        self._convert_from_normalized_item(norm_item)
                        for norm_item in norm_result.items
                    ]
                else:
                    # dry_run: solo arricchimento sugar/sodium
                    for meal_item, norm_item in zip(meal_items, norm_result.items):
                        if meal_item.sugar is None and norm_item.sugar is not None:
                            meal_item.sugar = norm_item.sugar
                        if meal_item.sodium is None and norm_item.sodium is not None:
                            meal_item.sodium = norm_item.sodium

            # Calcola totale calorie
            total_calories = self._calculate_total_calories(meal_items)

            # Estrae dish name dall'adapter se disponibile
            dish_name = getattr(self.legacy_adapter, "_last_dish_name", None)

            # Estrae fallback reason se presente
            fallback_reason = getattr(self.legacy_adapter, "last_fallback_reason", None)

            return MealAnalysisResult(
                items=meal_items,
                source=self.legacy_adapter.name(),
                dish_name=dish_name,
                total_calories=total_calories,
                fallback_reason=fallback_reason,
            )

        except Exception as exc:
            raise MealAnalysisError(f"Errore durante analisi foto pasto: {exc}") from exc

    def _convert_to_meal_item(self, legacy_item: Any) -> MealItem:
        """Converte da MealPhotoItemPredictionRecord a MealItem domain."""
        return MealItem(
            label=legacy_item.label,
            confidence=legacy_item.confidence,
            quantity_g=legacy_item.quantity_g,
            calories=legacy_item.calories,
            protein=legacy_item.protein,
            carbs=legacy_item.carbs,
            fat=legacy_item.fat,
            fiber=legacy_item.fiber,
            sugar=legacy_item.sugar,
            sodium=legacy_item.sodium,
            enrichment_source=getattr(legacy_item, "enrichment_source", None),
            calorie_corrected=getattr(legacy_item, "calorie_corrected", None),
        )

    def _convert_to_normalized_item(self, meal_item: MealItem) -> NormalizedMealItem:
        """Converte da MealItem a NormalizedMealItem per pipeline."""
        return NormalizedMealItem(
            label=meal_item.label,
            quantity_g=meal_item.quantity_g or 0.0,
            calories=float(meal_item.calories) if meal_item.calories else None,
            protein=meal_item.protein,
            carbs=meal_item.carbs,
            fat=meal_item.fat,
            fiber=meal_item.fiber,
            sugar=meal_item.sugar,
            sodium=meal_item.sodium,
            enrichment_source=meal_item.enrichment_source,
        )

    def _convert_from_normalized_item(self, norm_item: NormalizedMealItem) -> MealItem:
        """Converte da NormalizedMealItem a MealItem domain."""
        return MealItem(
            label=norm_item.label,
            confidence=1.0,  # La normalizzazione non modifica confidence
            quantity_g=norm_item.quantity_g,
            calories=int(round(norm_item.calories)) if norm_item.calories else None,
            protein=norm_item.protein,
            carbs=norm_item.carbs,
            fat=norm_item.fat,
            fiber=norm_item.fiber,
            sugar=norm_item.sugar,
            sodium=norm_item.sodium,
            enrichment_source=norm_item.enrichment_source,
            calorie_corrected=norm_item.calorie_corrected,
        )

    def _calculate_total_calories(self, items: List[MealItem]) -> int:
        """Calcola totale calorie da lista items."""
        total = 0
        for item in items:
            if item.calories:
                total += item.calories
        return total

    @classmethod
    def create_with_defaults(cls) -> "MealAnalysisService":
        """Factory method con configurazione default."""
        from inference.adapter import get_active_adapter

        legacy_adapter = get_active_adapter()
        debug_enabled = os.getenv("AI_MEAL_PHOTO_DEBUG") == "1"
        pipeline = MealNormalizationPipeline(debug_enabled=debug_enabled)

        return cls(
            legacy_adapter=legacy_adapter,
            normalization_pipeline=pipeline,
        )


__all__ = [
    "MealAnalysisService",
]
