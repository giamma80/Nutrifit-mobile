"""
Unit tests for USDA domain models.
"""

import time

import pytest

from backend.v2.domain.meal.nutrition.usda_models import (
    CategoryProfile,
    FoodCategory,
    USDACacheEntry,
    USDADataType,
    USDAFoodItem,
    USDANutrient,
    USDASearchResult,
)


class TestUSDANutrient:
    """Test USDANutrient model."""

    def test_create_valid_nutrient(self) -> None:
        """Should create valid nutrient."""
        nutrient = USDANutrient(
            number="208",
            name="Energy",
            amount=52.0,
            unit="kcal",
        )

        assert nutrient.number == "208"
        assert nutrient.name == "Energy"
        assert nutrient.amount == 52.0
        assert nutrient.unit == "kcal"

    def test_nutrient_is_immutable(self) -> None:
        """Should be immutable."""
        nutrient = USDANutrient(number="208", name="Energy", amount=52.0, unit="kcal")

        with pytest.raises(Exception):
            nutrient.amount = 100.0  # noqa: SLF001


class TestUSDAFoodItem:
    """Test USDAFoodItem model."""

    def test_create_valid_food_item(self) -> None:
        """Should create valid food item."""
        food = USDAFoodItem(
            fdc_id="123456",
            description="Apple, raw",
            data_type=USDADataType.SR_LEGACY,
            nutrients=[],
        )

        assert food.fdc_id == "123456"
        assert food.description == "Apple, raw"
        assert food.data_type == USDADataType.SR_LEGACY
        assert len(food.nutrients) == 0

    def test_food_with_nutrients(self) -> None:
        """Should store nutrients."""
        nutrients = [
            USDANutrient(number="208", name="Energy", amount=52.0, unit="kcal"),
            USDANutrient(number="203", name="Protein", amount=0.3, unit="g"),
        ]

        food = USDAFoodItem(
            fdc_id="123",
            description="Apple",
            data_type=USDADataType.SR_LEGACY,
            nutrients=nutrients,
        )

        assert len(food.nutrients) == 2
        assert food.nutrients[0].number == "208"
        assert food.nutrients[1].number == "203"

    def test_branded_food_with_barcode(self) -> None:
        """Should store branded food data."""
        food = USDAFoodItem(
            fdc_id="789",
            description="Coca Cola",
            data_type=USDADataType.BRANDED,
            nutrients=[],
            brand_owner="Coca-Cola Company",
            gtin_upc="049000050103",
        )

        assert food.brand_owner == "Coca-Cola Company"
        assert food.gtin_upc == "049000050103"

    def test_food_is_immutable(self) -> None:
        """Should be immutable."""
        food = USDAFoodItem(
            fdc_id="123",
            description="Apple",
            data_type=USDADataType.SR_LEGACY,
            nutrients=[],
        )

        with pytest.raises(Exception):
            food.description = "Banana"  # noqa: SLF001


class TestUSDASearchResult:
    """Test USDASearchResult model."""

    def test_create_empty_result(self) -> None:
        """Should create empty search result."""
        result = USDASearchResult(
            total_hits=0,
            current_page=1,
            total_pages=0,
            foods=[],
        )

        assert result.total_hits == 0
        assert len(result.foods) == 0

    def test_create_with_results(self) -> None:
        """Should create result with foods."""
        foods = [
            USDAFoodItem(
                fdc_id="1",
                description="Apple",
                data_type=USDADataType.SR_LEGACY,
                nutrients=[],
            ),
            USDAFoodItem(
                fdc_id="2",
                description="Banana",
                data_type=USDADataType.SR_LEGACY,
                nutrients=[],
            ),
        ]

        result = USDASearchResult(
            total_hits=2,
            current_page=1,
            total_pages=1,
            foods=foods,
        )

        assert result.total_hits == 2
        assert len(result.foods) == 2
        assert result.foods[0].description == "Apple"


class TestUSDACacheEntry:
    """Test USDACacheEntry model."""

    def test_create_cache_entry(self) -> None:
        """Should create valid cache entry."""
        food = USDAFoodItem(
            fdc_id="123",
            description="Apple",
            data_type=USDADataType.SR_LEGACY,
            nutrients=[],
        )

        expires_at = time.time() + 3600  # 1 hour

        entry = USDACacheEntry(
            key="barcode:123",
            food_item=food,
            expires_at=expires_at,
        )

        assert entry.key == "barcode:123"
        assert entry.food_item.fdc_id == "123"
        assert not entry.is_expired()

    def test_expired_entry(self) -> None:
        """Should detect expired entry."""
        food = USDAFoodItem(
            fdc_id="123",
            description="Apple",
            data_type=USDADataType.SR_LEGACY,
            nutrients=[],
        )

        expires_at = time.time() - 1  # Already expired

        entry = USDACacheEntry(
            key="barcode:123",
            food_item=food,
            expires_at=expires_at,
        )

        assert entry.is_expired()

    def test_not_expired_entry(self) -> None:
        """Should detect valid entry."""
        food = USDAFoodItem(
            fdc_id="123",
            description="Apple",
            data_type=USDADataType.SR_LEGACY,
            nutrients=[],
        )

        expires_at = time.time() + 3600

        entry = USDACacheEntry(
            key="barcode:123",
            food_item=food,
            expires_at=expires_at,
        )

        assert not entry.is_expired()


class TestCategoryProfile:
    """Test CategoryProfile model."""

    def test_create_fruit_profile(self) -> None:
        """Should create valid category profile."""
        profile = CategoryProfile(
            category=FoodCategory.FRUIT,
            calories_per_100g=52.0,
            protein_per_100g=0.3,
            carbs_per_100g=14.0,
            fat_per_100g=0.2,
        )

        assert profile.category == FoodCategory.FRUIT
        assert profile.calories_per_100g == 52.0
        assert profile.protein_per_100g == 0.3

    def test_profile_with_optional_nutrients(self) -> None:
        """Should handle optional nutrients."""
        profile = CategoryProfile(
            category=FoodCategory.VEGETABLE,
            calories_per_100g=25.0,
            protein_per_100g=2.0,
            carbs_per_100g=5.0,
            fat_per_100g=0.3,
            fiber_per_100g=2.0,
            sugar_per_100g=2.0,
            sodium_per_100g=20.0,
        )

        assert profile.fiber_per_100g == 2.0
        assert profile.sugar_per_100g == 2.0
        assert profile.sodium_per_100g == 20.0

    def test_reject_negative_values(self) -> None:
        """Should reject negative nutrient values."""
        with pytest.raises(ValueError):
            CategoryProfile(
                category=FoodCategory.FRUIT,
                calories_per_100g=-10.0,
                protein_per_100g=0.3,
                carbs_per_100g=14.0,
                fat_per_100g=0.2,
            )
