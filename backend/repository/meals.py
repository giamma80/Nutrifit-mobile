"""Meal repository abstraction (in-memory implementation).

Obiettivo: isolare accesso e futura migrazione a storage persistente.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Iterable
import bisect


@dataclass(slots=True)
class MealRecord:
    id: str
    user_id: str
    name: str
    quantity_g: float
    timestamp: str  # ISO8601 Z
    barcode: Optional[str] = None
    idempotency_key: Optional[str] = None
    nutrient_snapshot_json: Optional[str] = None
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None

    def sort_key(self) -> str:
        # Usato per ordinamento reverse (timestamp discendente)
        return self.timestamp


class MealRepository:
    """Interfaccia minima futura (per DB adapter).

    Per ora forniamo solo l'implementazione in-memory.
    """

    def add(self, meal: MealRecord) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def find_by_idempotency(
        self, user_id: str, key: str
    ) -> Optional[MealRecord]:  # pragma: no cover
        raise NotImplementedError

    def list(
        self,
        user_id: str,
        limit: int,
        after: Optional[str],
        before: Optional[str],
    ) -> List[MealRecord]:  # pragma: no cover
        raise NotImplementedError

    def list_all(self, user_id: str) -> List[MealRecord]:  # pragma: no cover
        """Return all meals for a user (no ordering guarantee in interface).

        Implementazioni concrete possono ottimizzare; in-memory restituisce
        lista già ordinata per timestamp asc.
        """
        raise NotImplementedError


class InMemoryMealRepository(MealRepository):
    def __init__(self) -> None:
        # Lista ordinata per timestamp asc; lettura reverse per query
        self._data: List[MealRecord] = []
        self._idemp: dict[tuple[str, str], str] = {}
        self._by_id: dict[str, MealRecord] = {}

    def add(self, meal: MealRecord) -> None:
        # Inserimento mantenendo ordine asc (timestamp) tramite bisect
        ts_list = [m.timestamp for m in self._data]
        idx = bisect.bisect_left(ts_list, meal.timestamp)
        self._data.insert(idx, meal)
        self._by_id[meal.id] = meal
        if meal.idempotency_key:
            self._idemp[(meal.user_id, meal.idempotency_key)] = meal.id

    def find_by_idempotency(self, user_id: str, key: str) -> Optional[MealRecord]:
        mid = self._idemp.get((user_id, key))
        if not mid:
            return None
        return self._by_id.get(mid)

    def list(
        self,
        user_id: str,
        limit: int,
        after: Optional[str],
        before: Optional[str],
    ) -> List[MealRecord]:
        # Filtra user
        items: Iterable[MealRecord] = (m for m in self._data if m.user_id == user_id)
        if after:
            items = (m for m in items if m.timestamp > after)
        if before:
            items = (m for m in items if m.timestamp < before)
        # Ordine discendente
        result = list(items)
        result.sort(key=lambda m: m.timestamp, reverse=True)
        return result[:limit]

    def list_all(self, user_id: str) -> List[MealRecord]:
        return [m for m in self._data if m.user_id == user_id]


# Istanza condivisa (per semplice uso)
meal_repo: MealRepository = InMemoryMealRepository()
