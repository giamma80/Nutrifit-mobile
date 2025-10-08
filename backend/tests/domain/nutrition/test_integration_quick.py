"""Quick integration test per nutrition domain vs existing logic."""

import pytest

from domain.nutrition.application.nutrition_service import get_nutrition_service
from domain.nutrition.model import UserPhysicalData, ActivityLevel, GoalStrategy


def test_nutrition_service_initialization():
    """Test che il servizio si inizializzi correttamente."""
    service = get_nutrition_service()
    assert service is not None


def test_bmr_tdee_calculations():
    """Test calcoli BMR/TDEE base."""
    service = get_nutrition_service()
    if not service:
        pytest.skip("Nutrition service not available")
    
    physical_data = UserPhysicalData(
        age=30,
        weight_kg=75.0,
        height_cm=180.0,
        sex="male",
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
    )
    
    bmr = service.calculate_bmr(physical_data)
    tdee = service.calculate_tdee(bmr, physical_data.activity_level)
    
    # Mifflin-St Jeor: 10*75 + 6.25*180 - 5*30 + 5 = 1730
    assert abs(bmr - 1730.0) < 0.1
    # TDEE = BMR * 1.55 = 2681.5
    assert abs(tdee - 2681.5) < 0.1


def test_macro_targets_calculation():
    """Test calcolo macro targets."""
    service = get_nutrition_service()
    if not service:
        pytest.skip("Nutrition service not available")
    
    physical_data = UserPhysicalData(
        age=30,
        weight_kg=75.0,
        height_cm=180.0,
        sex="male",
        activity_level=ActivityLevel.MODERATELY_ACTIVE,
    )
    
    targets = service.calculate_macro_targets(
        tdee=2000.0,
        strategy=GoalStrategy.CUT,
        physical_data=physical_data,
    )
    
    # CUT = -20% = 1600 kcal
    assert targets.calories == 1600
    # Protein = 75 * 1.8 = 135g
    assert abs(targets.protein_g - 135.0) < 1.0


def test_calorie_recomputation():
    """Test recompute calorie da macro."""
    service = get_nutrition_service()
    if not service:
        pytest.skip("Nutrition service not available")
    
    from domain.nutrition.model import NutrientValues
    
    # Test: 20g protein, 30g carbs, 10g fat = 290 kcal
    nutrients = NutrientValues(
        protein=20.0,
        carbs=30.0,
        fat=10.0,
        calories=None,
    )
    
    new_calories, was_corrected = service.recompute_calories_from_macros(nutrients)
    
    assert new_calories == 290.0
    assert was_corrected is True


def test_category_classification():
    """Test classificazione categoria alimenti."""
    from domain.nutrition.adapters.category_adapter import CategoryProfileAdapter
    
    adapter = CategoryProfileAdapter()
    
    # Test classificazione base
    assert adapter.classify_food("salmone alla griglia") == "lean_fish"
    assert adapter.classify_food("petto di pollo") == "poultry"
    assert adapter.classify_food("limone spremuto") == "citrus_garnish"
    
    # Test garnish clamp
    qty, clamped = adapter.apply_garnish_clamp(3.0, "citrus_garnish")
    assert qty == 5.0  # Clampato al minimo
    assert clamped is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])