import pytest
from typing import Any, Dict, List, Set
from httpx import AsyncClient, Response


def _q(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_analyze_meal_photo_basic(client: AsyncClient) -> None:
    mutation = _q(
        """
        mutation {
          analyzeMealPhoto(input:{photoId:"ph1"}) {
            id status items { label confidence quantityG calories }
            idempotencyKeyUsed
          }
        }
        """
    )
    r: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] = r.json()["data"]["analyzeMealPhoto"]
    assert data["status"] == "COMPLETED"
    assert len(data["items"]) == 2
    labels: Set[str] = {it["label"] for it in data["items"]}
    assert {"Insalata mista", "Petto di pollo"} == labels


@pytest.mark.asyncio
async def test_analyze_idempotent_same_key(client: AsyncClient) -> None:
    mutation = _q(
        'mutation { analyzeMealPhoto(input:{photoId:"same", '
        'idempotencyKey:"AIK1"}) { id items { label } } }'
    )
    r1: Response = await client.post("/graphql", json={"query": mutation})
    r2: Response = await client.post("/graphql", json={"query": mutation})
    a1: Dict[str, Any] = r1.json()["data"]["analyzeMealPhoto"]
    a2: Dict[str, Any] = r2.json()["data"]["analyzeMealPhoto"]
    assert a1["id"] == a2["id"]
    assert a1["items"] == a2["items"]


@pytest.mark.asyncio
async def test_confirm_creates_meals_and_is_idempotent(
    client: AsyncClient,
) -> None:
    analyze = _q(
        'mutation { analyzeMealPhoto(input:{photoId:"conf1", '
        'idempotencyKey:"AKCONF"}) { id items { label } } }'
    )
    r: Response = await client.post("/graphql", json={"query": analyze})
    analysis_id: str = r.json()["data"]["analyzeMealPhoto"]["id"]
    confirm = _q(
        f'mutation {{ confirmMealPhoto(input:{{analysisId:"{analysis_id}", '
        "acceptedIndexes:[0,1]}) { analysisId createdMeals "
        "{ name calories quantityG } } }"
    )
    first: Response = await client.post("/graphql", json={"query": confirm})
    second: Response = await client.post("/graphql", json={"query": confirm})
    d1: Dict[str, Any] = first.json()["data"]["confirmMealPhoto"]
    d2: Dict[str, Any] = second.json()["data"]["confirmMealPhoto"]
    assert d1["analysisId"] == analysis_id
    # Idempotenza: stessi due pasti, non duplicati
    assert len(d1["createdMeals"]) == 2
    assert {m["name"] for m in d1["createdMeals"]} == {
        m["name"] for m in d2["createdMeals"]
    }


@pytest.mark.asyncio
async def test_confirm_invalid_index(client: AsyncClient) -> None:
    analyze = _q(
        'mutation { analyzeMealPhoto(input:{photoId:"err1"}) { id } }'
    )
    r: Response = await client.post("/graphql", json={"query": analyze})
    analysis_id: str = r.json()["data"]["analyzeMealPhoto"]["id"]
    bad = _q(
        f'mutation {{ confirmMealPhoto(input:{{analysisId:"{analysis_id}", '
        "acceptedIndexes:[5]}) { analysisId } }"
    )
    resp: Response = await client.post("/graphql", json={"query": bad})
    errs: List[Dict[str, Any]] | None = resp.json().get("errors")
    assert errs and any("INVALID_INDEX" in e.get("message", "") for e in errs)
