"""Meal data adapter - bridges to existing repository layer.

Implementa MealDataPort utilizzando meal_repo e logica aggregazione
esistente da app.py per mantenere compatibilità.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from domain.nutrition.model import NutrientValues
from domain.nutrition.ports import MealDataPort
from repository.meals import meal_repo  # Existing repo


logger = logging.getLogger("domain.nutrition.adapters.meal_data")


class MealDataAdapter(MealDataPort):
    """Adapter che utilizza meal_repo esistente."""

    def get_daily_meals(self, user_id: str, date: str) -> List[Dict[str, Any]]:
        """Recupera pasti giornalieri usando meal_repo."""
        try:
            all_meals = meal_repo.list_all(user_id)
            # Filtra per data (timestamp starts with date YYYY-MM-DD)
            day_meals = [meal for meal in all_meals if meal.timestamp.startswith(date)]

            # Convert MealRecord to dict per compatibilità
            return [
                {
                    "id": meal.id,
                    "name": meal.name,
                    "quantity_g": meal.quantity_g,
                    "timestamp": meal.timestamp,
                    "calories": meal.calories,
                    "protein": meal.protein,
                    "carbs": meal.carbs,
                    "fat": meal.fat,
                    "fiber": meal.fiber,
                    "sugar": meal.sugar,
                    "sodium": meal.sodium,
                }
                for meal in day_meals
            ]

        except Exception as e:
            logger.error(f"Error fetching daily meals: {e}")
            return []

    def get_daily_totals(self, user_id: str, date: str) -> NutrientValues:
        """Calcola totali nutrizionali usando logica esistente da app.py."""
        try:
            meals = self.get_daily_meals(user_id, date)

            def _acc(name: str) -> float:
                total = 0.0
                for meal in meals:
                    val = meal.get(name)
                    if val is not None:
                        total += float(val)
                return total

            def _opt(name: str) -> float:
                if not meals:
                    return 0.0
                val = _acc(name)
                return round(val, 2)

            return NutrientValues(
                calories=int(_acc("calories")) if meals else 0,
                protein=_opt("protein"),
                carbs=_opt("carbs"),
                fat=_opt("fat"),
                fiber=_opt("fiber"),
                sugar=_opt("sugar"),
                sodium=_opt("sodium"),
            )

        except Exception as e:
            logger.error(f"Error calculating daily totals: {e}")
            return NutrientValues()


__all__ = ["MealDataAdapter"]
