"""USDA FoodData Central API client - Implements INutritionProvider port.

Adapted from: ai_models/usda_client.py
Preserves all existing logic (matching, fallback, caching) while implementing
the INutritionProvider port for dependency inversion.

Key Features:
- USDA API search and nutrient lookup
- Circuit breaker (5 failures → 60s timeout)
- Retry logic (exponential backoff)
- Nutrient extraction and mapping
- Label normalization
"""

# mypy: warn-unused-ignores=False

import asyncio
import logging
import os
from typing import Optional, Dict, List, Any
from functools import lru_cache

import aiohttp
from circuitbreaker import circuit
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile

logger = logging.getLogger(__name__)


class USDAClient:
    """
    USDA FoodData Central API client implementing INutritionProvider port.

    This adapter uses USDA API to implement the nutrition provider port
    defined by the domain layer.

    Follows Dependency Inversion Principle:
    - Domain defines INutritionProvider interface (port)
    - Infrastructure provides USDAClient implementation (adapter)

    Example:
        >>> async with USDAClient() as client:
        ...     profile = await client.get_nutrients("chicken breast", 100.0)
        ...     if profile:
        ...         print(f"Calories: {profile.calories}")
    """

    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize USDA client.

        API documentation: https://fdc.nal.usda.gov/api-guide

        Args:
            api_key: USDA FoodData Central API key (optional)
                    Falls back to AI_USDA_API_KEY env var or default key
        """
        # Set API key from parameter or environment with fallback
        env_key = os.getenv("AI_USDA_API_KEY")
        default_key = "zqOnb4hdPJlvU1f9WBmMS8wRgphfPng9ja02KIpy"
        self.api_key = api_key or env_key or default_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "USDAClient":
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5.0))
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    @circuit(failure_threshold=5, recovery_timeout=60, name="usda_search")  # type: ignore[misc]
    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
    )
    async def search_food(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for foods in USDA database.

        Args:
            query: Search term
            limit: Maximum number of results

        Returns:
            List of found foods

        Example:
            >>> foods = await client.search_food("chicken breast")
            >>> if foods:
            ...     fdc_id = foods[0]["fdcId"]
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        params: Dict[str, str] = {
            "query": query,
            "dataType": "Foundation,SR Legacy",  # Focus on base data
            "pageSize": str(limit),
        }

        if self.api_key:
            params["api_key"] = self.api_key

        logger.debug(
            "Searching USDA",
            extra={"query": query, "limit": limit},
        )

        try:
            async with self._session.get(
                f"{self.BASE_URL}/foods/search", params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    foods = data.get("foods", [])
                    result = foods if isinstance(foods, list) else []

                    logger.info(
                        "USDA search complete",
                        extra={
                            "query": query,
                            "results_count": len(result),
                        },
                    )

                    return result
                else:
                    logger.warning(
                        "USDA API warning",
                        extra={"status": response.status, "query": query},
                    )
                    return []

        except asyncio.TimeoutError:
            logger.error("USDA API timeout", extra={"query": query})
            return []
        except Exception as e:
            logger.error(
                "USDA API error",
                extra={"query": query, "error": str(e)},
            )
            return []

    @circuit(failure_threshold=5, recovery_timeout=60, name="usda_nutrients")  # type: ignore[misc]
    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError)),
    )
    async def get_nutrients_by_id(self, fdc_id: int) -> Optional[Dict[str, float]]:
        """
        Get nutrients for a specific food by FDC ID.

        Args:
            fdc_id: FoodData Central ID

        Returns:
            Dictionary with nutrient values or None if error
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        params: Dict[str, str] = {}
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            async with self._session.get(
                f"{self.BASE_URL}/food/{fdc_id}", params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._extract_nutrients(data)
                else:
                    logger.warning(
                        "USDA food detail failed",
                        extra={"fdc_id": fdc_id, "status": response.status},
                    )
                    return None

        except Exception as e:
            logger.error(
                "USDA food detail error",
                extra={"fdc_id": fdc_id, "error": str(e)},
            )
            return None

    async def get_nutrients(self, identifier: str, quantity_g: float) -> Optional[NutrientProfile]:
        """
        Get nutrient profile for a food identifier.

        Implements INutritionProvider.get_nutrients() port.

        Args:
            identifier: Food label/name (e.g., "chicken breast", "banana")
            quantity_g: Reference quantity in grams (typically 100.0)

        Returns:
            NutrientProfile if found, None if not available

        Example:
            >>> profile = await client.get_nutrients("chicken breast", 100.0)
            >>> if profile:
            ...     print(f"Protein: {profile.protein}g per 100g")
        """
        logger.info(
            "Getting nutrients from USDA",
            extra={"identifier": identifier, "quantity_g": quantity_g},
        )

        # Normalize label for search
        normalized_label = normalize_food_label(identifier)

        # For generic simple foods, prefer raw/fresh versions
        # Only add "raw" if not already specified (fried, boiled, etc.)
        simple_foods_prefer_raw = [
            "potato",
            "potatoes",
            "tomato",
            "tomatoes",
            "onion",
            "onions",
            "carrot",
            "carrots",
            "spinach",
            "broccoli",
            "zucchini",
            "eggplant",
            "bell pepper",
            "cucumber",
        ]

        # Eggs need special handling: "whole raw" to avoid egg whites
        eggs_variants = ["eggs", "egg"]

        # Check if label is generic (no preparation method specified)
        has_preparation = any(
            prep in normalized_label.lower()
            for prep in [
                "raw",
                "fried",
                "boiled",
                "baked",
                "grilled",
                "roasted",
                "steamed",
                "cooked",
                "dried",
                "canned",
                "whole",
                "white",
                "yolk",
            ]
        )

        # Add "raw" or "whole raw" for simple foods without preparation
        search_label = normalized_label
        if not has_preparation:
            if normalized_label.lower() in eggs_variants:
                # Eggs: add "whole raw" to get whole eggs not whites
                search_label = f"{normalized_label} whole raw"
                logger.debug(
                    "Adding 'whole raw' to eggs query",
                    extra={"original": normalized_label, "modified": search_label},
                )
            elif normalized_label.lower() in simple_foods_prefer_raw:
                # Other simple foods: just add "raw"
                search_label = f"{normalized_label} raw"
                logger.debug(
                    "Adding 'raw' to generic food query",
                    extra={"original": normalized_label, "modified": search_label},
                )

        # Search for food in USDA with higher limit for better selection
        foods = await self.search_food(search_label, limit=8)

        if not foods:
            logger.info(
                "No USDA results",
                extra={"identifier": identifier},
            )
            return None

        # Filter and rank results to prefer natural/raw foods over processed
        def score_food_naturalness(description: str) -> int:
            """Score food by naturalness (higher = more natural/raw)."""
            desc_lower = description.lower()

            # Heavily penalize processed/dried/powdered foods
            processed_keywords = [
                "dehydrated",
                "powder",
                "dried",
                "canned",
                "crackers",
                "cakes",
                "juice",
                "croissant",
                "strudel",
                "snacks",
                "bars",
                "cereal",
            ]
            if any(kw in desc_lower for kw in processed_keywords):
                return -100

            # Favor fresh/raw forms
            if any(kw in desc_lower for kw in ["raw", "fresh"]):
                return 50

            # Neutral for normal preparations (fried, boiled, etc.)
            return 0

        # Sort by naturalness score (highest first)
        foods_with_scores = [
            (food, score_food_naturalness(food.get("description", ""))) for food in foods
        ]
        foods_sorted = sorted(foods_with_scores, key=lambda x: x[1], reverse=True)

        logger.debug(
            "USDA food selection",
            extra={
                "identifier": identifier,
                "top_result": foods_sorted[0][0].get("description"),
                "score": foods_sorted[0][1],
            },
        )

        # Try results in order of preference (best score first)
        for food, score in foods_sorted:
            fdc_id = food.get("fdcId")
            if not fdc_id:
                continue

            # Get detailed nutrients
            nutrients_dict = await self.get_nutrients_by_id(fdc_id)

            if nutrients_dict and nutrients_dict.get("calories", 0) > 0:
                # Found valid result with calories > 0
                logger.info(
                    "USDA food selected",
                    extra={
                        "identifier": identifier,
                        "fdc_id": fdc_id,
                        "description": food.get("description"),
                        "score": score,
                    },
                )
                break
        else:
            # No valid results found
            logger.warning(
                "No valid USDA nutrients found",
                extra={"identifier": identifier},
            )
            return None

        # nutrients_dict is now set from the loop above
        # Convert to NutrientProfile domain entity
        # USDA nutrients are ALWAYS per 100g - NO SCALING here
        # The service layer (enrichment_service.py) calls with quantity_g=100.0
        # and then uses profile.scale_to_quantity(actual_quantity) to scale

        profile = NutrientProfile(
            calories=int(nutrients_dict.get("calories", 0.0)),
            protein=nutrients_dict.get("protein", 0.0),
            carbs=nutrients_dict.get("carbs", 0.0),
            fat=nutrients_dict.get("fat", 0.0),
            fiber=nutrients_dict.get("fiber", 0.0),
            sugar=nutrients_dict.get("sugar", 0.0),
            sodium=nutrients_dict.get("sodium", 0.0),
            quantity_g=100.0,  # Always 100g base from USDA
            source="USDA",
            confidence=0.95,  # USDA is high confidence source
        )

        logger.info(
            "USDA nutrients retrieved",
            extra={
                "identifier": identifier,
                "fdc_id": fdc_id,
                "calories": profile.calories,
            },
        )

        return profile

    def _extract_nutrients(self, food_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract base nutrients from USDA data.

        CRITICAL: USDA nutrients are ALWAYS per 100g for FoodData Central.
        The API documentation states all nutrient values are normalized to 100g.

        Args:
            food_data: Complete USDA food data

        Returns:
            Dictionary with nutrient values (per 100g base)
        """
        nutrients: Dict[str, float] = {
            "calories": 0.0,
            "protein": 0.0,
            "carbs": 0.0,
            "fat": 0.0,
            "fiber": 0.0,
            "sugar": 0.0,
            "sodium": 0.0,
            "calcium": 0.0,
        }

        # Mapping USDA nutrient IDs → our values
        nutrient_mapping = {
            1003: "protein",  # Protein
            1005: "carbs",  # Carbohydrate, by difference
            1004: "fat",  # Total lipid (fat)
            1079: "fiber",  # Fiber, total dietary
            1063: "sugar",  # Sugars, total including NLEA
            1093: "sodium",  # Sodium, Na (mg)
            1087: "calcium",  # Calcium, Ca (mg)
            1008: "calories",  # Energy (kcal)
        }

        food_nutrients = food_data.get("foodNutrients", [])

        # Debug logging
        food_desc = food_data.get("description", "unknown")
        serving_size = food_data.get("servingSize")
        serving_unit = food_data.get("servingSizeUnit")

        logger.debug(
            "Extracting USDA nutrients",
            extra={
                "description": food_desc,
                "servingSize": serving_size,
                "servingSizeUnit": serving_unit,
                "nutrient_count": len(food_nutrients),
            },
        )

        for nutrient in food_nutrients:
            # USDA API can return two different structures:
            # 1. Search API: nutrientId + value (direct)
            # 2. Detail API: nutrient.id + amount (nested)
            # We support both

            # Method 1: Search API (new)
            nutrient_id = nutrient.get("nutrientId")
            amount = nutrient.get("value")

            # Method 2: Detail API (original) - fallback if method 1 fails
            if nutrient_id is None or amount is None:
                nutrient_info = nutrient.get("nutrient", {})
                nutrient_id = nutrient_info.get("id")
                amount = nutrient.get("amount")

            if nutrient_id in nutrient_mapping and amount is not None:
                field_name = nutrient_mapping[nutrient_id]
                nutrients[field_name] = float(amount)

                # Debug: log first few nutrients to verify data
                if field_name in ["calories", "protein", "carbs"]:
                    logger.debug(
                        f"USDA nutrient {field_name}",
                        extra={"nutrient_id": nutrient_id, "value": float(amount)},
                    )

        logger.debug(
            "USDA nutrients extracted (per 100g base)",
            extra={
                "calories": nutrients["calories"],
                "protein": nutrients["protein"],
                "carbs": nutrients["carbs"],
                "fat": nutrients["fat"],
            },
        )

        return nutrients


@lru_cache(maxsize=64)
def normalize_food_label(label: str) -> str:
    """
    Normalize food label for USDA search.

    With prompt v3, labels already come in English from LLM,
    so this function only does basic cleanup.

    Args:
        label: Label in English from AI prompt

    Returns:
        Cleaned label for USDA lookup

    Example:
        >>> normalize_food_label("Chicken Breast, Roasted")
        'chicken breast roasted'
    """
    # Basic normalization - remove extra spaces and lowercase
    normalized = label.lower().strip()

    # Remove special characters but keep spaces for compound terms
    import re

    normalized = re.sub(r"[^\w\s-]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # For compound terms like "ground beef" → "ground beef" (keep)
    # For single words like "chicken" → "chicken" (keep)

    return normalized
