from __future__ import annotations

from typing import Optional, Mapping, Any, Protocol
import strawberry


@strawberry.type
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


class _ProductLike(Protocol):  # pragma: no cover - protocol ausiliario
    barcode: str
    name: str
    brand: Optional[str]
    category: Optional[str]
    nutrients: Mapping[str, Any]


def map_product(dto: _ProductLike) -> Product:
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


__all__ = ["Product", "map_product"]
