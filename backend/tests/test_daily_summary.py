import pytest
from httpx import AsyncClient
from app import app, Product
from repository.meals import meal_repo
from repository.activities import activity_repo
from cache import cache


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
    act_events = getattr(activity_repo, "_events_by_user", None)
    if act_events is not None:
        act_events.clear()
    dup = getattr(activity_repo, "_duplicate_keys", None)
    if dup is not None:
        dup.clear()
    batch = getattr(activity_repo, "_batch_idempo", None)
    if batch is not None:
        batch.clear()


@pytest.mark.asyncio
async def test_daily_summary_empty_day() -> None:
    _reset_repo()
    query = _q(
        """
        { dailySummary(date: \"2025-01-10\") {
            date
            userId
            meals
            calories
            protein
            activitySteps
            activityCaloriesOut
            activityEvents
            caloriesDeficit
            caloriesReplenishedPercent
        } }
        """
    )
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/graphql", json={"query": query})
    data = resp.json()["data"]["dailySummary"]
    assert data["date"] == "2025-01-10"
    assert data["meals"] == 0
    assert data["calories"] == 0
    assert data["protein"] == 0.0
    assert data["activitySteps"] == 0
    assert data["activityCaloriesOut"] == 0.0
    assert data["activityEvents"] == 0
    assert data["caloriesDeficit"] == 0
    assert data["caloriesReplenishedPercent"] == 0


@pytest.mark.asyncio
async def test_daily_summary_aggregation() -> None:
    _reset_repo()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        m1 = _q(
            """
            mutation {
                logMeal(
                    input:{
                        name:\"A\"
                        quantityG:100
                        timestamp:\"2025-02-01T08:00:00Z\"
                        barcode:\"123\"
                    }
                ) { id }
            }
            """
        )
        m2 = _q(
            """
            mutation {
                logMeal(
                    input:{
                        name:\"B\"
                        quantityG:50
                        timestamp:\"2025-02-01T09:00:00Z\"
                        barcode:\"123\"
                    }
                ) { id }
            }
            """
        )
        await ac.post("/graphql", json={"query": m1})
        await ac.post("/graphql", json={"query": m2})
        # Impostiamo i totali activity tramite nuova mutation syncHealthTotals
        sync = _q(
            """
            mutation {
                syncHealthTotals(
                    input:{
                        timestamp: \"2025-02-01T09:15:00Z\"
                        date: \"2025-02-01\"
                        steps: 50
                        caloriesOut: 3.2
                    }
                ) { accepted duplicate reset }
            }
            """
        )
        await ac.post("/graphql", json={"query": sync})
        query = _q(
            """
            { dailySummary(date: \"2025-02-01\") {
                meals
                calories
                activitySteps
                activityCaloriesOut
                activityEvents
                caloriesDeficit
                caloriesReplenishedPercent
            } }
            """
        )
        resp = await ac.post("/graphql", json={"query": query})
    ds = resp.json()["data"]["dailySummary"]
    assert ds["meals"] == 2
    assert isinstance(ds["calories"], int)
    assert ds["activitySteps"] == 50
    assert ds["activityCaloriesOut"] == 3.2
    # Con la nuova fonte i totali provengono da syncHealthTotals; non abbiamo
    # inserito minute events quindi gli eventi risultano 0.
    assert ds["activityEvents"] == 0
    assert isinstance(ds["caloriesDeficit"], int)
    assert isinstance(ds["caloriesReplenishedPercent"], int)


@pytest.mark.asyncio
async def test_daily_summary_user_isolation() -> None:
    _reset_repo()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        m1 = _q(
            """
            mutation {
                logMeal(
                    input:{
                        name:\"A\"
                        quantityG:80
                        timestamp:\"2025-03-01T10:00:00Z\"
                    }
                ) { id }
            }
            """
        )
        m2 = _q(
            """
            mutation {
                logMeal(
                    input:{
                        name:\"B\"
                        userId:\"u2\"
                        quantityG:40
                        timestamp:\"2025-03-01T11:00:00Z\"
                    }
                ) { id }
            }
            """
        )
        await ac.post("/graphql", json={"query": m1})
        await ac.post("/graphql", json={"query": m2})
        # Impostiamo snapshot distinti per due utenti
        sync_def = _q(
            """
            mutation {
                syncHealthTotals(
                    input:{
                        timestamp: \"2025-03-01T10:10:00Z\"
                        date: \"2025-03-01\"
                        steps: 10
                        caloriesOut: 1.0
                    }
                ) { accepted }
            }
            """
        )
        sync_u2 = _q(
            """
            mutation {
                syncHealthTotals(
                    userId: \"u2\"
                    input:{
                        timestamp: \"2025-03-01T11:10:00Z\"
                        date: \"2025-03-01\"
                        steps: 5
                        caloriesOut: 0.5
                    }
                ) { accepted }
            }
            """
        )
        await ac.post("/graphql", json={"query": sync_def})
        await ac.post("/graphql", json={"query": sync_u2})
        q_default = _q(
            """
            { dailySummary(date: \"2025-03-01\") {
                userId
                meals
                activitySteps
                caloriesDeficit
                caloriesReplenishedPercent
            } }
            """
        )
        q_u2 = _q(
            """
            { dailySummary(date: \"2025-03-01\", userId: \"u2\") {
                userId
                meals
                activitySteps
                caloriesDeficit
                caloriesReplenishedPercent
            } }
            """
        )
        r_def = await ac.post("/graphql", json={"query": q_default})
        r_u2 = await ac.post("/graphql", json={"query": q_u2})
    d_def = r_def.json()["data"]["dailySummary"]
    d_u2 = r_u2.json()["data"]["dailySummary"]
    assert d_def["userId"] == "default" and d_def["meals"] == 1
    assert d_u2["userId"] == "u2" and d_u2["meals"] == 1
    assert d_def["activitySteps"] == 10
    assert d_u2["activitySteps"] == 5
    assert "caloriesDeficit" in d_def and "caloriesReplenishedPercent" in d_def
    assert "caloriesDeficit" in d_u2 and "caloriesReplenishedPercent" in d_u2


@pytest.mark.asyncio
async def test_daily_summary_surplus_and_clamp() -> None:
    _reset_repo()
    synthetic = Product(
        barcode="SURPLUS1",
        name="Mega Synthetic",
        brand=None,
        category=None,
        calories=500,
        protein=10.0,
        carbs=50.0,
        fat=20.0,
        fiber=5.0,
        sugar=25.0,
        sodium=200.0,
    )
    cache.set("product:SURPLUS1", synthetic, 600)
    async with AsyncClient(app=app, base_url="http://test") as ac:
        sync = _q(
            """
            mutation {
                syncHealthTotals(
                    input:{
                        timestamp: \"2025-04-01T07:05:00Z\"
                        date: \"2025-04-01\"
                        steps: 0
                        caloriesOut: 2.0
                    }
                ) { accepted }
            }
            """
        )
        await ac.post("/graphql", json={"query": sync})
        meal = _q(
            """
            mutation {
                logMeal(
                    input:{
                        name: \"MegaBar\"
                        quantityG:300
                        timestamp: \"2025-04-01T08:00:00Z\"
                        barcode: \"SURPLUS1\"
                    }
                ) { id calories }
            }
            """
        )
        await ac.post("/graphql", json={"query": meal})
        query = _q(
            """
            { dailySummary(date: \"2025-04-01\") {
                calories
                activityCaloriesOut
                caloriesDeficit
                caloriesReplenishedPercent
            } }
            """
        )
        resp = await ac.post("/graphql", json={"query": query})
    ds = resp.json()["data"]["dailySummary"]
    assert ds["activityCaloriesOut"] == 2.0
    assert isinstance(ds["calories"], int)
    assert ds["caloriesDeficit"] == (ds["activityCaloriesOut"] - ds["calories"])
    assert ds["caloriesReplenishedPercent"] == 999
