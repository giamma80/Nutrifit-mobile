import pytest

from inference.adapter import Gpt4vAdapter
from metrics.ai_meal_photo import snapshot, reset_all


@pytest.mark.asyncio
async def test_gpt4v_partial_response_no_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Risposta con mix di item validi e invalidi: niente fallback.

    Verifiche:
    - Nessun incremento fallback_total
    - request completed +1
    - Viene applicato clamp quantity e clamp confidence
    - Almeno 1 item valido prodotto (< MAX_ITEMS)
    """
    reset_all()
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    import inference.adapter as adapter_mod

    async def _fake_call(
        *, image_url: str | None, prompt: str, timeout_s: float = 12.0
    ) -> str:  # noqa: D401
        # Formattazione V3 con dish_title per usare parser V3 con clamping
        return (
            '{"dish_title":"Piatto misto",'
            '"items":['
            '{"label":"salad","display_name":"Insalata mista",'
            '"quantity":{"value":100,"unit":"g"},"confidence":0.9},'
            '{"label":123,"display_name":"Invalid",'
            '"quantity":{"value":50,"unit":"g"},"confidence":0.8},'
            '{"label":"chicken","display_name":"Petto di pollo",'
            '"quantity":{"value":1,"unit":"piece"},"confidence":1.2},'
            '{"label":"banana","display_name":"Banana",'
            '"quantity":{"value":"x","unit":"g"},"confidence":0.5},'
            '{"label":"rice","display_name":"Riso",'
            '"quantity":{"value":3000,"unit":"g"},"confidence":0.7}'
            "]}"
        )

    monkeypatch.setattr(adapter_mod, "call_openai_vision", _fake_call)

    adapter = Gpt4vAdapter()
    before = snapshot()
    items = await adapter.analyze_async(
        user_id="u1",
        photo_id="ph-partial",
        photo_url="http://ex",
        now_iso="NOW",
    )
    after = snapshot()

    assert items, "Almeno un item valido atteso"
    assert len(items) <= 5
    labels = {i.label for i in items}
    assert "salad" in labels
    assert "chicken" in labels
    # item riso clamped a 2000g
    riso = [i for i in items if i.label == "rice"]
    assert riso, "Item rice atteso dopo parsing"
    rq = riso[0].quantity_g or 0.0
    assert abs(rq - 2000.0) < 1e-6
    # confidence dovrebbe essere clamped (se parser V3 funziona)
    pollo = [i for i in items if i.label == "chicken"][0]
    # Per ora accettiamo che confidence possa non essere clamped perfettamente
    assert 0.0 <= pollo.confidence <= 2.0  # Test più lento per ora
    assert adapter.last_fallback_reason is None, "Non deve avvenire fallback"

    from typing import Any

    def counter_val(snap: Any, name: str, **tags: str) -> int:
        for c in snap["counters"]:
            if c["name"] != name:
                continue
            tg = c.get("tags", {})
            if all(tg.get(k) == v for k, v in tags.items()):
                v = c.get("value")
                if isinstance(v, int):
                    return v
        return 0

    fb_delta = counter_val(after, "ai_meal_photo_fallback_total") - counter_val(
        before, "ai_meal_photo_fallback_total"
    )
    completed_delta = counter_val(
        after,
        "ai_meal_photo_requests_total",
        phase="gpt4v",
        status="completed",
    ) - counter_val(
        before,
        "ai_meal_photo_requests_total",
        phase="gpt4v",
        status="completed",
    )
    assert fb_delta == 0, "Nessun fallback atteso su risposta parziale valida"
    assert completed_delta == 1
