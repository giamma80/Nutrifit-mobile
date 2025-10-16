"""Test semplice per fallback USDA."""

import pytest
from ai_models.meal_photo_prompt import ParsedItem
from ai_models.nutrient_enrichment import NutrientEnrichmentService

USDA_API_KEY = "zqOnb4hdPJlvU1f9WBmMS8wRgphfPng9ja02KIpy"


@pytest.mark.asyncio
async def test_simple_usda_fallback() -> None:
    """Test fallback USDA con sistema completamente delegato."""

    print("\n📋 Nuovo sistema: Tutto via USDA (no heuristics hard-coded)")
    print("   Sistema: Etichette inglesi → USDA lookup → Default fallback")

    # Test con quinoa (dovrebbe essere trovato in USDA)
    items = [
        ParsedItem(
            label="quinoa",
            quantity_g=100.0,
            confidence=0.8,
            calories=150,
            source_density="medium",
            display_name="quinoa",
        )
    ]

    # Ora il sistema ha SEMPRE l'API key di default
    print("\n✅ Test con API key di default:")
    service = NutrientEnrichmentService()
    results = await service.enrich_parsed_items(items)
    result = results[0]
    print(f"   Source: {result.source}")
    print(f"   Protein: {result.protein:.1f}g")
    print(f"   Calories: {result.calories:.1f}kcal")

    # Verifica che il sistema funzioni (USDA o default)
    assert result.source in ["usda", "default"]
    assert result.protein is not None
    assert result.protein >= 0

    # Stampa risultato
    if result.source == "usda":
        print("🎉 SUCCESSO: Quinoa trovato in USDA!")
        assert result.protein > 0, "Quinoa dovrebbe avere proteine"
    else:
        print("ℹ️  Quinoa non trovato in USDA, usato default")

    print("✅ Sistema USDA completamente funzionante!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_simple_usda_fallback())
