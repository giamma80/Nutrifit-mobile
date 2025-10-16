"""
Test per verificare che il prompt migliorato generi label USDA corrette.
"""

import pytest
from unittest.mock import patch, MagicMock
from inference.adapter import Gpt4vAdapter


def test_improved_usda_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test che verifica il prompt migliorato generi label USDA corrette
    come 'eggs' invece di 'egg'.
    """
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    # Mock response con label USDA corrette
    mock_response = (
        '{"dish_title": "Uova strapazzate", "items": ['
        '{"label": "eggs", "display_name": "uova", '
        '"quantity": {"value": 100, "unit": "g"}, "confidence": 0.9}]}'
    )

    # Patch simbolo importato in adapter
    import inference.adapter as adapter_mod

    async def _fake_call(*, image_url: str | None, prompt: str, timeout_s: float = 12.0) -> str:
        # Verifica che il prompt contenga le nuove regole USDA
        assert "eggs non egg" in prompt
        assert "nomenclatura USDA" in prompt
        assert "ESEMPI label USDA corretti: eggs" in prompt
        return mock_response

    monkeypatch.setattr(adapter_mod, "call_openai_vision", _fake_call)

    adapter = Gpt4vAdapter()

    # Mock del nutrient enrichment
    with patch("ai_models.nutrient_enrichment.NutrientEnrichmentService") as mock_service:
        mock_enrich_result = MagicMock(
            success=True,
            protein=12.4,
            carbs=0.96,
            fat=9.96,
            fiber=0.0,
            sodium=129.0,
            sugar=0.2,
            source="USDA",
        )
        mock_service_instance = MagicMock()
        mock_service_instance.enrich_parsed_items.return_value = [mock_enrich_result]
        mock_service.return_value = mock_service_instance

        # Esegui l'analisi
        items = adapter.analyze(
            user_id="test_user",
            photo_id="test_photo",
            photo_url="https://example.com/photo.jpg",
            now_iso="2024-01-01T12:00:00Z",
        )

        # Verifica che la label sia corretta per USDA
        assert len(items) == 1
        assert items[0].label == "eggs"  # Non "egg"!

        # Verifica che dishName sia in italiano
        dish_name = getattr(adapter, "_last_dish_name", None)
        assert dish_name == "Uova strapazzate"
