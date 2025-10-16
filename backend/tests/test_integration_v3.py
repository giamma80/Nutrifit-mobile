"""Test integrazione end-to-end con prompt v3 e USDA."""

import pytest
from ai_models.meal_photo_prompt import parse_and_validate_v3
from ai_models.nutrient_enrichment import NutrientEnrichmentService


@pytest.mark.asyncio
async def test_end_to_end_v3_with_enrichment() -> None:
    """
    Test end-to-end: prompt v3 → etichette inglesi → enrichment con USDA.
    """

    # Simula risposta LLM con prompt v3
    llm_response = """
    {
        "dish_title": "Petto di pollo grigliato con riso pilaf",
        "items": [
            {
                "label": "chicken",
                "display_name": "petto di pollo",
                "quantity": {"value": 150, "unit": "g"},
                "confidence": 0.92
            },
            {
                "label": "rice",
                "display_name": "riso pilaf",
                "quantity": {"value": 80, "unit": "g"},
                "confidence": 0.88
            },
            {
                "label": "vegetables",
                "display_name": "verdure miste",
                "quantity": {"value": 100, "unit": "g"},
                "confidence": 0.75
            }
        ]
    }
    """

    # STEP 1: Parsing v3 con etichette inglesi
    dish_title, parsed_items = parse_and_validate_v3(llm_response)

    assert dish_title == "Petto di pollo grigliato con riso pilaf"
    assert len(parsed_items) == 3

    # Verifica che le etichette siano in inglese (per USDA)
    labels = [item.label for item in parsed_items]
    assert "chicken" in labels
    assert "rice" in labels
    assert "vegetables" in labels

    # Verifica che i display_names siano in italiano (per UI)
    display_names = [item.display_name for item in parsed_items]
    assert "petto di pollo" in display_names
    assert "riso pilaf" in display_names
    assert "verdure miste" in display_names

    # STEP 2: Enrichment con lookup migliorato (senza API key USDA)
    service = NutrientEnrichmentService()
    enriched_results = await service.enrich_parsed_items(parsed_items)

    assert len(enriched_results) == 3

    # Verifica enrichment chicken (dovrebbe trovarlo tramite USDA o fallback)
    chicken_result = next(
        r for r, item in zip(enriched_results, parsed_items) if item.label == "chicken"
    )
    assert chicken_result.source in ["usda", "default"]  # USDA o fallback
    assert chicken_result.protein is not None and chicken_result.protein >= 0

    # Verifica stats (nuovo sistema senza heuristics)
    stats = service.get_stats()
    assert stats["hit_usda"] + stats["hit_default"] == 3  # Tutti processati
    assert stats["enriched"] == 3


@pytest.mark.asyncio
async def test_v3_unknown_english_food_fallback() -> None:
    """
    Test che alimenti inglesi sconosciuti usino il fallback di default.
    """

    # Simula risposta con alimento sconosciuto
    llm_response = """
    {
        "dish_title": "Exotic quinoa salad",
        "items": [
            {
                "label": "quinoa",
                "display_name": "quinoa",
                "quantity": {"value": 100, "unit": "g"},
                "confidence": 0.8
            }
        ]
    }
    """

    dish_title, parsed_items = parse_and_validate_v3(llm_response)

    # Enrichment
    service = NutrientEnrichmentService()
    enriched_results = await service.enrich_parsed_items(parsed_items)

    assert len(enriched_results) == 1

    # Quinoa - può essere trovato tramite USDA o andare a default
    quinoa_result = enriched_results[0]
    assert quinoa_result.source in ["usda", "default"]
    assert quinoa_result.protein is not None
    assert quinoa_result.calories is not None


def test_v3_prompt_generation() -> None:
    """Test che il prompt v3 contenga le istruzioni corrette."""
    from ai_models.meal_photo_prompt import generate_prompt_v3

    prompt = generate_prompt_v3()

    # Verifica elementi chiave del prompt v3
    assert "dish_title" in prompt
    assert "label" in prompt
    assert "display_name" in prompt
    assert "inglese" in prompt
    assert "italiano" in prompt
    assert "chicken" in prompt  # Esempi di termini inglesi
    assert "USDA" in prompt


def test_usda_system_integration() -> None:
    """Test che il sistema USDA sia integrato correttamente."""
    from ai_models.usda_client import USDAClient, normalize_food_label
    from ai_models.nutrient_enrichment import NutrientEnrichmentService

    # Test normalizzazione etichette per USDA
    normalized = normalize_food_label("ChIcKeN")
    assert normalized == "chicken"

    # Test service con API key
    service = NutrientEnrichmentService()
    assert service.usda_api_key is not None

    # Test client USDA
    client = USDAClient()
    assert client.api_key is not None
