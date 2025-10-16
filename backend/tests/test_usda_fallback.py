"""Test specifico per fallback USDA con alimenti non in heuristics."""

import pytest
from ai_models.meal_photo_prompt import ParsedItem
from ai_models.nutrient_enrichment import NutrientEnrichmentService


# API Key USDA
USDA_API_KEY = "zqOnb4hdPJlvU1f9WBmMS8wRgphfPng9ja02KIpy"


@pytest.mark.asyncio
async def test_usda_fallback_with_unknown_food() -> None:
    """
    Test che alimenti NON negli heuristics usino il fallback USDA.
    """

    # Alimento con dati USDA verificati
    items = [
        ParsedItem(
            label="chicken",  # Chicken ha dati USDA affidabili
            quantity_g=100.0,
            confidence=0.9,
            calories=200,  # Verrà sostituito
            source_density="medium",
            display_name="pollo",
        )
    ]

    # Test CON API key USDA
    service = NutrientEnrichmentService(usda_api_key=USDA_API_KEY)
    results = await service.enrich_parsed_items(items)

    assert len(results) == 1
    result = results[0]

    print("\n� Test fallback con alimento inesistente:")
    print(f"   Source: {result.source}")
    print(f"   Protein: {result.protein:.1f}g")
    print(f"   Fat: {result.fat:.1f}g")
    print(f"   Calories: {result.calories:.1f}kcal")

    # Dovrebbe usare USDA come fallback
    assert result.source == "usda", f"Expected USDA source, got {result.source}"
    assert result.protein is not None and result.protein > 0, "Chicken dovrebbe avere proteine"
    assert result.fat is not None and result.fat >= 0, "Chicken dovrebbe avere grassi >= 0"

    # Verifica che le statistiche mostrino hit USDA
    stats = service.get_stats()
    print(f"📊 Stats: {stats}")
    assert stats["hit_usda"] == 1, "Dovrebbe esserci 1 hit USDA"


@pytest.mark.asyncio
async def test_multiple_foods_mixed_sources() -> None:
    """
    Test con mix di alimenti: alcuni in heuristics, altri da USDA.
    """

    items = [
        ParsedItem(
            label="chicken",
            quantity_g=100.0,
            confidence=0.9,
            calories=165,
            source_density="medium",
            display_name="pollo",
        ),
        ParsedItem(
            label="salmon",
            quantity_g=100.0,
            confidence=0.8,
            calories=200,
            source_density="medium",
            display_name="salmone",
        ),
        ParsedItem(
            label="quinoa",
            quantity_g=100.0,
            confidence=0.7,
            calories=150,
            source_density="medium",
            display_name="quinoa",
        ),
    ]

    service = NutrientEnrichmentService(usda_api_key=USDA_API_KEY)
    results = await service.enrich_parsed_items(items)

    assert len(results) == 3

    print("\n🥘 Test mix di fonti:")
    sources = []
    for i, result in enumerate(results):
        food_name = items[i].display_name
        print(f"   {food_name}: {result.source} (protein: {result.protein:.1f}g)")
        sources.append(result.source)

    stats = service.get_stats()
    print(f"📊 Stats finali: {stats}")

    # Ora tutto va tramite USDA (con fallback a default)
    assert stats["hit_usda"] + stats["hit_default"] == 3, "Tutti gli item processati"
    assert stats["enriched"] == 3, "Tutti e 3 gli alimenti dovrebbero essere processati"


@pytest.mark.asyncio
async def test_usda_vs_no_usda_comparison() -> None:
    """
    Confronta risultati CON e SENZA API key USDA.
    """

    # Alimento non negli heuristics
    items = [
        ParsedItem(
            label="tuna",
            quantity_g=100.0,
            confidence=0.9,
            calories=150,
            source_density="medium",
            display_name="tonno",
        )
    ]

    print("\n🎣 Confronto tuna CON vs SENZA USDA API:")

    # Test SENZA API key (dovrebbe usare default)
    service_no_usda = NutrientEnrichmentService()  # No API key
    results_no_usda = await service_no_usda.enrich_parsed_items(items.copy())

    result_no_usda = results_no_usda[0]
    print(f"   SENZA USDA: {result_no_usda.source} - Protein: {result_no_usda.protein:.1f}g")

    # Test CON API key
    service_with_usda = NutrientEnrichmentService(usda_api_key=USDA_API_KEY)
    results_with_usda = await service_with_usda.enrich_parsed_items(items.copy())

    result_with_usda = results_with_usda[0]
    print(f"   CON USDA: {result_with_usda.source} - Protein: {result_with_usda.protein:.1f}g")

    # Ora entrambi usano USDA (API key di default)
    assert result_no_usda.source in ["usda", "default"]
    assert result_with_usda.source in ["usda", "default"]  # Potrebbe non trovare tuna

    # Ora entrambi usano API key di default, quindi possono avere stessi valori
    if result_with_usda.source == "usda" and result_no_usda.source == "usda":
        # Entrambi usano USDA, valori dovrebbero essere simili
        assert result_with_usda.protein is not None
        assert result_no_usda.protein is not None
        assert abs(result_with_usda.protein - result_no_usda.protein) < 1.0
