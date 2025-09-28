import pytest
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
async def test_update_meal_name_and_quantity(client) -> None:
    _reset()
    create = """
    mutation {
      logMeal(input:{name:"Pasta", quantityG:100}) {
        id name quantityG
      }
    }
    """
    r_create = await client.post("/graphql", json={"query": create})
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
    r_upd = await client.post("/graphql", json={"query": upd})
    body = r_upd.json()["data"]["updateMeal"]
    assert body["name"] == "Pasta Integrale"
    assert body["quantityG"] == 150


@pytest.mark.asyncio
async def test_delete_meal(client) -> None:
    _reset()
    create = """
    mutation { logMeal(input:{name:"Juice", quantityG:50}) { id } }
    """
    r_create = await client.post("/graphql", json={"query": create})
    meal_id = r_create.json()["data"]["logMeal"]["id"]
    delete_q = f'mutation {{ deleteMeal(id: "{meal_id}") }}'
    r_del = await client.post("/graphql", json={"query": delete_q})
    # seconda delete deve restituire false
    r_del2 = await client.post("/graphql", json={"query": delete_q})
    assert r_del.json()["data"]["deleteMeal"] is True
    assert r_del2.json()["data"]["deleteMeal"] is False
