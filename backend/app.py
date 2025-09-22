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
from strawberry.types import Info
from graphql import GraphQLError

from cache import cache
from openfoodfacts import adapter

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


# ----------------- Meal Logging (B2) -----------------
@strawberry.type
@dataclasses.dataclass
class MealEntry:
    id: str
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


@strawberry.input
class LogMealInput:
    name: str
    quantity_g: float
    timestamp: Optional[str] = None
    barcode: Optional[str] = None
    idempotency_key: Optional[str] = None


_MEALS: List[MealEntry] = []  # in-memory store semplice
_MEAL_IDEMPOTENCY: Dict[str, str] = {}  # key hash -> meal.id


def _enrich_from_product(prod: Product, quantity_g: float) -> Dict[str, Optional[float]]:
    factor = quantity_g / 100.0 if quantity_g else 1.0
    enriched: Dict[str, Optional[float]] = {}
    fields = [
        "calories",
        "protein",
        "carbs",
        "fat",
        "fiber",
        "sugar",
        "sodium",
    ]
    for field in fields:
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
        idempotency_key = input.idempotency_key or (
            f"{input.name.lower()}|{round(input.quantity_g, 3)}|" f"{ts}|{input.barcode or ''}"
        )
        if idempotency_key in _MEAL_IDEMPOTENCY:
            existing_id = _MEAL_IDEMPOTENCY[idempotency_key]
            for m in _MEALS:
                if m.id == existing_id:
                    return m

        nutrient_keys = [
            "calories",
            "protein",
            "carbs",
            "fat",
            "fiber",
            "sugar",
            "sodium",
        ]
        nutrients: Dict[str, Optional[float]] = {k: None for k in nutrient_keys}

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

        meal = MealEntry(
            id=str(uuid.uuid4()),
            name=input.name,
            quantity_g=input.quantity_g,
            timestamp=ts,
            barcode=input.barcode,
            idempotency_key=idempotency_key,
            nutrient_snapshot_json=None,
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
        _MEALS.append(meal)
        _MEAL_IDEMPOTENCY[idempotency_key] = meal.id
        return meal


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
