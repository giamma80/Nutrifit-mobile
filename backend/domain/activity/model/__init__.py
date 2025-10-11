"""Activity domain models.

Contiene Value Objects immutabili e strutture aggregate usate dai servizi
applicativi per unificare la doppia sorgente dati corrente:

  * Minute-level events (repository.activities)
  * Cumulative snapshots + deltas (repository.health_totals)

Obiettivi principali del modelling:
  * Normalizzazione timestamp a precisione minuto per ActivityEvent
  * Rappresentazione semantica di uno snapshot cumulativo (HealthSnapshot)
  * Espressione di un delta calcolato (ActivityDelta) con flag reset/duplicate
  * Riepilogo giornaliero consolidato (DailyActivitySummary) che astragga
    l'origine (event vs snapshot) mantenendo compat retro con GraphQL.

Nota: la logica di calcolo/delta detection resta nei servizi application;
qui solo invariants leggeri e helper di normalizzazione.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import datetime as _dt


class ActivitySource(str, Enum):
    """Fonte dell'evento activity.

    Duplicata (nominalmente) rispetto a repository.activities.ActivitySource per
    disaccoppiare il dominio dal dettaglio infrastrutturale ed evitare import
    ciclici nelle future adapter implementations.
    """

    APPLE_HEALTH = "APPLE_HEALTH"
    GOOGLE_FIT = "GOOGLE_FIT"
    MANUAL = "MANUAL"


def _normalize_minute_iso(ts: str) -> str:
    """Normalizza una stringa ISO8601 alla precisione minuto UTC.

    Se parsing fallisce ritorna la stringa originale (decisione fail-soft; la
    validazione formale avverrà nei servizi o adapter)."""
    try:
        # Supporta suffisso Z oppure offset esplicito
        if ts.endswith("Z"):
            dt = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            dt = _dt.datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_dt.timezone.utc)
        dt = dt.astimezone(_dt.timezone.utc)
        dt = dt.replace(second=0, microsecond=0)
        return dt.isoformat().replace("+00:00", "Z")
    except ValueError:
        return ts  # fail-soft


@dataclass(slots=True, frozen=True)
class ActivityEvent:
    """Evento activity minuto (o granularità coerente >= minuto).

    Invarianti leggeri:
      * steps >= 0 se presente
      * calories_out >= 0 se presente
      * hr_avg nel range plausibile (25..240) se presente
    (La violazione non lancia eccezione qui: i servizi di ingest possono
    filtrare; qui possiamo permettere creazione 'loose' per favorire mapping.)
    """

    user_id: str
    ts: str
    steps: Optional[int] = None
    calories_out: Optional[float] = None
    hr_avg: Optional[float] = None
    source: ActivitySource = ActivitySource.MANUAL

    def normalized(self) -> "ActivityEvent":
        """Ritorna una copia con timestamp normalizzato a minuto UTC."""
        norm = _normalize_minute_iso(self.ts)
        if norm == self.ts:
            return self
        return ActivityEvent(
            user_id=self.user_id,
            ts=norm,
            steps=self.steps,
            calories_out=self.calories_out,
            hr_avg=self.hr_avg,
            source=self.source,
        )


@dataclass(slots=True, frozen=True)
class HealthSnapshot:
    """Snapshot cumulativo (steps/calories_out) per un determinato giorno.

    Rappresenta l'input 'grezzo' della mutation syncHealthTotals.
    """

    user_id: str
    date: str  # YYYY-MM-DD
    timestamp: str  # ISO8601 full precision
    steps_total: int
    calories_out_total: float
    hr_avg_session: Optional[float] = None

    def key(self) -> tuple[str, str]:  # per raggruppamento
        return self.user_id, self.date


@dataclass(slots=True, frozen=True)
class ActivityDelta:
    """Delta derivato dal confronto con lo snapshot precedente.

    Flags:
      * reset=True se i contatori totali sono diminuiti (restart device)
      * duplicate=True se snapshot identico (delta = 0,0)
    """

    user_id: str
    date: str
    timestamp: str
    steps_delta: int
    calories_out_delta: float
    steps_total: int
    calories_out_total: float
    hr_avg_session: Optional[float]
    reset: bool
    duplicate: bool


@dataclass(slots=True, frozen=True)
class DailyActivitySummary:
    """Aggregazione giornaliera consolidata.

    Usa come fonte principale gli snapshot/delta (più affidabili per totali) e
    gli eventi minuto solo per metriche di diagnosi (events_count)."""

    user_id: str
    date: str
    total_steps: int
    total_calories_out: float
    events_count: int

    def calories_out_rounded(self, ndigits: int = 2) -> float:
        return round(self.total_calories_out, ndigits)


__all__ = [
    "ActivitySource",
    "ActivityEvent",
    "HealthSnapshot",
    "ActivityDelta",
    "DailyActivitySummary",
]
