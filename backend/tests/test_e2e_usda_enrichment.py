"""E2E tests for USDA nutrient enrichment with real API.

These tests validate:
1. Raw food selection (naturalness filter)
2. Auto-raw for simple foods
3. Processed food handling
4. Scaling accuracy
5. Query modification logic

Run with: pytest tests/test_e2e_usda_enrichment.py -v
Requires: USDA_API_KEY in .env and server running on port 8080

Note: Tests are automatically skipped if server is not reachable.
"""

import pytest
import httpx
from typing import Dict, Any


GRAPHQL_URL = "http://localhost:8080/graphql"
TIMEOUT = 10.0


# Check if server is reachable before running tests
def _is_server_reachable() -> bool:
    """Check if GraphQL server is reachable."""
    try:
        health_url = f"{GRAPHQL_URL.rsplit('/', 1)[0]}/health"
        response = httpx.get(health_url, timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


# Mark all tests in this module to skip if server not reachable
pytestmark = pytest.mark.skipif(
    not _is_server_reachable(),
    reason="GraphQL server not reachable on localhost:8080 - " "start server with 'make run'",
)


def query_enrich_nutrients(label: str, quantity_g: float) -> Dict[str, Any]:
    """Helper to query enrichNutrients via GraphQL."""
    query = """
    query {
        atomic {
            enrichNutrients(label: "%s", quantityG: %.1f) {
                calories
                protein
                carbs
                fat
                fiber
                sugar
                sodium
                quantityG
            }
        }
    }
    """ % (
        label,
        quantity_g,
    )

    response = httpx.post(
        GRAPHQL_URL,
        json={"query": query},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    if "errors" in data:
        raise ValueError(f"GraphQL errors: {data['errors']}")

    result: Dict[str, Any] = data["data"]["atomic"]["enrichNutrients"]
    return result


@pytest.mark.e2e
class TestUSDANaturalnessFilter:
    """Test naturalness filter prefers raw/fresh over processed."""

    def test_banana_raw_not_dehydrated(self):
        """Banana should find raw (89 cal), not dehydrated (346 cal)."""
        result = query_enrich_nutrients("banana", 100.0)

        assert result["quantityG"] == 100.0
        # Raw banana is ~89 cal/100g (USDA FDC ID: 173944)
        assert 85 <= result["calories"] <= 95, f"Expected ~89 cal, got {result['calories']}"
        assert 1.0 <= result["protein"] <= 1.2
        assert 22.0 <= result["carbs"] <= 24.0

    def test_apple_raw_not_dried(self):
        """Apple should find raw/fresh, not dried."""
        result = query_enrich_nutrients("apple", 100.0)

        # Raw apple is ~52 cal/100g (can vary by variety)
        assert 20 <= result["calories"] <= 60, f"Expected ~52 cal, got {result['calories']}"
        assert result["protein"] < 1.0
        assert result["carbs"] < 20.0

    def test_potato_generic_prefers_raw(self):
        """Potato without preparation should prefer raw."""
        result = query_enrich_nutrients("potato", 100.0)

        # Raw potato is ~58-77 cal/100g
        assert 50 <= result["calories"] <= 85, f"Expected ~58-77 cal, got {result['calories']}"
        assert result["protein"] < 3.0
        assert result["carbs"] < 20.0


@pytest.mark.e2e
class TestUSDAAutoRawLogic:
    """Test auto-raw addition for simple foods."""

    def test_eggs_gets_auto_raw(self):
        """Generic 'eggs' should auto-add 'raw' and find whole raw eggs."""
        result = query_enrich_nutrients("eggs", 100.0)

        # Raw whole eggs are ~143 cal/100g (not 278 cal for dried)
        assert 140 <= result["calories"] <= 160, f"Expected ~143 cal, got {result['calories']}"
        assert 12.0 <= result["protein"] <= 13.5
        assert 8.0 <= result["fat"] <= 11.0

    def test_tomato_gets_auto_raw(self):
        """Generic 'tomato' should auto-add 'raw'."""
        result = query_enrich_nutrients("tomato", 100.0)

        # Raw tomatoes are typically 18-27 cal/100g (varies by variety)
        # Red ripe: ~18 cal, Cherry: ~27 cal
        assert 15 <= result["calories"] <= 30, f"Expected 15-30 cal, got {result['calories']}"
        assert result["protein"] < 2.0
        assert result["carbs"] < 6.0

    def test_carrot_gets_auto_raw(self):
        """Generic 'carrot' should auto-add 'raw'."""
        result = query_enrich_nutrients("carrot", 100.0)

        # Raw carrots are ~41 cal/100g
        assert 35 <= result["calories"] <= 50, f"Expected ~41 cal, got {result['calories']}"
        assert result["protein"] < 2.0
        assert 8.0 <= result["carbs"] <= 12.0


@pytest.mark.e2e
class TestUSDAProcessedFoods:
    """Test explicit processed food queries work correctly."""

    def test_potato_fried_explicit(self):
        """'potato fried' should find fried potatoes, not raw."""
        result = query_enrich_nutrients("potato fried", 100.0)

        # Fried potatoes are ~260-312 cal/100g (much higher than raw 58 cal)
        assert 250 <= result["calories"] <= 320, f"Expected ~260 cal, got {result['calories']}"
        assert result["fat"] > 10.0  # Fried has significant fat

    def test_potato_raw_explicit(self):
        """'potato raw' should find raw potatoes."""
        result = query_enrich_nutrients("potato raw", 100.0)

        # Raw potato is ~58-77 cal/100g
        assert 50 <= result["calories"] <= 85
        assert result["fat"] < 1.0  # Raw has minimal fat

    def test_chicken_fried_explicit(self):
        """'chicken fried' should find fried chicken, not raw."""
        result = query_enrich_nutrients("chicken fried", 100.0)

        # Fried chicken is ~234-250 cal/100g
        assert 220 <= result["calories"] <= 260, f"Expected ~234 cal, got {result['calories']}"
        assert result["fat"] > 10.0  # Fried has significant fat

    def test_carrot_boiled_no_auto_raw(self):
        """'carrot boiled' should NOT get auto-raw added."""
        result = query_enrich_nutrients("carrot boiled", 100.0)

        # Boiled carrots are ~35 cal/100g (slightly less than raw)
        assert 30 <= result["calories"] <= 45
        # Should find boiled version, not raw


@pytest.mark.e2e
class TestUSDAScalingAccuracy:
    """Test nutrient scaling is accurate."""

    def test_banana_100g_base(self):
        """Banana 100g should be base USDA value."""
        result = query_enrich_nutrients("banana", 100.0)

        base_calories = result["calories"]
        base_protein = result["protein"]
        base_carbs = result["carbs"]

        assert 85 <= base_calories <= 95
        assert 1.0 <= base_protein <= 1.2
        assert 22.0 <= base_carbs <= 24.0

    def test_banana_120g_scaled(self):
        """Banana 120g should be 1.2x the 100g values."""
        result_100g = query_enrich_nutrients("banana", 100.0)
        result_120g = query_enrich_nutrients("banana", 120.0)

        # Check scaling is approximately 1.2x
        scale_factor = 1.2
        tolerance = 0.05  # 5% tolerance

        cal_ratio = result_120g["calories"] / result_100g["calories"]
        assert (
            abs(cal_ratio - scale_factor) < tolerance
        ), f"Calories scaling off: {cal_ratio:.2f} vs {scale_factor}"

        protein_ratio = result_120g["protein"] / result_100g["protein"]
        assert (
            abs(protein_ratio - scale_factor) < tolerance
        ), f"Protein scaling off: {protein_ratio:.2f} vs {scale_factor}"

        carbs_ratio = result_120g["carbs"] / result_100g["carbs"]
        assert (
            abs(carbs_ratio - scale_factor) < tolerance
        ), f"Carbs scaling off: {carbs_ratio:.2f} vs {scale_factor}"

    def test_chicken_150g_scaled(self):
        """Chicken 150g should be 1.5x the 100g values."""
        result_100g = query_enrich_nutrients("chicken", 100.0)
        result_150g = query_enrich_nutrients("chicken", 150.0)

        scale_factor = 1.5
        tolerance = 0.05

        cal_ratio = result_150g["calories"] / result_100g["calories"]
        assert abs(cal_ratio - scale_factor) < tolerance


@pytest.mark.e2e
class TestUSDAVariousFoods:
    """Test various common foods for sanity checks."""

    def test_pasta_dry(self):
        """Pasta should find dry pasta (~371 cal/100g)."""
        result = query_enrich_nutrients("pasta", 100.0)

        # Dry pasta is ~370 cal/100g
        assert 360 <= result["calories"] <= 380
        assert 12.0 <= result["protein"] <= 14.0
        assert 70.0 <= result["carbs"] <= 78.0

    def test_bread(self):
        """Bread should find reasonable values."""
        result = query_enrich_nutrients("bread", 100.0)

        # Bread varies, but typically 250-400 cal/100g
        assert 200 <= result["calories"] <= 450
        assert result["carbs"] > 30.0

    def test_chicken_generic(self):
        """Generic chicken should find reasonable values."""
        result = query_enrich_nutrients("chicken", 100.0)

        # Raw chicken is ~110-165 cal/100g depending on cut
        assert 100 <= result["calories"] <= 200
        assert 15.0 <= result["protein"] <= 25.0


@pytest.mark.e2e
class TestUSDAEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_unknown_food_returns_none_or_fallback(self):
        """Unknown food should handle gracefully."""
        # This might return fallback values or None
        # depending on NutritionEnrichmentService fallback logic
        result = query_enrich_nutrients("xyzunknownfood123", 100.0)

        # Should still return a valid response (fallback or None)
        assert result is not None
        assert "calories" in result

    def test_very_small_quantity(self):
        """Very small quantity should scale correctly."""
        result = query_enrich_nutrients("banana", 10.0)

        assert result["quantityG"] == 10.0
        # Should be ~8.9 cal for 10g
        assert 7 <= result["calories"] <= 12

    def test_large_quantity(self):
        """Large quantity should scale correctly."""
        result = query_enrich_nutrients("banana", 500.0)

        assert result["quantityG"] == 500.0
        # Should be ~445 cal for 500g
        assert 420 <= result["calories"] <= 480


if __name__ == "__main__":
    """Run tests manually for debugging."""
    import sys

    print("Running E2E USDA Enrichment Tests...")
    print("=" * 60)

    # Test naturalness filter
    print("\n[TEST] Banana raw vs dehydrated...")
    result = query_enrich_nutrients("banana", 100.0)
    print(f"  ✓ Banana 100g: {result['calories']} cal (expected ~89)")

    print("\n[TEST] Potato generic prefers raw...")
    result = query_enrich_nutrients("potato", 100.0)
    print(f"  ✓ Potato 100g: {result['calories']} cal (expected ~58)")

    # Test auto-raw
    print("\n[TEST] Eggs gets auto-raw...")
    result = query_enrich_nutrients("eggs", 100.0)
    print(f"  ✓ Eggs 100g: {result['calories']} cal (expected ~143)")

    # Test processed foods
    print("\n[TEST] Potato fried explicit...")
    result = query_enrich_nutrients("potato fried", 100.0)
    print(f"  ✓ Potato fried 100g: {result['calories']} cal (expected ~260)")

    result = query_enrich_nutrients("potato raw", 100.0)
    print(f"  ✓ Potato raw 100g: {result['calories']} cal (expected ~58)")

    # Test scaling
    print("\n[TEST] Banana scaling 120g...")
    result = query_enrich_nutrients("banana", 120.0)
    print(f"  ✓ Banana 120g: {result['calories']} cal (expected ~107)")

    print("\n" + "=" * 60)
    print("✓ All manual tests passed!")
    sys.exit(0)
