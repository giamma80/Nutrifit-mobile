"""OpenFoodFacts Adapter

Responsabilità:
- Fetch prodotto per barcode
- Normalizzare nutrienti principali (100g) in struttura interna
- Gestire errori (404, timeout, dati incompleti)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import httpx

BASE_URL = "https://world.openfoodfacts.org/api/v2/product"  # v2 simplified
TIMEOUT_S = 8.0


@dataclass
class FoodItemDTO:
    barcode: str
    name: str
    brand: Optional[str]
    category: Optional[str]
    # nutrients keys:
    #  calories(kcal), protein(g), carbs(g), fat(g)
    #  fiber(g?), sugar(g?), sodium(mg?)
    nutrients: Dict[str, float]
    raw: Dict[str, Any]


class OpenFoodFactsError(Exception):
    """Errore generico adapter OFF"""


class ProductNotFound(OpenFoodFactsError):
    """Barcode non trovato"""


async def fetch_product(barcode: str) -> FoodItemDTO:
    url = f"{BASE_URL}/{barcode}.json"
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        resp = await client.get(url)
    if resp.status_code == 404:
        raise ProductNotFound(barcode)
    if resp.status_code >= 500:
        raise OpenFoodFactsError(f"Server error {resp.status_code}")
    data = resp.json()
    status = data.get("status")
    if status != 1:
        raise ProductNotFound(barcode)
    product = data.get("product", {})
    nutr = product.get("nutriments", {})

    def gf(key: str) -> Optional[float]:
        v = nutr.get(key)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    name = (
        product.get("product_name")
        or product.get("generic_name")
        or "Unknown"
    )
    brand = (product.get("brands") or '').split(',')[0].strip() or None
    category = (product.get("categories_tags") or [None])[0]

    # Normalize field names map
    # convert kJ (energy_100g) to kcal if energy-kcal missing
    kcal = gf("energy-kcal_100g") or (
        gf("energy_100g") and gf("energy_100g") / 4.184
    )
    protein = gf("proteins_100g")
    carbs = gf("carbohydrates_100g")
    fat = gf("fat_100g")
    fiber = gf("fiber_100g")
    sugar = gf("sugars_100g")
    # salt(g)*400 ≈ mg sodium
    sodium = gf("sodium_100g") or (
        gf("salt_100g") and gf("salt_100g") * 400
    )

    nutrients: Dict[str, float] = {}
    if kcal is not None:
        nutrients["calories"] = round(kcal)
    if protein is not None:
        nutrients["protein"] = round(protein, 2)
    if carbs is not None:
        nutrients["carbs"] = round(carbs, 2)
    if fat is not None:
        nutrients["fat"] = round(fat, 2)
    if fiber is not None:
        nutrients["fiber"] = round(fiber, 2)
    if sugar is not None:
        nutrients["sugar"] = round(sugar, 2)
    if sodium is not None:
        nutrients["sodium"] = round(sodium, 0)

    return FoodItemDTO(
        barcode=barcode,
        name=name,
        brand=brand,
        category=category,
        nutrients=nutrients,
        raw=product,
    )
