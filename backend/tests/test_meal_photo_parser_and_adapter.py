import json
import pytest
from typing import List

from ai_models.meal_photo_prompt import (
    parse_and_validate,
    ParsedItem,
    ParseError,
)
from inference.adapter import get_active_adapter
from metrics.ai_meal_photo import snapshot


# -------- Parser Unit Tests --------


def test_parse_basic() -> None:
    raw = json.dumps(
        {
            "items": [
                {
                    "label": "Insalata mista",
                    "quantity": {"value": 120, "unit": "g"},
                    "confidence": 0.91,
                },
                {
                    "label": "Petto di pollo",
                    "quantity": {"value": 130, "unit": "g"},
                    "confidence": 0.80,
                },
            ]
        }
    )
    parsed: List[ParsedItem] = parse_and_validate(raw)
    assert len(parsed) == 2
    assert parsed[0].label == "insalata mista"
    assert parsed[0].calories >= 0


def test_parse_piece_conversion() -> None:
    raw = json.dumps(
        {
            "items": [
                {
                    "label": "Mela",
                    "quantity": {
                        "value": 1,
                        "unit": "piece",
                        "label_hint": "mela",
                    },
                    "confidence": 0.5,
                }
            ]
        }
    )
    parsed = parse_and_validate(raw)
    # peso medio mela 150g --> calories > 0
    assert parsed[0].quantity_g >= 149
    assert parsed[0].calories > 0


def test_parse_clamp_and_confidence_range() -> None:
    raw = json.dumps(
        {
            "items": [
                {
                    "label": "Riso",
                    "quantity": {"value": 5000, "unit": "g"},
                    "confidence": 5.0,
                },
                {
                    "label": "X",
                    "quantity": {"value": -10, "unit": "g"},
                    "confidence": -2,
                },
            ]
        }
    )
    parsed = parse_and_validate(raw)
    # primo item clamped a 2000g, confidence clamped 1.0
    assert parsed[0].quantity_g == 2000
    assert 0 <= parsed[0].confidence <= 1
    # Nota: il secondo item viene mantenuto con quantity 0 clampata
    assert len(parsed) == 2


def test_parse_missing_items_raises() -> None:
    raw = json.dumps({"foo": []})
    with pytest.raises(ParseError):
        parse_and_validate(raw)


def test_parse_empty_items_ok() -> None:
    raw = json.dumps({"items": []})
    parsed = parse_and_validate(raw)
    assert parsed == []


# -------- Adapter Selection Tests --------


@pytest.mark.asyncio
async def test_gpt4v_adapter_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    adapter = get_active_adapter()
    items = adapter.analyze(
        user_id="u1", photo_id="p1", photo_url=None, now_iso="NOW"
    )
    assert adapter.name() == "gpt4v"
    assert len(items) >= 1
    assert all(it.calories is not None for it in items)


@pytest.mark.asyncio
async def test_fallback_on_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from inference import adapter as adapter_mod

    class BrokenGpt(adapter_mod.Gpt4vAdapter):
        def _simulate_model_output(self) -> str:  # noqa: D401
            return "not-json"

    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setattr(adapter_mod, "Gpt4vAdapter", BrokenGpt)
    a = get_active_adapter()
    before = snapshot()
    items = a.analyze(
        user_id="u1", photo_id="p1", photo_url=None, now_iso="NOW"
    )
    after = snapshot()
    # Fallback stub produce 2 items
    assert len(items) == 2
    assert a.name() == "gpt4v"
    fb = [
        c
        for c in after["counters"]
        if c["name"] == "ai_meal_photo_fallback_total"
        and c["tags"].get("reason", "").startswith("PARSE_")
    ]
    prev = [
        c
        for c in before["counters"]
        if c["name"] == "ai_meal_photo_fallback_total"
        and c["tags"].get("reason", "").startswith("PARSE_")
    ]
    prev_val = prev[0]["value"] if prev else 0
    assert fb and fb[0]["value"] >= prev_val + 1


def test_gpt4v_real_disabled_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    # NON abilitiamo AI_GPT4V_REAL_ENABLED → deve scattare REAL_DISABLED
    adapter = get_active_adapter()
    items = adapter.analyze(
        user_id="u2", photo_id="p2", photo_url=None, now_iso="NOW"
    )
    assert items
    data = snapshot()
    fb = []
    for c in data["counters"]:
        if c["name"] != "ai_meal_photo_fallback_total":
            continue
        reason = c["tags"].get("reason")
        if reason in {"REAL_DISABLED", "MISSING_API_KEY"}:
            fb.append(c)
    assert fb, "Atteso fallback metric per REAL_DISABLED o MISSING_API_KEY"
