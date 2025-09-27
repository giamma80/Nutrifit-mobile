"""Minimal metrics registry (Issue 29) – in-memory, thread-safe, zero dipendenze.

Obiettivi:
* Fornire counters e histogram basilari per pipeline AI Meal Photo.
* Snapshot leggibile nei test.
* Niente esposizione HTTP/GraphQL (aggiungibile più avanti).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, Tuple, List, Any, TypedDict
import time


TagKey = Tuple[str, Tuple[Tuple[str, str], ...]]  # (metric_name, sorted_tags)


def _tag_key(name: str, tags: Dict[str, str]) -> TagKey:
    return name, tuple(sorted(tags.items()))


@dataclass
class Counter:
    name: str
    tags: Dict[str, str]
    _value: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def inc(self, amount: int = 1) -> None:
        with self._lock:
            self._value += amount

    def value(self) -> int:
        with self._lock:
            return self._value


@dataclass
class Histogram:
    name: str
    tags: Dict[str, str]
    _values: List[float] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, repr=False)
    _max_samples: int = 2000  # cap per memoria (sliding window)

    def observe(self, value: float) -> None:
        with self._lock:
            if len(self._values) >= self._max_samples:
                # drop oldest (simple strategy)
                self._values.pop(0)
            self._values.append(value)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            if not self._values:
                return {
                    "count": 0,
                    "avg": 0.0,
                    "p95": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                }
            vals = list(self._values)
        vals.sort()
        count = len(vals)
        avg = sum(vals) / count
        p95 = vals[int(0.95 * (count - 1))]
        return {
            "count": count,
            "avg": avg,
            "p95": p95,
            "min": vals[0],
            "max": vals[-1],
        }


class CounterSnap(TypedDict):
    name: str
    tags: Dict[str, str]
    value: int


class HistogramSnap(TypedDict):
    name: str
    tags: Dict[str, str]
    count: int
    avg: float
    p95: float
    min: float
    max: float


class RegistrySnapshot(TypedDict):
    counters: List[CounterSnap]
    histograms: List[HistogramSnap]
    generatedAt: float


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: Dict[TagKey, Counter] = {}
        self._histograms: Dict[TagKey, Histogram] = {}
        self._lock = Lock()

    def counter(self, name: str, **tags: str) -> Counter:
        key = _tag_key(name, tags)
        with self._lock:
            ctr = self._counters.get(key)
            if ctr is None:
                ctr = Counter(name=name, tags=tags)
                self._counters[key] = ctr
            return ctr

    def histogram(self, name: str, **tags: str) -> Histogram:
        key = _tag_key(name, tags)
        with self._lock:
            h = self._histograms.get(key)
            if h is None:
                h = Histogram(name=name, tags=tags)
                self._histograms[key] = h
            return h

    def snapshot(self) -> RegistrySnapshot:
        # Rappresentazione serializzabile per test
        data: RegistrySnapshot = {
            "counters": [],
            "histograms": [],
            "generatedAt": time.time(),
        }
        # copy references under lock, read values outside to limit contention
        with self._lock:
            counters = list(self._counters.values())
            histograms = list(self._histograms.values())
        for c in counters:
            counter_snap: CounterSnap = {
                "name": c.name,
                "tags": c.tags,
                "value": c.value(),
            }
            data["counters"].append(counter_snap)
        for h in histograms:
            snap = h.snapshot()
            hist: HistogramSnap = {
                "name": h.name,
                "tags": h.tags,
                "count": snap["count"],
                "avg": snap["avg"],
                "p95": snap["p95"],
                "min": snap["min"],
                "max": snap["max"],
            }
            data["histograms"].append(hist)
        return data


registry = MetricsRegistry()
