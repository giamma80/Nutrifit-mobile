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
async def test_heuristic_matching(service: NutrientEnrichmentService) -> None:
    """Test heuristic matching per item conosciuti."""
    items = [
        ParsedItem(
            label="pollo", quantity_g=100.0, confidence=0.9, calories=200, source_density="medium"
        )
    ]
    results = await service.enrich_parsed_items(items)

    assert len(results) == 1
    result = results[0]

    assert result.success is True
    assert result.source == "heuristic"
    assert result.protein == 25.0
    assert result.carbs == 0.0
    assert result.fat == 4.0
    assert result.fiber == 0.0


@pytest.mark.asyncio
async def test_default_fallback(service: NutrientEnrichmentService) -> None:
    """Test fallback a valori default per item sconosciuti."""
    items = [
        ParsedItem(
            label="unknown", quantity_g=100.0, confidence=0.8, calories=100, source_density="low"
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
            label="pollo", quantity_g=200.0, confidence=0.9, calories=400, source_density="medium"
        )
    ]
    results = await service.enrich_parsed_items(items)

    result = results[0]
    assert result.protein == 50.0  # 25.0 * 2.0 (200g/100g)
    assert result.fat == 8.0  # 4.0 * 2.0


@pytest.mark.asyncio
async def test_mixed_batch(service: NutrientEnrichmentService) -> None:
    """Test batch con mix heuristic + default."""
    items = [
        ParsedItem(
            label="pollo", quantity_g=200.0, confidence=0.9, calories=250, source_density="medium"
        ),
        ParsedItem(
            label="riso", quantity_g=100.0, confidence=0.8, calories=130, source_density="high"
        ),
        ParsedItem(
            label="unknown", quantity_g=50.0, confidence=0.7, calories=60, source_density="low"
        ),
    ]
    results = await service.enrich_parsed_items(items)

    assert len(results) == 3

    # pollo (heuristic)
    assert results[0].source == "heuristic"
    assert results[0].protein == 50.0  # 25.0 * 2.0 (200g/100g)

    # riso (heuristic)
    assert results[1].source == "heuristic"
    assert results[1].protein == 3.0  # 3.0 * 1.0 (100g/100g)

    # unknown (default)
    assert results[2].source == "default"
    assert results[2].protein == 1.0  # 2.0 * 0.5 (50g/100g)


@pytest.mark.asyncio
async def test_stats_tracking(service: NutrientEnrichmentService) -> None:
    """Test tracking statistiche."""
    items = [
        ParsedItem(
            label="pollo", quantity_g=100.0, confidence=0.9, calories=200, source_density="medium"
        ),
        ParsedItem(
            label="unknown", quantity_g=100.0, confidence=0.8, calories=100, source_density="low"
        ),
    ]
    await service.enrich_parsed_items(items)

    stats = service.get_stats()
    assert stats["enriched"] == 2
    assert stats["hit_heuristic"] == 1  # pollo
    assert stats["hit_default"] == 1  # unknown


@pytest.mark.asyncio
async def test_empty_list(service: NutrientEnrichmentService) -> None:
    """Test lista vuota."""
    results = await service.enrich_parsed_items([])
    assert results == []


def test_enrichment_result_dataclass() -> None:
    """Test EnrichmentResult dataclass."""
    result = EnrichmentResult(
        success=True,
        source="heuristic",
        protein=25.0,
        carbs=0.0,
        fat=4.0,
        fiber=0.0,
    )

    assert result.success is True
    assert result.source == "heuristic"
    assert result.protein == 25.0
    assert result.carbs == 0.0
    assert result.fat == 4.0
    assert result.fiber == 0.0
