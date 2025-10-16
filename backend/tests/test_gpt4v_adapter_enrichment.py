"""Test integrazione enrichment in Gpt4vAdapter."""

import pytest

from inference.adapter import Gpt4vAdapter
from metrics.ai_meal_photo import snapshot, reset_all


@pytest.mark.asyncio
async def test_gpt4v_enrichment_integration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test enrichment integration: macro fields popolati correttamente.

    Verifica:
    - Items con campi macro popolati dall'enrichment
    - Metriche enrichment registrate
    - Macro fill ratio calcolata correttamente
    """
    reset_all()
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_GPT4V_REAL_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")

    # Mock vision API per restituire items conosciuti nel heuristic
    import inference.adapter as adapter_mod

    async def _fake_call(*, image_url: str, prompt: str, timeout_s: float = 12.0) -> str:
        return (
            '{"items":['
            '{"label":"pollo","quantity":{"value":100,"unit":"g"},"confidence":0.9},'
            '{"label":"unknown_food","quantity":{"value":50,"unit":"g"},"confidence":0.7}'
            "]}"
        )

    monkeypatch.setattr(adapter_mod, "call_openai_vision", _fake_call)

    adapter = Gpt4vAdapter()
    before = snapshot()

    items = await adapter.analyze_async(
        user_id="u1",
        photo_id="ph-enrich",
        photo_url="http://example.com/photo.jpg",
        now_iso="2024-01-01T12:00:00Z",
    )

    after = snapshot()

    # Verifica items popolati
    assert len(items) == 2

    # Item 1: pollo (dovrebbe avere heuristic)
    pollo_item = items[0]
    assert pollo_item.label == "pollo"
    assert pollo_item.quantity_g == 100.0
    # Nuovo sistema: può essere USDA o default
    assert pollo_item.protein is not None and pollo_item.protein > 0
    # I valori specifici dipendono ora da USDA/default, non heuristics fisse

    # Item 2: unknown_food (dovrebbe avere default)
    unknown_item = items[1]
    assert unknown_item.label == "unknownfood"  # parser rimuove underscore
    assert unknown_item.quantity_g == 50.0
    assert unknown_item.protein == 1.0  # default: 2.0 * 0.5
    assert unknown_item.carbs == 5.0  # default: 10.0 * 0.5
    assert unknown_item.fat == 0.5  # default: 1.0 * 0.5
    assert unknown_item.fiber == 0.5  # default: 1.0 * 0.5

    # Verifica metriche enrichment
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

    def histogram_count(snap: Any, name: str, **tags: str) -> int:
        for h in snap.get("histograms", []):
            if h["name"] != name:
                continue
            tg = h.get("tags", {})
            if all(tg.get(k) == v for k, v in tags.items()):
                count = h.get("count", 0)
                return int(count) if count is not None else 0
        return 0

    # Enrichment success counter (nuovo sistema: usa tag generici)
    enrichment_success = counter_val(
        after,
        "ai_meal_photo_enrichment_success_total",
        source="gpt4v",
        items="2",
    ) - counter_val(
        before,
        "ai_meal_photo_enrichment_success_total",
        source="gpt4v",
        items="2",
    )
    assert enrichment_success == 1, "Una operazione enrichment attesa"

    # Enrichment latency histogram
    enrichment_latency_count = histogram_count(
        after,
        "ai_meal_photo_enrichment_latency_ms",
        source="gpt4v",
    ) - histogram_count(
        before,
        "ai_meal_photo_enrichment_latency_ms",
        source="gpt4v",
    )
    assert enrichment_latency_count == 1, "Una misurazione latency enrichment attesa"

    # Macro fill ratio histogram
    macro_fill_count = histogram_count(
        after,
        "ai_meal_photo_macro_fill_ratio",
        source="gpt4v",
        filled="8",  # 4 campi per pollo + 4 campi per unknown
        total="8",  # 4 campi possibili * 2 items
    ) - histogram_count(
        before,
        "ai_meal_photo_macro_fill_ratio",
        source="gpt4v",
        filled="8",
        total="8",
    )
    assert macro_fill_count == 1, "Una misurazione macro fill ratio attesa"


@pytest.mark.asyncio
async def test_enrichment_service_stats_tracking() -> None:
    """Test stats tracking del servizio enrichment."""
    from ai_models.nutrient_enrichment import NutrientEnrichmentService
    from ai_models.meal_photo_prompt import ParsedItem

    service = NutrientEnrichmentService()

    # Batch con mix heuristic/default
    items = [
        ParsedItem(
            label="pollo",
            quantity_g=100.0,
            confidence=0.9,
            calories=200,
            source_density="medium",
        ),
        ParsedItem(
            label="riso",
            quantity_g=100.0,
            confidence=0.8,
            calories=130,
            source_density="high",
        ),
        ParsedItem(
            label="unknown",
            quantity_g=100.0,
            confidence=0.7,
            calories=100,
            source_density="low",
        ),
    ]

    await service.enrich_parsed_items(items)

    stats = service.get_stats()
    assert stats["enriched"] == 3  # Ora tutti gli item vengono processati
    # Nuovo sistema: tutto via USDA + default
    assert stats["hit_usda"] + stats["hit_default"] == 3
