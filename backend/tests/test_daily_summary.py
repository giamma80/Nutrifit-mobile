import pytest
from httpx import AsyncClient
from app import app
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
async def test_daily_summary_empty_day() -> None:
    _reset_repo()
    query = _q(
        """
        { dailySummary(date: \"2025-01-10\") {
            date userId meals calories protein
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
        query = _q(
            """
            { dailySummary(date: \"2025-02-01\") { meals calories } }
            """
        )
        resp = await ac.post("/graphql", json={"query": query})
    ds = resp.json()["data"]["dailySummary"]
    # Nota: ignoriamo enrichment: verifichiamo solo il conteggio pasti.
    assert ds["meals"] == 2
    assert isinstance(ds["calories"], int)


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
        q_default = _q(
            """
            { dailySummary(date: \"2025-03-01\") { userId meals } }
            """
        )
        q_u2 = _q(
            """
            { dailySummary(date: \"2025-03-01\", userId: \"u2\") {
                userId meals
            } }
            """
        )
        r_def = await ac.post("/graphql", json={"query": q_default})
        r_u2 = await ac.post("/graphql", json={"query": q_u2})
    d_def = r_def.json()["data"]["dailySummary"]
    d_u2 = r_u2.json()["data"]["dailySummary"]
    assert d_def["userId"] == "default" and d_def["meals"] == 1
    assert d_u2["userId"] == "u2" and d_u2["meals"] == 1
