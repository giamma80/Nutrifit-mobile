"""Activity domain repository interface.

Definisce il contratto per la persistenza del dominio Activity,
seguendo lo stesso pattern di Meal e NutritionalProfile
per coerenza architetturale.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any

from domain.activity.model import (
    ActivityEvent,
    HealthSnapshot,
    ActivityDelta,
)


class IActivityRepository(ABC):
    """Repository interface per il dominio Activity.

    Unifica l'accesso a eventi activity minute-level e snapshot cumulativi.
    Sostituisce i precedenti ActivityEventsPort e ActivitySnapshotsPort
    per uniformità con gli altri domini.
    """

    # ===== Eventi Activity (minute-level) =====

    @abstractmethod
    async def ingest_events(
        self,
        events: List[ActivityEvent],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[int, int, List[Tuple[int, str]]]:
        """Ingest batch di eventi activity con deduplication.

        Args:
            events: Lista di ActivityEvent da persistere
            idempotency_key: Chiave opzionale per idempotency

        Returns:
            Tupla (accepted_count, duplicates_count, rejected_list)
            dove rejected_list contiene [(index, reason_code), ...]
        """

    @abstractmethod
    async def list_events(
        self,
        user_id: str,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        limit: int = 100,
    ) -> List[ActivityEvent]:
        """Lista eventi activity in range temporale.

        Args:
            user_id: ID utente
            start_ts: Timestamp ISO8601 inizio range (opzionale)
            end_ts: Timestamp ISO8601 fine range (opzionale)
            limit: Numero massimo di eventi da restituire

        Returns:
            Lista di ActivityEvent ordinati per timestamp
        """

    @abstractmethod
    async def get_daily_events_count(self, user_id: str, date: str) -> int:
        """Conta eventi per diagnostica.

        Args:
            user_id: ID utente
            date: Data in formato YYYY-MM-DD

        Returns:
            Numero di eventi registrati per la data specificata
        """

    # ===== Snapshot cumulativi e Delta calculation =====

    @abstractmethod
    async def record_snapshot(
        self,
        snapshot: HealthSnapshot,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra snapshot cumulativo e calcola delta vs precedente.

        Args:
            snapshot: HealthSnapshot da registrare
            idempotency_key: Chiave opzionale per idempotency

        Returns:
            Dizionario con:
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
    async def list_deltas(
        self,
        user_id: str,
        date: str,
        after_ts: Optional[str] = None,
        limit: int = 200,
    ) -> List[ActivityDelta]:
        """Lista delta per debugging/tracing.

        Args:
            user_id: ID utente
            date: Data in formato YYYY-MM-DD
            after_ts: Timestamp ISO8601 per filtrare delta successivi
            limit: Numero massimo di delta da restituire

        Returns:
            Lista di ActivityDelta ordinati per timestamp
        """

    @abstractmethod
    async def get_daily_totals(self, user_id: str, date: str) -> Tuple[int, float]:
        """Aggrega totali giornalieri da delta.

        Args:
            user_id: ID utente
            date: Data in formato YYYY-MM-DD

        Returns:
            Tupla (total_steps, total_calories_out)
        """


__all__ = ["IActivityRepository"]
