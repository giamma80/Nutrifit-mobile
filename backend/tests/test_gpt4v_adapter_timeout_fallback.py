import pytest

from inference.adapter import Gpt4vAdapter, StubAdapter
from metrics.ai_meal_photo import snapshot, reset_all


@pytest.mark.asyncio
async def test_gpt4v_timeout_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout nella chiamata vision: fallback a simulazione.

    Verifiche:
    - fallback_total +1, errors_total invariato
    - richiesta conteggiata come completed
    - last_fallback_reason inizia con "TIMEOUT:"
    - items non vuoti (simulazione JSON) e calorie insalata diverse dallo stub
    """
    reset_all()
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    import inference.adapter as adapter_mod

    from inference.vision_client import VisionTimeoutError

    class _FakeTimeout(VisionTimeoutError):
        pass

    async def _raise_timeout(
        *, image_url: str | None, prompt: str, timeout_s: float = 12.0
    ) -> str:  # noqa: D401
        raise _FakeTimeout("deadline")

    monkeypatch.setattr(adapter_mod, "call_openai_vision", _raise_timeout)

    adapter = Gpt4vAdapter()
    before = snapshot()
    items = await adapter.analyze_async(
        user_id="u1",
        photo_id="ph-timeout",
        photo_url="http://ex",
        now_iso="NOW",
    )
    after = snapshot()

    assert items, "Attesi items da simulazione dopo timeout"
    assert adapter.last_fallback_reason
    assert adapter.last_fallback_reason.startswith(
        "TIMEOUT:"
    ), "Fallback reason TIMEOUT attesa"

    # Confronto calorie primo item (insalata) tra stub e simulazione
    stub_first = (
        await StubAdapter().analyze_async(
            user_id="_", photo_id=None, photo_url=None, now_iso="_"
        )
    )[0]
    # La simulazione calcola calorie via densità (20 kcal/100g) => 150g -> 30
    sim_first = items[0]
    if sim_first.label.startswith("insalata"):
        assert (
            sim_first.calories != stub_first.calories
        ), "Calorie simulate devono differire dallo stub"

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

    fb_delta = counter_val(
        after, "ai_meal_photo_fallback_total"
    ) - counter_val(before, "ai_meal_photo_fallback_total")
    err_delta = counter_val(after, "ai_meal_photo_errors_total") - counter_val(
        before, "ai_meal_photo_errors_total"
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
    assert fb_delta == 1, "Atteso un fallback su timeout"
    assert err_delta == 0, (
        "Timeout non incrementa errors_total (solo fallback)"
    )
    assert completed_delta == 1, (
        "Richiesta deve risultare completed nonostante timeout"
    )
