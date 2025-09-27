"""Instrumentation helpers per AI Meal Photo (Issue 29).

Uso previsto prima della Fase 1 heuristica per ottenere baseline stub.

Metriche definite:
* Counter ai_meal_photo_requests_total{phase, status}
* Counter ai_meal_photo_fallback_total{reason}
* Histogram ai_meal_photo_latency_ms{}
* Counter ai_meal_photo_errors_total{code}
* Counter ai_meal_photo_failed_total{code} (solo errori terminali / failureReason)

Fase 1 aggiungerà tag source=STUB|HEURISTIC e codici errore
(Issue 33) separati.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Optional, Iterator

from .core import registry, RegistrySnapshot


def record_request(phase: str, status: str) -> None:
    registry.counter("ai_meal_photo_requests_total", phase=phase, status=status).inc()


def record_fallback(reason: str) -> None:
    registry.counter("ai_meal_photo_fallback_total", reason=reason).inc()


def record_latency_ms(ms: float) -> None:
    registry.histogram("ai_meal_photo_latency_ms").observe(ms)


def record_error(code: str) -> None:
    """Conta qualsiasi errore individuale (analisiErrors)."""
    registry.counter("ai_meal_photo_errors_total", code=code).inc()


def record_failed(code: str) -> None:
    """Conta failureReason finale (bloccante)."""
    registry.counter("ai_meal_photo_failed_total", code=code).inc()


@contextmanager
def time_analysis(phase: str, status_on_exit: Optional[str] = None) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
        record_request(phase=phase, status=status_on_exit or "completed")
    except Exception:
        record_request(phase=phase, status="failed")
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        record_latency_ms(elapsed_ms)


def snapshot() -> RegistrySnapshot:  # pragma: no cover - passthrough
    return registry.snapshot()
