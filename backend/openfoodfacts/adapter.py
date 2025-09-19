"""OpenFoodFacts Adapter

Responsabilità:
- Fetch prodotto per barcode
- Normalizzare nutrienti principali (100g) in struttura interna
- Gestire errori (404, timeout, dati incompleti)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, TypedDict
import asyncio
import httpx

BASE_URL = "https://world.openfoodfacts.org/api/v2/product"  # v2 simplified
TIMEOUT_S = 8.0
# Retry configuration (simple exponential backoff)
MAX_RETRIES = 3  # total tentativi inclusa la prima richiesta
INITIAL_BACKOFF_S = 0.2  # base backoff per il primo retry
BACKOFF_FACTOR = 2.0  # moltiplicatore esponenziale
RETRY_STATUS_CODES = {500, 502, 503, 504}


class NutrientsDict(TypedDict, total=False):
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    sugar: float
    sodium: float


@dataclass(slots=True)
class ProductDTO:
    barcode: str
    name: str
    brand: Optional[str]
    category: Optional[str]
    nutrients: NutrientsDict
    raw: Dict[str, Any]


class OpenFoodFactsError(Exception):
    """Errore generico adapter OFF"""


class ProductNotFound(OpenFoodFactsError):
    """Barcode non trovato"""


async def fetch_product(barcode: str) -> ProductDTO:
    url = f"{BASE_URL}/{barcode}.json"
    attempt = 0
    backoff = INITIAL_BACKOFF_S
    while True:
        attempt += 1
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
                resp = await client.get(url)
            if resp.status_code == 404:
                raise ProductNotFound(barcode)
            if resp.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                # server temporaneamente indisponibile, retry
                await asyncio.sleep(backoff)
                backoff *= BACKOFF_FACTOR
                continue
            if resp.status_code in RETRY_STATUS_CODES:
                raise OpenFoodFactsError(f"Server error {resp.status_code}")
            if resp.status_code >= 500:
                # altri 5xx non elencati → errore diretto
                raise OpenFoodFactsError(f"Server error {resp.status_code}")
            break
        except (
            httpx.ReadTimeout,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.HTTPError,
        ) as e:
            if attempt >= MAX_RETRIES:
                raise OpenFoodFactsError(f"Network error after {attempt} attempts: {e}") from e
            await asyncio.sleep(backoff)
            backoff *= BACKOFF_FACTOR

    # fuori dal loop: resp ok
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

    name = product.get("product_name") or product.get("generic_name") or "Unknown"
    brand = (product.get("brands") or "").split(",")[0].strip() or None
    category = (product.get("categories_tags") or [None])[0]

    # Normalize field names map
    # kcal: prefer energy-kcal_100g
    # fallback convert from kJ (energy_100g / 4.184)
    kcal = gf("energy-kcal_100g")
    if kcal is None:
        energy_kj = gf("energy_100g")
        if energy_kj is not None:
            kcal = energy_kj / 4.184

    protein = gf("proteins_100g")
    carbs = gf("carbohydrates_100g")
    fat = gf("fat_100g")
    fiber = gf("fiber_100g")
    sugar = gf("sugars_100g")

    # sodium: prefer sodium_100g
    # fallback salt_100g (g) * 400 => mg sodium approx
    sodium = gf("sodium_100g")
    if sodium is None:
        salt_g = gf("salt_100g")
        if salt_g is not None:
            sodium = salt_g * 400

    nutrients: NutrientsDict = {}
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

    return ProductDTO(
        barcode=barcode,
        name=name,
        brand=brand,
        category=category,
        nutrients=nutrients,
        raw=product,
    )
