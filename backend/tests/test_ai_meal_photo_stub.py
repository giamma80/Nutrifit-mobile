import pytest
from httpx import AsyncClient
from app import app


def _q(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


@pytest.mark.asyncio
async def test_analyze_meal_photo_basic() -> None:
    mutation = _q(
        """
        mutation {
          analyzeMealPhoto(input:{photoId:"ph1"}) {
            id status items { label confidence quantityG calories }
            idempotencyKeyUsed
          }
        }
        """
    )
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/graphql", json={"query": mutation})
    data = r.json()["data"]["analyzeMealPhoto"]
    assert data["status"] == "COMPLETED"
    assert len(data["items"]) == 2
    labels = {it["label"] for it in data["items"]}
    assert {"Insalata mista", "Petto di pollo"} == labels


@pytest.mark.asyncio
async def test_analyze_idempotent_same_key() -> None:
    mutation = _q(
        'mutation { analyzeMealPhoto(input:{photoId:"same", '
        'idempotencyKey:"AIK1"}) { id items { label } } }'
    )
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r1 = await ac.post("/graphql", json={"query": mutation})
        r2 = await ac.post("/graphql", json={"query": mutation})
    a1 = r1.json()["data"]["analyzeMealPhoto"]
    a2 = r2.json()["data"]["analyzeMealPhoto"]
    assert a1["id"] == a2["id"]
    assert a1["items"] == a2["items"]


@pytest.mark.asyncio
async def test_confirm_creates_meals_and_is_idempotent() -> None:
    analyze = _q(
        'mutation { analyzeMealPhoto(input:{photoId:"conf1", '
        'idempotencyKey:"AKCONF"}) { id items { label } } }'
    )
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/graphql", json={"query": analyze})
        analysis_id = r.json()["data"]["analyzeMealPhoto"]["id"]
        confirm = _q(
            f'mutation {{ confirmMealPhoto(input:{{analysisId:"{analysis_id}", '
            'acceptedIndexes:[0,1]}}) {{ analysisId createdMeals '
            '{{ name calories quantityG }} }} }}'
        )
        first = await ac.post("/graphql", json={"query": confirm})
        second = await ac.post("/graphql", json={"query": confirm})
    d1 = first.json()["data"]["confirmMealPhoto"]
    d2 = second.json()["data"]["confirmMealPhoto"]
    assert d1["analysisId"] == analysis_id
    # Idempotenza: stessi due pasti, non duplicati
    assert len(d1["createdMeals"]) == 2
    assert {m["name"] for m in d1["createdMeals"]} == {
        m["name"] for m in d2["createdMeals"]
    }


@pytest.mark.asyncio
async def test_confirm_invalid_index() -> None:
    analyze = _q(
        'mutation { analyzeMealPhoto(input:{photoId:"err1"}) { id } }'
    )
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/graphql", json={"query": analyze})
        analysis_id = r.json()["data"]["analyzeMealPhoto"]["id"]
        bad = _q(
            f'mutation {{ confirmMealPhoto(input:{{analysisId:"{analysis_id}", '
            'acceptedIndexes:[5]}}) {{ analysisId }} }}'
        )
        resp = await ac.post("/graphql", json={"query": bad})
    errs = resp.json().get("errors")
    assert errs and any("INVALID_INDEX" in e.get("message", "") for e in errs)
