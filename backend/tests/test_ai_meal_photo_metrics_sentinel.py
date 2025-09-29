import pytest
from metrics.ai_meal_photo import snapshot, reset_all
from inference.adapter import get_active_adapter


@pytest.mark.asyncio
async def test_ai_meal_photo_metrics_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica baseline metriche dopo una singola analisi stub.

    Obiettivo: evitare regressioni dove
    richieste/fallback/error non cambiano più
    (es. doppio conteggio o mancato incremento). Usa modalità stub per percorsi
    deterministici e non richiedere chiavi esterne.
    """
    reset_all()
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "stub")
    adapter = get_active_adapter()
    before = snapshot()
    items = await adapter.analyze_async(
        user_id="sentinel", photo_id="ph1", photo_url=None, now_iso="NOW"
    )
    after = snapshot()
    assert items, "Attesi item dal percorso stub"

    from typing import Any

    def counter_val(snap: Any, name: str, **tag_filters: str) -> int:
        for c in snap["counters"]:
            if c["name"] != name:
                continue
            tags = c.get("tags", {})
            if all(tags.get(k) == v for k, v in tag_filters.items()):
                val = c.get("value")
                if isinstance(val, int):
                    return val
        return 0

    req_completed_delta = counter_val(
        after,
        "ai_meal_photo_requests_total",
        phase="stub",
        status="completed",
    ) - counter_val(
        before,
        "ai_meal_photo_requests_total",
        phase="stub",
        status="completed",
    )
    # Stub non dovrebbe generare fallback o error
    fb_total_delta = counter_val(
        after, "ai_meal_photo_fallback_total"
    ) - counter_val(before, "ai_meal_photo_fallback_total")
    err_total_delta = counter_val(
        after, "ai_meal_photo_errors_total"
    ) - counter_val(before, "ai_meal_photo_errors_total")

    assert req_completed_delta == 1, "Una richiesta stub completata attesa"
    assert fb_total_delta == 0, "Nessun fallback atteso per stub"
    assert err_total_delta == 0, "Nessun errore atteso per stub"
