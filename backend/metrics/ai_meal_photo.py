"""Instrumentation helpers per AI Meal Photo.

Metriche attuali (tutte con label opzionale `source` se fornita):
* Counter ai_meal_photo_requests_total{phase,status,source?}
* Counter ai_meal_photo_fallback_total{reason,source?}
* Histogram ai_meal_photo_latency_ms{source?}
* Counter ai_meal_photo_errors_total{code,source?}
* Counter ai_meal_photo_failed_total{code,source?}

NOTE:
`phase` distingue eventuali sotto-fasi (es. "heuristic_pre", "model").
`source` identifica l'adapter principale (stub|heuristic|model|fallback).
Per ora `phase` e `source` coincidono (adapter.name()).
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Optional, Iterator

from .core import registry, RegistrySnapshot


def record_request(
    phase: str,
    status: str,
    *,
    source: Optional[str] = None,
) -> None:
    tags = {"phase": phase, "status": status}
    if source:
        tags["source"] = source
    registry.counter("ai_meal_photo_requests_total", **tags).inc()


def record_fallback(reason: str, *, source: Optional[str] = None) -> None:
    tags = {"reason": reason}
    if source:
        tags["source"] = source
    registry.counter("ai_meal_photo_fallback_total", **tags).inc()


def record_latency_ms(ms: float, *, source: Optional[str] = None) -> None:
    if source:
        registry.histogram("ai_meal_photo_latency_ms", source=source).observe(ms)
    else:
        registry.histogram("ai_meal_photo_latency_ms").observe(ms)


def record_error(code: str, *, source: Optional[str] = None) -> None:
    """Conta qualsiasi errore individuale (analisiErrors)."""
    tags = {"code": code}
    if source:
        tags["source"] = source
    registry.counter("ai_meal_photo_errors_total", **tags).inc()


def record_failed(code: str, *, source: Optional[str] = None) -> None:
    """Conta failureReason finale (bloccante)."""
    tags = {"code": code}
    if source:
        tags["source"] = source
    registry.counter("ai_meal_photo_failed_total", **tags).inc()


def record_parse_success(
    items_count: int,
    *,
    prompt_version: int,
    source: Optional[str] = None,
) -> None:
    tags = {"items": str(items_count), "prompt_version": str(prompt_version)}
    if source:
        tags["source"] = source
    registry.counter("ai_meal_photo_parse_success_total", **tags).inc()


def record_parse_failed(
    error: str,
    *,
    prompt_version: int,
    source: Optional[str] = None,
) -> None:
    tags = {"error": error, "prompt_version": str(prompt_version)}
    if source:
        tags["source"] = source
    registry.counter("ai_meal_photo_parse_failed_total", **tags).inc()


def record_parse_clamped(
    count: int,
    *,
    prompt_version: int,
    source: Optional[str] = None,
) -> None:
    if count <= 0:
        return
    tags = {"prompt_version": str(prompt_version)}
    if source:
        tags["source"] = source
    registry.counter("ai_meal_photo_parse_clamped_total", **tags).inc(count)


@contextmanager
def time_analysis(
    phase: str,
    *,
    source: Optional[str] = None,
    status_on_exit: Optional[str] = None,
) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
        record_request(
            phase=phase,
            status=status_on_exit or "completed",
            source=source,
        )
    except Exception:
        record_request(phase=phase, status="failed", source=source)
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        record_latency_ms(elapsed_ms, source=source)


def snapshot() -> RegistrySnapshot:  # pragma: no cover - passthrough
    return registry.snapshot()


def reset_all() -> None:  # pragma: no cover - test utility
    """Resetta tutte le metriche (uso test)."""
    registry.reset()
