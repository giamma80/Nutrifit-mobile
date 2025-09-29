import pytest

from inference.adapter import Gpt4vAdapter, StubAdapter
from metrics.ai_meal_photo import snapshot, reset_all


def test_gpt4v_parse_error_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parse non JSON: fallback a stub + metriche fallback & error.

    Verifiche:
    - items uguali allo stub
    - fallback_total +1
    - errors_total +1
    """
    reset_all()
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    import inference.adapter as adapter_mod

    async def _fake_call(
        *, image_url: str | None, prompt: str, timeout_s: float = 12.0
    ) -> str:  # noqa: D401
        return "RISPOSTA LIBERA SENZA JSON"

    monkeypatch.setattr(adapter_mod, "call_openai_vision", _fake_call)

    adapter = Gpt4vAdapter()
    before = snapshot()
    items = adapter.analyze(user_id="u1", photo_id="ph-parse", photo_url="http://ex", now_iso="NOW")
    after = snapshot()

    stub_items = StubAdapter().analyze(user_id="_", photo_id=None, photo_url=None, now_iso="_")
    assert len(items) == len(stub_items)
    # Confronto semplice su etichette
    assert [i.label for i in items] == [i.label for i in stub_items]

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
    err_delta = counter_val(after, "ai_meal_photo_errors_total") - counter_val(
        before, "ai_meal_photo_errors_total"
    )
    assert fb_delta == 1, "Atteso un fallback su parse error"
    assert err_delta == 1, "Atteso un errore conteggiato su parse error"
