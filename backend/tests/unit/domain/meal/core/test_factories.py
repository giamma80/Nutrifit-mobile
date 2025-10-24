"""Unit tests for MealFactory.

Tests factory methods for creating Meal aggregates from various sources.
"""

import pytest
from datetime import datetime, timezone

from domain.meal.core.factories import MealFactory
from domain.meal.core.entities.meal import Meal
from domain.meal.core.entities.meal_entry import MealEntry


class TestCreateFromAnalysis:
    """Test suite for create_from_analysis factory method."""

    def test_creates_meal_with_single_item(self) -> None:
        """Test creating meal from single analysis item."""
        items = [
            (
                {
                    "label": "pasta",
                    "display_name": "Pasta al Pomodoro",
                    "quantity_g": 150.0,
                    "confidence": 0.95,
                },
                {
                    "calories": 200,
                    "protein": 7.0,
                    "carbs": 40.0,
                    "fat": 2.0,
                },
            )
        ]

        meal = MealFactory.create_from_analysis(
            user_id="user123", items=items, source="PHOTO", meal_type="LUNCH"
        )

        assert isinstance(meal, Meal)
        assert meal.user_id == "user123"
        assert meal.meal_type == "LUNCH"
        assert len(meal.entries) == 1
        assert meal.total_calories == 200
        assert meal.total_protein == 7.0

    def test_creates_meal_with_multiple_items(self) -> None:
        """Test creating meal from multiple analysis items."""
        items = [
            (
                {"label": "pasta", "display_name": "Pasta", "quantity_g": 150.0},
                {"calories": 200, "protein": 7.0, "carbs": 40.0, "fat": 2.0},
            ),
            (
                {"label": "chicken", "display_name": "Grilled Chicken", "quantity_g": 100.0},
                {"calories": 165, "protein": 31.0, "carbs": 0.0, "fat": 3.6},
            ),
            (
                {"label": "salad", "display_name": "Mixed Salad", "quantity_g": 80.0},
                {"calories": 20, "protein": 1.0, "carbs": 4.0, "fat": 0.2},
            ),
        ]

        meal = MealFactory.create_from_analysis(
            user_id="user123", items=items, source="PHOTO", meal_type="LUNCH"
        )

        assert len(meal.entries) == 3
        assert meal.total_calories == 385  # 200 + 165 + 20
        assert meal.total_protein == 39.0  # 7 + 31 + 1
        assert meal.total_carbs == 44.0  # 40 + 0 + 4
        assert meal.total_fat == 5.8  # 2 + 3.6 + 0.2

    def test_creates_meal_with_optional_nutrients(self) -> None:
        """Test creating meal with optional micronutrients."""
        items = [
            (
                {"label": "banana", "display_name": "Banana", "quantity_g": 120.0},
                {
                    "calories": 105,
                    "protein": 1.3,
                    "carbs": 27.0,
                    "fat": 0.4,
                    "fiber": 3.1,
                    "sugar": 14.4,
                    "sodium": 1.2,
                },
            )
        ]

        meal = MealFactory.create_from_analysis(
            user_id="user123", items=items, source="MANUAL", meal_type="SNACK"
        )

        assert meal.total_fiber == 3.1
        assert meal.total_sugar == 14.4
        assert meal.total_sodium == 1.2

    def test_creates_meal_with_custom_timestamp(self) -> None:
        """Test creating meal with specific timestamp."""
        custom_time = datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        items = [
            (
                {"label": "pasta", "display_name": "Pasta", "quantity_g": 150.0},
                {"calories": 200, "protein": 7.0, "carbs": 40.0, "fat": 2.0},
            )
        ]

        meal = MealFactory.create_from_analysis(
            user_id="user123", items=items, source="PHOTO", timestamp=custom_time
        )

        assert meal.timestamp == custom_time

    def test_creates_meal_with_default_timestamp(self) -> None:
        """Test creating meal with default timestamp (now)."""
        before = datetime.now(timezone.utc)
        items = [
            (
                {"label": "pasta", "display_name": "Pasta", "quantity_g": 150.0},
                {"calories": 200, "protein": 7.0, "carbs": 40.0, "fat": 2.0},
            )
        ]

        meal = MealFactory.create_from_analysis(user_id="user123", items=items, source="PHOTO")
        after = datetime.now(timezone.utc)

        assert before <= meal.timestamp <= after

    def test_creates_meal_with_analysis_id(self) -> None:
        """Test creating meal with analysis_id."""
        items = [
            (
                {"label": "pasta", "display_name": "Pasta", "quantity_g": 150.0},
                {"calories": 200, "protein": 7.0, "carbs": 40.0, "fat": 2.0},
            )
        ]

        meal = MealFactory.create_from_analysis(
            user_id="user123", items=items, source="PHOTO", analysis_id="analysis_abc123"
        )

        assert meal.analysis_id == "analysis_abc123"

    def test_creates_meal_with_photo_url(self) -> None:
        """Test creating meal with photo_url."""
        items = [
            (
                {"label": "pasta", "display_name": "Pasta", "quantity_g": 150.0},
                {"calories": 200, "protein": 7.0, "carbs": 40.0, "fat": 2.0},
            )
        ]

        meal = MealFactory.create_from_analysis(
            user_id="user123",
            items=items,
            source="PHOTO",
            photo_url="https://example.com/meal.jpg",
        )

        # Photo URL should be in the entry
        assert meal.entries[0].image_url == "https://example.com/meal.jpg"

    def test_entries_have_correct_meal_id(self) -> None:
        """Test that all entries have the same meal_id as the meal."""
        items = [
            (
                {"label": "item1", "display_name": "Item 1", "quantity_g": 100.0},
                {"calories": 100, "protein": 5.0, "carbs": 10.0, "fat": 1.0},
            ),
            (
                {"label": "item2", "display_name": "Item 2", "quantity_g": 100.0},
                {"calories": 100, "protein": 5.0, "carbs": 10.0, "fat": 1.0},
            ),
        ]

        meal = MealFactory.create_from_analysis(user_id="user123", items=items, source="PHOTO")

        for entry in meal.entries:
            assert entry.meal_id == meal.id

    def test_entries_have_correct_source(self) -> None:
        """Test that entries have the correct source."""
        items = [
            (
                {"label": "pasta", "display_name": "Pasta", "quantity_g": 150.0},
                {"calories": 200, "protein": 7.0, "carbs": 40.0, "fat": 2.0},
            )
        ]

        meal = MealFactory.create_from_analysis(user_id="user123", items=items, source="BARCODE")

        assert meal.entries[0].source == "BARCODE"

    def test_preserves_confidence_from_recognition(self) -> None:
        """Test that confidence from recognition is preserved."""
        items = [
            (
                {
                    "label": "pasta",
                    "display_name": "Pasta",
                    "quantity_g": 150.0,
                    "confidence": 0.87,
                },
                {"calories": 200, "protein": 7.0, "carbs": 40.0, "fat": 2.0},
            )
        ]

        meal = MealFactory.create_from_analysis(user_id="user123", items=items, source="PHOTO")

        assert meal.entries[0].confidence == 0.87

    def test_defaults_confidence_to_1_if_not_provided(self) -> None:
        """Test that confidence defaults to 1.0 if not in recognition data."""
        items = [
            (
                {"label": "pasta", "display_name": "Pasta", "quantity_g": 150.0},
                {"calories": 200, "protein": 7.0, "carbs": 40.0, "fat": 2.0},
            )
        ]

        meal = MealFactory.create_from_analysis(user_id="user123", items=items, source="MANUAL")

        assert meal.entries[0].confidence == 1.0

    def test_preserves_optional_metadata(self) -> None:
        """Test that optional metadata (category, barcode) is preserved."""
        items = [
            (
                {
                    "label": "pasta",
                    "display_name": "Pasta",
                    "quantity_g": 150.0,
                    "category": "grains",
                    "barcode": "1234567890",
                },
                {"calories": 200, "protein": 7.0, "carbs": 40.0, "fat": 2.0},
            )
        ]

        meal = MealFactory.create_from_analysis(user_id="user123", items=items, source="BARCODE")

        assert meal.entries[0].category == "grains"
        assert meal.entries[0].barcode == "1234567890"

    def test_raises_if_items_empty(self) -> None:
        """Test that ValueError is raised if items list is empty."""
        with pytest.raises(ValueError, match="Cannot create meal with no items"):
            MealFactory.create_from_analysis(user_id="user123", items=[], source="PHOTO")


class TestCreateManual:
    """Test suite for create_manual factory method."""

    def test_creates_meal_with_manual_entry(self) -> None:
        """Test creating meal from manual entry."""
        meal = MealFactory.create_manual(
            user_id="user123",
            name="Banana",
            quantity_g=120.0,
            calories=105,
            protein=1.3,
            carbs=27.0,
            fat=0.4,
            meal_type="SNACK",
        )

        assert isinstance(meal, Meal)
        assert meal.user_id == "user123"
        assert meal.meal_type == "SNACK"
        assert len(meal.entries) == 1
        assert meal.total_calories == 105
        assert meal.total_protein == 1.3

    def test_manual_entry_has_correct_attributes(self) -> None:
        """Test that manual entry has correct attributes."""
        meal = MealFactory.create_manual(
            user_id="user123",
            name="Apple",
            quantity_g=150.0,
            calories=78,
            protein=0.4,
            carbs=20.8,
            fat=0.3,
        )

        entry = meal.entries[0]
        assert entry.name == "Apple"
        assert entry.display_name == "Apple"
        assert entry.quantity_g == 150.0
        assert entry.source == "MANUAL"
        assert entry.confidence == 1.0

    def test_creates_meal_with_optional_micronutrients(self) -> None:
        """Test creating manual meal with optional micronutrients."""
        meal = MealFactory.create_manual(
            user_id="user123",
            name="Oatmeal",
            quantity_g=200.0,
            calories=150,
            protein=5.0,
            carbs=27.0,
            fat=3.0,
            fiber=4.0,
            sugar=1.0,
            sodium=5.0,
        )

        assert meal.total_fiber == 4.0
        assert meal.total_sugar == 1.0
        assert meal.total_sodium == 5.0

    def test_creates_meal_with_custom_timestamp(self) -> None:
        """Test creating manual meal with custom timestamp."""
        custom_time = datetime(2025, 1, 15, 8, 0, 0, tzinfo=timezone.utc)

        meal = MealFactory.create_manual(
            user_id="user123",
            name="Eggs",
            quantity_g=100.0,
            calories=155,
            protein=13.0,
            carbs=1.1,
            fat=11.0,
            timestamp=custom_time,
        )

        assert meal.timestamp == custom_time

    def test_creates_meal_with_default_timestamp(self) -> None:
        """Test creating manual meal with default timestamp."""
        before = datetime.now(timezone.utc)

        meal = MealFactory.create_manual(
            user_id="user123",
            name="Eggs",
            quantity_g=100.0,
            calories=155,
            protein=13.0,
            carbs=1.1,
            fat=11.0,
        )

        after = datetime.now(timezone.utc)
        assert before <= meal.timestamp <= after

    def test_entry_has_correct_meal_id(self) -> None:
        """Test that entry has same meal_id as meal."""
        meal = MealFactory.create_manual(
            user_id="user123",
            name="Rice",
            quantity_g=200.0,
            calories=260,
            protein=5.0,
            carbs=58.0,
            fat=0.5,
        )

        assert meal.entries[0].meal_id == meal.id

    def test_default_meal_type_is_snack(self) -> None:
        """Test that default meal_type is SNACK."""
        meal = MealFactory.create_manual(
            user_id="user123",
            name="Nuts",
            quantity_g=30.0,
            calories=180,
            protein=6.0,
            carbs=6.0,
            fat=16.0,
        )

        assert meal.meal_type == "SNACK"


class TestCreateEmpty:
    """Test suite for create_empty factory method."""

    def test_creates_empty_meal_with_placeholder(self) -> None:
        """Test creating empty meal with placeholder entry."""
        meal, meal_id = MealFactory.create_empty(user_id="user123", meal_type="BREAKFAST")

        assert isinstance(meal, Meal)
        assert meal.user_id == "user123"
        assert meal.meal_type == "BREAKFAST"
        assert len(meal.entries) == 1
        assert meal.entries[0].name == "placeholder"
        assert meal.id == meal_id

    def test_placeholder_has_zero_nutrients(self) -> None:
        """Test that placeholder entry has zero nutrients."""
        meal, _ = MealFactory.create_empty(user_id="user123")

        assert meal.total_calories == 0
        assert meal.total_protein == 0.0
        assert meal.total_carbs == 0.0
        assert meal.total_fat == 0.0

    def test_returns_meal_id_for_creating_entries(self) -> None:
        """Test that returned meal_id matches meal.id."""
        meal, meal_id = MealFactory.create_empty(user_id="user123")

        assert meal_id == meal.id
        assert meal.entries[0].meal_id == meal_id

    def test_creates_with_custom_timestamp(self) -> None:
        """Test creating empty meal with custom timestamp."""
        custom_time = datetime(2025, 1, 15, 7, 0, 0, tzinfo=timezone.utc)

        meal, _ = MealFactory.create_empty(user_id="user123", timestamp=custom_time)

        assert meal.timestamp == custom_time

    def test_default_meal_type_is_snack(self) -> None:
        """Test that default meal_type is SNACK."""
        meal, _ = MealFactory.create_empty(user_id="user123")

        assert meal.meal_type == "SNACK"


class TestFactoryInvariantsAndValidation:
    """Test suite for factory validation and invariants."""

    def test_totals_are_correctly_calculated(self) -> None:
        """Test that factory correctly calculates totals."""
        items = [
            (
                {"label": "item1", "display_name": "Item 1", "quantity_g": 100.0},
                {"calories": 100, "protein": 10.0, "carbs": 15.0, "fat": 2.0},
            ),
            (
                {"label": "item2", "display_name": "Item 2", "quantity_g": 100.0},
                {"calories": 200, "protein": 20.0, "carbs": 25.0, "fat": 5.0},
            ),
        ]

        meal = MealFactory.create_from_analysis(user_id="user123", items=items, source="PHOTO")

        # Verify totals match sum of entries
        assert meal.total_calories == sum(e.calories for e in meal.entries)
        assert meal.total_protein == sum(e.protein for e in meal.entries)
        assert meal.total_carbs == sum(e.carbs for e in meal.entries)
        assert meal.total_fat == sum(e.fat for e in meal.entries)

    def test_created_meal_passes_invariant_validation(self) -> None:
        """Test that factory-created meals pass invariant validation."""
        meal = MealFactory.create_manual(
            user_id="user123",
            name="Test Food",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
        )

        # Should not raise
        meal.validate_invariants()

    def test_all_entries_are_mealentry_instances(self) -> None:
        """Test that all entries are MealEntry instances."""
        items = [
            (
                {"label": "item1", "display_name": "Item 1", "quantity_g": 100.0},
                {"calories": 100, "protein": 5.0, "carbs": 10.0, "fat": 1.0},
            ),
            (
                {"label": "item2", "display_name": "Item 2", "quantity_g": 100.0},
                {"calories": 100, "protein": 5.0, "carbs": 10.0, "fat": 1.0},
            ),
        ]

        meal = MealFactory.create_from_analysis(user_id="user123", items=items, source="PHOTO")

        for entry in meal.entries:
            assert isinstance(entry, MealEntry)
