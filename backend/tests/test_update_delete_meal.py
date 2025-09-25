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
async def test_update_meal_name_and_quantity() -> None:
    _reset()
    create = """
    mutation {
      logMeal(input:{name:"Pasta", quantityG:100}) {
        id name quantityG
      }
    }
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r_create = await ac.post("/graphql", json={"query": create})
    meal_id = r_create.json()["data"]["logMeal"]["id"]
    upd = f"""
        mutation {{
            updateMeal(
                input:{{
                    id:\"{meal_id}\"
                    name:\"Pasta Integrale\"
                    quantityG:150
                }}
            ) {{
        id name quantityG
      }}
    }}
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r_upd = await ac.post("/graphql", json={"query": upd})
    body = r_upd.json()["data"]["updateMeal"]
    assert body["name"] == "Pasta Integrale"
    assert body["quantityG"] == 150


@pytest.mark.asyncio
async def test_delete_meal() -> None:
    _reset()
    create = """
    mutation { logMeal(input:{name:"Juice", quantityG:50}) { id } }
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r_create = await ac.post("/graphql", json={"query": create})
    meal_id = r_create.json()["data"]["logMeal"]["id"]
    delete_q = f'mutation {{ deleteMeal(id: "{meal_id}") }}'
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r_del = await ac.post("/graphql", json={"query": delete_q})
        # seconda delete deve restituire false
        r_del2 = await ac.post("/graphql", json={"query": delete_q})
    assert r_del.json()["data"]["deleteMeal"] is True
    assert r_del2.json()["data"]["deleteMeal"] is False
