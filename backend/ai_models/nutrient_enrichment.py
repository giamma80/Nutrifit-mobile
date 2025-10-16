"""Nutrient Enrichment Service."""

from dataclasses import dataclass
from typing import Optional, List, Dict
import asyncio
import time

from ai_models.meal_photo_prompt import ParsedItem
from ai_models.usda_client import USDAClient, normalize_food_label, USDANutrient


@dataclass
class EnrichmentResult:
    """Risultato arricchimento singolo item."""

    success: bool
    source: str
    # Macronutrienti
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    # Minerali (mg)
    sodium: Optional[float] = None
    calcium: Optional[float] = None
    # Energia
    calories: Optional[float] = None


# Dizionari hard-coded rimossi - ora deleghiamo tutto al sistema USDA API


class NutrientEnrichmentService:
    """Servizio arricchimento nutrizionale."""

    def __init__(self, usda_api_key: Optional[str] = None) -> None:
        self.stats_enriched = 0
        self.stats_hit_usda = 0
        self.stats_hit_default = 0
        # Usa sempre la API key - quella di default se non fornita
        self.usda_api_key = usda_api_key or "zqOnb4hdPJlvU1f9WBmMS8wRgphfPng9ja02KIpy"

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
        """Processa un batch di items con fallback USDA."""
        results = []

        for item in batch:
            result = await self._enrich_single_item(item)
            results.append(result)
            self.stats_enriched += 1

        return results

    async def _enrich_single_item(self, item: ParsedItem) -> EnrichmentResult:
        """
        Arricchisce singolo item seguendo il flusso semplificato:
        1. Prova USDA lookup direttamente
        2. Valori di default se USDA fallisce
        """
        factor = item.quantity_g / 100.0

        # STEP 1: Prova USDA lookup (sempre, con API key di default)
        usda_nutrients = await self._try_usda_lookup(item.label)
        if usda_nutrients:
            self.stats_hit_usda += 1
            return EnrichmentResult(
                success=True,
                source="usda",
                protein=usda_nutrients.protein * factor,
                carbs=usda_nutrients.carbs * factor,
                fat=usda_nutrients.fat * factor,
                fiber=usda_nutrients.fiber * factor,
                sugar=usda_nutrients.sugar * factor,
                sodium=usda_nutrients.sodium * factor,
                calcium=usda_nutrients.calcium * factor,
                calories=usda_nutrients.calories * factor,
            )

        # STEP 2: Default values se USDA fallisce
        self.stats_hit_default += 1
        return self._create_default_result(item)

    async def _try_usda_lookup(self, label: str) -> Optional[USDANutrient]:
        """
        Prova lookup USDA per etichetta alimento.

        Returns:
            Nutrienti USDA o None se non trovato/errore
        """
        try:
            normalized_label = normalize_food_label(label)

            async with USDAClient(self.usda_api_key) as client:
                # Cerca alimenti
                foods = await client.search_food(normalized_label, limit=3)

                if not foods:
                    return None

                # Prova primo risultato (più rilevante per ranking USDA)
                first_food = foods[0]
                fdc_id = first_food.get("fdcId")

                if fdc_id:
                    nutrients = await client.get_nutrients(fdc_id)
                    if nutrients:
                        return nutrients

        except Exception:
            # Fallimento silenzioso - non bloccare enrichment
            pass

        return None

    def _create_default_result(self, item: ParsedItem) -> EnrichmentResult:
        """Crea risultato con valori di default ragionevoli."""
        factor = item.quantity_g / 100.0

        # Calcolo calorie da macronutrienti (Atwater factors)
        protein_cal = 2.0 * 4  # 4 kcal/g protein
        carbs_cal = 10.0 * 4  # 4 kcal/g carbs
        fat_cal = 1.0 * 9  # 9 kcal/g fat
        total_calories = (protein_cal + carbs_cal + fat_cal) * factor

        return EnrichmentResult(
            success=True,
            source="default",
            protein=2.0 * factor,
            carbs=10.0 * factor,
            fat=1.0 * factor,
            fiber=1.0 * factor,
            sugar=2.0 * factor,  # Stima conservativa zuccheri
            sodium=50.0 * factor,  # mg - valore medio alimenti
            calcium=30.0 * factor,  # mg - valore medio alimenti
            calories=total_calories,
        )

    def get_stats(self) -> Dict[str, int]:
        """Return current enrichment statistics."""
        return {
            "enriched": self.stats_enriched,
            "hit_usda": self.stats_hit_usda,
            "hit_default": self.stats_hit_default,
        }
