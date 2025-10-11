"""Activity domain adapters.

Implementazioni dei ports che bridgano ai repository legacy esistenti:
- ActivityEventsAdapter → repository.activities.activity_repo
- ActivitySnapshotsAdapter → repository.health_totals.health_totals_repo

Mantiene piena backward compatibility e semantic equivalence.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any

from domain.activity.ports import ActivityEventsPort, ActivitySnapshotsPort
from domain.activity.model import (
    ActivityEvent,
    HealthSnapshot,
    ActivityDelta,
    ActivitySource as DomainActivitySource,
)


class ActivityEventsAdapter(ActivityEventsPort):
    """Adapter per eventi activity minute-level."""

    def __init__(self) -> None:
        # Import lazy per evitare circular dependency
        from repository.activities import (
            activity_repo,
            ActivityEventRecord,
            ActivitySource,
        )

        self._repo = activity_repo
        self._record_cls = ActivityEventRecord
        self._source_enum = ActivitySource

    def ingest_events(
        self,
        events: List[ActivityEvent],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[int, int, List[Tuple[int, str]]]:
        """Converti domain events → repository records e ingest."""
        repo_events = []

        for event in events:
            # Normalizza prima della conversione
            normalized_event = event.normalized()

            # Map domain source → repo source
            repo_source = self._source_enum[normalized_event.source.value]

            repo_record = self._record_cls(
                user_id=normalized_event.user_id,
                ts=normalized_event.ts,
                steps=normalized_event.steps,
                calories_out=normalized_event.calories_out,
                hr_avg=normalized_event.hr_avg,
                source=repo_source,
            )
            repo_events.append(repo_record)

        return self._repo.ingest_batch(repo_events)

    def list_events(
        self,
        user_id: str,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        limit: int = 100,
    ) -> List[ActivityEvent]:
        """Lista eventi → converti a domain objects."""
        repo_records = self._repo.list(user_id, start_ts, end_ts, limit)

        domain_events = []
        for record in repo_records:
            # Map repo source → domain source
            domain_source = DomainActivitySource(record.source.value)

            domain_event = ActivityEvent(
                user_id=record.user_id,
                ts=record.ts,
                steps=record.steps,
                calories_out=record.calories_out,
                hr_avg=record.hr_avg,
                source=domain_source,
            )
            domain_events.append(domain_event)

        return domain_events

    def get_daily_events_count(self, user_id: str, date: str) -> int:
        """Conta eventi per diagnosi."""
        stats = self._repo.get_daily_stats(user_id, date + "T00:00:00Z")
        events_count = stats.get("events_count", 0)
        return int(events_count)


class ActivitySnapshotsAdapter(ActivitySnapshotsPort):
    """Adapter per snapshot cumulativi e delta calculation."""

    def __init__(self) -> None:
        # Import lazy per evitare circular dependency
        from repository.health_totals import health_totals_repo

        self._repo = health_totals_repo

    def record_snapshot(
        self,
        snapshot: HealthSnapshot,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record snapshot → converti result."""
        result = self._repo.record_snapshot(
            user_id=snapshot.user_id,
            date=snapshot.date,
            timestamp=snapshot.timestamp,
            steps=snapshot.steps_total,
            calories_out=snapshot.calories_out_total,
            hr_avg_session=snapshot.hr_avg_session,
            idempotency_key=idempotency_key,
        )

        # Converti delta record → domain object se presente
        domain_delta = None
        if result["delta_record"]:
            repo_delta = result["delta_record"]
            domain_delta = ActivityDelta(
                user_id=repo_delta.user_id,
                date=repo_delta.date,
                timestamp=repo_delta.timestamp,
                steps_delta=repo_delta.steps_delta,
                calories_out_delta=repo_delta.calories_out_delta,
                steps_total=repo_delta.steps_total,
                calories_out_total=repo_delta.calories_out_total,
                hr_avg_session=repo_delta.hr_avg_session,
                reset=result["reset"],
                duplicate=result["duplicate"],
            )

        return {
            "accepted": result["accepted"],
            "duplicate": result["duplicate"],
            "reset": result["reset"],
            "idempotency_key_used": result["idempotency_key_used"],
            "idempotency_conflict": result["idempotency_conflict"],
            "delta": domain_delta,
        }

    def list_deltas(
        self,
        user_id: str,
        date: str,
        after_ts: Optional[str] = None,
        limit: int = 200,
    ) -> List[ActivityDelta]:
        """Lista delta → converti a domain objects."""
        repo_deltas = self._repo.list_deltas(
            user_id=user_id, date=date, after_ts=after_ts, limit=limit
        )

        domain_deltas = []
        for repo_delta in repo_deltas:
            domain_delta = ActivityDelta(
                user_id=repo_delta.user_id,
                date=repo_delta.date,
                timestamp=repo_delta.timestamp,
                steps_delta=repo_delta.steps_delta,
                calories_out_delta=repo_delta.calories_out_delta,
                steps_total=repo_delta.steps_total,
                calories_out_total=repo_delta.calories_out_total,
                hr_avg_session=repo_delta.hr_avg_session,
                reset=False,  # Non disponibile in repo record
                duplicate=(repo_delta.steps_delta == 0 and repo_delta.calories_out_delta == 0.0),
            )
            domain_deltas.append(domain_delta)

        return domain_deltas

    def get_daily_totals(self, user_id: str, date: str) -> Tuple[int, float]:
        """Aggrega totali giornalieri."""
        return self._repo.daily_totals(user_id=user_id, date=date)


__all__ = [
    "ActivityEventsAdapter",
    "ActivitySnapshotsAdapter",
]
