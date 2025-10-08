"""Test di equivalenza tra nuovo MealAnalysisService e percorso legacy."""

from unittest.mock import patch
import pytest
from httpx import AsyncClient


def _q(query: str) -> str:
    """Normalizza query GraphQL rimuovendo spazi extra."""
    return " ".join(query.split())


@pytest.mark.asyncio
async def test_meal_analysis_service_equivalence(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test equivalenza tra nuovo service e legacy."""
    # Setup environment
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "0")

    mutation = _q(
        """
        mutation {
          analyzeMealPhoto(input:{photoId:"equivalence_test"}) {
            id status source totalCalories items {
              label confidence quantityG calories protein carbs fat
              fiber sugar sodium enrichmentSource calorieCorrected
            }
          }
        }
        """
    )

    # Test 1: Percorso legacy
    response_legacy = await client.post("/graphql", json={"query": mutation})
    payload_legacy = response_legacy.json()
    assert "errors" not in payload_legacy
    data_legacy = payload_legacy["data"]["analyzeMealPhoto"]

    # Test 2: Nuovo service
    monkeypatch.setenv("AI_MEAL_ANALYSIS_V2", "1")
    response_v2 = await client.post("/graphql", json={"query": mutation})
    payload_v2 = response_v2.json()
    assert "errors" not in payload_v2
    data_v2 = payload_v2["data"]["analyzeMealPhoto"]

    # Verifica equivalenza
    assert data_legacy["status"] == data_v2["status"]

    # V2 dovrebbe avere suffisso "_v2" nel source
    expected_v2_source = f"{data_legacy['source']}_v2"
    assert data_v2["source"] == expected_v2_source

    assert data_legacy["totalCalories"] == data_v2["totalCalories"]
    assert len(data_legacy["items"]) == len(data_v2["items"])

    # Verifica items (campo per campo)
    fields = [
        "label",
        "confidence",
        "quantityG",
        "calories",
        "protein",
        "carbs",
        "fat",
        "fiber",
        "sugar",
        "sodium",
        "enrichmentSource",
        "calorieCorrected",
    ]

    for legacy_item, v2_item in zip(data_legacy["items"], data_v2["items"]):
        for field in fields:
            assert legacy_item[field] == v2_item[field]


@pytest.mark.asyncio
async def test_meal_analysis_service_fallback(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica che il fallback funzioni in caso di errori."""
    monkeypatch.setenv("AI_MEAL_ANALYSIS_V2", "1")
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")

    target = (
        "domain.meal.application.meal_analysis_service." "MealAnalysisService.analyze_meal_photo"
    )

    with patch(target) as mock_analyze:
        mock_analyze.side_effect = Exception("Test error")

        mutation = _q(
            """
            mutation {
              analyzeMealPhoto(input:{photoId:"error_test"}) {
                id status source
              }
            }
            """
        )

        response = await client.post("/graphql", json={"query": mutation})
        payload = response.json()

        # Il fallback dovrebbe funzionare (nessun errore GraphQL)
        assert "errors" not in payload
        # Verifica che sia tornato al legacy (senza "_v2")
        data = payload["data"]["analyzeMealPhoto"]
        assert "v2" not in data.get("source", "")
