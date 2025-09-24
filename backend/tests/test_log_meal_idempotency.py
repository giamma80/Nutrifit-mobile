import json
import pytest
from httpx import AsyncClient
from app import app
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
async def test_log_meal_idempotent_without_timestamp() -> None:
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
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r1 = await ac.post("/graphql", json={"query": query})
        r2 = await ac.post("/graphql", json={"query": query})
    d1 = r1.json()["data"]["logMeal"]
    d2 = r2.json()["data"]["logMeal"]
    assert d1["id"] == d2["id"]


@pytest.mark.asyncio
async def test_log_meal_different_timestamp_not_idempotent() -> None:
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
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r1 = await ac.post("/graphql", json={"query": q1})
        r2 = await ac.post("/graphql", json={"query": q2})
    id1 = r1.json()["data"]["logMeal"]["id"]
    id2 = r2.json()["data"]["logMeal"]["id"]
    assert id1 != id2


@pytest.mark.asyncio
async def test_log_meal_explicit_idempotency_key_wins() -> None:
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
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r1 = await ac.post("/graphql", json={"query": q1})
        r2 = await ac.post("/graphql", json={"query": q2})
    d1 = r1.json()["data"]["logMeal"]
    d2 = r2.json()["data"]["logMeal"]
    assert d1["id"] == d2["id"]
    assert d2["quantityG"] == 120


@pytest.mark.asyncio
async def test_snapshot_present_only_with_barcode() -> None:
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
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r_no = await ac.post("/graphql", json={"query": q_no})
        r_bc = await ac.post("/graphql", json={"query": q_bc})
    snap_no = r_no.json()["data"]["logMeal"]["nutrientSnapshotJson"]
    snap_bc = r_bc.json()["data"]["logMeal"]["nutrientSnapshotJson"]
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
