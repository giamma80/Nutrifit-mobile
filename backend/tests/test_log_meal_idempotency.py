import json
import pytest
from typing import Any, Dict, List
from httpx import AsyncClient, Response
from repository.meals import meal_repo


def _reset() -> None:
    data = getattr(meal_repo, "_data", None)
    if data is not None:
        data.clear()
    idemp = getattr(meal_repo, "_idemp", None)
    if idemp is not None:
        idemp.clear()
    by_id = getattr(meal_repo, "_by_id", None)
    if by_id is not None:
        by_id.clear()


@pytest.mark.asyncio
async def test_log_meal_idempotent_without_timestamp(
    client: AsyncClient,
) -> None:
    _reset()
    query = """
    mutation {
      logMeal(
        input:{name:"Banana", quantityG:100}
      ) {
        id
        name
        quantityG
      }
    }
    """
    r1: Response = await client.post("/graphql", json={"query": query})
    r2: Response = await client.post("/graphql", json={"query": query})
    d1: Dict[str, Any] = r1.json()["data"]["logMeal"]
    d2: Dict[str, Any] = r2.json()["data"]["logMeal"]
    assert d1["id"] == d2["id"]


@pytest.mark.asyncio
async def test_log_meal_different_timestamp_not_idempotent(
    client: AsyncClient,
) -> None:
    _reset()
    q1 = """
    mutation {
      logMeal(
        input:{
          name:"Toast"
          quantityG:30
          timestamp:"2025-09-24T08:00:00Z"
        }
      ) { id }
    }
    """
    q2 = """
    mutation {
      logMeal(
        input:{
          name:"Toast"
          quantityG:30
          timestamp:"2025-09-24T08:00:05Z"
        }
      ) { id }
    }
    """
    r1: Response = await client.post("/graphql", json={"query": q1})
    r2: Response = await client.post("/graphql", json={"query": q2})
    id1: str = r1.json()["data"]["logMeal"]["id"]
    id2: str = r2.json()["data"]["logMeal"]["id"]
    assert id1 != id2


@pytest.mark.asyncio
async def test_log_meal_explicit_idempotency_key_wins(
    client: AsyncClient,
) -> None:
    _reset()
    q1 = """
    mutation {
      logMeal(
        input:{
          name:"Yogurt"
          quantityG:120
          idempotencyKey:"K1"
        }
      ) { id quantityG }
    }
    """
    q2 = """
    mutation {
      logMeal(
        input:{
          name:"Yogurt"
          quantityG:200
          idempotencyKey:"K1"
        }
      ) { id quantityG }
    }
    """
    r1: Response = await client.post("/graphql", json={"query": q1})
    r2: Response = await client.post("/graphql", json={"query": q2})
    d1: Dict[str, Any] = r1.json()["data"]["logMeal"]
    d2: Dict[str, Any] = r2.json()["data"]["logMeal"]
    assert d1["id"] == d2["id"]
    assert d2["quantityG"] == 120


@pytest.mark.asyncio
async def test_snapshot_present_only_with_barcode(client: AsyncClient) -> None:
    _reset()
    q_no = """
    mutation {
      logMeal(
        input:{name:"Pane", quantityG:40}
      ) { id nutrientSnapshotJson }
    }
    """
    q_bc = """
    mutation {
      logMeal(
        input:{name:"Bar", quantityG:50, barcode:"123456"}
      ) { id nutrientSnapshotJson }
    }
    """
    r_no: Response = await client.post("/graphql", json={"query": q_no})
    r_bc: Response = await client.post("/graphql", json={"query": q_bc})
    snap_no: Any = r_no.json()["data"]["logMeal"]["nutrientSnapshotJson"]
    snap_bc: Any = r_bc.json()["data"]["logMeal"]["nutrientSnapshotJson"]
    assert snap_no is None
    if snap_bc is not None:
        parsed = json.loads(snap_bc)
        for field in [
            "calories",
            "protein",
            "carbs",
            "fat",
            "fiber",
            "sugar",
            "sodium",
        ]:
            assert field in parsed


@pytest.mark.asyncio
async def test_multiple_entries_with_different_idempotency_keys(
    client: AsyncClient,
) -> None:
    """Due pasti identici ma con idempotencyKey diverso devono creare
    due record distinti e risultare nella lista."""
    _reset()
    q1 = """
    mutation {
      logMeal(input:{name:"Apple", quantityG:80, idempotencyKey:"A1"}) {
        id idempotencyKey
      }
    }
    """
    q2 = """
    mutation {
      logMeal(input:{name:"Apple", quantityG:80, idempotencyKey:"A2"}) {
        id idempotencyKey
      }
    }
    """
    list_query = """
    { mealEntries(limit:10){ id idempotencyKey name quantityG } }
    """
    r1: Response = await client.post("/graphql", json={"query": q1})
    r2: Response = await client.post("/graphql", json={"query": q2})
    rl: Response = await client.post("/graphql", json={"query": list_query})
    id1: str = r1.json()["data"]["logMeal"]["id"]
    id2: str = r2.json()["data"]["logMeal"]["id"]
    assert id1 != id2
    entries: List[Dict[str, Any]] = rl.json()["data"]["mealEntries"]
    keys = {e["idempotencyKey"] for e in entries}
    assert "A1" in keys and "A2" in keys
