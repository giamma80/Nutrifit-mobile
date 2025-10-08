"""Nutrition domain ports (interfaces).

Definisce contratti per accesso ai dati nutrizionali e calcoli metabolici.
Implementazioni concrete in adapters/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List, Tuple

from domain.nutrition.model import (
    NutritionPlan,
    UserPhysicalData,
    DailyNutritionSummary,
    NutrientValues,
    CategoryProfile,
)


class NutritionPlanPort(ABC):
    """Port per persistenza e retrieval piani nutrizionali."""

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> Optional[NutritionPlan]:
        """Recupera piano nutrizionale utente corrente."""
        pass

    @abstractmethod
    def save(self, plan: NutritionPlan) -> NutritionPlan:
        """Salva piano nutrizionale aggiornato."""
        pass

    @abstractmethod
    def create_default_plan(
        self,
        user_id: str,
        physical_data: UserPhysicalData,
    ) -> NutritionPlan:
        """Crea piano default per nuovo utente."""
        pass


class MealDataPort(ABC):
    """Port per accesso dati pasti e aggregazioni."""

    @abstractmethod
    def get_daily_meals(self, user_id: str, date: str) -> List[Dict[str, Any]]:
        """Recupera tutti i pasti per data (YYYY-MM-DD)."""
        pass

    @abstractmethod
    def get_daily_totals(
        self,
        user_id: str,
        date: str,
    ) -> NutrientValues:
        """Calcola totali nutrizionali giornalieri."""
        pass


class ActivityDataPort(ABC):
    """Port per dati attività fisica e calorie consumate."""

    @abstractmethod
    def get_daily_activity(
        self,
        user_id: str,
        date: str,
    ) -> Dict[str, float]:
        """Recupera steps e calories_out per data."""
        pass

    @abstractmethod
    def get_weekly_activity_avg(
        self,
        user_id: str,
        end_date: str,
    ) -> Dict[str, float]:
        """Media attività ultimi 7 giorni."""
        pass


class CategoryProfilePort(ABC):
    """Port per profili nutrizionali categoria."""

    @abstractmethod
    def get_profile(self, category: str) -> Optional[CategoryProfile]:
        """Recupera profilo per categoria alimento."""
        pass

    @abstractmethod
    def get_all_profiles(self) -> Dict[str, CategoryProfile]:
        """Recupera tutti i profili disponibili."""
        pass

    @abstractmethod
    def classify_food(self, food_label: str) -> Optional[str]:
        """Classifica alimento in categoria."""
        pass

    @abstractmethod
    def apply_garnish_clamp(self, quantity_g: float, category: str) -> Tuple[float, bool]:
        """Applica clamp per garnish su quantità."""
        pass


class NutritionSummaryPort(ABC):
    """Port per aggregazioni nutrizionali storiche."""

    @abstractmethod
    def get_summary(
        self,
        user_id: str,
        date: str,
    ) -> Optional[DailyNutritionSummary]:
        """Recupera summary giornaliero esistente."""
        pass

    @abstractmethod
    def save_summary(self, summary: DailyNutritionSummary) -> None:
        """Persiste summary calcolato."""
        pass

    @abstractmethod
    def get_range_summaries(
        self,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> List[DailyNutritionSummary]:
        """Recupera summary per range date."""
        pass


__all__ = [
    "NutritionPlanPort",
    "MealDataPort",
    "ActivityDataPort",
    "CategoryProfilePort",
    "NutritionSummaryPort",
]
