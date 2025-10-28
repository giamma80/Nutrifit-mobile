from __future__ import annotations

from typing import Optional, Mapping, Any, Protocol
import strawberry


@strawberry.type
class Product:
    barcode: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    calories: Optional[int] = None  # kcal
    protein: Optional[float] = None  # grams
    carbs: Optional[float] = None  # grams
    fat: Optional[float] = None  # grams
    fiber: Optional[float] = None  # grams
    sugar: Optional[float] = None  # grams
    sodium: Optional[float] = None  # milligrams (mg)
    image_url: Optional[str] = None


class _ProductLike(Protocol):  # pragma: no cover - protocol ausiliario
    barcode: str
    name: str
    brand: Optional[str]
    category: Optional[str]
    nutrients: Mapping[str, Any]
    image_url: Optional[str]


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
        image_url=getattr(dto, "image_url", None),
    )


__all__ = ["Product", "map_product"]
