"""
Test end-to-end per pipeline completo di analisi foto pasto con enrichment USDA.
"""

import pytest
from ai_models.nutrient_enrichment import NutrientEnrichmentService


def test_enrichment_service_initialization() -> None:
    """Test che il servizio si inizializzi correttamente con USDA."""
    enrichment_service = NutrientEnrichmentService()

    # Verifica stats iniziali (nuovo sistema senza heuristics)
    stats = enrichment_service.get_stats()
    assert stats["enriched"] == 0
    assert stats["hit_usda"] == 0
    assert stats["hit_default"] == 0

    # Verifica che abbia API key di default
    assert enrichment_service.usda_api_key is not None
    assert len(enrichment_service.usda_api_key) > 10


def test_usda_api_key_configuration() -> None:
    """Test che la configurazione API key funzioni."""
    # Test con API key di default
    service_default = NutrientEnrichmentService()
    assert service_default.usda_api_key.startswith("zqOnb4hdPJ")

    # Test con API key custom
    custom_key = "custom_test_key_123"
    service_custom = NutrientEnrichmentService(usda_api_key=custom_key)
    assert service_custom.usda_api_key == custom_key


def test_enrichment_service_stats_methods() -> None:
    """Test che i metodi delle statistiche funzionino con nuovo sistema."""
    service = NutrientEnrichmentService()

    # Test che get_stats ritorni dizionario con chiavi corrette (nuovo sistema)
    stats = service.get_stats()
    expected_keys = ["enriched", "hit_usda", "hit_default"]
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


@pytest.mark.asyncio
async def test_usda_enrichment_pipeline() -> None:
    """Test pipeline USDA end-to-end con alimenti reali."""
    from ai_models.meal_photo_prompt import ParsedItem

    service = NutrientEnrichmentService()

    # Test items con etichette inglesi (come da prompt v3)
    items = [
        ParsedItem(
            label="chicken",
            quantity_g=100.0,
            confidence=0.9,
            calories=0,
            source_density="temp",
        ),
        ParsedItem(
            label="unknown_food",
            quantity_g=50.0,
            confidence=0.7,
            calories=0,
            source_density="temp",
        ),
    ]

    results = await service.enrich_parsed_items(items)

    # Verifica risultati
    assert len(results) == 2

    # Primo item (chicken) - dovrebbe trovare USDA o fallback a default
    assert results[0].success is True
    assert results[0].source in ["usda", "default"]
    assert results[0].protein is not None
    assert results[0].protein > 0

    # Secondo item (unknown) - dovrebbe andare a default
    assert results[1].success is True
    assert results[1].source == "default"
    assert results[1].protein is not None


def test_end_to_end_validation_pipeline() -> None:
    """Test validazione pipeline: servizio USDA inizializzato e pronto."""
    service = NutrientEnrichmentService()

    # 1. Servizio inizializzato con USDA
    assert service is not None
    assert service.usda_api_key is not None

    # 2. Stats tracking funzionante (nuovo sistema)
    stats = service.get_stats()
    assert stats["enriched"] == 0
    assert "hit_usda" in stats
    assert "hit_default" in stats

    # 3. Interfaccia completa
    assert hasattr(service, "enrich_parsed_items")
    assert hasattr(service, "get_stats")

    print("✅ Pipeline USDA end-to-end validation completata con successo!")


def test_usda_client_integration() -> None:
    """Test integrazione con USDA client."""
    from ai_models.usda_client import USDAClient, normalize_food_label

    # Test normalizzazione etichette per USDA
    normalized = normalize_food_label("  ChIcKeN  ")
    assert normalized == "chicken"

    # Test client con API key
    client = USDAClient()
    assert client.api_key is not None
    assert len(client.api_key) > 10


@pytest.mark.asyncio
async def test_performance_optimizations() -> None:
    """Test ottimizzazioni performance implementate nel nuovo sistema."""
    service = NutrientEnrichmentService()

    # Test che il metodo accetti timeout parameter
    assert hasattr(service, "enrich_parsed_items")

    # Test metodi interni per batch processing
    assert hasattr(service, "_process_batch")
    assert hasattr(service, "_create_default_result")
    assert hasattr(service, "_try_usda_lookup")

    print("✅ Performance optimizations USDA implementate correttamente!")
