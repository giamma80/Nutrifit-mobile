from __future__ import annotations
from typing import Optional, List
import strawberry
from repository.activities import ActivitySource as _RepoActivitySource

# Definizione enum GraphQL per le sorgenti attività (spostata da app.py)
ActivitySource = strawberry.enum(_RepoActivitySource, name="ActivitySource")


@strawberry.type
class ActivityEvent:
    user_id: str
    ts: str
    steps: Optional[int] = None
    calories_out: Optional[float] = None
    hr_avg: Optional[float] = None
    # Annotiamo con l'enum originale per evitare warning type checker
    source: _RepoActivitySource = strawberry.field(default=_RepoActivitySource.MANUAL)


@strawberry.type
class RejectedActivityEvent:
    index: int
    reason: str


@strawberry.type
class IngestActivityResult:
    accepted: int
    duplicates: int
    rejected: List[RejectedActivityEvent]
    idempotency_key_used: Optional[str] = None


@strawberry.type
class HealthTotalsDelta:
    id: str
    user_id: str
    date: str
    timestamp: str
    steps_delta: int
    calories_out_delta: float
    steps_total: int
    calories_out_total: float
    hr_avg_session: Optional[float] = None


@strawberry.type
class SyncHealthTotalsResult:
    accepted: bool
    duplicate: bool
    reset: bool
    idempotency_key_used: Optional[str]
    idempotency_conflict: bool
    delta: Optional[HealthTotalsDelta]


@strawberry.type
class CacheStats:
    keys: int
    hits: int
    misses: int


__all__ = [
    "ActivitySource",
    "ActivityEvent",
    "RejectedActivityEvent",
    "IngestActivityResult",
    "HealthTotalsDelta",
    "SyncHealthTotalsResult",
    "CacheStats",
]
