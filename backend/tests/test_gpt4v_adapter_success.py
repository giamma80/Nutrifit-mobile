import pytest

from inference.adapter import Gpt4vAdapter, StubAdapter
from metrics.ai_meal_photo import snapshot, reset_all


@pytest.mark.asyncio
async def test_gpt4v_success_monkeypatched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Success case: modello vision mock restituisce JSON valido.

    Verifica:
    - Nessun fallback registrato
    - Items derivati dal parsing (>=1) e diversi (potenzialmente) dallo stub
    - Incremento counter richieste completate con phase=gpt4v, status=completed
    """
    reset_all()
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    # Patch simbolo importato in adapter
    import inference.adapter as adapter_mod

    async def _fake_call(*, image_url: str | None, prompt: str, timeout_s: float = 12.0) -> str:
        return (
            '{"items":[{"label":"Insalata mista","quantity":'
            '{"value":120,"unit":"g"},"confidence":0.9},'
            '{"label":"Petto di pollo","quantity":{"value":110,"unit":"g"},'
            '"confidence":0.85}]}'
        )

    monkeypatch.setattr(adapter_mod, "call_openai_vision", _fake_call)

    adapter = Gpt4vAdapter()
    before = snapshot()
    items = await adapter.analyze_async(
        user_id="u1",
        photo_id="ph-success",
        photo_url="http://ex",
        now_iso="NOW",
    )
    after = snapshot()

    assert items, "Attesi items dal path gpt4v"
    # Confronto semplice: stub produce quantità 150 e 120; qui 120 e 110
    stub_items = await StubAdapter().analyze_async(
        user_id="_", photo_id=None, photo_url=None, now_iso="_"
    )
    stub_quantities = sorted([int(it.quantity_g or 0) for it in stub_items])
    new_quantities = sorted([int(it.quantity_g or 0) for it in items])
    assert new_quantities != stub_quantities, "Quantità dovrebbero differire dal puro stub"

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
    fallback_total_delta = counter_val(after, "ai_meal_photo_fallback_total") - counter_val(
        before, "ai_meal_photo_fallback_total"
    )
    assert completed_delta == 1, "Una richiesta gpt4v completata attesa"
    assert fallback_total_delta == 0, "Nessun fallback atteso nel success case"
