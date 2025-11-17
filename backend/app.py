from __future__ import annotations

# Standard library
import os
import datetime
import dataclasses
import logging as _logging
from contextlib import asynccontextmanager
from typing import Final, Any, Optional

# Third-party
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

# Local application imports
from cache import cache
from repository.health_totals import health_totals_repo  # NEW

# TEMPORARILY DISABLED DURING REFACTOR - Phase 0
# from graphql.types_meal import (
#     MealEntry,
#     DailySummary,
#     LogMealInput,
#     UpdateMealInput,
#     enrich_from_product,
# )
# from domain.nutrition.integration import get_nutrition_integration_service

# Phase 5: New GraphQL resolvers (CQRS)
from graphql.resolvers.meal.atomic_queries import AtomicQueries
from graphql.resolvers.meal.aggregate_queries import AggregateQueries
from graphql.resolvers.meal.mutations import MealMutations
from graphql.resolvers.activity.queries import ActivityQueries
from graphql.resolvers.activity.mutations import ActivityMutations
from graphql.resolvers.nutritional_profile import (
    NutritionalProfileQueries,
    NutritionalProfileMutations,
)
from graphql.resolvers.user.queries import UserQueries
from graphql.resolvers.user.mutations import UserMutations
from graphql.context import create_context
from infrastructure.persistence.factory import get_meal_repository
from infrastructure.user.repository_factory import get_user_repository
from infrastructure.persistence.nutritional_profile_factory import (
    get_profile_repository,
)
from infrastructure.events.in_memory_bus import InMemoryEventBus
from infrastructure.cache.in_memory_idempotency_cache import (
    InMemoryIdempotencyCache,
)
from application.meal.orchestrators.photo_orchestrator import (
    MealAnalysisOrchestrator,
)
from application.meal.orchestrators.barcode_orchestrator import BarcodeOrchestrator
from domain.meal.core.factories.meal_factory import MealFactory
from infrastructure.meal.providers.factory import (
    create_vision_provider,
    create_nutrition_provider,
    create_barcode_provider,
    get_vision_provider,
    get_nutrition_provider,
    get_barcode_provider,
)
from domain.meal.recognition.services.recognition_service import FoodRecognitionService
from domain.meal.barcode.services.barcode_service import BarcodeService
from domain.meal.nutrition.services.enrichment_service import NutritionEnrichmentService
from infrastructure.nutritional_profile.adapters import (
    BMRCalculatorAdapter,
    TDEECalculatorAdapter,
    MacroCalculatorAdapter,
)

# from graphql.types_ai import AnalyzeMealPhotoInput  # Replaced
from graphql.types_activity_health import (
    HealthTotalsInput,
    HealthTotalsDelta,
    SyncHealthTotalsResult,
    CacheStats,
)

# --- Basic logging configuration (minimal) ---
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
try:
    _logging.basicConfig(
        level=getattr(_logging, _LOG_LEVEL, _logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
except Exception:  # pragma: no cover
    _logging.basicConfig(level=_logging.INFO)

for _ln in ("startup", "ai.normalize"):
    _lg = _logging.getLogger(_ln)
    if _lg.level == 0:  # not set explicitly
        _lg.setLevel(getattr(_logging, _LOG_LEVEL, _logging.INFO))

# TTL in secondi per la cache del prodotto (default 10 minuti)
PRODUCT_CACHE_TTL_S = float(os.getenv("PRODUCT_CACHE_TTL_S", "600"))

# Versione letta da env (Docker build ARG -> ENV APP_VERSION)
APP_VERSION = os.getenv("APP_VERSION", "0.0.0-dev")


# ----------------- Meal Logging (B2) + Repository refactor -----------------
"""GraphQL types spostati in moduli per ridurre complessità mypy."""


# ----------------- Activity Ingestion (B3) -----------------
# Riutilizziamo l'enum del repository per evitare duplicazione incoerente
# Enum e ActivityEvent con default già definiti in modulo types_activity_health


# ----------------- Health Totals Sync (B4) -----------------

# ----------------- AI Meal Photo Stub (Fase 0) -----------------
"""Tipi AI spostati in graphql.types_ai"""


# Legacy function removed - using only V2 domain service flow


NUTRIENT_FIELDS = ...  # Disabled during Phase 5 refactor


"""Input types spostati in graphql.types_* modules"""


DEFAULT_USER_ID = "default"


# TEMPORARILY DISABLED DURING REFACTOR - Phase 0
# _enrich_from_product = enrich_from_product  # retro compat


# TEMPORARILY DISABLED DURING REFACTOR - Phase 0: DailySummary type removed
# Helper functions for daily summary will be reimplemented in Phase 5

# def _daily_summary_nutrition_domain(
#     uid: str,
#     date: str,
#     nutrition_integration: Any,
# ) -> DailySummary:
#     """Daily summary with nutrition domain V2 integration."""
#     # Calculate base summary data for nutrition domain to enhance
#     all_meals = meal_repo.list_all(uid)
#     day_meals = [m for m in all_meals if m.timestamp.startswith(date)]
#
#     def _acc(name: str) -> float:
#         total = 0.0
#         for m in day_meals:
#             val = getattr(m, name)
#             if val is not None:
#                 total += float(val)
#         return total
#
#     calories_total = int(_acc("calories")) if day_meals else 0
#
#     def _opt(name: str) -> Optional[float]:
#         if not day_meals:
#             return 0.0
#         val = _acc(name)
#         return round(val, 2)
#
#     # Get activity data from health_totals_repo
#     steps_tot, cal_out_tot = health_totals_repo.daily_totals(user_id=uid, date=date)
#     act_stats = activity_repo.get_daily_stats(uid, date + "T00:00:00Z")
#     events_count = act_stats.get("events_count", 0)
#     calories_deficit = int(round(cal_out_tot - calories_total))
#
#     if cal_out_tot > 0:
#         pct = (calories_total / cal_out_tot) * 100
#         if pct < 0:
#             pct = 0
#         if pct > 999:
#             pct = 999
#         calories_replenished_percent = int(round(pct))
#     else:
#         calories_replenished_percent = 0
#
#     # Create base summary for nutrition domain to enhance
#     base_summary = {
#         "date": date,
#         "user_id": uid,
#         "meals": len(day_meals),
#         "calories": calories_total,
#         "protein": _opt("protein"),
#         "carbs": _opt("carbs"),
#         "fat": _opt("fat"),
#         "fiber": _opt("fiber"),
#         "sugar": _opt("sugar"),
#         "sodium": _opt("sodium"),
#         "activity_steps": steps_tot,
#         "activity_calories_out": cal_out_tot,
#         "activity_events": events_count,
#         "calories_deficit": calories_deficit,
#         "calories_replenished_percent": calories_replenished_percent,
#     }
#
#     # Get enhanced summary from nutrition domain
#     enhanced_dict = nutrition_integration.enhanced_daily_summary(
#         user_id=uid,
#         date=date,
#         fallback_summary=base_summary,
#     )
#
#     # Create DailySummary from enhanced data
#     return DailySummary(
#         date=enhanced_dict["date"],
#         user_id=enhanced_dict["user_id"],
#         meals=enhanced_dict["meals"],
#         calories=enhanced_dict["calories"],
#         protein=enhanced_dict["protein"],
#         carbs=enhanced_dict["carbs"],
#         fat=enhanced_dict["fat"],
#         fiber=enhanced_dict["fiber"],
#         sugar=enhanced_dict["sugar"],
#         sodium=enhanced_dict["sodium"],
#         activity_steps=enhanced_dict["activity_steps"],
#         activity_calories_out=enhanced_dict["activity_calories_out"],
#         activity_events=enhanced_dict["activity_events"],
#         calories_deficit=enhanced_dict.get("enhanced_calculations", {}).get(
#             "deficit_v2", enhanced_dict["calories_deficit"]
#         ),
#         calories_replenished_percent=enhanced_dict.get("enhanced_calculations", {}).get(
#             "replenished_pct_v2", enhanced_dict["calories_replenished_percent"]
#         ),
#     )


@strawberry.type
class Query:
    @strawberry.field
    def server_time(self) -> str:
        return datetime.datetime.utcnow().isoformat() + "Z"

    @strawberry.field
    def health(self) -> str:
        return "ok"

    # ============================================
    # Phase 5: New CQRS Meal Resolvers
    # ============================================

    @strawberry.field(  # type: ignore[misc]
        description="Atomic utility queries for testing capabilities"
    )
    def atomic(self) -> AtomicQueries:
        """Atomic queries for testing individual capabilities in isolation.

        Example:
            query {
              atomic {
                recognizeFood(photoUrl: "https://...") { items { label } }
              }
            }
        """
        return AtomicQueries()

    @strawberry.field(description="Aggregate meal data queries")  # type: ignore[misc]
    def meals(self) -> AggregateQueries:
        """Aggregate queries for meal data operations (CQRS).

        Example:
            query {
              meals {
                meal(mealId: "...", userId: "user123") { totalCalories }
                search(userId: "user123", queryText: "chicken") { meals { id } }
              }
            }
        """
        return AggregateQueries()

    @strawberry.field(description="Activity data queries")  # type: ignore[misc]
    def activity(self) -> ActivityQueries:
        """Activity and health data queries.

        Example:
            query {
              activity {
                entries(userId: "user123", limit: 10) { steps }
                syncEntries(date: "2025-10-25", userId: "user123") { timestamp }
              }
            }
        """
        return ActivityQueries()

    @strawberry.field(description="Nutritional profile queries")  # type: ignore[misc]
    def nutritional_profile(self) -> NutritionalProfileQueries:
        """Nutritional profile queries (CQRS).

        Example:
            query {
              nutritionalProfile {
                nutritionalProfile(userId: "user123") { caloriesTarget }
                progressScore(profileId: "...", startDate: "2024-01-01",
                              endDate: "2024-01-31") { weightDelta }
              }
            }
        """
        return NutritionalProfileQueries()

    @strawberry.field(description="User domain queries")  # type: ignore[misc]
    def user(self) -> UserQueries:
        """User queries for authentication and profile data.

        Example:
            query {
              user {
                exists(auth0Sub: "auth0|123") { exists }
                byId(userId: "user-uuid") { email }
              }
            }
        """
        return UserQueries()

    # ============================================
    # Legacy Resolvers (MOVED TO AGGREGATES)
    # ============================================

    # MOVED: activityEntries → activity.entries
    # MOVED: syncEntries → activity.syncEntries
    # MOVED: searchMeals → meals.search
    # MOVED: dailySummary → meals.dailySummary

    # ============================================
    # Legacy Resolvers (TEMPORARILY DISABLED)
    # ============================================

    # TEMPORARILY DISABLED DURING REFACTOR - Phase 0: MealEntry type removed
    # Will be reimplemented in Phase 5 with new GraphQL schema
    # @strawberry.field(description="Lista pasti più recenti (desc)")  # type: ignore[misc]
    # def meal_entries(
    #     self,
    #     info: Info[Any, Any],  # noqa: ARG002
    #     limit: int = 20,
    #     after: Optional[str] = None,
    #     before: Optional[str] = None,
    #     user_id: Optional[str] = None,
    # ) -> List[MealEntry]:
    #     if limit <= 0:
    #         limit = 20
    #     if limit > 200:
    #         limit = 200
    #     uid = user_id or DEFAULT_USER_ID
    #     records = meal_repo.list(uid, limit, after, before)
    #     return [MealEntry(**dataclasses.asdict(r)) for r in records]

    # TEMPORARILY DISABLED DURING REFACTOR - Phase 0: DailySummary type removed
    # Will be reimplemented in Phase 5 with new GraphQL schema
    # @strawberry.field(description="Riepilogo nutrienti per giorno (UTC)")  # type: ignore[misc]
    # def daily_summary(
    #     self,
    #     info: Info[Any, Any],  # noqa: ARG002
    #     date: str,
    #     user_id: Optional[str] = None,
    # ) -> DailySummary:
    #     """Aggrega nutrienti dei pasti il cui timestamp inizia con 'date'.
    #
    #     'date' formato YYYY-MM-DD. Validazione minima per ora.
    #     """
    #     uid = user_id or DEFAULT_USER_ID
    #
    #     # Nutrition domain V2 è sempre attivo
    #     nutrition_integration = get_nutrition_integration_service()
    #     return _daily_summary_nutrition_domain(uid, date, nutrition_integration)

    @strawberry.field(description="Statistiche cache prodotto")  # type: ignore[misc]
    def cache_stats(self, info: Info[Any, Any]) -> "CacheStats":  # noqa: ARG002,E501
        s = cache.stats()
        return CacheStats(
            keys=s["keys"],
            hits=s["hits"],
            misses=s["misses"],
        )


@strawberry.type
class Mutation:
    # TEMPORARILY DISABLED DURING REFACTOR - Phase 0: LogMealInput, MealEntry types removed
    # Will be reimplemented in Phase 5 with new GraphQL schema
    # @strawberry.mutation(
    #     description=("Log di un pasto con arricchimento nutrienti se barcode noto")
    # )  # type: ignore[misc]
    # async def log_meal(
    #     self, info: Info[Any, Any], input: LogMealInput
    # ) -> MealEntry:  # noqa: ARG002
    #     # Feature flag routing to domain integration
    #     from graphql.meal_resolver import get_meal_resolver
    #
    #     return await get_meal_resolver().log_meal(info, input)
    #     if input.quantity_g <= 0:
    #         raise GraphQLError("INVALID_QUANTITY: quantity_g deve essere > 0")
    #     ts = input.timestamp or datetime.datetime.utcnow().isoformat() + "Z"
    #     user_id = input.user_id or DEFAULT_USER_ID
    #     # Idempotency key non deve dipendere da timestamp server; se timestamp
    #     # non è fornito dall'utente non lo includiamo nella chiave.
    #     # se utente non specifica timestamp non includerlo nella chiave
    #     base_ts_for_key = input.timestamp or ""
    #     idempotency_key = input.idempotency_key or (
    #         f"{input.name.lower()}|{round(input.quantity_g, 3)}|"
    #         f"{base_ts_for_key}|{input.barcode or ''}|{user_id}"
    #     )
    #     existing = meal_repo.find_by_idempotency(user_id, idempotency_key)
    #     if existing:
    #         return MealEntry(**dataclasses.asdict(existing))
    #
    #     nutrients: Dict[str, Optional[float]] = {k: None for k in NUTRIENT_FIELDS}
    #
    #     prod: Optional[Product] = None
    #     if input.barcode:
    #         key = f"product:{input.barcode}"
    #         prod_cached = cache.get(key)
    #         if prod_cached:
    #             prod = prod_cached
    #         else:
    #             try:
    #                 dto = await adapter.fetch_product(input.barcode)
    #                 prod = _map_product(dto)
    #                 cache.set(key, prod, PRODUCT_CACHE_TTL_S)
    #             except adapter.ProductNotFound:
    #                 prod = None
    #             except adapter.OpenFoodFactsError:
    #                 prod = None
    #     if prod:
    #         nutrients = _enrich_from_product(prod, input.quantity_g)
    #
    #     meal = MealRecord(
    #         id=str(uuid.uuid4()),
    #         user_id=user_id,
    #         name=input.name,
    #         quantity_g=input.quantity_g,
    #         timestamp=ts,
    #         barcode=input.barcode,
    #         idempotency_key=idempotency_key,
    #         nutrient_snapshot_json=(
    #             __import__("json").dumps(
    #                 {k: nutrients[k] for k in NUTRIENT_FIELDS},
    #                 sort_keys=True,
    #             )
    #             if prod
    #             else None
    #         ),
    #         calories=(
    #             nutrients["calories"]
    #             if nutrients["calories"] is None
    #             else int(nutrients["calories"])
    #         ),
    #         protein=nutrients["protein"],
    #         carbs=nutrients["carbs"],
    #         fat=nutrients["fat"],
    #         fiber=nutrients["fiber"],
    #         sugar=nutrients["sugar"],
    #         sodium=nutrients["sodium"],
    #     )
    #     meal_repo.add(meal)
    #     return MealEntry(**dataclasses.asdict(meal))

    # TEMPORARILY DISABLED DURING REFACTOR - Phase 0: UpdateMealInput, MealEntry types removed
    # Will be reimplemented in Phase 5 with new GraphQL schema
    # @strawberry.mutation(description="Aggiorna un pasto esistente")  # type: ignore[misc]
    # async def update_meal(
    #     self, info: Info[Any, Any], input: UpdateMealInput
    # ) -> MealEntry:  # noqa: ARG002
    #     # Feature flag routing to domain integration
    #     from graphql.meal_resolver import get_meal_resolver
    #
    #     return await get_meal_resolver().update_meal(info, input)

    # TEMPORARILY DISABLED DURING REFACTOR - Phase 0: meal_resolver removed
    # Will be reimplemented in Phase 5 with new GraphQL schema
    # @strawberry.mutation(description="Cancella un pasto")  # type: ignore[misc]
    # async def delete_meal(self, info: Info[Any, Any], id: str) -> bool:  # noqa: ARG002
    #     # Feature flag routing to domain integration
    #     from graphql.meal_resolver import get_meal_resolver
    #
    #     return await get_meal_resolver().delete_meal(info, id)

    # ============================================
    # Phase 5: New CQRS Meal Mutations
    # ============================================

    @strawberry.field(description="Meal domain mutations (CQRS commands)")  # type: ignore[misc]
    def meals(self) -> MealMutations:
        """Meal domain mutations following CQRS pattern.

        Example:
            mutation {
              meals {
                analyzeMealPhoto(input: {...}) {
                  ... on MealAnalysisSuccess { meal { id } }
                }
              }
            }
        """
        return MealMutations()

    # ============================================
    # Activity & Health Mutations
    # ============================================

    @strawberry.field(description="Activity domain mutations")  # type: ignore[misc]
    def activity(self) -> ActivityMutations:
        """Activity domain mutations.

        Example:
            mutation {
              activity {
                syncActivityEvents(input: [...]) {
                  accepted
                  duplicates
                  rejected { index reason }
                }
              }
            }
        """
        return ActivityMutations()

    @strawberry.field(description="Nutritional profile mutations")  # type: ignore[misc]
    def nutritional_profile(self) -> NutritionalProfileMutations:
        """Nutritional profile mutations (CQRS commands).

        Example:
            mutation {
              nutritionalProfile {
                createNutritionalProfile(input: {...}) { profileId }
                recordProgress(input: {...}) { date weight }
              }
            }
        """
        return NutritionalProfileMutations()

    @strawberry.field(description="User domain mutations")  # type: ignore[misc]
    def user(self) -> UserMutations:
        """User mutations for authentication and profile management.

        Example:
            mutation {
              user {
                authenticateOrCreate(input: {...}) { userId }
                updatePreferences(input: {...}) { success }
              }
            }
        """
        return UserMutations()

    @strawberry.mutation(  # type: ignore[misc]
        description="Sincronizza snapshot cumulativi attività"
    )
    def sync_health_totals(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        input: HealthTotalsInput,
        idempotency_key: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> SyncHealthTotalsResult:
        uid = user_id or input.user_id or DEFAULT_USER_ID
        res = health_totals_repo.record_snapshot(
            user_id=uid,
            date=input.date,
            timestamp=input.timestamp,
            steps=input.steps,
            calories_out=input.calories_out,
            hr_avg_session=input.hr_avg_session,
            idempotency_key=idempotency_key,
        )
        delta_rec = res["delta_record"]
        delta_obj = None
        if delta_rec:
            delta_obj = HealthTotalsDelta(**dataclasses.asdict(delta_rec))
        return SyncHealthTotalsResult(
            accepted=res["accepted"],
            duplicate=res["duplicate"],
            reset=res["reset"],
            idempotency_key_used=res["idempotency_key_used"],
            idempotency_conflict=res["idempotency_conflict"],
            delta=delta_obj,
        )

    # TEMPORARILY DISABLED DURING REFACTOR - Phase 0
    # Replaced by Phase 5 MealMutations.analyzeMealPhoto
    # --- AI Photo Stub Mutations ---
    # @strawberry.mutation(  # type: ignore[misc]
    #     description="Analizza una foto (stub deterministico)"
    # )
    # async def analyze_meal_photo(
    #     self,
    #     info: Info[Any, Any],  # noqa: ARG002
    #     input: AnalyzeMealPhotoInput,
    # ) -> MealPhotoAnalysis:
    #     """Async mutation per analisi foto.
    #
    #     Evita uso di asyncio.run dentro event loop (pytest/strawberry) e
    #     utilizza il nuovo percorso create_or_get_async.
    #     """
    #     # TEMPORARILY DISABLED DURING REFACTOR - Phase 0
    #     # uid = input.user_id or DEFAULT_USER_ID
    #     # now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    #
    #     # Domain service V2 (only path)
    #     # from domain.meal.application.meal_analysis_service import (
    #     #     MealAnalysisService,
    #     # )
    #     # from domain.meal.model import MealAnalysisRequest
    #     raise NotImplementedError("Meal analysis service temporarily disabled during refactor")


# Use create_schema() to ensure all resolvers are included
from graphql.schema import create_schema  # noqa: E402

schema = create_schema()

# Explicit export per mypy/tests
__all__: list[str] = []


@asynccontextmanager
async def lifespan(_: FastAPI) -> Any:  # pragma: no cover osservabilità
    """Application lifecycle manager - gestisce startup/shutdown di tutte le risorse.

    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                      LIFESPAN CONTEXT MANAGER                             ║
    ║                                                                           ║
    ║  RUOLO:                                                                   ║
    ║  Gestisce il ciclo di vita completo delle risorse dell'applicazione:     ║
    ║  - Inizializza client HTTP (OpenAI, USDA, OpenFoodFacts) via async with  ║
    ║  - Prepara database connections (MongoDB - Phase 7.1)                    ║
    ║  - Configura observability (logs, metrics, tracing)                      ║
    ║  - Garantisce cleanup automatico alla chiusura                           ║
    ║                                                                           ║
    ║  PATTERN:                                                                 ║
    ║  1. STARTUP (prima di yield):                                            ║
    ║     - Entra nei context manager dei client HTTP                          ║
    ║     - Inizializza sessioni aiohttp/AsyncOpenAI                           ║
    ║     - Assegna ai singleton globali per dependency injection              ║
    ║     - Logga configurazione e snapshot environment                        ║
    ║                                                                           ║
    ║  2. RUNTIME (yield):                                                     ║
    ║     - Applicazione serve requests con risorse inizializzate              ║
    ║                                                                           ║
    ║  3. SHUTDOWN (dopo yield):                                               ║
    ║     - Context manager chiudono automaticamente sessioni HTTP             ║
    ║     - Database connections rilasciate (future)                           ║
    ║     - Zero memory leak garantito                                         ║
    ║                                                                           ║
    ║  IMPLEMENTATO (Phase 7.0):                                               ║
    ║  ✅ OpenAI Vision Client (async with)                                    ║
    ║  ✅ USDA Nutrition Client (async with)                                   ║
    ║  ✅ OpenFoodFacts Barcode Client (async with)                            ║
    ║                                                                           ║
    ║  TODO (Phase 7.1+):                                                      ║
    ║  ⚪ MongoDB connection pool (async with motor.AsyncIOMotorClient)        ║
    ║  ⚪ Redis cache connection (se necessario)                               ║
    ║  ⚪ External API health checks                                           ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """
    logger = _logging.getLogger("startup")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: LOGGING & OBSERVABILITY
    # ═══════════════════════════════════════════════════════════════════════════
    api_key = os.getenv("OPENAI_API_KEY")
    masked_key = None
    if api_key:
        if len(api_key) > 8:
            masked_key = api_key[:4] + "..." + api_key[-4:]
        else:
            masked_key = "***"

    logger.info(
        "startup.config",
        extra={
            "openai_key_present": bool(api_key),
            "openai_key_masked": masked_key,
        },
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: HTTP CLIENT INITIALIZATION (async with context managers)
    # ═══════════════════════════════════════════════════════════════════════════
    # Factory crea client non inizializzati, lifespan li inizializza via async with
    # Questo garantisce:
    # - Sessioni HTTP attive durante tutta la vita del server
    # - Cleanup automatico alla chiusura (no memory leak)
    # - Context manager __aenter__/__aexit__ eseguiti correttamente

    logger.info("lifespan.startup", extra={"phase": "http_clients_init"})

    vision_client = create_vision_provider()
    nutrition_client = create_nutrition_provider()
    barcode_client = create_barcode_provider()

    async with (
        vision_client as initialized_vision,  # type: ignore[attr-defined]
        nutrition_client as initialized_nutrition,  # type: ignore[attr-defined]
        barcode_client as initialized_barcode,  # type: ignore[attr-defined]
    ):

        # Assegna ai singleton globali per dependency injection
        global _vision_provider, _nutrition_provider, _barcode_provider
        global _recognition_service, _nutrition_service, _barcode_service
        global _photo_orchestrator, _barcode_orchestrator

        _vision_provider = initialized_vision
        _nutrition_provider = initialized_nutrition
        _barcode_provider = initialized_barcode

        # CRITICAL: Ricostruisci servizi con provider inizializzati
        # I servizi creati al module load tengono riferimenti a provider non inizializzati
        _recognition_service = FoodRecognitionService(_vision_provider)
        _nutrition_service = NutritionEnrichmentService(
            usda_provider=_nutrition_provider,
            category_provider=_nutrition_provider,
            fallback_provider=_nutrition_provider,
        )
        _barcode_service = BarcodeService(_barcode_provider)

        # Ricostruisci orchestrator con servizi aggiornati
        _photo_orchestrator = MealAnalysisOrchestrator(
            recognition_service=_recognition_service,
            nutrition_service=_nutrition_service,
            meal_factory=_meal_factory,
        )
        _barcode_orchestrator = BarcodeOrchestrator(
            barcode_service=_barcode_service,
            nutrition_service=_nutrition_service,
            meal_factory=_meal_factory,
        )

        logger.info(
            "lifespan.clients_ready",
            extra={
                "vision": type(initialized_vision).__name__,
                "nutrition": type(initialized_nutrition).__name__,
                "barcode": type(initialized_barcode).__name__,
            },
        )

        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 3: FUTURE - DATABASE INITIALIZATION (Phase 7.1)
        # ═══════════════════════════════════════════════════════════════════════
        # TODO: Quando implementeremo MongoDB repository:
        # db_client = create_mongodb_client()
        # async with db_client as initialized_db:
        #     global _meal_repository
        #     _meal_repository = MongoDBMealRepository(initialized_db)
        #     logger.info("lifespan.mongodb_ready", ...)

        # ═══════════════════════════════════════════════════════════════════════
        # RUNTIME: Application serves requests
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("lifespan.ready", extra={"status": "serving"})
        yield

        # ═══════════════════════════════════════════════════════════════════════
        # SHUTDOWN: Cleanup automatico (context manager close sessions)
        # ═══════════════════════════════════════════════════════════════════════
        logger.info("lifespan.shutdown", extra={"status": "cleanup"})


app = FastAPI(
    title="Nutrifit Backend Subgraph",
    version=APP_VERSION,
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
async def version() -> dict[str, str]:
    return {"version": APP_VERSION}


# ============================================
# Phase 5: GraphQL Context Setup
# ============================================

# Create singleton instances (persistent across requests for testing)
# IMPORTANT: In production, these should be request-scoped or use proper connection pooling

# Repository (environment-based selection via factory)
# Environment variable controls repository selection:
# - MEAL_REPOSITORY: "inmemory" (default) | "mongodb" (P7.1)
# - PROFILE_REPOSITORY: "inmemory" (default) | "mongodb" (P7.1)
# - USER_REPOSITORY: "inmemory" (default) | "mongodb"
_meal_repository = get_meal_repository()
_profile_repository = get_profile_repository()
_user_repository = get_user_repository()  # Environment-based selection

_event_bus = InMemoryEventBus()
_idempotency_cache = InMemoryIdempotencyCache()
_meal_factory = MealFactory()

# Nutritional Profile adapters (Hexagonal Architecture)
_bmr_calculator = BMRCalculatorAdapter()
_tdee_calculator = TDEECalculatorAdapter()
_macro_calculator = MacroCalculatorAdapter()

# Create providers (environment-based selection via factory)
# Environment variables control provider selection:
# - VISION_PROVIDER: "openai" | "stub" (default: stub)
# - NUTRITION_PROVIDER: "usda" | "stub" (default: stub)
# - BARCODE_PROVIDER: "openfoodfacts" | "stub" (default: stub)
_vision_provider = get_vision_provider()
_nutrition_provider = get_nutrition_provider()
_barcode_provider = get_barcode_provider()

# Wrap providers in domain services
_recognition_service = FoodRecognitionService(_vision_provider)
_nutrition_service = NutritionEnrichmentService(
    usda_provider=_nutrition_provider,
    category_provider=_nutrition_provider,
    fallback_provider=_nutrition_provider,
)
_barcode_service = BarcodeService(_barcode_provider)

# Create orchestrators
_photo_orchestrator = MealAnalysisOrchestrator(
    recognition_service=_recognition_service,
    nutrition_service=_nutrition_service,
    meal_factory=_meal_factory,
)
_barcode_orchestrator = BarcodeOrchestrator(
    barcode_service=_barcode_service,
    nutrition_service=_nutrition_service,
    meal_factory=_meal_factory,
)

# Nutritional Profile orchestrator
from application.nutritional_profile.orchestrators.profile_orchestrator import (  # noqa: E501, E402
    ProfileOrchestrator,
)

_profile_orchestrator = ProfileOrchestrator(
    bmr_service=_bmr_calculator,  # type: ignore
    tdee_service=_tdee_calculator,  # type: ignore
    macro_service=_macro_calculator,  # type: ignore
)


def get_graphql_context() -> Any:
    """Create GraphQL context with all dependencies.

    Returns dict-like context for resolver dependency injection.

    Note: Uses singleton instances for testing (persistent across requests).
    In production, these should be request-scoped or use proper connection pooling.
    """
    return create_context(
        meal_repository=_meal_repository,
        profile_repository=_profile_repository,
        user_repository=_user_repository,
        event_bus=_event_bus,
        idempotency_cache=_idempotency_cache,
        meal_orchestrator=_photo_orchestrator,  # Supports both photo and text
        photo_orchestrator=_photo_orchestrator,  # Backward compatibility
        barcode_orchestrator=_barcode_orchestrator,
        profile_orchestrator=_profile_orchestrator,
        recognition_service=_recognition_service,
        enrichment_service=_nutrition_service,
        barcode_service=_barcode_service,
    )


graphql_app: Final[GraphQLRouter[Any, Any]] = GraphQLRouter(
    schema, context_getter=get_graphql_context
)
app.include_router(graphql_app, prefix="/graphql")


# DEBUG: Diagnostic endpoint to check schema
@app.get("/debug/schema-info")
async def debug_schema_info() -> dict[str, Any]:
    """Debug endpoint to inspect the GraphQL schema."""
    from strawberry.printer import print_schema

    # Check if graphql_app has the schema
    router_schema = graphql_app.schema if hasattr(graphql_app, "schema") else None

    mutation_type_def = (
        getattr(schema.mutation, "_type_definition", None) if schema.mutation else None
    )
    mutation_fields = [f.name for f in mutation_type_def.fields] if mutation_type_def else []

    return {
        "module_schema_has_mutation": schema.mutation is not None,
        "router_schema_has_mutation": (
            router_schema.mutation is not None if router_schema else "N/A"
        ),
        "schemas_are_same_object": (schema is router_schema if router_schema else False),
        "mutation_type_name": (schema.mutation.__name__ if schema.mutation else None),
        "mutation_fields": mutation_fields,
        "schema_preview": print_schema(schema)[:500],
    }


# REST API: Image Upload endpoint
from api.upload import router as upload_router  # noqa: E402

app.include_router(upload_router)


# ============================================
# API Documentation Endpoints
# ============================================
