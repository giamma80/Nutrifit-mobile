import pytest
from httpx import AsyncClient, Response
from typing import Any, Dict


def _q(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_graphql_analyze_meal_photo_end_to_end(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test E2E minimale della mutation analyzeMealPhoto.

    Obiettivi:
    - Schema include la mutation
    - Stub adapter produce due item
    - Verifica campi chiave (status, items, id)
    - Regression guard per refactor
    """
    # Forza modalità stub eliminando variabili ambiente impostate
    for k in [
        "AI_MEAL_PHOTO_MODE",
        "AI_GPT4V_REAL_ENABLED",
        "OPENAI_API_KEY",
        "OPENAI_VISION_MODEL",
    ]:
        monkeypatch.delenv(k, raising=False)

        mutation = _q(
            """
                mutation TestAnalyze {
                    analyzeMealPhoto(input:{photoId:"test-ph-graphql"}) {
                        id
                        status
                        items { label confidence quantityG }
                    }
                }
                """
        )
    resp: Response = await client.post("/graphql", json={"query": mutation})
    payload: Dict[str, Any] = resp.json()

    assert "errors" not in payload, f"Unexpected GraphQL errors: {payload.get('errors')}"
    data = payload["data"]["analyzeMealPhoto"]
    assert data["status"] == "COMPLETED"
    assert len(data["items"]) == 2, "Stub adapter dovrebbe restituire due item fissi"
    labels = {it["label"] for it in data["items"]}
    # Non vincoliamo l'ordine, solo la presenza delle etichette conosciute
    assert {"mixed salad", "chicken breast"} == labels
    # id deve esistere ed essere stringa non vuota
    assert isinstance(data["id"], str) and data["id"], "id analisi mancante o vuoto"
