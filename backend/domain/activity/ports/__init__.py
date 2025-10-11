"""Activity domain ports (interfaces).

Definisce i contratti per l'accesso ai dati senza dipendere dall'implementazione
specifica. Gli adapter implementeranno queste interfacce bridging ai repository
legacy (activity_repo, health_totals_repo).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any

from domain.activity.model import (
    ActivityEvent,
    HealthSnapshot,
    ActivityDelta,
)


class ActivityEventsPort(ABC):
    """Port per accesso agli eventi activity minute-level."""

    @abstractmethod
    def ingest_events(
        self,
        events: List[ActivityEvent],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[int, int, List[Tuple[int, str]]]:
        """Ingest batch eventi con deduplication.

        Returns:
            (accepted_count, duplicates_count, rejected_list)
            rejected_list: [(index, reason_code), ...]
        """

    @abstractmethod
    def list_events(
        self,
        user_id: str,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        limit: int = 100,
    ) -> List[ActivityEvent]:
        """Lista eventi activity in range temporale."""

    @abstractmethod
    def get_daily_events_count(self, user_id: str, date: str) -> int:
        """Conta eventi per diagnostica (usato in DailyActivitySummary)."""


class ActivitySnapshotsPort(ABC):
    """Port per gestione snapshot cumulativi e delta calculation."""

    @abstractmethod
    def record_snapshot(
        self,
        snapshot: HealthSnapshot,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra snapshot e calcola delta vs precedente.

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

    @abstractmethod
    def list_deltas(
        self,
        user_id: str,
        date: str,
        after_ts: Optional[str] = None,
        limit: int = 200,
    ) -> List[ActivityDelta]:
        """Lista delta per debugging/tracing."""

    @abstractmethod
    def get_daily_totals(self, user_id: str, date: str) -> Tuple[int, float]:
        """Aggrega totali giornalieri da delta.

        Returns:
            (total_steps, total_calories_out)
        """


__all__ = [
    "ActivityEventsPort",
    "ActivitySnapshotsPort",
]
