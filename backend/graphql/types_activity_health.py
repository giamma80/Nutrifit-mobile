from __future__ import annotations
from typing import Optional, List
import strawberry
from repository.activities import ActivitySource as _RepoActivitySource
from domain.shared.types import GroupByPeriod as _GroupByPeriod

# Definizione enum GraphQL per le sorgenti attività (spostata da app.py)
ActivitySource = strawberry.enum(_RepoActivitySource, name="ActivitySource")

# Enum per raggruppamento periodi (DAY, WEEK, MONTH) - condiviso con meal
GroupByPeriod = strawberry.enum(_GroupByPeriod, name="GroupByPeriod")


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


@strawberry.type
class ActivityPeriodSummary:
    """Activity aggregate summary for a period (day/week/month)."""

    period: str
    start_date: str
    end_date: str
    total_steps: int
    total_calories_out: float
    total_active_minutes: int
    avg_heart_rate: Optional[float]
    event_count: int

    @strawberry.field(description="Has any activity data")  # type: ignore[misc]
    def has_activity(self) -> bool:
        """Check if period has any activity."""
        return self.total_steps > 0 or self.event_count > 0

    @strawberry.field(description="Avg steps per day in period")  # type: ignore[misc]
    def avg_daily_steps(self) -> float:
        """Calculate average daily steps in period."""
        # Calculate days in period
        from datetime import datetime

        start = datetime.fromisoformat(self.start_date.replace("Z", "+00:00"))
        end = datetime.fromisoformat(self.end_date.replace("Z", "+00:00"))
        days = (end - start).days + 1
        return self.total_steps / days if days > 0 else 0.0


@strawberry.input
class AggregateRangeInput:
    """Input for activity aggregate range query."""

    user_id: str
    start_date: str
    end_date: str
    group_by: GroupByPeriod = GroupByPeriod.DAY


@strawberry.type
class ActivityRangeResult:
    """Result for aggregateRange query with periods and total aggregate."""

    periods: List[ActivityPeriodSummary]  # Per-period breakdown
    total: ActivityPeriodSummary  # Total aggregate across entire range


__all__ = [
    "ActivitySource",
    "GroupByPeriod",
    "ActivityMinuteInput",
    "HealthTotalsInput",
    "ActivityEvent",
    "RejectedActivityEvent",
    "IngestActivityResult",
    "HealthTotalsDelta",
    "SyncHealthTotalsResult",
    "CacheStats",
    "ActivityPeriodSummary",
    "AggregateRangeInput",
    "ActivityRangeResult",
]
