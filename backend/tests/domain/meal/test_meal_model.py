"""Tests for meal domain model.

Comprehensive test suite for meal aggregate root and value objects.
Tests business invariants, immutability, and domain behavior.
"""

import json
from datetime import datetime

import pytest

from domain.meal.model import (
    Meal,
    MealId,
    NutrientProfile,
    ProductInfo,
    ScaledNutrients,
    UserId,
)


class TestMealId:
    """Test cases for MealId value object."""

    def test_generate_creates_unique_ids(self) -> None:
        """Test that generate() creates unique identifiers."""
        id1 = MealId.generate()
        id2 = MealId.generate()

        assert id1 != id2
        assert isinstance(id1.value, str)
        assert len(id1.value) > 0

    def test_from_string_creates_valid_id(self) -> None:
        """Test creating MealId from string value."""
        test_id = "test-meal-id-123"
        meal_id = MealId.from_string(test_id)

        assert meal_id.value == test_id
        assert str(meal_id) == test_id

    def test_from_string_validates_input(self) -> None:
        """Test that from_string validates input."""
        with pytest.raises(ValueError, match="MealId must be non-empty string"):
            MealId.from_string("")

        with pytest.raises(ValueError, match="MealId must be non-empty string"):
            MealId.from_string(None)  # type: ignore

    def test_immutability(self) -> None:
        """Test that MealId is immutable."""
        meal_id = MealId.generate()

        with pytest.raises(AttributeError):
            meal_id.value = "new-value"  # type: ignore


class TestUserId:
    """Test cases for UserId value object."""

    def test_from_string_creates_valid_id(self) -> None:
        """Test creating UserId from string value."""
        test_id = "user-123"
        user_id = UserId.from_string(test_id)

        assert user_id.value == test_id
        assert str(user_id) == test_id

    def test_from_string_validates_input(self) -> None:
        """Test that from_string validates input."""
        with pytest.raises(ValueError, match="UserId must be non-empty string"):
            UserId.from_string("")

        with pytest.raises(ValueError, match="UserId must be non-empty string"):
            UserId.from_string(None)  # type: ignore


class TestNutrientProfile:
    """Test cases for NutrientProfile value object."""

    def test_scale_to_quantity_calculation(self) -> None:
        """Test nutrient scaling calculation."""
        profile = NutrientProfile(
            calories_per_100g=200.0,
            protein_per_100g=15.5,
            carbs_per_100g=30.0,
            fat_per_100g=8.2,
        )

        # Scale to 150g portion
        scaled = profile.scale_to_quantity(150.0)

        assert scaled.calories == 300  # 200 * 1.5, rounded to int
        assert scaled.protein == 23.25  # 15.5 * 1.5
        assert scaled.carbs == 45.0  # 30.0 * 1.5
        assert scaled.fat == 12.3  # 8.2 * 1.5
        assert scaled.fiber is None
        assert scaled.sugar is None
        assert scaled.sodium is None

    def test_scale_to_quantity_with_all_nutrients(self) -> None:
        """Test scaling with all nutrients populated."""
        profile = NutrientProfile(
            calories_per_100g=250.0,
            protein_per_100g=20.0,
            carbs_per_100g=40.0,
            fat_per_100g=10.0,
            fiber_per_100g=5.0,
            sugar_per_100g=15.0,
            sodium_per_100g=500.0,
        )

        # Scale to 80g portion
        scaled = profile.scale_to_quantity(80.0)

        assert scaled.calories == 200  # 250 * 0.8
        assert scaled.protein == 16.0  # 20.0 * 0.8
        assert scaled.carbs == 32.0  # 40.0 * 0.8
        assert scaled.fat == 8.0  # 10.0 * 0.8
        assert scaled.fiber == 4.0  # 5.0 * 0.8
        assert scaled.sugar == 12.0  # 15.0 * 0.8
        assert scaled.sodium == 400.0  # 500.0 * 0.8

    def test_scale_to_quantity_validates_positive_quantity(self) -> None:
        """Test that scale_to_quantity validates positive quantity."""
        profile = NutrientProfile(calories_per_100g=200.0)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            profile.scale_to_quantity(0.0)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            profile.scale_to_quantity(-10.0)

    def test_has_nutrients_detection(self) -> None:
        """Test has_nutrients() method."""
        # Empty profile
        empty_profile = NutrientProfile()
        assert not empty_profile.has_nutrients()

        # Profile with some nutrients
        profile_with_data = NutrientProfile(calories_per_100g=200.0)
        assert profile_with_data.has_nutrients()

        # Profile with different nutrient
        profile_with_protein = NutrientProfile(protein_per_100g=15.0)
        assert profile_with_protein.has_nutrients()


class TestScaledNutrients:
    """Test cases for ScaledNutrients value object."""

    def test_total_calories_returns_calories(self) -> None:
        """Test total_calories() method."""
        nutrients = ScaledNutrients(
            calories=300,
            protein=25.0,
            carbs=40.0,
            fat=12.0,
        )

        assert nutrients.total_calories() == 300

    def test_total_calories_returns_none_when_no_calories(self) -> None:
        """Test total_calories() with no calorie data."""
        nutrients = ScaledNutrients(protein=25.0, carbs=40.0)

        assert nutrients.total_calories() is None


class TestProductInfo:
    """Test cases for ProductInfo value object."""

    def test_enrich_meal_with_quantity(self) -> None:
        """Test enriching meal with scaled nutrients."""
        profile = NutrientProfile(
            calories_per_100g=350.0,
            protein_per_100g=12.0,
            carbs_per_100g=70.0,
            fat_per_100g=5.0,
        )

        product = ProductInfo(
            barcode="1234567890123",
            name="Test Product",
            nutrient_profile=profile,
        )

        # Get nutrients for 120g portion
        nutrients = product.enrich_meal_with_quantity(120.0)

        assert nutrients.calories == 420  # 350 * 1.2
        assert nutrients.protein == 14.4  # 12.0 * 1.2
        assert nutrients.carbs == 84.0  # 70.0 * 1.2
        assert nutrients.fat == 6.0  # 5.0 * 1.2


class TestMeal:
    """Test cases for Meal aggregate root."""

    def test_create_valid_meal(self) -> None:
        """Test creating valid meal."""
        meal_id = MealId.generate()
        user_id = UserId.from_string("user-123")
        timestamp = datetime(2024, 1, 15, 12, 30, 0)

        meal = Meal(
            id=meal_id,
            user_id=user_id,
            name="Chicken Breast",
            quantity_g=150.0,
            timestamp=timestamp,
        )

        assert meal.id == meal_id
        assert meal.user_id == user_id
        assert meal.name == "Chicken Breast"
        assert meal.quantity_g == 150.0
        assert meal.timestamp == timestamp
        assert meal.nutrients is None
        assert meal.barcode is None
        assert meal.idempotency_key is None

    def test_meal_validates_business_invariants(self) -> None:
        """Test meal validation of business rules."""
        meal_id = MealId.generate()
        user_id = UserId.from_string("user-123")
        timestamp = datetime.utcnow()

        # Empty name should fail
        with pytest.raises(ValueError, match="Meal name cannot be empty"):
            Meal(
                id=meal_id,
                user_id=user_id,
                name="",
                quantity_g=150.0,
                timestamp=timestamp,
            )

        # Zero quantity should fail
        with pytest.raises(ValueError, match="Meal quantity must be positive"):
            Meal(
                id=meal_id,
                user_id=user_id,
                name="Valid Name",
                quantity_g=0.0,
                timestamp=timestamp,
            )

        # Negative quantity should fail
        with pytest.raises(ValueError, match="Meal quantity must be positive"):
            Meal(
                id=meal_id,
                user_id=user_id,
                name="Valid Name",
                quantity_g=-10.0,
                timestamp=timestamp,
            )

    def test_update_nutrients(self) -> None:
        """Test updating meal with nutritional information."""
        meal = self._create_sample_meal()
        nutrients = ScaledNutrients(
            calories=300,
            protein=25.0,
            carbs=15.0,
            fat=8.0,
        )

        updated_meal = meal.update_nutrients(nutrients)

        # Original meal unchanged (immutability)
        assert meal.nutrients is None
        assert meal.nutrient_snapshot_json is None

        # New meal has nutrients
        assert updated_meal.nutrients == nutrients
        assert updated_meal.nutrient_snapshot_json is not None

        # Verify JSON snapshot
        snapshot = json.loads(updated_meal.nutrient_snapshot_json)
        assert snapshot["calories"] == 300
        assert snapshot["protein"] == 25.0
        assert snapshot["carbs"] == 15.0
        assert snapshot["fat"] == 8.0

    def test_change_quantity(self) -> None:
        """Test changing meal quantity."""
        meal = self._create_sample_meal()

        updated_meal = meal.change_quantity(200.0)

        # Original unchanged
        assert meal.quantity_g == 150.0

        # New meal has updated quantity
        assert updated_meal.quantity_g == 200.0
        assert updated_meal.id == meal.id  # Same ID
        assert updated_meal.name == meal.name  # Other fields unchanged

    def test_change_quantity_validates_positive(self) -> None:
        """Test quantity change validation."""
        meal = self._create_sample_meal()

        with pytest.raises(ValueError, match="New quantity must be positive"):
            meal.change_quantity(0.0)

        with pytest.raises(ValueError, match="New quantity must be positive"):
            meal.change_quantity(-50.0)

    def test_update_basic_info(self) -> None:
        """Test updating basic meal information."""
        meal = self._create_sample_meal()
        new_timestamp = datetime(2024, 1, 16, 18, 0, 0)

        updated_meal = meal.update_basic_info(
            name="Updated Chicken Breast",
            timestamp=new_timestamp,
            barcode="1234567890123",
        )

        # Original unchanged
        assert meal.name == "Chicken Breast"
        assert meal.barcode is None

        # New meal updated
        assert updated_meal.name == "Updated Chicken Breast"
        assert updated_meal.timestamp == new_timestamp
        assert updated_meal.barcode == "1234567890123"
        assert updated_meal.quantity_g == meal.quantity_g  # Unchanged

    def test_update_basic_info_validates_name(self) -> None:
        """Test basic info update validates name."""
        meal = self._create_sample_meal()

        with pytest.raises(ValueError, match="Meal name cannot be empty"):
            meal.update_basic_info(name="")

    def test_total_calories(self) -> None:
        """Test total_calories() method."""
        meal = self._create_sample_meal()

        # No nutrients yet
        assert meal.total_calories() is None

        # Add nutrients
        nutrients = ScaledNutrients(calories=250, protein=20.0)
        meal_with_nutrients = meal.update_nutrients(nutrients)

        assert meal_with_nutrients.total_calories() == 250

    def test_has_nutritional_data(self) -> None:
        """Test has_nutritional_data() method."""
        meal = self._create_sample_meal()

        # Initially no data
        assert not meal.has_nutritional_data()

        # Add nutrients
        nutrients = ScaledNutrients(calories=250)
        meal_with_nutrients = meal.update_nutrients(nutrients)

        assert meal_with_nutrients.has_nutritional_data()

    def test_has_barcode(self) -> None:
        """Test has_barcode() method."""
        meal = self._create_sample_meal()

        # Initially no barcode
        assert not meal.has_barcode()

        # Add barcode
        meal_with_barcode = meal.update_basic_info(barcode="1234567890123")

        assert meal_with_barcode.has_barcode()

        # Empty barcode should return False
        meal_with_empty_barcode = meal.update_basic_info(barcode="")
        assert not meal_with_empty_barcode.has_barcode()

    def test_should_recalculate_nutrients(self) -> None:
        """Test should_recalculate_nutrients() logic."""
        meal = self._create_sample_meal()

        # Quantity change should trigger recalculation
        assert meal.should_recalculate_nutrients(new_quantity_g=200.0)

        # Same quantity should not trigger
        assert not meal.should_recalculate_nutrients(new_quantity_g=150.0)

        # Barcode change should trigger recalculation
        assert meal.should_recalculate_nutrients(new_barcode="1234567890123")

        # Same barcode should not trigger
        assert not meal.should_recalculate_nutrients(new_barcode=None)

        # Both changing should trigger
        assert meal.should_recalculate_nutrients(
            new_quantity_g=200.0,
            new_barcode="1234567890123",
        )

    def test_immutability(self) -> None:
        """Test that Meal is immutable."""
        meal = self._create_sample_meal()

        with pytest.raises(AttributeError):
            meal.name = "New Name"  # type: ignore

        with pytest.raises(AttributeError):
            meal.quantity_g = 200.0  # type: ignore

    def _create_sample_meal(self) -> Meal:
        """Create a sample meal for testing."""
        return Meal(
            id=MealId.generate(),
            user_id=UserId.from_string("user-123"),
            name="Chicken Breast",
            quantity_g=150.0,
            timestamp=datetime(2024, 1, 15, 12, 30, 0),
        )
