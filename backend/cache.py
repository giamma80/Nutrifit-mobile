"""Semplice cache in-memory TTL.

Usata per la query product(barcode).
Non thread-safe avanzata: sufficiente per singolo worker di sviluppo.
"""

from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class _Entry:
    value: Any
    expires_at: float


class SimpleCache:
    def __init__(self) -> None:
        self._data: Dict[str, _Entry] = {}

    def get(self, key: str) -> Optional[Any]:
        e = self._data.get(key)
        if not e:
            return None
        if e.expires_at < time.time():  # scaduto
            self._data.pop(key, None)
            return None
        return e.value

    def set(self, key: str, value: Any, ttl: float) -> None:
        self._data[key] = _Entry(value=value, expires_at=time.time() + ttl)

    def purge_expired(self) -> None:
        now = time.time()
        for k, e in list(self._data.items()):
            if e.expires_at < now:
                self._data.pop(k, None)


cache = SimpleCache()
