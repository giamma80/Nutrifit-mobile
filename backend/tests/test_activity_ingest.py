import pytest
from typing import Any, Dict, List
from httpx import AsyncClient, Response
from repository.activities import activity_repo


def _q(s: str) -> str:
    return " ".join(line.strip() for line in s.strip().splitlines())


def _reset_activity_repo() -> None:
    store = getattr(activity_repo, "_events_by_user", None)
    if store is not None:
        store.clear()
    dups = getattr(activity_repo, "_duplicate_keys", None)
    if dups is not None:
        dups.clear()
    batch = getattr(activity_repo, "_batch_idempo", None)
    if batch is not None:
        batch.clear()


@pytest.mark.asyncio
async def test_activity_ingest_happy_path(
    client: AsyncClient,
) -> None:
    _reset_activity_repo()
    mutation = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: "u1"
            idempotencyKey: "k-happy"
            input:[
              { ts:"2025-01-01T10:03:12Z" steps:100 source:MANUAL }
              { ts:"2025-01-01T10:05:59Z" steps:80 hrAvg:90 source:MANUAL }
            ]
          ){ accepted duplicates rejected { index reason } }
        }
        """
    )
    resp: Response = await client.post("/graphql", json={"query": mutation})
    data: Dict[str, Any] | None = resp.json()["data"].get(
        "ingestActivityEvents"
    )
    assert data is not None, resp.json()
    assert data["accepted"] == 2
    assert data["duplicates"] == 0
    assert data["rejected"] == []


@pytest.mark.asyncio
async def test_activity_ingest_duplicates_second_batch(
    client: AsyncClient,
) -> None:
    _reset_activity_repo()
    m1 = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: \"u1\"
            idempotencyKey: \"k-dup-1\"
            input:[{ ts: \"2025-01-02T09:10:45Z\" steps:50 source:MANUAL }]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    m2 = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: \"u1\"
            idempotencyKey: \"k-dup-2\"
            input:[{ ts: \"2025-01-02T09:10:00Z\" steps:50 source:MANUAL }]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    r1: Response = await client.post("/graphql", json={"query": m1})
    d1: Dict[str, Any] = r1.json()["data"]["ingestActivityEvents"]
    assert d1["accepted"] == 1 and d1["duplicates"] == 0
    r2: Response = await client.post("/graphql", json={"query": m2})
    d2: Dict[str, Any] = r2.json()["data"]["ingestActivityEvents"]
    assert d2["accepted"] == 0
    assert d2["duplicates"] == 1
    assert d2["rejected"] == []


@pytest.mark.asyncio
async def test_activity_ingest_conflict(client: AsyncClient) -> None:
    _reset_activity_repo()
    first = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: \"u1\"
            idempotencyKey: \"k-conf-1\"
            input:[{ ts: \"2025-01-03T11:00:07Z\" steps:30 source:MANUAL }]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    second_conflict = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: \"u1\"
            idempotencyKey: \"k-conf-2\"
            input:[{ ts: \"2025-01-03T11:00:00Z\" steps:35 source:MANUAL }]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    await client.post("/graphql", json={"query": first})
    r2: Response = await client.post(
        "/graphql", json={"query": second_conflict}
    )
    d2: Dict[str, Any] = r2.json()["data"]["ingestActivityEvents"]
    assert d2["accepted"] == 0 and d2["duplicates"] == 0
    assert len(d2["rejected"]) == 1
    assert d2["rejected"][0]["reason"] == "CONFLICT_DIFFERENT_DATA"


@pytest.mark.asyncio
async def test_activity_ingest_normalization_duplicate_via_seconds(
    client: AsyncClient,
) -> None:
    _reset_activity_repo()
    m1 = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: "u1"
            idempotencyKey: "k-norm-1"
            input:[{ ts: "2025-01-04T06:15:47Z" steps:10 source:MANUAL }]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    m2 = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: "u1"
            idempotencyKey: "k-norm-2"
            input:[{ ts: "2025-01-04T06:15:00Z" steps:10 source:MANUAL }]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    r1: Response = await client.post("/graphql", json={"query": m1})
    assert r1.json()["data"]["ingestActivityEvents"]["accepted"] == 1
    r2: Response = await client.post("/graphql", json={"query": m2})
    d2: Dict[str, Any] = r2.json()["data"]["ingestActivityEvents"]
    assert d2["accepted"] == 0 and d2["duplicates"] == 1


@pytest.mark.asyncio
async def test_activity_ingest_invalid_values(client: AsyncClient) -> None:
    _reset_activity_repo()
    m = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: "u1"
            idempotencyKey: "k-invalid"
            input:[
              { ts: "BAD_TS" steps:10 source:MANUAL }
              { ts: "2025-01-05T08:00:03Z" steps:-5 source:MANUAL }
              { ts: "2025-01-05T08:01:03Z" steps:5 hrAvg:3000 source:MANUAL }
            ]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    r: Response = await client.post("/graphql", json={"query": m})
    d: Dict[str, Any] = r.json()["data"]["ingestActivityEvents"]
    assert d["accepted"] == 0
    reasons = sorted([x["reason"] for x in d["rejected"]])
    assert set(reasons) >= {
        "NORMALIZATION_FAILED",
        "NEGATIVE_VALUE",
        "OUT_OF_RANGE_HR",
    }


@pytest.mark.asyncio
async def test_activity_ingest_idempotency_cache_and_conflict(
    client: AsyncClient,
) -> None:
    _reset_activity_repo()
    batch1 = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: "u1"
            idempotencyKey: "k-idem"
            input:[{ ts: "2025-01-06T09:10:10Z" steps:42 source:MANUAL }]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    batch1_repeat_same = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: "u1"
            idempotencyKey: "k-idem"
            input:[{ ts: "2025-01-06T09:10:44Z" steps:42 source:MANUAL }]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    batch_conflict = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: "u1"
            idempotencyKey: "k-idem"
            input:[{ ts: "2025-01-06T09:10:10Z" steps:43 source:MANUAL }]
          ) { accepted duplicates rejected { index reason } }
        }
        """
    )
    r1: Response = await client.post("/graphql", json={"query": batch1})
    d1: Dict[str, Any] = r1.json()["data"]["ingestActivityEvents"]
    assert d1["accepted"] == 1
    r2: Response = await client.post(
        "/graphql", json={"query": batch1_repeat_same}
    )
    d2: Dict[str, Any] = r2.json()["data"]["ingestActivityEvents"]
    assert d2["accepted"] == 1 and d2["duplicates"] == 0
    r3: Response = await client.post(
        "/graphql", json={"query": batch_conflict}
    )
    body3: Dict[str, Any] = r3.json()
    assert body3.get("errors"), body3


@pytest.mark.asyncio
async def test_activity_ingest_auto_idempotency_key(
    client: AsyncClient,
) -> None:
    """Auto-generate e riuso deterministico della chiave idempotenza."""
    _reset_activity_repo()
    mutation_first = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: "u1"
            input:[
              { ts:"2025-01-07T07:00:15Z" steps:10 source:MANUAL }
              { ts:"2025-01-07T07:01:45Z" steps:5 source:MANUAL }
            ]
          ){ accepted duplicates rejected { index reason } idempotencyKeyUsed }
        }
        """
    )
    mutation_second_same = mutation_first
    mutation_changed = _q(
        """
        mutation {
          ingestActivityEvents(
            userId: "u1"
            input:[
              { ts:"2025-01-07T07:00:15Z" steps:11 source:MANUAL }
              { ts:"2025-01-07T07:01:45Z" steps:5 source:MANUAL }
            ]
          ){ accepted duplicates rejected { index reason } idempotencyKeyUsed }
        }
        """
    )
    r1: Response = await client.post(
        "/graphql", json={"query": mutation_first}
    )
    d1: Dict[str, Any] = r1.json()["data"]["ingestActivityEvents"]
    assert d1["accepted"] == 2 and d1["duplicates"] == 0
    auto_key = d1["idempotencyKeyUsed"]
    assert auto_key and auto_key.startswith("auto-")
    r2: Response = await client.post(
        "/graphql", json={"query": mutation_second_same}
    )
    d2: Dict[str, Any] = r2.json()["data"]["ingestActivityEvents"]
    assert d2["accepted"] == 2 and d2["duplicates"] == 0
    assert d2["idempotencyKeyUsed"] == auto_key
    r3: Response = await client.post(
        "/graphql", json={"query": mutation_changed}
    )
    d3: Dict[str, Any] = r3.json()["data"]["ingestActivityEvents"]
    assert d3["accepted"] == 0 and d3["duplicates"] == 1
    reasons: List[str] = [r["reason"] for r in d3["rejected"]]
    assert "CONFLICT_DIFFERENT_DATA" in reasons
    assert d3["idempotencyKeyUsed"].startswith("auto-")
    assert d3["idempotencyKeyUsed"] != auto_key
