from repository.ai_meal_photo import meal_photo_repo
from metrics.ai_meal_photo import snapshot
from typing import Any
import os


def _clear_env() -> None:
    for var in ["AI_HEURISTIC_ENABLED", "AI_REMOTE_ENABLED"]:
        if var in os.environ:
            del os.environ[var]


def test_metrics_source_label_stub(monkeypatch: Any) -> None:
    _clear_env()
    monkeypatch.delenv("AI_HEURISTIC_ENABLED", raising=False)
    monkeypatch.delenv("AI_REMOTE_ENABLED", raising=False)
    # snapshot iniziale per eventuali confronti futuri (non usato ora)
    snapshot()
    repo = meal_photo_repo
    rec = repo.create_or_get(
        user_id="u1",
        photo_id="p1",
        photo_url=None,
        idempotency_key=None,
        now_iso="2025-09-27T10:00:00Z",
    )
    assert rec.source == "stub"
    after = snapshot()
    req = [
        c
        for c in after["counters"]
        if c["name"] == "ai_meal_photo_requests_total"
    ]
    assert any(c["tags"].get("source") == "stub" for c in req)


def test_metrics_source_label_heuristic(
    monkeypatch: Any,
) -> None:
    _clear_env()
    monkeypatch.setenv("AI_HEURISTIC_ENABLED", "1")
    monkeypatch.delenv("AI_REMOTE_ENABLED", raising=False)
    repo = meal_photo_repo
    rec = repo.create_or_get(
        user_id="u2",
        photo_id="p2",
        photo_url="http://x/water.png",
        idempotency_key=None,
        now_iso="2025-09-27T10:01:00Z",
    )
    assert rec.source == "heuristic"
    snap = snapshot()
    req = [
        c
        for c in snap["counters"]
        if c["name"] == "ai_meal_photo_requests_total"
    ]
    assert any(c["tags"].get("source") == "heuristic" for c in req)


def test_metrics_source_label_remote_fallback(
    monkeypatch: Any,
) -> None:
    _clear_env()
    # Abilita remote ma forza timeout riducendo timeout_ms
    # ed aumentando latency per forzare fallback
    monkeypatch.setenv("AI_REMOTE_ENABLED", "1")
    monkeypatch.setenv(
        "REMOTE_TIMEOUT_MS",
        "10",
    )  # bassissimo per forzare fallback
    monkeypatch.setenv("REMOTE_LATENCY_MS", "50")
    monkeypatch.setenv("REMOTE_JITTER_MS", "0")
    repo = meal_photo_repo
    rec = repo.create_or_get(
        user_id="u3",
        photo_id="p3",
        photo_url=None,
        idempotency_key=None,
        now_iso="2025-09-27T10:02:00Z",
    )
    # Il source nel record riflette l'adapter attivo (model), anche se fallback
    # interno ha prodotto dati (per ora non distinguiamo fallback nel source).
    assert rec.source == "model"
    snap = snapshot()
    req = [
        c
        for c in snap["counters"]
        if c["name"] == "ai_meal_photo_requests_total"
    ]
    assert any(c["tags"].get("source") == "model" for c in req)
