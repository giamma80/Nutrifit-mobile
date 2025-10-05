import pytest
from typing import List, Dict
from rules.category_profiles import NormalizedItem, normalize
from inference.adapter import Gpt4vAdapter


def test_normalize_enforce_garnish_and_constraints() -> None:
    items: List[NormalizedItem] = [
        NormalizedItem(
            label="Parsley",
            quantity_g=50.0,
            calories=20.0,
            protein=None,
            carbs=None,
            fat=None,
            fiber=None,
        ),
        NormalizedItem(
            label="Salmon",
            quantity_g=120.0,
            calories=240.0,
            protein=25.0,
            carbs=5.0,  # violerà hard constraint
            fat=8.0,
            fiber=None,
        ),
    ]
    res = normalize(items=items, mode="enforce")
    parsley, salmon = res.items
    # Garnish clamp
    assert parsley.quantity_g == 10.0
    # Category classification sets herb
    assert parsley.category == "herb"
    # Hard constraint on salmon carbs
    assert salmon.carbs == 0.0


@pytest.mark.asyncio
async def test_gpt4v_adapter_enforce_applies_clamp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_MEAL_PHOTO_MODE", "gpt4v")
    monkeypatch.setenv("AI_NORMALIZATION_MODE", "enforce")
    monkeypatch.delenv("AI_GPT4V_REAL_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from inference.adapter import Gpt4vAdapter as _Adapter

    def fake_sim(self: Gpt4vAdapter) -> str:
        import json

        data = {
            "items": [
                {
                    "label": "parsley",
                    "quantity": {"value": 50, "unit": "g"},
                    "confidence": 0.9,
                },
                {
                    "label": "salmon",
                    "quantity": {"value": 120, "unit": "g"},
                    "confidence": 0.85,
                },
            ]
        }
        return json.dumps(data)

    monkeypatch.setattr(_Adapter, "_simulate_model_output", fake_sim, raising=True)
    adapter = Gpt4vAdapter()
    items = await adapter.analyze_async(
        user_id="u",
        photo_id="p1",
        photo_url=None,
        now_iso="2025-01-01T00:00:00Z",
    )
    # Retrieve parsley + salmon
    from ai_models.meal_photo_models import MealPhotoItemPredictionRecord

    labels: Dict[str, MealPhotoItemPredictionRecord] = {i.label: i for i in items}
    assert labels["parsley"].quantity_g == 10.0, labels["parsley"].quantity_g
    # Hard constraint sets carbs to 0 for salmon (if enrichment assigned >2)
    # Default enrichment gives carbs >2 so hard constraint should zero it
    assert (labels["salmon"].carbs or 0) <= 2.0
