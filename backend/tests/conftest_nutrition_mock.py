"""Mock per nutrition domain service nei test."""

from typing import Any
from dataclasses import dataclass
import pytest

# Importiamo i repository per leggere i dati reali
from repository.meals import meal_repo
from repository.health_totals import health_totals_repo
from repository.activities import activity_repo


@dataclass
class MockNutritionDailySummary:
    """Mock della DailySummary del nutrition domain."""

    date: str
    user_id: str
    meals: int
    calories: int
    protein: float
    carbs: float
    fat: float
    fiber: float
    sugar: float
    sodium: float
    activity_steps: int
    activity_calories_out: float
    activity_events: int
    calories_deficit: int
    calories_replenished_percent: int

    # Campi V2 mockati
    target_adherence: float = 0.85
    macro_balance_score: float = 0.92


class MockNutritionService:
    """Mock del nutrition service che calcola summary realistici dai repository."""

    def calculate_daily_summary(self, user_id: str, date: str) -> MockNutritionDailySummary:
        """Calcola daily summary leggendo dati reali dai repository."""

        # Leggi pasti dal repository
        all_meals = meal_repo.list_all(user_id)
        day_meals = [m for m in all_meals if m.timestamp.startswith(date)]

        # Aggrega nutrienti
        def _acc(name: str) -> float:
            total = 0.0
            for m in day_meals:
                val = getattr(m, name, None)
                if val is not None:
                    total += float(val)
            return total

        def _opt(name: str) -> float:
            if not day_meals:
                return 0.0
            val = _acc(name)
            return round(val, 2)

        calories_total = int(_acc("calories")) if day_meals else 0

        # Leggi activity data dal health_totals_repo
        steps_tot, cal_out_tot = health_totals_repo.daily_totals(user_id=user_id, date=date)

        # Statistiche activity events per compatibilità
        act_stats = activity_repo.get_daily_stats(user_id, date + "T00:00:00Z")
        events_count = act_stats.get("events_count", 0)

        # Calcola deficit e percentuali
        calories_deficit = int(round(cal_out_tot - calories_total))
        if cal_out_tot > 0:
            pct = (calories_total / cal_out_tot) * 100
            # Clamp per evitare valori esplosivi
            if pct < 0:
                pct = 0
            if pct > 999:
                pct = 999
            calories_replenished_percent = int(round(pct))
        else:
            calories_replenished_percent = 0

        return MockNutritionDailySummary(
            date=date,
            user_id=user_id,
            meals=len(day_meals),
            calories=calories_total,
            protein=_opt("protein"),
            carbs=_opt("carbs"),
            fat=_opt("fat"),
            fiber=_opt("fiber"),
            sugar=_opt("sugar"),
            sodium=_opt("sodium"),
            activity_steps=steps_tot,
            activity_calories_out=cal_out_tot,
            activity_events=events_count,
            calories_deficit=calories_deficit,
            calories_replenished_percent=calories_replenished_percent,
        )


@pytest.fixture
def mock_nutrition_service(
    monkeypatch: pytest.MonkeyPatch,
) -> MockNutritionService:
    """Fixture che mocka il nutrition service con calcoli realistici."""

    # Mock del service
    mock_service = MockNutritionService()

    # Mock del get_nutrition_service
    monkeypatch.setattr(
        "domain.nutrition.application.nutrition_service.get_nutrition_service", lambda: mock_service
    )

    # Mock dell'integration service per usare il nostro mock
    from domain.nutrition.integration import NutritionIntegrationService

    def mock_init(self: Any) -> None:
        self._nutrition_service = mock_service

    monkeypatch.setattr(NutritionIntegrationService, "__init__", mock_init)

    return mock_service
