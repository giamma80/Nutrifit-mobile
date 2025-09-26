"""Repository in-memory per snapshot cumulativi attività (syncHealthTotals).

Responsabilità:
* Registrare snapshot cumulativi (steps, calories_out) per (user_id, date)
* Calcolare delta rispetto al precedente (o primo/reset)
* Rilevare duplicate (snapshot identico) e reset (contatori diminuiti)
* Idempotenza via chiave opzionale (auto se assente)
* Esporre elenco delta per query `syncEntries`

Nota: hr_avg_session è escluso dalla firma idempotenza.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import uuid


@dataclass(slots=True)
class HealthTotalsDeltaRecord:
    id: str
    user_id: str
    date: str  # YYYY-MM-DD
    timestamp: str  # ISO8601 (qualsiasi precisione, mantenuta come passata)
    steps_delta: int
    calories_out_delta: float
    steps_total: int
    calories_out_total: float
    hr_avg_session: Optional[float] = None


class HealthTotalsRepository:
    def __init__(self) -> None:
        # (user_id, date) -> lista ordinata di delta
        self._deltas: Dict[Tuple[str, str], List[HealthTotalsDeltaRecord]] = {}
        # Ultimo snapshot totale per (user_id, date)
        self._last_totals: Dict[Tuple[str, str], Tuple[int, float, Optional[float], str]] = {}
        # Idempotency: (user_id, key) -> signature
        self._idemp: Dict[Tuple[str, str], str] = {}

    # ----------------- API pubblica -----------------
    def record_snapshot(
        self,
        *,
        user_id: str,
        date: str,
        timestamp: str,
        steps: int,
        calories_out: float,
        hr_avg_session: Optional[float],
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra snapshot cumulativo restituendo il risultato applicativo.

        Ritorna un dict:
        {
          'accepted': bool,
          'duplicate': bool,
          'reset': bool,
          'idempotency_key_used': str,
          'idempotency_conflict': bool,
          'delta_record': HealthTotalsDeltaRecord | None
        }
        """
        if steps < 0 or calories_out < 0:
            raise ValueError("Snapshot con valori negativi non valido")

        signature_basis = f"{date}|{steps}|{round(calories_out, 4)}|{user_id}"
        signature = hashlib.sha256(signature_basis.encode("utf-8")).hexdigest()

        auto_key = None
        if idempotency_key is None:
            auto_key = "auto-" + signature[:16]
            idempotency_key = auto_key
        key_tuple = (user_id, idempotency_key)
        existing_sig = self._idemp.get(key_tuple)
        if existing_sig is not None and existing_sig != signature:
            # Conflitto: chiave riusata con payload diverso
            return {
                "accepted": False,
                "duplicate": False,
                "reset": False,
                "idempotency_key_used": idempotency_key,
                "idempotency_conflict": True,
                "delta_record": None,
            }
        if existing_sig is None:
            # Registra la signature (anche se poi duplicate) per coerenza
            self._idemp[key_tuple] = signature

        # Duplicate detection: confronto con ultimo snapshot valori
        last_key = (user_id, date)
        duplicate = False
        reset = False
        prev_steps = 0
        prev_cal = 0.0
        prev_hr = None
        prev_signature = None
        if last_key in self._last_totals:
            prev_steps, prev_cal, prev_hr, prev_signature = self._last_totals[last_key]
            if steps == prev_steps and round(calories_out, 4) == round(prev_cal, 4):
                duplicate = True
        # Reset se decremento di almeno uno dei contatori
        if not duplicate and last_key in self._last_totals:
            if steps < prev_steps or calories_out < prev_cal:
                reset = True

        if duplicate:
            # Non creiamo nuovo delta: restituiamo delta "virtuale" (0,0)
            delta = HealthTotalsDeltaRecord(
                id="dup-" + uuid.uuid4().hex[:12],
                user_id=user_id,
                date=date,
                timestamp=timestamp,
                steps_delta=0,
                calories_out_delta=0.0,
                steps_total=steps,
                calories_out_total=calories_out,
                hr_avg_session=(hr_avg_session if hr_avg_session is not None else prev_hr),
            )
            return {
                "accepted": False,
                "duplicate": True,
                "reset": False,
                "idempotency_key_used": idempotency_key,
                "idempotency_conflict": False,
                "delta_record": delta,
            }

        # Calcolo delta (reset o incremento normale)
        if last_key not in self._deltas:
            self._deltas[last_key] = []
        if last_key not in self._last_totals or reset:
            steps_delta = steps
            cal_delta = calories_out
        else:
            steps_delta = steps - prev_steps
            cal_delta = calories_out - prev_cal
        delta_rec = HealthTotalsDeltaRecord(
            id=uuid.uuid4().hex,
            user_id=user_id,
            date=date,
            timestamp=timestamp,
            steps_delta=steps_delta,
            calories_out_delta=round(cal_delta, 4),
            steps_total=steps,
            calories_out_total=round(calories_out, 4),
            hr_avg_session=hr_avg_session,
        )
        self._deltas[last_key].append(delta_rec)
        self._last_totals[last_key] = (
            steps,
            calories_out,
            hr_avg_session,
            signature,
        )
        return {
            "accepted": True,
            "duplicate": False,
            "reset": reset,
            "idempotency_key_used": idempotency_key,
            "idempotency_conflict": False,
            "delta_record": delta_rec,
        }

    def list_deltas(
        self,
        *,
        user_id: str,
        date: str,
        after_ts: Optional[str] = None,
        limit: int = 200,
    ) -> List[HealthTotalsDeltaRecord]:
        arr = self._deltas.get((user_id, date), [])
        res: List[HealthTotalsDeltaRecord] = []
        for d in arr:
            if after_ts and d.timestamp <= after_ts:
                continue
            res.append(d)
            if len(res) >= limit:
                break
        return res

    def daily_totals(self, *, user_id: str, date: str) -> Tuple[int, float]:
        deltas = self._deltas.get((user_id, date), [])
        steps = sum(d.steps_delta for d in deltas)
        calories_out = round(sum(d.calories_out_delta for d in deltas), 4)
        return steps, calories_out


# Istanza globale
health_totals_repo = HealthTotalsRepository()
