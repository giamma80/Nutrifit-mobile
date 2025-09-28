import pytest
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
async def test_meal_entries_empty(client) -> None:
    _reset_repo()
    query = _q("""{ mealEntries { id } }""")
    resp = await client.post("/graphql", json={"query": query})
    assert resp.json()["data"]["mealEntries"] == []


@pytest.mark.asyncio
async def test_meal_entries_after_logging(client) -> None:
    _reset_repo()
    mutation1 = _q(
        """
        mutation {
          logMeal(input:{name:"Mela", quantityG:100}) {
            id userId name quantityG
          }
        }
        """
    )
    mutation2 = _q(
        """
        mutation {
          logMeal(input:{name:"Pera", quantityG:120}) {
            id userId name quantityG
          }
        }
        """
    )
    r1 = await client.post("/graphql", json={"query": mutation1})
    id1 = r1.json()["data"]["logMeal"]["id"]
    r2 = await client.post("/graphql", json={"query": mutation2})
    id2 = r2.json()["data"]["logMeal"]["id"]
    query = _q("""{ mealEntries(limit:10) { id name userId } }""")
    resp = await client.post("/graphql", json={"query": query})
    entries = resp.json()["data"]["mealEntries"]
    assert entries[0]["id"] == id2
    assert entries[1]["id"] == id1
    assert all(e["userId"] == "default" for e in entries)


@pytest.mark.asyncio
async def test_meal_entries_limit(client) -> None:
    _reset_repo()
    for i in range(5):
        mutation = _q(
            f"""
            mutation {{
              logMeal(input:{{name:"Item{i}", quantityG:50}}) {{ id }}
            }}
            """
        )
        await client.post("/graphql", json={"query": mutation})
    query = _q("""{ mealEntries(limit:3) { id } }""")
    resp = await client.post("/graphql", json={"query": query})
    entries = resp.json()["data"]["mealEntries"]
    assert len(entries) == 3


@pytest.mark.asyncio
async def test_meal_entries_idempotency_no_duplicate(client) -> None:
    _reset_repo()
    mutation = _q(
        """
        mutation {
          logMeal(input:{name:"Banana", quantityG:80, idempotencyKey:"abc"}) {
            id
          }
        }
        """
    )
    r1 = await client.post("/graphql", json={"query": mutation})
    id1 = r1.json()["data"]["logMeal"]["id"]
    r2 = await client.post("/graphql", json={"query": mutation})
    id2 = r2.json()["data"]["logMeal"]["id"]
    assert id1 == id2
    query = _q("""{ mealEntries { id } }""")
    resp = await client.post("/graphql", json={"query": query})
    ids = [e["id"] for e in resp.json()["data"]["mealEntries"] if e["id"] == id1]
    assert len(ids) == 1


@pytest.mark.asyncio
async def test_meal_entries_after_before_filters(client) -> None:
    _reset_repo()
    # Inseriamo 3 pasti con timestamp controllati
    ts1 = "2025-01-01T10:00:00Z"
    ts2 = "2025-01-01T11:00:00Z"
    ts3 = "2025-01-01T12:00:00Z"
    for name, ts in [("Pasto1", ts1), ("Pasto2", ts2), ("Pasto3", ts3)]:
        mutation = _q(
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
    resp_after = await client.post("/graphql", json={"query": query_after})
    ts_list_after = [e["timestamp"] for e in resp_after.json()["data"]["mealEntries"]]
    assert ts_list_after == [ts3, ts2]
    query_before = _q(f"""{{ mealEntries(before:"{ts3}") {{ timestamp }} }}""")
    resp_before = await client.post("/graphql", json={"query": query_before})
    ts_list_before = [e["timestamp"] for e in resp_before.json()["data"]["mealEntries"]]
    assert ts_list_before == [ts2, ts1]


@pytest.mark.asyncio
async def test_meal_entries_limit_normalization(client) -> None:
    _reset_repo()
    # Inseriamo 25 pasti senza timestamp custom (ordina per ts generato)
    for i in range(25):
        mutation = _q(
            f"""
            mutation {{
              logMeal(input:{{name:\"L{i}\", quantityG:10}}) {{ id }}
            }}
            """
        )
        await client.post("/graphql", json={"query": mutation})
    # limit 0 -> fallback 20 (default) definito nel resolver
    query = _q("""{ mealEntries(limit:0) { id } }""")
    resp = await client.post("/graphql", json={"query": query})
    entries = resp.json()["data"]["mealEntries"]
    assert len(entries) == 20
