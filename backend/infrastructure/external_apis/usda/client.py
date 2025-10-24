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

        # Search for food in USDA
        foods = await self.search_food(normalized_label, limit=5)

        if not foods:
            logger.info(
                "No USDA results",
                extra={"identifier": identifier},
            )
            return None

        # Get nutrients from first result
        fdc_id = foods[0].get("fdcId")
        if not fdc_id:
            logger.warning(
                "No FDC ID in result",
                extra={"identifier": identifier},
            )
            return None

        # Get detailed nutrients
        nutrients_dict = await self.get_nutrients_by_id(fdc_id)

        if not nutrients_dict:
            logger.warning(
                "Failed to get nutrients by ID",
                extra={"identifier": identifier, "fdc_id": fdc_id},
            )
            return None

        # Convert to NutrientProfile domain entity
        # Note: NutrientProfile includes calories, protein, carbs, fat, fiber, sugar, sodium
        # Calcium is extracted but not currently used in domain model
        profile = NutrientProfile(
            calories=int(nutrients_dict.get("calories", 0.0)),
            protein=nutrients_dict.get("protein", 0.0),
            carbs=nutrients_dict.get("carbs", 0.0),
            fat=nutrients_dict.get("fat", 0.0),
            fiber=nutrients_dict.get("fiber", 0.0),
            sugar=nutrients_dict.get("sugar", 0.0),
            sodium=nutrients_dict.get("sodium", 0.0),
            quantity_g=quantity_g,
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

        Args:
            food_data: Complete USDA food data

        Returns:
            Dictionary with nutrient values
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
