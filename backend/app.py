from __future__ import annotations

import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
import datetime
import dataclasses
import os
import uuid
from typing import (
    Final,
    Any,
    Optional,
    Dict,
    List,
    Protocol,
    Mapping,
    cast,
)
from enum import Enum
from strawberry.types import Info
from graphql import GraphQLError

from cache import cache
from openfoodfacts import adapter
from repository.meals import meal_repo, MealRecord  # NEW
from repository.activities import (
    activity_repo,
    ActivityEventRecord as _ActivityEventRecord,
    ActivitySource as _RepoActivitySource,
)  # NEW
from repository.health_totals import health_totals_repo  # NEW
from repository.ai_meal_photo import meal_photo_repo
import hashlib as _hashlib  # NEW
import json as _json  # NEW
from nutrients import NUTRIENT_FIELDS

# TTL in secondi per la cache del prodotto (default 10 minuti)
PRODUCT_CACHE_TTL_S = float(os.getenv("PRODUCT_CACHE_TTL_S", "600"))

# Versione letta da env (Docker build ARG -> ENV APP_VERSION)
APP_VERSION = os.getenv("APP_VERSION", "0.0.0-dev")


@strawberry.type
@dataclasses.dataclass
class Product:
    barcode: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None


class _ProductLike(Protocol):
    barcode: str
    name: str
    brand: Optional[str]
    category: Optional[str]
    nutrients: Mapping[str, Any]


def _map_product(dto: _ProductLike) -> Product:
    n = dto.nutrients
    return Product(
        barcode=dto.barcode,
        name=dto.name,
        brand=dto.brand,
        category=dto.category,
        calories=n.get("calories"),
        protein=n.get("protein"),
        carbs=n.get("carbs"),
        fat=n.get("fat"),
        fiber=n.get("fiber"),
        sugar=n.get("sugar"),
        sodium=n.get("sodium"),
    )


# ----------------- Meal Logging (B2) + Repository refactor -----------------
@strawberry.type
@dataclasses.dataclass
class MealEntry:
    id: str
    user_id: str  # NEW
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


@strawberry.type
@dataclasses.dataclass
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
    # Activity (B3)
    activity_steps: int = 0
    activity_calories_out: float = 0.0
    activity_events: int = 0
    # Calorie balance snapshot (deficit positivo = più consumate che ingerite)
    calories_deficit: int = 0
    calories_replenished_percent: int = 0  # 0-100 (o >100 se surplus)


# ----------------- Activity Ingestion (B3) -----------------
# Riutilizziamo l'enum del repository per evitare duplicazione incoerente
ActivitySource = strawberry.enum(_RepoActivitySource, name="ActivitySource")


@strawberry.type
@dataclasses.dataclass
class ActivityEvent:
    user_id: str
    ts: str  # ISO timestamp normalizzato a minuto UTC
    steps: Optional[int] = None
    calories_out: Optional[float] = None
    hr_avg: Optional[float] = None
    source: ActivitySource = ActivitySource.MANUAL


@strawberry.type
@dataclasses.dataclass
class RejectedActivityEvent:
    index: int
    reason: str


@strawberry.type
@dataclasses.dataclass
class IngestActivityResult:
    accepted: int
    duplicates: int
    rejected: List[RejectedActivityEvent]
    idempotency_key_used: Optional[str] = None


# ----------------- Health Totals Sync (B4) -----------------


@strawberry.type
@dataclasses.dataclass
class HealthTotalsDelta:
    id: str
    user_id: str
    date: str
    timestamp: str
    steps_delta: int
    calories_out_delta: float
    steps_total: int
    calories_out_total: float
    hr_avg_session: Optional[float] = None


@strawberry.type
@dataclasses.dataclass
class SyncHealthTotalsResult:
    accepted: bool
    duplicate: bool
    reset: bool
    idempotency_key_used: Optional[str]
    idempotency_conflict: bool
    delta: Optional[HealthTotalsDelta]


# ----------------- AI Meal Photo Stub (Fase 0) -----------------


@strawberry.enum
class MealPhotoAnalysisStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@strawberry.type
@dataclasses.dataclass
class MealPhotoItemPrediction:
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


@strawberry.type
@dataclasses.dataclass
class MealPhotoAnalysis:
    id: str
    user_id: str
    status: MealPhotoAnalysisStatus
    created_at: str
    source: str  # 'STUB' per fase 0
    items: List[MealPhotoItemPrediction]
    raw_json: Optional[str] = None
    idempotency_key_used: Optional[str] = None


@strawberry.type
@dataclasses.dataclass
class ConfirmMealPhotoResult:
    analysis_id: str
    created_meals: List[MealEntry]


@strawberry.input
class AnalyzeMealPhotoInput:
    photo_id: Optional[str] = None
    photo_url: Optional[str] = None
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@strawberry.input
class ConfirmMealPhotoInput:
    analysis_id: str
    accepted_indexes: List[int]
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None


def _map_analysis(rec) -> MealPhotoAnalysis:  # type: ignore[no-untyped-def]
    return MealPhotoAnalysis(
        id=rec.id,
        user_id=rec.user_id,
        status=MealPhotoAnalysisStatus(rec.status),
        created_at=rec.created_at,
        source="STUB",
        items=[
            MealPhotoItemPrediction(
                label=i.label,
                confidence=i.confidence,
                quantity_g=i.quantity_g,
                calories=i.calories,
                protein=i.protein,
                carbs=i.carbs,
                fat=i.fat,
                fiber=i.fiber,
                sugar=i.sugar,
                sodium=i.sodium,
            )
            for i in rec.items
        ],
        raw_json=rec.raw_json,
        idempotency_key_used=rec.idempotency_key_used,
    )


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
    source: ActivitySource = ActivitySource.MANUAL


@strawberry.input
class LogMealInput:
    name: str
    quantity_g: float
    timestamp: Optional[str] = None
    barcode: Optional[str] = None
    idempotency_key: Optional[str] = None
    user_id: Optional[str] = None  # NEW (default handled in mutation)


@strawberry.input
class UpdateMealInput:
    id: str
    name: Optional[str] = None
    quantity_g: Optional[float] = None
    timestamp: Optional[str] = None
    barcode: Optional[str] = None
    user_id: Optional[str] = None


DEFAULT_USER_ID = "default"


def _enrich_from_product(prod: Product, quantity_g: float) -> Dict[str, Optional[float]]:
    factor = quantity_g / 100.0 if quantity_g else 1.0
    enriched: Dict[str, Optional[float]] = {}
    for field in NUTRIENT_FIELDS:
        value = getattr(prod, field)
        if value is not None:
            if field == "calories":
                enriched[field] = int(round(value * factor))
            else:
                enriched[field] = round(value * factor, 2)
        else:
            enriched[field] = None
    return enriched


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
        prod = _map_product(cast("_ProductLike", dto))
        cache.set(key, prod, PRODUCT_CACHE_TTL_S)
        return prod

    @strawberry.field(description="Lista pasti più recenti (desc)")  # type: ignore[misc]
    def meal_entries(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        limit: int = 20,
        after: Optional[str] = None,
        before: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[MealEntry]:
        if limit <= 0:
            limit = 20
        if limit > 200:
            limit = 200
        uid = user_id or DEFAULT_USER_ID
        records = meal_repo.list(uid, limit, after, before)
        return [MealEntry(**dataclasses.asdict(r)) for r in records]

    @strawberry.field(description="Riepilogo nutrienti per giorno (UTC)")  # type: ignore[misc]
    def daily_summary(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        date: str,
        user_id: Optional[str] = None,
    ) -> DailySummary:
        """Aggrega nutrienti dei pasti il cui timestamp inizia con 'date'.

        'date' formato YYYY-MM-DD. Validazione minima per ora.
        """
        uid = user_id or DEFAULT_USER_ID
        all_meals = meal_repo.list_all(uid)
        day_meals = [m for m in all_meals if m.timestamp.startswith(date)]

        def _acc(field: str) -> float:
            total = 0.0
            for m in day_meals:
                val = getattr(m, field)
                if val is not None:
                    total += float(val)
            return total

        calories_total = int(_acc("calories")) if day_meals else 0

        def _opt(field: str) -> Optional[float]:
            if not day_meals:
                return 0.0
            val = _acc(field)
            return round(val, 2)

        # Nuova fonte totals: health_totals_repo (snapshot delta aggregation)
        steps_tot, cal_out_tot = health_totals_repo.daily_totals(user_id=uid, date=date)
        # Per diagnosi manteniamo events_count dalle minute events
        act_stats = activity_repo.get_daily_stats(uid, date + "T00:00:00Z")
        events_count = act_stats.get("events_count", 0)
        calories_deficit = int(round(cal_out_tot - calories_total))
        if cal_out_tot > 0:
            pct = (calories_total / cal_out_tot) * 100
            # Clamp per evitare valori esplosivi (retry / dati anomali)
            if pct < 0:
                pct = 0
            if pct > 999:
                pct = 999
            calories_replenished_percent = int(round(pct))
        else:
            calories_replenished_percent = 0
        return DailySummary(
            date=date,
            user_id=uid,
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
@dataclasses.dataclass
class CacheStats:
    keys: int
    hits: int
    misses: int


@strawberry.type
class Mutation:
    @strawberry.mutation(  # type: ignore[misc]
        description=("Log di un pasto con arricchimento nutrienti se barcode noto")
    )
    async def log_meal(
        self, info: Info[Any, Any], input: LogMealInput
    ) -> MealEntry:  # noqa: ARG002
        if input.quantity_g <= 0:
            raise GraphQLError("INVALID_QUANTITY: quantity_g deve essere > 0")
        ts = input.timestamp or datetime.datetime.utcnow().isoformat() + "Z"
        user_id = input.user_id or DEFAULT_USER_ID
        # Idempotency key non deve dipendere da timestamp server; se timestamp
        # non è fornito dall'utente non lo includiamo nella chiave.
        # se utente non specifica timestamp non includerlo nella chiave
        base_ts_for_key = input.timestamp or ""
        idempotency_key = input.idempotency_key or (
            f"{input.name.lower()}|{round(input.quantity_g, 3)}|"
            f"{base_ts_for_key}|{input.barcode or ''}|{user_id}"
        )
        existing = meal_repo.find_by_idempotency(user_id, idempotency_key)
        if existing:
            return MealEntry(**dataclasses.asdict(existing))

        nutrients: Dict[str, Optional[float]] = {k: None for k in NUTRIENT_FIELDS}

        prod: Optional[Product] = None
        if input.barcode:
            key = f"product:{input.barcode}"
            prod_cached = cache.get(key)
            if prod_cached:
                prod = prod_cached
            else:
                try:
                    dto = await adapter.fetch_product(input.barcode)
                    prod = _map_product(cast("_ProductLike", dto))
                    cache.set(key, prod, PRODUCT_CACHE_TTL_S)
                except adapter.ProductNotFound:
                    prod = None
                except adapter.OpenFoodFactsError:
                    prod = None
        if prod:
            nutrients = _enrich_from_product(prod, input.quantity_g)

        meal = MealRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=input.name,
            quantity_g=input.quantity_g,
            timestamp=ts,
            barcode=input.barcode,
            idempotency_key=idempotency_key,
            nutrient_snapshot_json=(
                __import__("json").dumps(
                    {k: nutrients[k] for k in NUTRIENT_FIELDS},
                    sort_keys=True,
                )
                if prod
                else None
            ),
            calories=(
                nutrients["calories"]
                if nutrients["calories"] is None
                else int(nutrients["calories"])
            ),
            protein=nutrients["protein"],
            carbs=nutrients["carbs"],
            fat=nutrients["fat"],
            fiber=nutrients["fiber"],
            sugar=nutrients["sugar"],
            sodium=nutrients["sodium"],
        )
        meal_repo.add(meal)
        return MealEntry(**dataclasses.asdict(meal))

    @strawberry.mutation(description="Aggiorna un pasto esistente")  # type: ignore[misc]
    async def update_meal(
        self, info: Info[Any, Any], input: UpdateMealInput
    ) -> MealEntry:  # noqa: ARG002
        rec = meal_repo.get(input.id)
        if not rec:
            raise GraphQLError("NOT_FOUND: meal id inesistente")
        # user isolation (se specificato user_id deve combaciare)
        if input.user_id and input.user_id != rec.user_id:
            raise GraphQLError("FORBIDDEN: user mismatch")
        # Decide se serve ricalcolo nutrienti (se barcode o quantity cambiano)
        new_barcode = input.barcode if input.barcode is not None else rec.barcode
        new_quantity = input.quantity_g if input.quantity_g is not None else rec.quantity_g
        nutrients: Dict[str, Optional[float]] = {k: getattr(rec, k) for k in NUTRIENT_FIELDS}
        prod: Optional[Product] = None
        recalc = False
        if new_barcode != rec.barcode or (
            input.quantity_g is not None and input.quantity_g != rec.quantity_g
        ):
            recalc = True
        if recalc and new_barcode:
            key = f"product:{new_barcode}"
            cached = cache.get(key)
            if cached:
                prod = cast(Product, cached)
            else:
                try:
                    dto = await adapter.fetch_product(new_barcode)
                    prod = _map_product(cast("_ProductLike", dto))
                    cache.set(key, prod, PRODUCT_CACHE_TTL_S)
                except adapter.ProductNotFound:
                    prod = None
                except adapter.OpenFoodFactsError:
                    prod = None
            if prod:
                nutrients = _enrich_from_product(prod, new_quantity)
        # Costruisci campi aggiornati
        update_fields: Dict[str, Any] = {}
        if input.name is not None:
            update_fields["name"] = input.name
        if input.quantity_g is not None:
            update_fields["quantity_g"] = input.quantity_g
        if input.timestamp is not None:
            update_fields["timestamp"] = input.timestamp
        if input.barcode is not None:
            update_fields["barcode"] = input.barcode
        # nutrienti / snapshot se ricalcolati
        if recalc and prod:
            update_fields.update(
                {
                    "calories": (
                        nutrients["calories"]
                        if nutrients["calories"] is None
                        else int(nutrients["calories"])
                    ),
                    "protein": nutrients["protein"],
                    "carbs": nutrients["carbs"],
                    "fat": nutrients["fat"],
                    "fiber": nutrients["fiber"],
                    "sugar": nutrients["sugar"],
                    "sodium": nutrients["sodium"],
                    "nutrient_snapshot_json": __import__("json").dumps(
                        {k: nutrients[k] for k in NUTRIENT_FIELDS},
                        sort_keys=True,
                    ),
                }
            )
        updated = meal_repo.update(input.id, **update_fields)
        assert updated is not None  # per mypy
        return MealEntry(**dataclasses.asdict(updated))

    @strawberry.mutation(description="Cancella un pasto")  # type: ignore[misc]
    def delete_meal(self, info: Info[Any, Any], id: str) -> bool:  # noqa: ARG002
        ok = meal_repo.delete(id)
        return ok

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
            repo_source = _RepoActivitySource[ev.source.name]
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
                    accepted=result_dict["accepted"],
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

    # --- AI Photo Stub Mutations ---
    @strawberry.mutation(  # type: ignore[misc]
        description="Analizza una foto (stub deterministico)"
    )
    def analyze_meal_photo(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        input: AnalyzeMealPhotoInput,
    ) -> MealPhotoAnalysis:
        uid = input.user_id or DEFAULT_USER_ID
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        rec = meal_photo_repo.create_or_get(
            user_id=uid,
            photo_id=input.photo_id,
            photo_url=input.photo_url,
            idempotency_key=input.idempotency_key,
            now_iso=now_iso,
        )
        return _map_analysis(rec)

    @strawberry.mutation(  # type: ignore[misc]
        description="Conferma items analisi foto e crea MealEntry"
    )
    def confirm_meal_photo(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        input: ConfirmMealPhotoInput,
    ) -> ConfirmMealPhotoResult:
        uid = input.user_id or DEFAULT_USER_ID
        analysis = meal_photo_repo.get(uid, input.analysis_id)
        if not analysis:
            raise GraphQLError("NOT_FOUND: analysis")
        # Validazione indici
        max_index = len(analysis.items) - 1
        created: List[MealEntry] = []
        for idx in input.accepted_indexes:
            if idx < 0 or idx > max_index:
                raise GraphQLError("INVALID_INDEX: out of range")
        # Creazione MealEntries
        for idx in input.accepted_indexes:
            pred = analysis.items[idx]
            meal = MealRecord(
                id=str(uuid.uuid4()),
                user_id=uid,
                name=pred.label,
                quantity_g=pred.quantity_g or 0.0,
                timestamp=datetime.datetime.utcnow().isoformat() + "Z",
                barcode=None,
                idempotency_key=f"ai:{analysis.id}:{idx}",
                nutrient_snapshot_json=None,
                calories=pred.calories,
                protein=pred.protein,
                carbs=pred.carbs,
                fat=pred.fat,
                fiber=pred.fiber,
                sugar=pred.sugar,
                sodium=pred.sodium,
            )
            # Idempotenza meal: se già creato restituiamo esistente
            existing = meal_repo.find_by_idempotency(uid, meal.idempotency_key or "")
            if existing:
                created.append(MealEntry(**dataclasses.asdict(existing)))
            else:
                meal_repo.add(meal)
                created.append(MealEntry(**dataclasses.asdict(meal)))
        return ConfirmMealPhotoResult(
            analysis_id=analysis.id,
            created_meals=created,
        )


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)

app = FastAPI(title="Nutrifit Backend Subgraph", version=APP_VERSION)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
async def version() -> dict[str, str]:
    return {"version": APP_VERSION}


graphql_app: Final[GraphQLRouter[Any, Any]] = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
