import pytest
from typing import Any, Dict, List
from httpx import AsyncClient, Response
from repository.meals import meal_repo


def _q(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


def _reset_repo() -> None:
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
async def test_meal_entries_empty(client: AsyncClient) -> None:
    _reset_repo()
    query = _q("""{ mealEntries { id } }""")
    resp: Response = await client.post("/graphql", json={"query": query})
    data: Dict[str, Any] = resp.json()["data"]
    entries: List[Dict[str, Any]] = data["mealEntries"]
    assert entries == []


@pytest.mark.asyncio
async def test_meal_entries_after_logging(client: AsyncClient) -> None:
    _reset_repo()
    mutation1: str = _q(
        """
        mutation {
          logMeal(input:{name:"Mela", quantityG:100}) {
            id userId name quantityG
          }
        }
        """
    )
    mutation2: str = _q(
        """
        mutation {
          logMeal(input:{name:"Pera", quantityG:120}) {
            id userId name quantityG
          }
        }
        """
    )
    r1: Response = await client.post("/graphql", json={"query": mutation1})
    id1: str = r1.json()["data"]["logMeal"]["id"]
    r2: Response = await client.post("/graphql", json={"query": mutation2})
    id2: str = r2.json()["data"]["logMeal"]["id"]
    query = _q("""{ mealEntries(limit:10) { id name userId } }""")
    resp: Response = await client.post("/graphql", json={"query": query})
    entries: List[Dict[str, Any]] = resp.json()["data"]["mealEntries"]
    assert entries[0]["id"] == id2
    assert entries[1]["id"] == id1
    assert all(e["userId"] == "default" for e in entries)


@pytest.mark.asyncio
async def test_meal_entries_limit(client: AsyncClient) -> None:
    _reset_repo()
    for i in range(5):
        mutation: str = _q(
            f"""
            mutation {{
              logMeal(input:{{name:"Item{i}", quantityG:50}}) {{ id }}
            }}
            """
        )
        await client.post("/graphql", json={"query": mutation})
    query = _q("""{ mealEntries(limit:3) { id } }""")
    resp: Response = await client.post("/graphql", json={"query": query})
    entries: List[Dict[str, Any]] = resp.json()["data"]["mealEntries"]
    assert len(entries) == 3


@pytest.mark.asyncio
async def test_meal_entries_idempotency_no_dup(client: AsyncClient) -> None:
    _reset_repo()
    mutation: str = _q(
        """
        mutation {
          logMeal(input:{name:"Banana", quantityG:80, idempotencyKey:"abc"}) {
            id
          }
        }
        """
    )
    r1: Response = await client.post("/graphql", json={"query": mutation})
    id1: str = r1.json()["data"]["logMeal"]["id"]
    r2: Response = await client.post("/graphql", json={"query": mutation})
    id2: str = r2.json()["data"]["logMeal"]["id"]
    assert id1 == id2
    query = _q("""{ mealEntries { id } }""")
    resp: Response = await client.post("/graphql", json={"query": query})
    meal_list: List[Dict[str, Any]] = resp.json()["data"]["mealEntries"]
    ids = [e["id"] for e in meal_list if e["id"] == id1]
    assert len(ids) == 1


@pytest.mark.asyncio
async def test_meal_entries_after_before_filters(client: AsyncClient) -> None:
    _reset_repo()
    ts1 = "2025-01-01T10:00:00Z"
    ts2 = "2025-01-01T11:00:00Z"
    ts3 = "2025-01-01T12:00:00Z"
    for name, ts in [("Pasto1", ts1), ("Pasto2", ts2), ("Pasto3", ts3)]:
        mutation: str = _q(
            f"""
            mutation {{
              logMeal(
                input:{{
                  name:"{name}",
                  quantityG:50,
                  timestamp:"{ts}"
                }}
              ) {{ id }}
            }}
            """
        )
        await client.post("/graphql", json={"query": mutation})
    query_after = _q(f"""{{ mealEntries(after:"{ts1}") {{ timestamp }} }}""")
    resp_after: Response = await client.post(
        "/graphql", json={"query": query_after}
    )
    ts_list_after: List[str] = [
        e["timestamp"] for e in resp_after.json()["data"]["mealEntries"]
    ]
    assert ts_list_after == [ts3, ts2]
    query_before = _q(f"""{{ mealEntries(before:"{ts3}") {{ timestamp }} }}""")
    resp_before: Response = await client.post(
        "/graphql", json={"query": query_before}
    )
    ts_list_before: List[str] = [
        e["timestamp"] for e in resp_before.json()["data"]["mealEntries"]
    ]
    assert ts_list_before == [ts2, ts1]


@pytest.mark.asyncio
async def test_meal_entries_limit_normalization(client: AsyncClient) -> None:
    _reset_repo()
    for i in range(25):
        mutation: str = _q(
            f"""
            mutation {{
              logMeal(input:{{name:\"L{i}\", quantityG:10}}) {{ id }}
            }}
            """
        )
        await client.post("/graphql", json={"query": mutation})
    query = _q("""{ mealEntries(limit:0) { id } }""")
    resp: Response = await client.post("/graphql", json={"query": query})
    entries: List[Dict[str, Any]] = resp.json()["data"]["mealEntries"]
    assert len(entries) == 20
