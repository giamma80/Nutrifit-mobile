"""Semplice client USDA FoodData Central API."""

import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import aiohttp
from functools import lru_cache


@dataclass
class USDANutrient:
    """Nutriente USDA completo."""

    # Macronutrienti base
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    fiber: float = 0.0
    sugar: float = 0.0  # g per 100g - zuccheri totali

    # Minerali essenziali
    sodium: float = 0.0  # mg per 100g
    calcium: float = 0.0  # mg per 100g

    # Energia
    calories: float = 0.0  # kcal per 100g


class USDAClient:
    """Client semplice per USDA FoodData Central API."""

    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self, api_key: Optional[str] = None):
        """

        documentazione API : https://fdc.nal.usda.gov/api-guide
        Initialize USDA client.
        API key is optional for basic usage but recommended
        API Key to set : zqOnb4hdPJlvU1f9WBmMS8wRgphfPng9ja02KIpy
        Args:
            api_key: USDA FoodData Central API key (opzionale per basic usage)
        """
        # Imposta API key di default se non fornita
        self.api_key = api_key or "zqOnb4hdPJlvU1f9WBmMS8wRgphfPng9ja02KIpy"
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "USDAClient":
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5.0))
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    async def search_food(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Cerca alimenti nel database USDA.

        Args:
            query: Termine di ricerca
            limit: Numero massimo risultati

        Returns:
            Lista alimenti trovati
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        params = {
            "query": query,
            "dataType": "Foundation,SR Legacy",  # Focus su dati base
            "pageSize": str(limit),
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            async with self._session.get(
                f"{self.BASE_URL}/foods/search", params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    foods = data.get("foods", [])
                    return foods if isinstance(foods, list) else []
                else:
                    # Log warning ma non fallire
                    print(f"USDA API warning: status {response.status}")
                    return []
        except asyncio.TimeoutError:
            print("USDA API timeout")
            return []
        except Exception as e:
            print(f"USDA API error: {e}")
            return []

    async def get_nutrients(self, fdc_id: int) -> Optional[USDANutrient]:
        """
        Ottiene nutrienti per un alimento specifico.

        Args:
            fdc_id: ID FoodData Central

        Returns:
            Nutrienti estratti o None se errore
        """
        if not self._session:
            raise RuntimeError("Client not initialized. Use async context manager.")

        params = {}
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
                    return None
        except Exception:
            return None

    def _extract_nutrients(self, food_data: Dict[str, Any]) -> USDANutrient:
        """
        Estrae nutrienti base da dati USDA.

        Args:
            food_data: Dati completi alimento USDA

        Returns:
            Nutrienti semplificati
        """
        nutrients = USDANutrient()

        # Mapping ID nutrienti USDA → nostri valori
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
            # L'API USDA può restituire due strutture diverse:
            # 1. Search API: nutrientId + value (diretti)
            # 2. Detail API: nutrient.id + amount (nested)
            # Supportiamo entrambe
            
            # Metodo 1: Search API (nuovo)
            nutrient_id = nutrient.get("nutrientId")
            amount = nutrient.get("value")
            
            # Metodo 2: Detail API (originale) - fallback se metodo 1 fallisce
            if nutrient_id is None or amount is None:
                nutrient_info = nutrient.get("nutrient", {})
                nutrient_id = nutrient_info.get("id")
                amount = nutrient.get("amount")

            if nutrient_id in nutrient_mapping and amount is not None:
                field_name = nutrient_mapping[nutrient_id]
                setattr(nutrients, field_name, float(amount))

        return nutrients


@lru_cache(maxsize=64)
def normalize_food_label(label: str) -> str:
    """
    Normalizza etichetta alimento per ricerca USDA.

    Con prompt v3, le etichette arrivano già in inglese dal LLM,
    quindi questa funzione fa solo pulizia base.

    Args:
        label: Etichetta in inglese dal prompt AI

    Returns:
        Etichetta pulita per USDA lookup
    """
    # Normalizzazione base - rimuovi spazi extra e lowercase
    normalized = label.lower().strip()

    # Rimuovi caratteri speciali ma mantieni spazi per termini composti
    import re

    normalized = re.sub(r"[^\w\s-]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Per termini composti come "ground beef" → "ground beef" (mantieni)
    # Per singole parole come "chicken" → "chicken" (mantieni)

    return normalized
