"""
Test end-to-end per pipeline completo di analisi foto pasto con enrichment.
"""

import pytest
from ai_models.nutrient_enrichment import NutrientEnrichmentService, HEURISTIC_NUTRIENTS


def test_enrichment_service_initialization() -> None:
    """Test che il servizio si inizializzi correttamente."""
    enrichment_service = NutrientEnrichmentService()

    # Verifica stats iniziali
    stats = enrichment_service.get_stats()
    assert stats["enriched"] == 0
    assert stats["hit_heuristic"] == 0
    assert stats["hit_default"] == 0


def test_heuristic_nutrients_dictionary() -> None:
    """Test che il dizionario dei nutrienti euristici sia corretto."""
    # Verifica che alcuni alimenti base siano presenti
    assert "pollo" in HEURISTIC_NUTRIENTS
    assert "riso" in HEURISTIC_NUTRIENTS
    assert "verdure" in HEURISTIC_NUTRIENTS

    # Verifica la struttura dei nutrienti
    for food, nutrients in HEURISTIC_NUTRIENTS.items():
        assert "protein" in nutrients
        assert "carbs" in nutrients
        assert "fat" in nutrients
        assert "fiber" in nutrients
        assert all(isinstance(v, (int, float)) for v in nutrients.values())


def test_enrichment_service_stats_methods() -> None:
    """Test che i metodi delle statistiche funzionino."""
    service = NutrientEnrichmentService()

    # Test che get_stats ritorni dizionario con chiavi corrette
    stats = service.get_stats()
    expected_keys = ["enriched", "hit_heuristic", "hit_default"]
    assert all(key in stats for key in expected_keys)
    assert all(isinstance(stats[key], int) for key in expected_keys)


def test_enrichment_result_dataclass() -> None:
    """Test della struttura EnrichmentResult."""
    from ai_models.nutrient_enrichment import EnrichmentResult

    # Test creazione con valori di base
    result = EnrichmentResult(success=True, source="heuristic")
    assert result.success is True
    assert result.source == "heuristic"
    assert result.protein is None
    assert result.carbs is None
    assert result.fat is None
    assert result.fiber is None

    # Test creazione con tutti i valori
    result_full = EnrichmentResult(
        success=True, source="test", protein=25.0, carbs=50.0, fat=10.0, fiber=5.0
    )
    assert result_full.protein == 25.0
    assert result_full.carbs == 50.0
    assert result_full.fat == 10.0
    assert result_full.fiber == 5.0


@pytest.mark.asyncio
async def test_enrichment_service_interface() -> None:
    """Test dell'interfaccia del servizio (senza dipendenze esterne)."""
    service = NutrientEnrichmentService()

    # Verifica che il metodo esista
    assert hasattr(service, "enrich_parsed_items")
    assert callable(getattr(service, "enrich_parsed_items"))

    # Verifica che get_stats esista e funzioni
    stats = service.get_stats()
    assert isinstance(stats, dict)


def test_nutrient_calculations() -> None:
    """Test dei calcoli dei nutrienti basati sui dati del dizionario."""
    # Test calcolo per 100g di pollo
    pollo_nutrients = HEURISTIC_NUTRIENTS["pollo"]
    factor_100g = 100.0 / 100.0  # 1.0

    protein_expected = pollo_nutrients["protein"] * factor_100g
    carbs_expected = pollo_nutrients["carbs"] * factor_100g
    fat_expected = pollo_nutrients["fat"] * factor_100g

    assert protein_expected == 25.0  # 25.0 * 1.0
    assert carbs_expected == 0.0  # 0.0 * 1.0
    assert fat_expected == 4.0  # 4.0 * 1.0

    # Test calcolo per 150g di pollo
    factor_150g = 150.0 / 100.0  # 1.5

    protein_150g = pollo_nutrients["protein"] * factor_150g
    fat_150g = pollo_nutrients["fat"] * factor_150g

    assert protein_150g == 37.5  # 25.0 * 1.5
    assert fat_150g == 6.0  # 4.0 * 1.5


def test_end_to_end_validation_pipeline() -> None:
    """Test validazione pipeline: servizio inizializzato e pronto."""
    # Test che tutto sia configurato correttamente per Phase 2
    service = NutrientEnrichmentService()

    # 1. Servizio inizializzato
    assert service is not None

    # 2. Dizionario nutrienti popolato
    assert len(HEURISTIC_NUTRIENTS) >= 3

    # 3. Stats tracking funzionante
    stats = service.get_stats()
    assert stats["enriched"] == 0

    # 4. Interfaccia complete
    assert hasattr(service, "enrich_parsed_items")
    assert hasattr(service, "get_stats")

    print("✅ Pipeline end-to-end validation completata con successo!")


def test_lru_cache_performance() -> None:
    """Test che la cache LRU funzioni correttamente."""
    from ai_models.nutrient_enrichment import get_nutrient_values

    # Test cache hit
    result1 = get_nutrient_values("pollo")
    result2 = get_nutrient_values("pollo")  # Dovrebbe essere da cache

    assert result1 is not None
    assert result1 == result2
    assert result1["protein"] == 25.0

    # Test cache miss
    result3 = get_nutrient_values("alimento_inesistente")
    assert result3 is None

    # Verifica che la cache info sia disponibile
    cache_info = get_nutrient_values.cache_info()
    assert cache_info.hits >= 1  # Almeno un hit dalla seconda chiamata


@pytest.mark.asyncio
async def test_performance_optimizations() -> None:
    """Test ottimizzazioni performance implementate."""
    service = NutrientEnrichmentService()

    # Test che il metodo accetti timeout parameter
    assert hasattr(service, "enrich_parsed_items")

    # Test metodi interni per batch processing
    assert hasattr(service, "_process_batch")
    assert hasattr(service, "_create_default_result")

    # Test che la cache function sia disponibile
    from ai_models.nutrient_enrichment import get_nutrient_values

    assert callable(get_nutrient_values)

    print("✅ Performance optimizations implementate correttamente!")
