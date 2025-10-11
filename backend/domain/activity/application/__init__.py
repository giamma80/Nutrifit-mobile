"""Activity domain application services.

Orchestrazione della business logic per Activity & Health tracking:

- ActivitySyncService: gestione snapshot, delta calculation, idempotenza
- ActivityAggregationService: costruzione DailyActivitySummary
- ActivityCalculationService: (future) metriche avanzate e insights

Servizi stateless che coordinano ports/adapters senza conoscenza
dell'implementazione concreta del storage.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Dict, Any

from domain.activity.model import (
    ActivityEvent,
    HealthSnapshot,
    ActivityDelta,
    DailyActivitySummary,
)
from domain.activity.ports import ActivityEventsPort, ActivitySnapshotsPort


class ActivitySyncService:
    """Servizio per sincronizzazione snapshot e gestione idempotenza."""

    def __init__(
        self,
        events_port: ActivityEventsPort,
        snapshots_port: ActivitySnapshotsPort,
    ) -> None:
        self._events_port = events_port
        self._snapshots_port = snapshots_port

    def ingest_activity_events(
        self,
        events: List[ActivityEvent],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[int, int, List[Tuple[int, str]]]:
        """Ingest batch eventi activity con normalizzazione e dedup.

        Returns:
            (accepted_count, duplicates_count, rejected_list)
        """
        if not events:
            return 0, 0, []

        # Normalizza tutti gli eventi prima dell'ingest
        normalized_events = [event.normalized() for event in events]

        return self._events_port.ingest_events(normalized_events, idempotency_key)

    def sync_health_snapshot(
        self,
        snapshot: HealthSnapshot,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sincronizza snapshot cumulativo con delta calculation.

        Returns:
            {
                'accepted': bool,
                'duplicate': bool,
                'reset': bool,
                'idempotency_key_used': str,
                'idempotency_conflict': bool,
                'delta': ActivityDelta | None
            }
        """
        return self._snapshots_port.record_snapshot(snapshot, idempotency_key)


class ActivityAggregationService:
    """Servizio per aggregazioni e summaries giornalieri."""

    def __init__(
        self,
        events_port: ActivityEventsPort,
        snapshots_port: ActivitySnapshotsPort,
    ) -> None:
        self._events_port = events_port
        self._snapshots_port = snapshots_port

    def calculate_daily_summary(self, user_id: str, date: str) -> DailyActivitySummary:
        """Calcola riepilogo giornaliero consolidato.

        Usa snapshot/delta come fonte primaria per totali affidabili;
        eventi minuto solo per count diagnostico.
        """
        # Totali da snapshot/delta (più affidabili)
        total_steps, total_calories_out = self._snapshots_port.get_daily_totals(user_id, date)

        # Count eventi per diagnosi
        events_count = self._events_port.get_daily_events_count(user_id, date)

        return DailyActivitySummary(
            user_id=user_id,
            date=date,
            total_steps=total_steps,
            total_calories_out=total_calories_out,
            events_count=events_count,
        )

    def list_activity_deltas(
        self,
        user_id: str,
        date: str,
        after_ts: Optional[str] = None,
        limit: int = 200,
    ) -> List[ActivityDelta]:
        """Lista delta per debugging/audit trail."""
        return self._snapshots_port.list_deltas(user_id, date, after_ts, limit)


class ActivityCalculationService:
    """Servizio per calcoli e metriche derivate (future extensions)."""

    def __init__(
        self,
        events_port: ActivityEventsPort,
        snapshots_port: ActivitySnapshotsPort,
    ) -> None:
        self._events_port = events_port
        self._snapshots_port = snapshots_port

    def calculate_activity_intensity(self, user_id: str, date: str) -> Optional[float]:
        """Calcola intensità media activity per il giorno.

        Future implementation: analizza distribuzione eventi nel tempo,
        identifica picchi di attività, calcola moving averages.
        """
        # Placeholder per future implementation
        return None

    def detect_activity_patterns(
        self, user_id: str, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Rileva pattern attività su range temporale.

        Future implementation: machine learning per identificare
        routine, giorni di riposo, trends settimanali.
        """
        # Placeholder per future implementation
        return {}


# Factory functions per dependency injection semplificata


def create_activity_sync_service(
    events_port: ActivityEventsPort, snapshots_port: ActivitySnapshotsPort
) -> ActivitySyncService:
    """Factory per ActivitySyncService."""
    return ActivitySyncService(events_port, snapshots_port)


def create_activity_aggregation_service(
    events_port: ActivityEventsPort, snapshots_port: ActivitySnapshotsPort
) -> ActivityAggregationService:
    """Factory per ActivityAggregationService."""
    return ActivityAggregationService(events_port, snapshots_port)


def create_activity_calculation_service(
    events_port: ActivityEventsPort, snapshots_port: ActivitySnapshotsPort
) -> ActivityCalculationService:
    """Factory per ActivityCalculationService."""
    return ActivityCalculationService(events_port, snapshots_port)


__all__ = [
    "ActivitySyncService",
    "ActivityAggregationService",
    "ActivityCalculationService",
    "create_activity_sync_service",
    "create_activity_aggregation_service",
    "create_activity_calculation_service",
]
