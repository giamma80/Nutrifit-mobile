"""
Test per verificare che dishName usi il dish_title italiano dal GPT-4V.
"""

import pytest
from unittest.mock import MagicMock, patch
from inference.adapter import Gpt4vAdapter


def test_dish_title_italian(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test che verifica dishName usi dish_title italiano quando disponibile.
    """
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    # Mock response dal GPT-4V con dish_title in italiano (formato V3)
    mock_response = (
        '{"dish_title": "Manzo con salsa e polenta", "items": ['
        '{"label": "beef", "display_name": "manzo", '
        '"quantity": {"value": 150, "unit": "g"}, "confidence": 0.9}, '
        '{"label": "tomato sauce", "display_name": "salsa di pomodoro", '
        '"quantity": {"value": 50, "unit": "g"}, "confidence": 0.8}, '
        '{"label": "polenta", "display_name": "polenta", '
        '"quantity": {"value": 100, "unit": "g"}, "confidence": 0.85}]}'
    )

    # Patch simbolo importato in adapter
    import inference.adapter as adapter_mod

    async def _fake_call(*, image_url: str | None, prompt: str, timeout_s: float = 12.0) -> str:
        return mock_response

    monkeypatch.setattr(adapter_mod, "call_openai_vision", _fake_call)

    adapter = Gpt4vAdapter()

    # Mock del nutrient enrichment per evitare chiamate USDA
    with patch("ai_models.nutrient_enrichment.NutrientEnrichmentService") as mock_service:
        mock_enrich_result = MagicMock(
            success=True,
            protein=25.0,
            carbs=15.0,
            fat=8.0,
            fiber=2.0,
            sodium=150.0,
            sugar=3.0,
            source="USDA",
        )
        mock_service_instance = MagicMock()
        mock_service_instance.enrich_parsed_items.return_value = [
            mock_enrich_result,
            mock_enrich_result,
            mock_enrich_result,
        ]
        mock_service.return_value = mock_service_instance

        # Esegui l'analisi
        items = adapter.analyze(
            user_id="test_user",
            photo_id="test_photo",
            photo_url="https://example.com/photo.jpg",
            now_iso="2024-01-01T12:00:00Z",
        )

        # Verifica che dishName sia in italiano
        dish_name = getattr(adapter, "_last_dish_name", None)
        assert dish_name == "Manzo con salsa e polenta"

        # Verifica che le label items siano ancora inglesi (per USDA)
        labels = [item.label for item in items]
        assert "beef" in labels
        assert "tomato sauce" in labels
        assert "polenta" in labels


def test_dish_title_fallback_to_english(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Test fallback all'euristica inglese quando dish_title è vuoto.
    """
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    # Mock response senza dish_title (formato V3)
    mock_response = (
        '{"dish_title": "", "items": ['
        '{"label": "beef", "display_name": "manzo", '
        '"quantity": {"value": 150, "unit": "g"}, "confidence": 0.9}, '
        '{"label": "sauce", "display_name": "salsa", '
        '"quantity": {"value": 50, "unit": "g"}, "confidence": 0.8}]}'
    )

    # Patch simbolo importato in adapter
    import inference.adapter as adapter_mod

    async def _fake_call(*, image_url: str | None, prompt: str, timeout_s: float = 12.0) -> str:
        return mock_response

    monkeypatch.setattr(adapter_mod, "call_openai_vision", _fake_call)

    adapter = Gpt4vAdapter()

    with patch("ai_models.nutrient_enrichment.NutrientEnrichmentService") as mock_service:
        mock_enrich_result = MagicMock(
            success=True,
            protein=25.0,
            carbs=5.0,
            fat=8.0,
            fiber=1.0,
            sodium=100.0,
            sugar=1.0,
            source="USDA",
        )
        mock_service_instance = MagicMock()
        mock_service_instance.enrich_parsed_items.return_value = [
            mock_enrich_result,
            mock_enrich_result,
        ]
        mock_service.return_value = mock_service_instance

        adapter.analyze(
            user_id="test_user",
            photo_id="test_photo",
            photo_url="https://example.com/photo.jpg",
            now_iso="2024-01-01T12:00:00Z",
        )

        # Dovrebbe usare l'euristica inglese
        expected = ["beef sauce bowl", "beef sauce", "sauce beef bowl"]
        dish_name = getattr(adapter, "_last_dish_name", None)
        assert dish_name in expected
