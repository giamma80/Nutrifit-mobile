from __future__ import annotations

# Standard library
import os
import datetime
import dataclasses
import hashlib as _hashlib  # NEW
import json as _json  # NEW
import logging as _logging
from contextlib import asynccontextmanager
from typing import Final, Any, Optional, List, cast

# Third-party
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from graphql import GraphQLError

# Local application imports
from cache import cache
from openfoodfacts import adapter
from repository.activities import (
    activity_repo,
    ActivityEventRecord as _ActivityEventRecord,
    ActivitySource as _RepoActivitySource,
)  # NEW
from repository.health_totals import health_totals_repo  # NEW
from inference.adapter import get_active_adapter

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

# Legacy AI types (keeping MealPhotoAnalysis for compatibility)
from graphql.types_ai import MealPhotoAnalysis

# from graphql.types_ai import AnalyzeMealPhotoInput  # Replaced by types_meal_mutations
from graphql.types_activity_health import (
    ActivitySource,
    ActivityEvent,
    RejectedActivityEvent,
    IngestActivityResult,
    HealthTotalsDelta,
    SyncHealthTotalsResult,
    CacheStats,
)
from graphql.types_product import Product, map_product

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


_map_product = map_product  # retro compat alias


# ----------------- Meal Logging (B2) + Repository refactor -----------------
"""GraphQL types spostati in moduli per ridurre complessità mypy."""


# ----------------- Activity Ingestion (B3) -----------------
# Riutilizziamo l'enum del repository per evitare duplicazione incoerente
# Enum e ActivityEvent con default già definiti in modulo types_activity_health


# ----------------- Health Totals Sync (B4) -----------------

# ----------------- AI Meal Photo Stub (Fase 0) -----------------
"""Tipi AI spostati in graphql.types_ai"""


# Legacy function removed - using only V2 domain service flow


@strawberry.input
class HealthTotalsInput:
    timestamp: str
    date: str
    steps: int
    calories_out: float
    hr_avg_session: Optional[float] = None
    user_id: Optional[str] = None


@strawberry.input
class ActivityMinuteInput:
    ts: str  # DateTime as string, will be normalized to minute precision
    steps: Optional[int] = 0
    calories_out: Optional[float] = None
    hr_avg: Optional[float] = None
    # Enum GraphQL (repo enum esposto) default MANUAL
    source: ActivitySource = ActivitySource.MANUAL


"""Input pasti spostati in graphql.types_meal"""


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
    def hello(self) -> str:
        return "nutrifit-backend alive"

    @strawberry.field
    def server_time(self) -> str:
        return datetime.datetime.utcnow().isoformat() + "Z"

    @strawberry.field
    def health(self) -> str:
        return "ok"

    @strawberry.field(description="Fetch prodotto da OpenFoodFacts (cache)")  # type: ignore[misc]
    async def product(
        self, info: Info[Any, Any], barcode: str
    ) -> Optional[Product]:  # noqa: ARG002
        key = f"product:{barcode}"
        cached = cache.get(key)
        if cached is not None:
            return cast(Product, cached)
        try:
            dto = await adapter.fetch_product(barcode)
        except adapter.ProductNotFound:
            return None
        except adapter.OpenFoodFactsError as e:
            raise GraphQLError(f"OPENFOODFACTS_ERROR: {e}") from e
        # cast per soddisfare protocollo _ProductLike (nutrients compatibili)
        prod = _map_product(cast(Any, dto))
        cache.set(key, prod, PRODUCT_CACHE_TTL_S)
        return prod

    # ============================================
    # Phase 5: New CQRS Meal Resolvers
    # ============================================

    @strawberry.field(description="Atomic utility queries for testing capabilities")
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

    @strawberry.field(description="Aggregate meal data queries")
    def meals(self) -> AggregateQueries:
        """Aggregate queries for meal data operations (CQRS).

        Example:
            query {
              meals {
                meal(mealId: "...", userId: "user123") { totalCalories }
              }
            }
        """
        return AggregateQueries()

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

    @strawberry.field(  # type: ignore[misc]
        description="Lista eventi activity minuto (diagnostica)"
    )
    def activity_entries(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        limit: int = 100,
        after: Optional[str] = None,
        before: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[ActivityEvent]:
        if limit <= 0:
            limit = 100
        if limit > 500:
            limit = 500
        uid = user_id or DEFAULT_USER_ID
        events = activity_repo.list(
            uid,
            start_ts=after,
            end_ts=before,
            limit=limit,
        )
        return [ActivityEvent(**dataclasses.asdict(e)) for e in events]

    @strawberry.field(description="Lista delta sync health totals per giorno")  # type: ignore[misc]
    def sync_entries(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        date: str,
        user_id: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 200,
    ) -> List[HealthTotalsDelta]:
        if limit <= 0:
            limit = 50
        if limit > 500:
            limit = 500
        uid = user_id or DEFAULT_USER_ID
        records = health_totals_repo.list_deltas(
            user_id=uid, date=date, after_ts=after, limit=limit
        )
        return [HealthTotalsDelta(**dataclasses.asdict(r)) for r in records]

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

    @strawberry.field(description="Meal domain mutations (CQRS commands)")
    def meal(self) -> MealMutations:
        """Meal domain mutations following CQRS pattern.

        Example:
            mutation {
              meal {
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

    @strawberry.mutation(  # type: ignore[misc]
        description="Ingest batch minute activity events (idempotent)"
    )
    def ingest_activity_events(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        input: List[ActivityMinuteInput],
        idempotency_key: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> IngestActivityResult:
        uid = user_id or DEFAULT_USER_ID
        # Canonicalize & normalize timestamps to minute BEFORE signature
        norm_events: List[_ActivityEventRecord] = []
        for ev in input:
            raw_ts = ev.ts
            ts_norm = activity_repo.normalize_minute_iso(raw_ts) or raw_ts
            src_name = getattr(ev.source, "name", "MANUAL")
            repo_source = _RepoActivitySource[src_name]
            norm_events.append(
                _ActivityEventRecord(
                    user_id=uid,
                    ts=ts_norm,
                    steps=ev.steps if ev.steps is not None else 0,
                    calories_out=ev.calories_out,
                    hr_avg=ev.hr_avg,
                    source=repo_source,
                )
            )
        sig_payload = [
            {
                "ts": e.ts,
                "steps": e.steps,
                "calories_out": e.calories_out,
                "hr_avg": e.hr_avg,
                "source": e.source.value,
            }
            for e in sorted(norm_events, key=lambda r: r.ts)
        ]
        canonical = _json.dumps(sig_payload, sort_keys=True, separators=(",", ":"))
        signature = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        # Se la chiave non è fornita generiamo deterministico da signature
        auto_key = None
        if idempotency_key is None:
            auto_key = "auto-" + signature[:16]
            idempotency_key = auto_key
        idem_key = (uid, idempotency_key)
        cached = getattr(activity_repo, "_batch_idempo", {}).get(idem_key)
        if cached:
            existing_sig, result_dict = cached
            if existing_sig == signature:
                # Cached result: convert rejected tuples into GraphQL objects
                return IngestActivityResult(
                    accepted=result_dict["accepted"],  # noqa: E501
                    duplicates=result_dict["duplicates"],
                    rejected=[
                        RejectedActivityEvent(index=idx, reason=reason)
                        for idx, reason in result_dict["rejected"]
                    ],
                    idempotency_key_used=idempotency_key,
                )
            raise GraphQLError("IdempotencyConflict: key re-used with different payload")
        # Ingest via repository (normalization & dedup inside repo)
        accepted, duplicates, rejected = activity_repo.ingest_batch(norm_events)
        # Cache idempotent result
        getattr(activity_repo, "_batch_idempo")[idem_key] = (
            signature,
            {
                "accepted": accepted,
                "duplicates": duplicates,
                "rejected": rejected,
            },
        )
        return IngestActivityResult(
            accepted=accepted,
            duplicates=duplicates,
            rejected=[RejectedActivityEvent(index=i, reason=r) for i, r in rejected],
            idempotency_key_used=idempotency_key,
        )

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


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)

# Esplicit export per mypy/tests
__all__ = [
    "Product",
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> Any:  # pragma: no cover osservabilità
    """Startup hook: log adapter e (se debug) snapshot env.

    Non logghiamo mai valori sensibili (OPENAI_API_KEY) ma solo presenza
    e maschera.
    """
    adapter = get_active_adapter()
    name = adapter.name()
    real_flag = os.getenv("AI_GPT4V_REAL_ENABLED")
    api_key = os.getenv("OPENAI_API_KEY")
    masked_key = None
    if api_key:
        if len(api_key) > 8:
            masked_key = api_key[:4] + "..." + api_key[-4:]
        else:
            masked_key = "***"
    logger = _logging.getLogger("startup")
    logger.info(
        "adapter.selected",
        extra={
            "adapter": name,
            "ai_meal_photo_mode": os.getenv("AI_MEAL_PHOTO_MODE"),
            "gpt4v_real_flag": real_flag,
            "openai_key_present": bool(api_key),
            "openai_key_masked": masked_key,
        },
    )

    # Snapshot esteso solo se debug attivo
    if os.getenv("AI_MEAL_PHOTO_DEBUG") == "1":
        env_keys = [
            "AI_MEAL_PHOTO_MODE",
            "AI_GPT4V_REAL_ENABLED",
            "OPENAI_VISION_MODEL",
            "AI_NORMALIZATION_MODE",
            "AI_PHOTO_URL_ALLOWED_HOSTS",
            "AI_USDA_ENABLED",
            "AI_USDA_SNAPSHOT",
            "AI_USDA_COOKING",
            "AI_USDA_MICROS",
            "AI_METRICS_PARSE",
            "AI_METRICS_NORMALIZATION",
            "AI_GPT_DAILY_QUOTA",
            "AI_GPT_RATE_LIMIT_PER_MIN",
            "AI_MEAL_PHOTO_DEBUG",
        ]
        snapshot = {k: os.getenv(k) for k in env_keys}
        logger.info("env.snapshot", extra={"env": snapshot})
    yield


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

# Import dependencies at module level
from graphql.context import create_context
from infrastructure.persistence.in_memory.meal_repository import InMemoryMealRepository
from infrastructure.events.in_memory_bus import InMemoryEventBus
from infrastructure.cache.in_memory_idempotency_cache import InMemoryIdempotencyCache
from application.meal.orchestrators.photo_orchestrator import PhotoOrchestrator
from application.meal.orchestrators.barcode_orchestrator import BarcodeOrchestrator
from domain.meal.core.factories.meal_factory import MealFactory
from infrastructure.meal.providers.stub_vision_provider import StubVisionProvider
from infrastructure.meal.providers.stub_nutrition_provider import StubNutritionProvider
from infrastructure.meal.providers.stub_barcode_provider import StubBarcodeProvider
from domain.meal.recognition.services.recognition_service import FoodRecognitionService
from domain.meal.barcode.services.barcode_service import BarcodeService
from domain.meal.nutrition.services.enrichment_service import NutritionEnrichmentService

# Create singleton instances (persistent across requests for testing)
# IMPORTANT: In production, these should be request-scoped or use proper connection pooling
_meal_repository = InMemoryMealRepository()
_event_bus = InMemoryEventBus()
_idempotency_cache = InMemoryIdempotencyCache()
_meal_factory = MealFactory()

# Create stub providers
_vision_provider = StubVisionProvider()
_nutrition_provider = StubNutritionProvider()
_barcode_provider = StubBarcodeProvider()

# Wrap providers in domain services
_recognition_service = FoodRecognitionService(_vision_provider)
_nutrition_service = NutritionEnrichmentService(
    usda_provider=_nutrition_provider,
    category_provider=_nutrition_provider,
    fallback_provider=_nutrition_provider,
)
_barcode_service = BarcodeService(_barcode_provider)

# Create orchestrators
_photo_orchestrator = PhotoOrchestrator(
    recognition_service=_recognition_service,
    nutrition_service=_nutrition_service,
    meal_factory=_meal_factory,
)
_barcode_orchestrator = BarcodeOrchestrator(
    barcode_service=_barcode_service,
    nutrition_service=_nutrition_service,
    meal_factory=_meal_factory,
)


def get_graphql_context() -> Any:
    """Create GraphQL context with all dependencies.

    Returns dict-like context for resolver dependency injection.

    Note: Uses singleton instances for testing (persistent across requests).
    In production, these should be request-scoped or use proper connection pooling.
    """
    return create_context(
        meal_repository=_meal_repository,
        event_bus=_event_bus,
        idempotency_cache=_idempotency_cache,
        photo_orchestrator=_photo_orchestrator,
        barcode_orchestrator=_barcode_orchestrator,
        recognition_service=_vision_provider,
        enrichment_service=_nutrition_provider,
        barcode_service=_barcode_provider,
    )


graphql_app: Final[GraphQLRouter[Any, Any]] = GraphQLRouter(
    schema, context_getter=get_graphql_context
)
app.include_router(graphql_app, prefix="/graphql")
