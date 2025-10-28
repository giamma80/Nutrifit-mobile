from __future__ import annotations
from typing import Optional, List
import strawberry
from repository.activities import ActivitySource as _RepoActivitySource

# Definizione enum GraphQL per le sorgenti attività (spostata da app.py)
ActivitySource = strawberry.enum(_RepoActivitySource, name="ActivitySource")


@strawberry.input
class ActivityMinuteInput:
    """Input for minute-level activity event."""

    ts: str  # DateTime as string, will be normalized to minute precision
    steps: Optional[int] = 0
    calories_out: Optional[float] = None
    hr_avg: Optional[float] = None
    # Enum GraphQL (repo enum esposto) default MANUAL
    source: ActivitySource = ActivitySource.MANUAL


@strawberry.input
class HealthTotalsInput:
    """Input for health totals snapshot."""

    timestamp: str
    date: str
    steps: int
    calories_out: float
    hr_avg_session: Optional[float] = None
    user_id: Optional[str] = None


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
    "ActivityMinuteInput",
    "HealthTotalsInput",
    "ActivityEvent",
    "RejectedActivityEvent",
    "IngestActivityResult",
    "HealthTotalsDelta",
    "SyncHealthTotalsResult",
    "CacheStats",
]
