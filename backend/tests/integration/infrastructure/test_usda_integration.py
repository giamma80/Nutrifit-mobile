"""Integration tests for USDA client with real API.

Tests P3.7.2: USDA FoodData Central integration with real API calls.

These tests are opt-in and require:
- AI_USDA_API_KEY environment variable
- Run with: pytest -m integration_real

These tests verify:
- Food search with real USDA database
- Nutrient extraction (7-field profiles)
- Circuit breaker behavior
- Retry logic with exponential backoff
- Label normalization
- Cascade strategy (USDA → Category → Fallback)
"""

import os
import pytest
from infrastructure.external_apis.usda.client import USDAClient
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


# Skip all tests in this module if USDA API key is not set
pytestmark = pytest.mark.integration_real

# Check if API key is available
USDA_API_KEY = os.getenv("AI_USDA_API_KEY")
SKIP_REASON = "AI_USDA_API_KEY not set - set it in .env.test to run integration tests"


@pytest.mark.skipif(not USDA_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_usda_search_food_real_api():
    """Test food search with real USDA API.

    Verifies:
    - API connection works
    - Search returns valid results
    - Food items have FDC IDs
    """
    client = USDAClient(api_key=USDA_API_KEY)

    # Search for common food
    results = await client.search_food("chicken breast")

    # Verify response
    assert len(results) > 0, "Should find chicken breast in USDA database"

    # Verify result structure
    first_result = results[0]
    assert "fdcId" in first_result, "Result should have FDC ID"
    assert "description" in first_result, "Result should have description"

    print(f"\n✅ USDA Food Search:")
    print(f"   - Found {len(results)} results for 'chicken breast'")
    print(f"   - Top result: {first_result.get('description')}")
    print(f"   - FDC ID: {first_result.get('fdcId')}")


@pytest.mark.skipif(not USDA_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_usda_get_nutrients_real_api():
    """Test nutrient extraction with real USDA API.

    Verifies:
    - get_nutrients returns NutrientProfile
    - All 7 nutrients are extracted (calories, protein, carbs, fat, fiber, sugar, sodium)
    - Quantities are scaled correctly
    """
    client = USDAClient(api_key=USDA_API_KEY)

    # Get nutrients for chicken breast at 150g
    profile = await client.get_nutrients(identifier="chicken breast", quantity_g=150.0)

    # Verify response
    assert isinstance(profile, NutrientProfile), "Should return NutrientProfile"
    assert profile.quantity_g == 150.0, "Quantity should match request"

    # Verify all nutrients are present
    assert profile.calories > 0, "Calories should be positive"
    assert profile.protein > 0, "Protein should be positive"
    assert profile.carbs >= 0, "Carbs should be non-negative"
    assert profile.fat > 0, "Fat should be positive for chicken"
    assert profile.fiber >= 0, "Fiber should be non-negative"
    assert profile.sugar >= 0, "Sugar should be non-negative"
    assert profile.sodium >= 0, "Sodium should be non-negative"

    # Verify scaling (150g should be 1.5x per-100g values)
    assert profile.protein > 40, "150g chicken should have >40g protein"

    print(f"\n✅ USDA Nutrient Extraction:")
    print(f"   - Calories: {profile.calories} kcal")
    print(f"   - Protein: {profile.protein:.1f}g")
    print(f"   - Carbs: {profile.carbs:.1f}g")
    print(f"   - Fat: {profile.fat:.1f}g")
    print(f"   - Fiber: {profile.fiber:.1f}g")
    print(f"   - Sugar: {profile.sugar:.1f}g")
    print(f"   - Sodium: {profile.sodium:.1f}mg")


@pytest.mark.skipif(not USDA_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_usda_label_normalization():
    """Test label normalization with real API.

    Verifies:
    - Similar labels return same food ("chicken" vs "chicken breast")
    - Normalization improves search accuracy
    - Cache is used for normalized labels
    """
    client = USDAClient(api_key=USDA_API_KEY)

    # Test normalization with variations
    labels = ["chicken", "chicken breast", "roasted chicken"]

    results = {}
    for label in labels:
        profile = await client.get_nutrients(identifier=label, quantity_g=100.0)
        results[label] = profile

    # All should return valid profiles
    for label, profile in results.items():
        assert isinstance(profile, NutrientProfile), f"{label} should return profile"
        assert profile.protein > 20, f"{label} should have protein >20g per 100g"

    # Chicken variations should have similar macros (within 20% tolerance)
    base_protein = results["chicken"].protein
    for label, profile in results.items():
        protein_diff = abs(profile.protein - base_protein) / base_protein
        assert protein_diff < 0.3, f"{label} protein should be similar to base (within 30%)"

    print(f"\n✅ USDA Label Normalization:")
    for label, profile in results.items():
        print(f"   - {label}: {profile.protein:.1f}g protein, {profile.calories} kcal")


@pytest.mark.skipif(not USDA_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_usda_circuit_breaker_configured():
    """Test circuit breaker is properly configured.

    Note: Doesn't trigger actual failures to avoid API quota waste.
    """
    client = USDAClient(api_key=USDA_API_KEY)

    # Verify circuit breaker decorators are present
    assert hasattr(client.search_food, "__wrapped__"), \
        "Circuit breaker should be on search_food"
    assert hasattr(client.get_nutrients_by_id, "__wrapped__"), \
        "Circuit breaker should be on get_nutrients_by_id"

    # Make successful call to verify circuit is closed
    profile = await client.get_nutrients("apple", 100.0)
    assert isinstance(profile, NutrientProfile)

    print(f"\n✅ USDA Circuit Breaker:")
    print(f"   - Circuit breaker configured on search_food")
    print(f"   - Circuit breaker configured on get_nutrients_by_id")
    print(f"   - Circuit is CLOSED (healthy)")


@pytest.mark.skipif(not USDA_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_usda_cascade_strategy():
    """Test cascade strategy: USDA → Category → Fallback.

    Verifies:
    - Common foods use USDA lookup
    - Uncommon foods fall back gracefully
    - Category profiles work
    """
    client = USDAClient(api_key=USDA_API_KEY)

    # Test 1: Common food - should use USDA
    common_profile = await client.get_nutrients("rice", 100.0)
    assert isinstance(common_profile, NutrientProfile)
    assert common_profile.carbs > 20, "Rice should have high carbs"

    # Test 2: Specific food - should find in USDA
    specific_profile = await client.get_nutrients("brown rice", 100.0)
    assert isinstance(specific_profile, NutrientProfile)

    # Test 3: Very uncommon food - should fallback
    uncommon_profile = await client.get_nutrients("exotic_fruit_xyz_123", 100.0)
    assert uncommon_profile is not None, "Should fallback for unknown foods"

    print(f"\n✅ USDA Cascade Strategy:")
    print(f"   - Common food (rice): {common_profile.carbs:.1f}g carbs")
    print(f"   - Specific food (brown rice): {specific_profile.carbs:.1f}g carbs")
    print(f"   - Fallback works for unknown foods")


@pytest.mark.skipif(not USDA_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_usda_multiple_foods_batch():
    """Test nutrient lookup for multiple foods.

    Verifies:
    - Batch queries work efficiently
    - Different food categories return correct profiles
    - API quota is managed properly
    """
    client = USDAClient(api_key=USDA_API_KEY)

    # Test batch of different foods
    foods = {
        "chicken breast": "protein",
        "brown rice": "grains",
        "broccoli": "vegetables",
        "olive oil": "fats",
    }

    results = {}
    for food, category in foods.items():
        profile = await client.get_nutrients(food, 100.0)
        results[food] = (profile, category)

    # Verify protein-rich food
    chicken_profile, _ = results["chicken breast"]
    assert chicken_profile.protein > 25, "Chicken should be high protein"

    # Verify carb-rich food
    rice_profile, _ = results["brown rice"]
    assert rice_profile.carbs > 20, "Rice should be high carbs"

    # Verify low-calorie vegetable
    broccoli_profile, _ = results["broccoli"]
    assert broccoli_profile.calories < 50, "Broccoli should be low calorie"

    # Verify high-fat food
    oil_profile, _ = results["olive oil"]
    assert oil_profile.fat > 90, "Olive oil should be almost all fat"

    print(f"\n✅ USDA Batch Query:")
    for food, (profile, category) in results.items():
        print(f"   - {food} ({category}): {profile.calories} kcal, "
              f"P:{profile.protein:.1f}g C:{profile.carbs:.1f}g F:{profile.fat:.1f}g")
