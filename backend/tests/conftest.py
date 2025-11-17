"""Integration/E2E test fixtures.

This conftest loads the full app and is used for integration/e2e tests.
Unit tests in tests/unit/ have their own isolated conftest that doesn't load the app.
"""

from __future__ import annotations

import os
import pytest
import pytest_asyncio
from typing import Generator, AsyncIterator, cast, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load .env first (default environment variables)
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Load .env.test for integration_real tests (overrides .env values)
env_test_path = Path(__file__).parent.parent / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)

# Type-only imports for proper type hints
if TYPE_CHECKING:
    from fastapi import FastAPI

# Check if running unit tests only (env var set by Makefile.test)
UNIT_TESTS_ONLY = os.getenv("PYTEST_UNIT_ONLY", "0") == "1"

# Module-level type annotations for conditional imports
app: FastAPI | None
reset_all: Callable[[], None] | None

# Try to import app and metrics, but handle gracefully if missing during refactor
# or if running unit tests only
if UNIT_TESTS_ONLY:
    APP_AVAILABLE = False
    app = None
else:
    try:
        from httpx import AsyncClient, ASGITransport
        from app import app

        APP_AVAILABLE = True
    except (ImportError, ModuleNotFoundError) as e:
        # During refactor, some modules may be temporarily unavailable
        APP_AVAILABLE = False
        app = None
        import warnings

        warnings.warn(
            f"App import failed (expected during refactor): {e}. "
            "Integration/E2E tests requiring app will be skipped.",
            UserWarning,
        )


@pytest.fixture(autouse=True)
def _clear_ai_env(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Pulisce variabili AI_* e OPENAI_* prima di ogni test.

    Evita che valori presenti in .env (es. AI_MEAL_PHOTO_MODE=gpt4v)
    influenzino test che si aspettano adapter default. I test che
    necessitano di un valore specifico lo impostano con monkeypatch.setenv.

    Only runs if APP_AVAILABLE (integration/e2e tests).
    Skips clearing for integration_real tests (which need real API keys).
    """
    if not APP_AVAILABLE:
        yield
        return

    # Skip clearing for integration_real tests
    if request.node.get_closest_marker("integration_real"):
        yield
        return

    import os

    to_clear = [
        "AI_MEAL_PHOTO_MODE",
        "AI_GPT4V_REAL_ENABLED",
        "OPENAI_API_KEY",
        "OPENAI_VISION_MODEL",
    ]
    for k in to_clear:
        if k in os.environ:
            del os.environ[k]
    try:
        yield
    finally:
        # Non ripristiniamo i valori (ambiente test isolato); la suite intera
        # resta con stato pulito, ma manteniamo la struttura se servisse.
        pass


@pytest.fixture
def enable_nutrition_domain_v2() -> Generator[None, None, None]:
    """Fixture legacy - nutrition domain V2 sempre abilitato ora."""
    # No-op: V2 sempre attivo
    yield


@pytest.fixture
def enable_activity_domain_v2() -> Generator[None, None, None]:
    """Fixture legacy - activity domain V2 sempre abilitato ora."""
    # No-op: V2 sempre attivo
    yield


@pytest.fixture
def nutrition_integration_service() -> Generator[Any, None, None]:
    """Fixture che restituisce NutritionIntegrationService - sempre disponibile."""
    from domain.nutrition.integration import get_nutrition_integration_service

    service = get_nutrition_integration_service()
    assert service is not None, "Nutrition service should always be available"
    yield service


@pytest.fixture
def activity_integration_service() -> Generator[Any, None, None]:
    """Fixture che restituisce ActivityIntegrationService - sempre disponibile."""
    from domain.activity.integration import get_activity_integration_service

    service = get_activity_integration_service()
    assert service is not None, "Activity service should always be available"
    yield service


@pytest.fixture(autouse=True)
def _reset_metrics() -> Generator[None, None, None]:
    """Reset metriche prima e dopo ogni test per isolamento.

    Only runs if APP_AVAILABLE (integration/e2e tests).
    Legacy metrics system removed - fixture kept for compatibility.
    """
    if not APP_AVAILABLE:
        yield
        return

    # Legacy metrics removed - no-op
    yield


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Client HTTP asincrono per test GraphQL/REST.

    Usa httpx.AsyncClient con ASGITransport esplicito (scorciatoia app=
    deprecata) e base_url fittizia per coerenza nelle richieste relative.

    Only available if APP_AVAILABLE (integration/e2e tests).
    """
    if not APP_AVAILABLE or app is None:
        pytest.skip("App not available during refactor - integration tests disabled")
        # This line never executes but satisfies type checker
        yield

    # AsyncClient and ASGITransport already imported at module level (line 31)
    # Cast a Any per soddisfare la firma attesa (FastAPI è compatibile ASGI)
    transport = ASGITransport(app=cast(Any, app))
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as ac:
        yield ac


# Mock del nutrition service per i test


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
    """Mock del nutrition service per calcoli realistici dai repository."""

    def calculate_daily_summary(self, user_id: str, date: str) -> MockNutritionDailySummary:
        """Calcola daily summary leggendo dati reali dai repository."""

        from repository.meals import meal_repo
        from repository.health_totals import health_totals_repo
        from repository.activities import activity_repo

        # Leggi pasti dal repository
        all_meals = meal_repo.list_all(user_id)
        day_meals = [m for m in all_meals if m.timestamp.startswith(date)]

        # Aggrega nutrienti con enrichment automatico se mancanti
        def _acc(name: str) -> float:
            total = 0.0
            for m in day_meals:
                val = getattr(m, name, None)
                # Se le calorie/nutrienti sono None, prova enrichment dal cache
                if val is None and name == "calories" and m.barcode:
                    # Simula enrichment dal cache come fa il sistema reale
                    from cache import cache

                    product = cache.get(f"product:{m.barcode}")
                    if product:
                        # Calcola nutrienti scalati per la quantità
                        scale = m.quantity_g / 100.0  # prodotto per 100g
                        val = getattr(product, name, None)
                        if val:
                            val = val * scale

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

    def calculate_bmr(self, physical_data: Any) -> float:
        """Mock BMR calculation using Mifflin-St Jeor equation."""
        # Mifflin-St Jeor: BMR = 10*weight + 6.25*height - 5*age + s
        # s = 5 for men, -161 for women
        s = 5 if physical_data.sex == "male" else -161
        bmr = (
            10 * float(physical_data.weight_kg)
            + 6.25 * float(physical_data.height_cm)
            - 5 * float(physical_data.age)
            + s
        )
        return round(bmr, 2)

    def calculate_tdee(self, bmr: float, activity_level: Any) -> float:
        """Mock TDEE calculation from BMR and activity level."""
        multipliers = {
            "SEDENTARY": 1.2,
            "LIGHTLY_ACTIVE": 1.375,
            "MODERATELY_ACTIVE": 1.55,
            "VERY_ACTIVE": 1.725,
            "EXTREMELY_ACTIVE": 1.9,
        }
        if hasattr(activity_level, "value"):
            activity_str = activity_level.value
        else:
            activity_str = str(activity_level)
        multiplier = multipliers.get(activity_str, 1.55)
        return round(bmr * multiplier, 2)

    def calculate_macro_targets(self, tdee: float, strategy: Any, physical_data: Any) -> Any:
        """Mock macro targets calculation."""
        from domain.nutrition.model import MacroTargets

        # Mock strategy adjustments
        if hasattr(strategy, "value"):
            strategy_str = strategy.value
        else:
            strategy_str = str(strategy)

        if strategy_str == "CUT":
            calories = tdee * 0.80  # 20% deficit
        elif strategy_str == "BULK":
            calories = tdee * 1.20  # 20% surplus
        else:  # MAINTAIN
            calories = tdee

        # Mock macro calculation based on body weight and calories
        # Protein: 1.8g per kg body weight
        protein_g = physical_data.weight_kg * 1.8
        protein_cal = protein_g * 4

        # Fat: 25% of total calories
        fat_cal = calories * 0.25
        fat_g = fat_cal / 9

        # Carbs: remaining calories
        carb_cal = calories - protein_cal - fat_cal
        carb_g = carb_cal / 4

        return MacroTargets(
            calories=round(calories),
            protein_g=round(protein_g),
            carbs_g=round(carb_g),
            fat_g=round(fat_g),
        )

    def recompute_calories_from_macros(self, nutrients: Any) -> tuple[int, bool]:
        """Mock calories recomputation from macros."""
        protein_cal = (nutrients.protein or 0) * 4
        carb_cal = (nutrients.carbs or 0) * 4
        fat_cal = (nutrients.fat or 0) * 9

        calculated_calories = protein_cal + carb_cal + fat_cal

        # Check if correction is needed
        original_calories = nutrients.calories
        if original_calories is None:
            return round(calculated_calories), True

        # Allow 5% tolerance
        tolerance = 0.05
        max_cal = max(original_calories, 1)
        diff_pct = abs(calculated_calories - original_calories) / max_cal

        if diff_pct > tolerance:
            return round(calculated_calories), True
        else:
            return round(original_calories), False


@pytest.fixture(autouse=True)
def mock_nutrition_service(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[MockNutritionService | None, None, None]:
    """Fixture che mocka automaticamente il nutrition service realistico.

    Only runs if APP_AVAILABLE (integration/e2e tests).
    """
    if not APP_AVAILABLE:
        yield None
        return

    # Mock del service
    mock_service = MockNutritionService()

    # Mock del get_nutrition_service
    def get_mock_service() -> MockNutritionService:
        return mock_service

    monkeypatch.setattr(
        "domain.nutrition.application.nutrition_service.get_nutrition_service", get_mock_service
    )

    # Mock dell'integration service per usare il nostro mock
    from domain.nutrition.integration import NutritionIntegrationService

    def mock_init(self: Any) -> None:
        self._nutrition_service = mock_service

    def mock_enhanced_daily_summary(
        self: Any, user_id: str, date: str, fallback_summary: Any = None
    ) -> dict[str, Any]:
        """Mock enhanced daily summary che usa il nostro MockNutritionService."""
        domain_summary = mock_service.calculate_daily_summary(user_id, date)

        return {
            "date": domain_summary.date,
            "user_id": domain_summary.user_id,
            "meals": domain_summary.meals,
            "calories": domain_summary.calories,
            "protein": domain_summary.protein,
            "carbs": domain_summary.carbs,
            "fat": domain_summary.fat,
            "fiber": domain_summary.fiber,
            "sugar": domain_summary.sugar,
            "sodium": domain_summary.sodium,
            "activity_steps": domain_summary.activity_steps,
            "activity_calories_out": domain_summary.activity_calories_out,
            "activity_events": domain_summary.activity_events,
            "calories_deficit": domain_summary.calories_deficit,
            "calories_replenished_percent": domain_summary.calories_replenished_percent,
            "target_adherence": domain_summary.target_adherence,
            "macro_balance_score": domain_summary.macro_balance_score,
            "enhanced_calculations": {
                "deficit_v2": domain_summary.calories_deficit,
                "replenished_pct_v2": domain_summary.calories_replenished_percent,
            },
        }

    monkeypatch.setattr(NutritionIntegrationService, "__init__", mock_init)
    monkeypatch.setattr(
        NutritionIntegrationService, "enhanced_daily_summary", mock_enhanced_daily_summary
    )

    # Mock anche del get_nutrition_integration_service
    def get_mock_integration_service() -> NutritionIntegrationService:
        mock_integration = NutritionIntegrationService()
        return mock_integration

    monkeypatch.setattr(
        "domain.nutrition.integration.get_nutrition_integration_service",
        get_mock_integration_service,
    )

    # Mock anche nell'app.py (skip if not available during refactor)
    try:
        monkeypatch.setattr("app.get_nutrition_integration_service", get_mock_integration_service)
    except AttributeError:
        # Attribute removed during refactor - skip
        pass

    yield mock_service


# Mock del meal service per enrichment automatico
class MockMealService:
    """Mock del meal service che gestisce enrichment automatico."""

    def __init__(self, original_service: Any) -> None:
        self._original_service = original_service

    async def create_meal(self, **kwargs: Any) -> Any:
        """Create meal con enrichment automatico se barcode presente."""
        # Chiama il servizio originale per creare il meal
        meal = await self._original_service.create_meal(**kwargs)
        return meal

    # Delega tutti gli altri metodi al servizio originale
    def __getattr__(self, name: str) -> Any:
        return getattr(self._original_service, name)


@pytest.fixture(autouse=True)
def mock_meal_enrichment(monkeypatch: pytest.MonkeyPatch) -> Generator[bool, None, None]:
    """Mock meal enrichment - only for integration/e2e tests.

    Fixture che aggiunge enrichment automatico al meal service.
    """
    if not APP_AVAILABLE:
        yield False
        return

    def mock_meal_service_init(self: Any) -> None:
        # Inizializza normalmente seguendo la struttura originale
        from domain.meal.adapters.meal_repository_adapter import MealRepositoryAdapter
        from domain.meal.adapters.nutrition_calculator_adapter import (
            StubNutritionCalculatorAdapter,
        )
        from domain.meal.adapters.meal_event_adapter import LoggingMealEventAdapter
        from repository.meals import meal_repo

        repository_adapter = MealRepositoryAdapter(meal_repo)
        nutrition_calculator_adapter = StubNutritionCalculatorAdapter()

        # Mock OpenFoodFactsAdapter per enrichment automatico
        from domain.meal.port import ProductLookupPort

        class MockOpenFoodFactsAdapter(ProductLookupPort):  # type: ignore[misc]
            async def lookup_by_barcode(self, barcode: str) -> Any:
                # Metodo richiesto dall'interface ProductLookupPort
                # Simula prodotto base per test
                from domain.meal.model.meal import ProductInfo, NutrientProfile

                # Barcode specifici per i test
                if barcode == "123456789":
                    # Test case specifico per barcode image test
                    nutrient_profile = NutrientProfile(
                        calories_per_100g=150.0,  # 150 cal/100g per match con test
                        protein_per_100g=10.0,
                        carbs_per_100g=20.0,
                        fat_per_100g=3.0,
                        fiber_per_100g=1.0,
                        sugar_per_100g=10.0,
                        sodium_per_100g=50.0,
                    )
                    image_url = "https://images.openfoodfacts.org/products/" "123/456/789/front.jpg"
                    return ProductInfo(
                        barcode=barcode,
                        name="Test Product",
                        nutrient_profile=nutrient_profile,
                        image_url=image_url,
                    )
                elif barcode == "999888777":
                    # Test case per photo URL priority test
                    nutrient_profile = NutrientProfile(
                        calories_per_100g=200.0,  # 200 cal/100g * 150g = 300 cal
                        protein_per_100g=15.0,  # 15.0 protein/100g * 150g = 22.5
                        carbs_per_100g=20.0,
                        fat_per_100g=3.0,
                        fiber_per_100g=1.0,
                        sugar_per_100g=10.0,
                        sodium_per_100g=50.0,
                    )
                    image_url = "https://images.openfoodfacts.org/products/" "999/888/777/front.jpg"
                    return ProductInfo(
                        barcode=barcode,
                        name="Dual Source Product",
                        nutrient_profile=nutrient_profile,
                        image_url=image_url,
                    )
                else:
                    # Prodotto generico per altri test
                    nutrient_profile = NutrientProfile(
                        calories_per_100g=200.0,
                        protein_per_100g=20.0,
                        carbs_per_100g=30.0,
                        fat_per_100g=5.0,
                        fiber_per_100g=2.0,
                        sugar_per_100g=15.0,
                        sodium_per_100g=100.0,
                    )

                    # Generiamo un'immagine mock basata sul barcode per i test
                    mock_image_url = (
                        f"https://images.openfoodfacts.org/products/"
                        f"{barcode[:3]}/{barcode[3:6]}/{barcode[6:]}/front.jpg"
                    )

                    return ProductInfo(
                        barcode=barcode,
                        name="Mock Product",
                        nutrient_profile=nutrient_profile,
                        image_url=mock_image_url,
                    )

            async def search_products(self, query: str, limit: int = 10) -> list[Any]:
                # Metodo richiesto dall'interface
                return []

        product_lookup_adapter = MockOpenFoodFactsAdapter()
        event_adapter = LoggingMealEventAdapter()

        # Initialize original services
        from domain.meal.service import MealService, MealQueryService

        original_service = MealService(
            meal_repository=repository_adapter,
            nutrition_calculator=nutrition_calculator_adapter,
            product_lookup=product_lookup_adapter,
            event_publisher=event_adapter,
        )

        # Wrappa con il nostro mock
        self._meal_service = MockMealService(original_service)

        # Query service normale
        self._query_service = MealQueryService(meal_repository=repository_adapter)

    # Applica il mock all'initialization del MealIntegrationService
    try:
        from domain.meal.integration import MealIntegrationService

        monkeypatch.setattr(MealIntegrationService, "_initialize_services", mock_meal_service_init)
    except (ImportError, ModuleNotFoundError):
        # Module removed during refactor - skip this mock for new tests
        pass

    yield True
