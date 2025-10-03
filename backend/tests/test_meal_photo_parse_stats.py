import json
from ai_models.meal_photo_prompt import parse_and_validate_with_stats


def test_parse_stats_success_and_clamp() -> None:
    raw = json.dumps(
        {
            "items": [
                {
                    "label": "Riso",
                    "quantity": {"value": 5000, "unit": "g"},
                    "confidence": 0.9,
                },
                {
                    "label": "X",
                    "quantity": {"value": -10, "unit": "g"},
                    "confidence": 0.2,
                },
            ]
        }
    )
    items, stats = parse_and_validate_with_stats(raw)
    assert stats.success is True
    assert stats.items_count == 2
    # primo item clamped + secondo item clamped (negativo) => almeno 2
    assert stats.clamped_count >= 2
    assert stats.prompt_version >= 2


def test_parse_stats_empty_items() -> None:
    raw = json.dumps({"items": []})
    items, stats = parse_and_validate_with_stats(raw)
    assert items == []
    assert stats.success is True
    assert stats.items_count == 0


def test_parse_stats_invalid_json() -> None:
    items, stats = parse_and_validate_with_stats("not-json")
    assert items == []
    assert stats.success is False
    assert stats.raw_error is not None


def test_parse_stats_missing_items() -> None:
    items, stats = parse_and_validate_with_stats(json.dumps({"foo": []}))
    assert items == []
    assert stats.success is False
    assert stats.raw_error == "MISSING_ITEMS_ARRAY"
