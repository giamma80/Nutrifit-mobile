"""Activity repository abstraction (in-memory implementation).

Obiettivo: gestione eventi activity minuto + aggregazioni future.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import bisect
import datetime
from enum import Enum


class ActivitySource(str, Enum):
    """Enum per sorgenti activity (duplicazione locale del GraphQL enum)."""

    APPLE_HEALTH = "APPLE_HEALTH"
    GOOGLE_FIT = "GOOGLE_FIT"
    MANUAL = "MANUAL"


@dataclass(slots=True)
class ActivityEventRecord:
    user_id: str
    ts: str  # ISO8601 Z normalizzato a minuto UTC
    steps: Optional[int] = None
    calories_out: Optional[float] = None
    hr_avg: Optional[float] = None
    source: ActivitySource = ActivitySource.MANUAL

    def sort_key(self) -> str:
        # Usato per ordinamento (timestamp ascendente per activity timeline)
        return self.ts

    def duplicate_key(self) -> Tuple[str, str]:
        """Key per identificare duplicati: (user_id, ts)."""
        return (self.user_id, self.ts)


class ActivityRepository:
    """Interfaccia minima futura (per DB adapter).

    Per ora forniamo solo l'implementazione in-memory.
    """

    def ingest_batch(
        self, events: List[ActivityEventRecord]
    ) -> Tuple[int, int, List[Tuple[int, str]]]:  # pragma: no cover
        """Ingest batch di eventi activity.

        Returns:
            (accepted_count, duplicates_count, rejected_list)
            rejected_list: [(index, reason), ...]
        """
        raise NotImplementedError

    def get_daily_stats(self, user_id: str, date: str) -> Dict[str, Any]:  # pragma: no cover
        """Aggrega stats activity per giorno specifico.

        Returns:
            {"total_steps": int, "total_calories_out": float,
             "events_count": int}
        """
        raise NotImplementedError


class InMemoryActivityRepository(ActivityRepository):
    """Implementazione in-memory del repository activity."""

    def __init__(self) -> None:
        # Storing events sorted by timestamp for efficient range queries
        # Key: user_id, Value: List[ActivityEventRecord] (sorted by ts)
        self._events_by_user: Dict[str, List[ActivityEventRecord]] = {}
        # Track duplicates by composite key for idempotency
        self._duplicate_keys: Dict[Tuple[str, str], ActivityEventRecord] = {}
        # Batch idempotency map: (user_id, key) -> (signature, cached_result)
        self._batch_idempo: Dict[Tuple[str, str], Tuple[str, Dict[str, Any]]] = {}

    # Reason codes constants
    INVALID_EVENT = "INVALID_EVENT"
    NEGATIVE_VALUE = "NEGATIVE_VALUE"
    OUT_OF_RANGE_HR = "OUT_OF_RANGE_HR"
    NORMALIZATION_FAILED = "NORMALIZATION_FAILED"
    CONFLICT_DIFFERENT_DATA = "CONFLICT_DIFFERENT_DATA"

    @staticmethod
    def normalize_minute_iso(ts: str) -> Optional[str]:
        """Normalizza a minuto UTC (YYYY-MM-DDTHH:MM:00Z)."""
        try:
            if ts.endswith("Z"):
                dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                dt = datetime.datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            dt = dt.astimezone(datetime.timezone.utc)
            dt = dt.replace(second=0, microsecond=0)
            return dt.isoformat().replace("+00:00", "Z")
        except ValueError:
            return None

    def ingest_batch(
        self, events: List[ActivityEventRecord]
    ) -> Tuple[int, int, List[Tuple[int, str]]]:
        """Ingest batch di eventi activity con deduplication e normalizzazione.

        Ritorna: (accepted, duplicates, [(index, reason_code), ...])
        """
        accepted = 0
        duplicates = 0
        rejected: List[Tuple[int, str]] = []

        for i, ev in enumerate(events):
            # Valori negativi
            if ev.steps is not None and ev.steps < 0:
                rejected.append((i, self.NEGATIVE_VALUE))
                continue
            if ev.calories_out is not None and ev.calories_out < 0:
                rejected.append((i, self.NEGATIVE_VALUE))
                continue
            if ev.hr_avg is not None:
                try:
                    hr = int(round(float(ev.hr_avg)))
                except (TypeError, ValueError):
                    rejected.append((i, self.INVALID_EVENT))
                    continue
                if hr < 25 or hr > 240:
                    rejected.append((i, self.OUT_OF_RANGE_HR))
                    continue
                ev.hr_avg = float(hr)

            if not ev.user_id or not ev.ts:
                rejected.append((i, self.INVALID_EVENT))
                continue

            norm = self.normalize_minute_iso(ev.ts)
            if not norm:
                rejected.append((i, self.NORMALIZATION_FAILED))
                continue
            ev.ts = norm

            key = ev.duplicate_key()
            existing = self._duplicate_keys.get(key)
            if existing:
                if self._events_identical(existing, ev):
                    duplicates += 1
                    continue
                rejected.append((i, self.CONFLICT_DIFFERENT_DATA))
                continue

            self._add_event(ev)
            accepted += 1

        return accepted, duplicates, rejected

    def get_daily_stats(self, user_id: str, date: str) -> Dict[str, Any]:
        """Aggrega stats activity per giorno specifico (UTC)."""
        if user_id not in self._events_by_user:
            return {"total_steps": 0, "total_calories_out": 0.0, "events_count": 0}

        # Parse date and create range
        try:
            dt = datetime.datetime.fromisoformat(date.replace("Z", "+00:00"))
            start_of_day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + datetime.timedelta(days=1)

            start_ts = start_of_day.isoformat().replace("+00:00", "Z")
            end_ts = end_of_day.isoformat().replace("+00:00", "Z")
        except ValueError:
            return {"total_steps": 0, "total_calories_out": 0.0, "events_count": 0}

        events = self.list(user_id, start_ts, end_ts, limit=10000)
        total_steps = 0
        total_calories_out = 0.0
        for event in events:
            if event.steps:
                total_steps += event.steps
            if event.calories_out:
                total_calories_out += event.calories_out
        return {
            "total_steps": total_steps,
            "total_calories_out": round(total_calories_out, 2),
            "events_count": len(events),
        }

    def list(
        self,
        user_id: str,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        limit: int = 100,
    ) -> List[ActivityEventRecord]:
        data = self._events_by_user.get(user_id)
        if not data:
            return []
        res: List[ActivityEventRecord] = []
        for ev in data:
            if start_ts and ev.ts < start_ts:
                continue
            if end_ts and ev.ts >= end_ts:
                continue
            res.append(ev)
            if len(res) >= limit:
                break
        return res

    def list_events(
        self,
        user_id: str,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        limit: int = 10000,
    ) -> List[ActivityEventRecord]:
        """List activity events for user within time range.

        Implementation delegates to list() method.
        """
        return self.list(user_id, start_ts, end_ts, limit)

    def list_all(self, user_id: str) -> List[ActivityEventRecord]:
        return list(self._events_by_user.get(user_id, []))

    def _validate_event(self, event: ActivityEventRecord) -> bool:
        """Valida i dati di un evento activity."""
        if not event.user_id or not event.ts:
            return False

        # Validate steps (if provided)
        if event.steps is not None and event.steps < 0:
            return False

        # Validate calories_out (if provided)
        if event.calories_out is not None and event.calories_out < 0:
            return False

        # Validate hr_avg (if provided)
        if event.hr_avg is not None and (event.hr_avg < 0 or event.hr_avg > 300):
            return False

        return True

    def _events_identical(self, a: ActivityEventRecord, b: ActivityEventRecord) -> bool:
        """Verifica se due eventi sono identici (per deduplication)."""
        return (
            a.user_id == b.user_id
            and a.ts == b.ts
            and a.steps == b.steps
            and a.calories_out == b.calories_out
            and a.hr_avg == b.hr_avg
            and a.source == b.source
        )

    def _add_event(self, event: ActivityEventRecord) -> None:
        """Aggiunge un evento mantenendo l'ordinamento per timestamp."""
        user_id = event.user_id

        if user_id not in self._events_by_user:
            self._events_by_user[user_id] = []

        # Insert in sorted order (by timestamp)
        events = self._events_by_user[user_id]
        bisect.insort(events, event, key=lambda e: e.sort_key())

        # Track for duplicates
        self._duplicate_keys[event.duplicate_key()] = event

    def get_idempotency(self, key: str) -> Optional[str]:
        """Recupera la signature cached per una chiave di idempotenza.

        Returns:
            signature string se presente, None altrimenti
        """
        # La chiave completa include user_id, ma per semplicità
        # cerchiamo tra tutte le chiavi che terminano con il nostro key
        for (_, k), (sig, _) in self._batch_idempo.items():
            if k == key:
                return sig
        return None

    def store_idempotency(self, key: str, signature: str, ttl_seconds: int = 86400) -> None:
        """Salva una signature per una chiave di idempotenza.

        Args:
            key: chiave di idempotenza
            signature: signature del payload
            ttl_seconds: TTL in secondi (ignorato in implementazione in-memory)
        """
        # Per l'implementazione in-memory, usiamo un user_id fittizio
        # In una implementazione reale con DB, useremmo il TTL
        user_key = ("__global__", key)
        # Salviamo signature e un dict vuoto come result placeholder
        self._batch_idempo[user_key] = (signature, {})


# Global instance (singleton pattern come meal_repo)
activity_repo = InMemoryActivityRepository()
