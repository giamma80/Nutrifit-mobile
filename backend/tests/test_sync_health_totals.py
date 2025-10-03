import pytest
from typing import Dict, Any
from httpx import AsyncClient, Response
from repository.health_totals import health_totals_repo


def _q(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


def _reset() -> None:
    # reset in-memory repo state
    getattr(health_totals_repo, "_deltas", {}).clear()
    getattr(health_totals_repo, "_last_totals", {}).clear()
    getattr(health_totals_repo, "_idemp", {}).clear()


@pytest.mark.asyncio
async def test_first_snapshot(client: AsyncClient) -> None:
    _reset()
    q = _q(
        """
        mutation { syncHealthTotals(
            input:{
              timestamp:"2025-06-01T10:00:00Z"
              date:"2025-06-01"
              steps:120
              caloriesOut:50.5
            }
        ) {
          accepted duplicate reset
                            delta {
                                stepsDelta
                                caloriesOutDelta
                                stepsTotal
                                caloriesOutTotal
                            }
        } }
        """
    )
    r: Response = await client.post("/graphql", json={"query": q})
    res: Dict[str, Any] = r.json()["data"]["syncHealthTotals"]
    assert res["accepted"] is True and res["duplicate"] is False
    d = res["delta"]
    assert d["stepsDelta"] == 120 and d["stepsTotal"] == 120
    assert d["caloriesOutDelta"] == 50.5 and d["caloriesOutTotal"] == 50.5


@pytest.mark.asyncio
async def test_incremental_snapshot(client: AsyncClient) -> None:
    _reset()
    first = _q(
        """
            mutation { syncHealthTotals(
                input:{
                    timestamp:"2025-06-02T10:00:00Z"
                    date:"2025-06-02"
                    steps:100
                    caloriesOut:10
                }
            ) { accepted } }
            """
    )
    await client.post("/graphql", json={"query": first})
    inc = _q(
        """
            mutation { syncHealthTotals(
                input:{
                    timestamp:"2025-06-02T11:00:00Z"
                    date:"2025-06-02"
                    steps:250
                    caloriesOut:34.2
                }
                        ) {
                            accepted
                                            delta {
                                                stepsDelta
                                                caloriesOutDelta
                                                stepsTotal
                                                caloriesOutTotal
                                            }
                        } }
            """
    )
    r: Response = await client.post("/graphql", json={"query": inc})
    d: Dict[str, Any] = r.json()["data"]["syncHealthTotals"]["delta"]
    assert d["stepsDelta"] == 150 and d["stepsTotal"] == 250
    assert d["caloriesOutDelta"] == 24.2 and d["caloriesOutTotal"] == 34.2


@pytest.mark.asyncio
async def test_duplicate_snapshot(client: AsyncClient) -> None:
    _reset()
    base = _q(
        """
            mutation { syncHealthTotals(
                input:{
                    timestamp:"2025-06-03T09:00:00Z"
                    date:"2025-06-03"
                    steps:400
                    caloriesOut:80
                }
            ) { accepted } }
            """
    )
    dup = _q(
        """
            mutation { syncHealthTotals(
                input:{
                    timestamp:"2025-06-03T09:05:00Z"
                    date:"2025-06-03"
                    steps:400
                    caloriesOut:80
                }
                        ) {
                            accepted duplicate
                                            delta {
                                                stepsDelta
                                                caloriesOutDelta
                                                stepsTotal
                                                caloriesOutTotal
                                            }
                        } }
            """
    )
    await client.post("/graphql", json={"query": base})
    r: Response = await client.post("/graphql", json={"query": dup})
    res: Dict[str, Any] = r.json()["data"]["syncHealthTotals"]
    assert res["accepted"] is False and res["duplicate"] is True
    d = res["delta"]
    assert d["stepsDelta"] == 0 and d["caloriesOutDelta"] == 0.0


@pytest.mark.asyncio
async def test_idempotency_conflict(client: AsyncClient) -> None:
    _reset()
    a = _q(
        """
            mutation { syncHealthTotals(
                idempotencyKey:"K1"
                input:{
                    timestamp:"2025-06-04T08:00:00Z"
                    date:"2025-06-04"
                    steps:100
                    caloriesOut:10
                }
            ) { accepted idempotencyConflict } }
            """
    )
    b = _q(
        """
            mutation { syncHealthTotals(
                idempotencyKey:"K1"
                input:{
                    timestamp:"2025-06-04T08:05:00Z"
                    date:"2025-06-04"
                    steps:101
                    caloriesOut:10
                }
            ) { accepted idempotencyConflict } }
            """
    )
    r1: Response = await client.post("/graphql", json={"query": a})
    r2: Response = await client.post("/graphql", json={"query": b})
    assert r1.json()["data"]["syncHealthTotals"]["accepted"] is True
    assert r2.json()["data"]["syncHealthTotals"]["idempotencyConflict"] is True


@pytest.mark.asyncio
async def test_reset_detection(client: AsyncClient) -> None:
    _reset()
    base = _q(
        """
            mutation { syncHealthTotals(
                input:{
                    timestamp:"2025-06-05T09:00:00Z"
                    date:"2025-06-05"
                    steps:500
                    caloriesOut:90
                }
            ) { accepted } }
            """
    )
    dec = _q(
        """
            mutation { syncHealthTotals(
                input:{
                    timestamp:"2025-06-05T10:00:00Z"
                    date:"2025-06-05"
                    steps:200
                    caloriesOut:30
                }
                        ) {
                            accepted reset
                            delta {
                                stepsDelta
                                caloriesOutDelta
                                stepsTotal
                                caloriesOutTotal
                            }
                        } }
            """
    )
    await client.post("/graphql", json={"query": base})
    r: Response = await client.post("/graphql", json={"query": dec})
    res: Dict[str, Any] = r.json()["data"]["syncHealthTotals"]
    assert res["reset"] is True and res["accepted"] is True
    d = res["delta"]
    assert d["stepsDelta"] == 200 and d["caloriesOutDelta"] == 30


@pytest.mark.asyncio
async def test_daily_summary_integration(client: AsyncClient) -> None:
    _reset()
    s1 = _q(
        """
            mutation { syncHealthTotals(
                input:{
                    timestamp:"2025-06-06T08:00:00Z"
                    date:"2025-06-06"
                    steps:100
                    caloriesOut:10
                }
            ) { accepted } }
            """
    )
    s2 = _q(
        """
            mutation { syncHealthTotals(
                input:{
                    timestamp:"2025-06-06T09:00:00Z"
                    date:"2025-06-06"
                    steps:150
                    caloriesOut:25
                }
            ) { accepted } }
            """
    )
    await client.post("/graphql", json={"query": s1})
    await client.post("/graphql", json={"query": s2})
    q = _q(
        """
            { dailySummary(date:"2025-06-06") {
                activitySteps
                activityCaloriesOut
            } }
            """
    )
    r: Response = await client.post("/graphql", json={"query": q})
    ds: Dict[str, Any] = r.json()["data"]["dailySummary"]
    assert ds["activitySteps"] == 150  # dalte = 100 + 50
    assert ds["activityCaloriesOut"] == 25.0
