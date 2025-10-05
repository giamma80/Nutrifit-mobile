"""Nutrient Enrichment Service."""

from dataclasses import dataclass
from typing import Optional, List, Dict
from functools import lru_cache
import asyncio
import time

from ai_models.meal_photo_prompt import ParsedItem


@dataclass(slots=True)
class EnrichmentResult:
    """Risultato arricchimento singolo item."""

    success: bool
    source: str
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None


# Cache per valori nutrienti per evitare ricerche ripetute
@lru_cache(maxsize=128)
def get_nutrient_values(food_label: str) -> Optional[Dict[str, float]]:
    """Ottiene valori nutrienti per un alimento da cache LRU."""
    heuristic_nutrients = {
        "pollo": {"protein": 25.0, "carbs": 0.0, "fat": 4.0, "fiber": 0.0},
        "riso": {"protein": 3.0, "carbs": 78.0, "fat": 0.5, "fiber": 1.0},
        "verdure": {"protein": 2.0, "carbs": 6.0, "fat": 0.3, "fiber": 3.0},
    }
    return heuristic_nutrients.get(food_label.lower())


HEURISTIC_NUTRIENTS = {
    "pollo": {"protein": 25.0, "carbs": 0.0, "fat": 4.0, "fiber": 0.0},
    "riso": {"protein": 3.0, "carbs": 78.0, "fat": 0.5, "fiber": 1.0},
    "verdure": {"protein": 2.0, "carbs": 6.0, "fat": 0.3, "fiber": 3.0},
}


class NutrientEnrichmentService:
    """Servizio arricchimento nutrizionale."""

    def __init__(self) -> None:
        self.stats_enriched = 0
        self.stats_hit_heuristic = 0
        self.stats_hit_default = 0

    async def enrich_parsed_items(
        self, items: List[ParsedItem], timeout: float = 5.0
    ) -> List[EnrichmentResult]:
        """
        Arricchisce lista ParsedItem con timeout e batch processing.

        Args:
            items: Lista di ParsedItem da arricchire
            timeout: Timeout in secondi per l'operazione

        Returns:
            Lista di EnrichmentResult
        """
        start_time = time.time()

        try:
            # Batch processing per performance con multipli items
            batch_size = min(50, len(items))  # Limite batch size
            results = []

            for i in range(0, len(items), batch_size):
                # Check timeout
                if time.time() - start_time > timeout:
                    # Incomplete batch con timeout
                    remaining_items = items[i:]
                    for item in remaining_items:
                        results.append(self._create_default_result(item))
                    break

                batch = items[i : i + batch_size]
                batch_results = await self._process_batch(batch)
                results.extend(batch_results)

                # Yield control per operazioni async
                if len(results) % 10 == 0:
                    await asyncio.sleep(0)  # Yield to event loop

            return results

        except Exception:
            # Fallback su timeout o errore
            return [self._create_default_result(item) for item in items]

    async def _process_batch(self, batch: List[ParsedItem]) -> List[EnrichmentResult]:
        """Processa un batch di items."""
        results = []
        for item in batch:
            # Usa cache LRU per lookup nutrienti
            nutrients = get_nutrient_values(item.label)

            if nutrients:
                factor = item.quantity_g / 100.0
                result = EnrichmentResult(
                    success=True,
                    source="heuristic",
                    protein=nutrients["protein"] * factor,
                    carbs=nutrients["carbs"] * factor,
                    fat=nutrients["fat"] * factor,
                    fiber=nutrients["fiber"] * factor,
                )
                self.stats_hit_heuristic += 1
            else:
                result = self._create_default_result(item)
                self.stats_hit_default += 1

            results.append(result)
            self.stats_enriched += 1

        return results

    def _create_default_result(self, item: ParsedItem) -> EnrichmentResult:
        """Crea risultato con valori di default."""
        factor = item.quantity_g / 100.0
        return EnrichmentResult(
            success=True,
            source="default",
            protein=2.0 * factor,
            carbs=10.0 * factor,
            fat=1.0 * factor,
            fiber=1.0 * factor,
        )

    def get_stats(self) -> Dict[str, int]:
        """Return current enrichment statistics."""
        return {
            "enriched": self.stats_enriched,
            "hit_heuristic": self.stats_hit_heuristic,
            "hit_default": self.stats_hit_default,
        }
