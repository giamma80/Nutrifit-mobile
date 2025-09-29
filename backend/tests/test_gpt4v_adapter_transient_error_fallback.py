import pytest

from inference.adapter import Gpt4vAdapter
from metrics.ai_meal_photo import snapshot, reset_all


@pytest.mark.asyncio
async def test_gpt4v_transient_error_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Errore transiente vision: fallback a simulazione (no errors_total).

    Verifiche:
    - fallback_total +1
    - errors_total invariato
    - last_fallback_reason prefix TRANSIENT:
    - richiesta completed
    """
    reset_all()
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    import inference.adapter as adapter_mod

    from inference.vision_client import VisionTransientError

    class _FakeTransient(VisionTransientError):
        pass

    async def _raise_transient(
        *, image_url: str | None, prompt: str, timeout_s: float = 12.0
    ) -> str:  # noqa: D401
        raise _FakeTransient("temporary")

    monkeypatch.setattr(adapter_mod, "call_openai_vision", _raise_transient)

    adapter = Gpt4vAdapter()
    before = snapshot()
    items = await adapter.analyze_async(
        user_id="u1",
        photo_id="ph-transient",
        photo_url="http://ex",
        now_iso="NOW",
    )
    after = snapshot()

    assert items, "Items simulati attesi"
    assert adapter.last_fallback_reason
    assert adapter.last_fallback_reason.startswith("TRANSIENT:")

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
    assert fb_delta == 1, "Atteso un fallback su errore transiente"
    assert err_delta == 0, "Errore transiente non deve contare come error"
    assert completed_delta == 1
