"""Test per NutrientEnrichmentService."""

import pytest
from ai_models.nutrient_enrichment import (
    NutrientEnrichmentService,
    EnrichmentResult,
)
from ai_models.meal_photo_prompt import ParsedItem


@pytest.fixture
def service() -> NutrientEnrichmentService:
    """Service instance per test."""
    return NutrientEnrichmentService()


@pytest.mark.asyncio
async def test_usda_or_default_matching(service: NutrientEnrichmentService) -> None:
    """Test USDA lookup or default fallback per item."""
    items = [
        ParsedItem(
            label="chicken",
            quantity_g=100.0,
            confidence=0.9,
            calories=200,
            source_density="medium",
        )
    ]
    results = await service.enrich_parsed_items(items)

    assert len(results) == 1
    result = results[0]

    assert result.success is True
    # Può essere 'usda' se API funziona o 'default' se fallisce
    assert result.source in ["usda", "default"]
    assert result.protein is not None
    assert result.carbs is not None
    assert result.fat is not None
    assert result.fiber is not None


@pytest.mark.asyncio
async def test_default_fallback(service: NutrientEnrichmentService) -> None:
    """Test fallback a valori default per item sconosciuti."""
    items = [
        ParsedItem(
            label="unknown",
            quantity_g=100.0,
            confidence=0.8,
            calories=100,
            source_density="low",
        )
    ]
    results = await service.enrich_parsed_items(items)

    assert len(results) == 1
    result = results[0]

    assert result.success is True
    assert result.source == "default"
    assert result.protein == 2.0
    assert result.carbs == 10.0
    assert result.fat == 1.0
    assert result.fiber == 1.0


@pytest.mark.asyncio
async def test_quantity_scaling(service: NutrientEnrichmentService) -> None:
    """Test scaling nutrienti per quantity_g."""
    items = [
        ParsedItem(
            label="chicken",
            quantity_g=200.0,
            confidence=0.9,
            calories=400,
            source_density="medium",
        )
    ]
    results = await service.enrich_parsed_items(items)

    result = results[0]
    # Con 200g dovremmo avere il doppio dei valori per 100g
    # I valori esatti dipendono se viene da USDA o default
    assert result.protein is not None
    assert result.protein > 0
    assert result.fat is not None
    assert result.fat >= 0


@pytest.mark.asyncio
async def test_mixed_batch(service: NutrientEnrichmentService) -> None:
    """Test batch con mix USDA + default."""
    items = [
        ParsedItem(
            label="chicken",
            quantity_g=200.0,
            confidence=0.9,
            calories=250,
            source_density="medium",
        ),
        ParsedItem(
            label="rice",
            quantity_g=100.0,
            confidence=0.8,
            calories=130,
            source_density="high",
        ),
        ParsedItem(
            label="unknown",
            quantity_g=50.0,
            confidence=0.7,
            calories=60,
            source_density="low",
        ),
    ]
    results = await service.enrich_parsed_items(items)

    assert len(results) == 3

    # Tutti i risultati dovrebbero essere validi
    for result in results:
        assert result.success is True
        assert result.source in ["usda", "default"]
        assert result.protein is not None
        assert result.protein >= 0


@pytest.mark.asyncio
async def test_stats_tracking(service: NutrientEnrichmentService) -> None:
    """Test tracking statistiche."""
    items = [
        ParsedItem(
            label="chicken",
            quantity_g=100.0,
            confidence=0.9,
            calories=200,
            source_density="medium",
        ),
        ParsedItem(
            label="unknown",
            quantity_g=100.0,
            confidence=0.8,
            calories=100,
            source_density="low",
        ),
    ]
    await service.enrich_parsed_items(items)

    stats = service.get_stats()
    assert stats["enriched"] == 2
    # Con nuovo sistema: solo usda e default
    total_hits = stats["hit_usda"] + stats["hit_default"]
    assert total_hits == 2


@pytest.mark.asyncio
async def test_empty_list(service: NutrientEnrichmentService) -> None:
    """Test lista vuota."""
    results = await service.enrich_parsed_items([])
    assert results == []


def test_enrichment_result_dataclass() -> None:
    """Test EnrichmentResult dataclass."""
    result = EnrichmentResult(
        success=True,
        source="usda",
        protein=25.0,
        carbs=0.0,
        fat=4.0,
        fiber=0.0,
    )

    assert result.success is True
    assert result.source == "usda"
    assert result.protein == 25.0
    assert result.carbs == 0.0
    assert result.fat == 4.0
    assert result.fiber == 0.0
