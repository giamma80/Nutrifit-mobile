"""Test integrazione USDA con nutrienti estesi."""

import pytest
from ai_models.nutrient_enrichment import NutrientEnrichmentService
from ai_models.meal_photo_prompt import ParsedItem


@pytest.mark.asyncio
async def test_enrichment_with_extended_nutrients() -> None:
    """Test arricchimento con nutrienti estesi (senza USDA)."""
    service = NutrientEnrichmentService()

    # Test con alimento conosciuto (chicken) - ora usa etichette inglesi
    items = [
        ParsedItem(
            label="chicken",  # Inglese per lookup nutrienti
            quantity_g=150.0,
            confidence=0.9,
            calories=165,  # Questo verrà sovrascritto
            source_density="medium",
            display_name="pollo",  # Italiano per display
        )
    ]

    results = await service.enrich_parsed_items(items)

    assert len(results) == 1
    result = results[0]

    # Verifica tutti i nutrienti estesi con dati USDA reali
    assert result.success is True
    assert result.source in ["usda", "default"]

    # Macronutrienti ragionevoli per pollo (150g)
    assert result.protein is not None and result.protein > 20.0
    assert result.carbs is not None and result.carbs >= 0.0
    assert result.fat is not None and result.fat >= 0.0
    assert result.fiber is not None and result.fiber >= 0.0

    # Micronutrienti
    assert result.sodium is not None and result.sodium >= 0.0
    assert result.calcium is not None and result.calcium >= 0.0

    # Calorie ragionevoli per pollo
    assert result.calories is not None and result.calories > 100.0


@pytest.mark.asyncio
async def test_enrichment_default_with_calculated_calories() -> None:
    """Test valori di default con calcolo calorie da macronutrienti."""
    service = NutrientEnrichmentService()

    # Test con alimento sconosciuto
    items = [
        ParsedItem(
            label="unknown_food",  # Termine inglese sconosciuto
            quantity_g=100.0,
            confidence=0.8,
            calories=200,  # Questo verrà sovrascritto
            source_density="medium",
            display_name="alimento sconosciuto",
        )
    ]

    results = await service.enrich_parsed_items(items)

    assert len(results) == 1
    result = results[0]

    assert result.success is True
    assert result.source == "default"

    # Verifica calcolo calorie con Atwater factors
    # 2g protein * 4 + 10g carbs * 4 + 1g fat * 9 = 8 + 40 + 9 = 57 kcal
    expected_calories = (2.0 * 4) + (10.0 * 4) + (1.0 * 9)
    assert result.calories == pytest.approx(expected_calories)

    # Verifica altri nutrienti default
    assert result.protein == pytest.approx(2.0)
    assert result.carbs == pytest.approx(10.0)
    assert result.fat == pytest.approx(1.0)
    assert result.fiber == pytest.approx(1.0)
    assert result.sugar == pytest.approx(2.0)
    assert result.sodium == pytest.approx(50.0)
    assert result.calcium == pytest.approx(30.0)


@pytest.mark.asyncio
async def test_enrichment_stats_include_usda() -> None:
    """Test che le statistiche includano il contatore USDA."""
    service = NutrientEnrichmentService()

    items = [
        ParsedItem(
            label="rice",
            quantity_g=100.0,
            confidence=0.9,
            calories=365,
            source_density="medium",
            display_name="riso",
        )
    ]

    await service.enrich_parsed_items(items)

    stats = service.get_stats()

    # Verifica che ci sia il campo hit_usda nelle stats (nuovo sistema)
    assert "hit_usda" in stats
    assert "hit_default" in stats
    assert "enriched" in stats

    # Con riso (alimento comune) dovrebbe essere trovato via USDA o default
    assert stats["hit_usda"] + stats["hit_default"] == 1
    assert stats["enriched"] == 1


def test_usda_service_initialization() -> None:
    """Test inizializzazione servizio con chiave USDA."""
    # Ora ha sempre chiave USDA di default
    service1 = NutrientEnrichmentService()
    assert service1.usda_api_key is not None

    # Con chiave USDA
    service2 = NutrientEnrichmentService(usda_api_key="test_key")
    assert service2.usda_api_key == "test_key"
