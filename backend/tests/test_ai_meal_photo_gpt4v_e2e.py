from typing import Any, Dict, List

import pytest
from httpx import AsyncClient, Response


def _q(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_analyze_meal_photo_gpt4v_total_calories(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E2E: verifica in modalità gpt4v calories e totalCalories.

    L'adapter Gpt4vAdapter (simulato) passa attraverso il parser calorie; ogni
    item deve avere calories settato e totalCalories deve essere la somma.
    """
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    mutation = _q(
        """
        mutation {
          analyzeMealPhoto(input:{photoId:"gptv1"}) {
            id status source totalCalories idempotencyKeyUsed
            items { label confidence quantityG calories }
          }
        }
        """
    )
    r: Response = await client.post("/graphql", json={"query": mutation})
    payload: Dict[str, Any] = r.json()
    assert "errors" not in payload, payload.get("errors")
    data = payload["data"]["analyzeMealPhoto"]
    assert data["status"] == "COMPLETED"
    assert data["source"] == "gpt4v"
    items: List[Dict[str, Any]] = data["items"]
    assert items, "Expected at least 1 item from gpt4v adapter"
    # Ogni item deve avere calories non null e >= 0
    calories_list = [it["calories"] for it in items]
    assert all(c is not None and c >= 0 for c in calories_list)
    # totalCalories coerente (tolleranza se rounding cambiasse)
    assert data["totalCalories"] == sum(calories_list)


@pytest.mark.asyncio
async def test_analyze_meal_photo_gpt4v_idempotent(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica idempotencyKey in modalità gpt4v come per stub."""
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    mutation = _q(
        'mutation { analyzeMealPhoto(input:{photoId:"gptv2", '
        'idempotencyKey:"GK1"}) { id items { label calories } '
        "totalCalories } }"
    )
    r1: Response = await client.post("/graphql", json={"query": mutation})
    r2: Response = await client.post("/graphql", json={"query": mutation})
    a1 = r1.json()["data"]["analyzeMealPhoto"]
    a2 = r2.json()["data"]["analyzeMealPhoto"]
    assert a1["id"] == a2["id"]
    assert a1["items"] == a2["items"]
    assert a1["totalCalories"] == a2["totalCalories"]
