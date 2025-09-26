import pytest
from httpx import AsyncClient
from app import app
from repository.meals import meal_repo
from repository.activities import activity_repo


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
    # reset activity
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
    # protein restituisce 0.0 come da implementazione
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
        # Due pasti stesso giorno
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
        # aggiungiamo alcune activity per il giorno
        ingest = _q(
            """
            mutation {
              ingestActivityEvents(
                input:[
                  { ts: \"2025-02-01T08:00:15Z\", steps: 50 }
                  { ts: \"2025-02-01T08:00:45Z\", steps: 50 }
                  { ts: \"2025-02-01T09:10:00Z\", caloriesOut: 3.2 }
                ]
                idempotencyKey: \"k1\"
              ) { accepted duplicates rejected { index reason } }
            }
            """
        )
        await ac.post("/graphql", json={"query": ingest})
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
    # Nota: ignoriamo enrichment: verifichiamo solo il conteggio pasti.
    assert ds["meals"] == 2
    assert isinstance(ds["calories"], int)
    # Activity: secondo evento stesso minuto è duplicato.
    # Steps totali 50, eventi 2.
    assert ds["activitySteps"] == 50
    assert ds["activityCaloriesOut"] == 3.2
    assert ds["activityEvents"] == 2
    # deficit = caloriesOut - caloriesIn (può essere negativo se surplus)
    assert isinstance(ds["caloriesDeficit"], int)
    assert isinstance(ds["caloriesReplenishedPercent"], int)


@pytest.mark.asyncio
async def test_daily_summary_user_isolation() -> None:
    _reset_repo()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # User default
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
        # Altro user
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
        # activity per default user
        ingest_def = _q(
            """
                        mutation {
                            ingestActivityEvents(
                                input:[
                                  { ts: \"2025-03-01T10:00:00Z\"
                                    steps:10 }
                                ]
                                idempotencyKey: \"kk1\"
                            ) { accepted }
                        }
            """
        )
        # activity per user u2
        ingest_u2 = _q(
            """
                        mutation {
                            ingestActivityEvents(
                                userId: \"u2\"
                                input:[{ts: \"2025-03-01T11:05:00Z\", steps:5}]
                                idempotencyKey: \"kk2\"
                            ) { accepted }
                        }
            """
        )
        await ac.post("/graphql", json={"query": ingest_def})
        await ac.post("/graphql", json={"query": ingest_u2})
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
    # Percentuali coerenti (0 o >0 se intake/out presenti)
    assert "caloriesDeficit" in d_def and "caloriesReplenishedPercent" in d_def
    assert "caloriesDeficit" in d_u2 and "caloriesReplenishedPercent" in d_u2


@pytest.mark.asyncio
async def test_daily_summary_surplus_and_clamp() -> None:
    """Percentuale >100 (surplus) e clamp <= 999."""
    _reset_repo()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        ingest = _q(
            """
            mutation {
              ingestActivityEvents(
                input:[
                  { ts: \"2025-04-01T07:00:00Z\" caloriesOut: 2.0 }
                ]
                idempotencyKey: \"act-low\"
              ) { accepted }
            }
            """
        )
        await ac.post("/graphql", json={"query": ingest})
        meal = _q(
            """
            mutation {
              logMeal(
                input:{
                  name: \"Mega\"
                  quantityG:300
                  timestamp: \"2025-04-01T08:00:00Z\"
                  barcode: \"123\"
                }
              ) { id }
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
    assert ds["caloriesDeficit"] == (
        ds["activityCaloriesOut"] - ds["calories"]
    )
    assert ds["caloriesReplenishedPercent"] >= 100
    assert ds["caloriesReplenishedPercent"] <= 999
