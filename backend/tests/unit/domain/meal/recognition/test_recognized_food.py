"""Unit tests for RecognizedFood entities.

Tests validation, business logic, and invariants.
"""

import pytest

from domain.meal.recognition.entities import FoodRecognitionResult, RecognizedFood


class TestRecognizedFood:
    """Test suite for RecognizedFood entity."""

    def test_creates_recognized_food_with_required_fields(self) -> None:
        """Test creating recognized food with required fields."""
        food = RecognizedFood(
            label="pasta",
            display_name="Spaghetti al Pomodoro",
            quantity_g=150.0,
            confidence=0.92,
        )

        assert food.label == "pasta"
        assert food.display_name == "Spaghetti al Pomodoro"
        assert food.quantity_g == 150.0
        assert food.confidence == 0.92
        assert food.category is None

    def test_creates_recognized_food_with_category(self) -> None:
        """Test creating recognized food with category."""
        food = RecognizedFood(
            label="chicken_breast",
            display_name="Grilled Chicken Breast",
            quantity_g=120.0,
            confidence=0.88,
            category="meat",
        )

        assert food.category == "meat"

    def test_raises_if_quantity_not_positive(self) -> None:
        """Test that non-positive quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            RecognizedFood(
                label="pasta",
                display_name="Pasta",
                quantity_g=0.0,
                confidence=0.9,
            )

        with pytest.raises(ValueError, match="Quantity must be positive"):
            RecognizedFood(
                label="pasta",
                display_name="Pasta",
                quantity_g=-10.0,
                confidence=0.9,
            )

    def test_raises_if_confidence_out_of_range(self) -> None:
        """Test that confidence outside [0, 1] raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            RecognizedFood(
                label="pasta",
                display_name="Pasta",
                quantity_g=150.0,
                confidence=-0.1,
            )

        with pytest.raises(ValueError, match="Confidence must be between"):
            RecognizedFood(
                label="pasta",
                display_name="Pasta",
                quantity_g=150.0,
                confidence=1.5,
            )

    def test_is_reliable_returns_true_for_high_confidence(self) -> None:
        """Test that is_reliable returns True for confidence > 0.7."""
        food = RecognizedFood(
            label="pasta",
            display_name="Pasta",
            quantity_g=150.0,
            confidence=0.85,
        )

        assert food.is_reliable() is True

    def test_is_reliable_returns_false_for_low_confidence(self) -> None:
        """Test that is_reliable returns False for confidence <= 0.7."""
        food = RecognizedFood(
            label="mystery",
            display_name="Unknown Food",
            quantity_g=100.0,
            confidence=0.6,
        )

        assert food.is_reliable() is False

    def test_is_reliable_boundary_at_0_7(self) -> None:
        """Test is_reliable boundary exactly at 0.7."""
        food_exactly = RecognizedFood(
            label="food",
            display_name="Food",
            quantity_g=100.0,
            confidence=0.7,
        )
        assert food_exactly.is_reliable() is False  # > 0.7, not >= 0.7

        food_above = RecognizedFood(
            label="food",
            display_name="Food",
            quantity_g=100.0,
            confidence=0.71,
        )
        assert food_above.is_reliable() is True


class TestFoodRecognitionResult:
    """Test suite for FoodRecognitionResult entity."""

    def test_creates_result_with_single_item(self) -> None:
        """Test creating result with single item."""
        item = RecognizedFood("pasta", "Pasta", 150.0, 0.9)
        result = FoodRecognitionResult(items=[item])

        assert len(result.items) == 1
        assert result.confidence == 0.9  # Auto-calculated from single item
        assert result.dish_name is None
        assert result.processing_time_ms == 0

    def test_creates_result_with_multiple_items(self) -> None:
        """Test creating result with multiple items."""
        items = [
            RecognizedFood("pasta", "Pasta", 150.0, 0.9),
            RecognizedFood("chicken", "Chicken", 100.0, 0.85),
            RecognizedFood("salad", "Salad", 80.0, 0.92),
        ]
        result = FoodRecognitionResult(items=items)

        assert len(result.items) == 3

    def test_auto_calculates_average_confidence(self) -> None:
        """Test that average confidence is auto-calculated."""
        items = [
            RecognizedFood("food1", "Food 1", 100.0, 0.9),
            RecognizedFood("food2", "Food 2", 100.0, 0.8),
        ]
        result = FoodRecognitionResult(items=items)

        # Average: (0.9 + 0.8) / 2 = 0.85
        assert pytest.approx(result.confidence, abs=0.001) == 0.85

    def test_uses_provided_confidence_if_not_zero(self) -> None:
        """Test that provided confidence is used if not zero."""
        items = [
            RecognizedFood("food1", "Food 1", 100.0, 0.9),
            RecognizedFood("food2", "Food 2", 100.0, 0.8),
        ]
        result = FoodRecognitionResult(items=items, confidence=0.95)

        assert result.confidence == 0.95  # Uses provided value

    def test_creates_result_with_dish_name(self) -> None:
        """Test creating result with overall dish name."""
        items = [RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
        result = FoodRecognitionResult(items=items, dish_name="Italian Lunch")

        assert result.dish_name == "Italian Lunch"

    def test_creates_result_with_processing_time(self) -> None:
        """Test creating result with processing time."""
        items = [RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
        result = FoodRecognitionResult(
            items=items,
            processing_time_ms=1250,
        )

        assert result.processing_time_ms == 1250

    def test_raises_if_items_empty(self) -> None:
        """Test that empty items list raises ValueError."""
        with pytest.raises(ValueError, match="Recognition must have at least one item"):
            FoodRecognitionResult(items=[])

    def test_is_reliable_returns_true_for_high_confidence(self) -> None:
        """Test that is_reliable returns True for average confidence > 0.7."""
        items = [
            RecognizedFood("food1", "Food 1", 100.0, 0.9),
            RecognizedFood("food2", "Food 2", 100.0, 0.85),
        ]
        result = FoodRecognitionResult(items=items)

        # Average: 0.875 > 0.7
        assert result.is_reliable() is True

    def test_is_reliable_returns_false_for_low_confidence(self) -> None:
        """Test that is_reliable returns False for average confidence <= 0.7."""
        items = [
            RecognizedFood("food1", "Food 1", 100.0, 0.6),
            RecognizedFood("food2", "Food 2", 100.0, 0.65),
        ]
        result = FoodRecognitionResult(items=items)

        # Average: 0.625 <= 0.7
        assert result.is_reliable() is False

    def test_total_quantity_g_sums_all_items(self) -> None:
        """Test that total_quantity_g sums all item quantities."""
        items = [
            RecognizedFood("pasta", "Pasta", 150.0, 0.9),
            RecognizedFood("chicken", "Chicken", 120.0, 0.85),
            RecognizedFood("salad", "Salad", 80.0, 0.92),
        ]
        result = FoodRecognitionResult(items=items)

        assert result.total_quantity_g() == 350.0  # 150 + 120 + 80

    def test_item_count_returns_number_of_items(self) -> None:
        """Test that item_count returns correct number."""
        items = [
            RecognizedFood("food1", "Food 1", 100.0, 0.9),
            RecognizedFood("food2", "Food 2", 100.0, 0.8),
            RecognizedFood("food3", "Food 3", 100.0, 0.85),
        ]
        result = FoodRecognitionResult(items=items)

        assert result.item_count() == 3

    def test_reliable_items_filters_by_confidence(self) -> None:
        """Test that reliable_items returns only items with confidence > 0.7."""
        items = [
            RecognizedFood("reliable1", "Reliable 1", 100.0, 0.9),  # Reliable
            RecognizedFood("unreliable", "Unreliable", 100.0, 0.5),  # Not reliable
            RecognizedFood("reliable2", "Reliable 2", 100.0, 0.85),  # Reliable
            RecognizedFood("borderline", "Borderline", 100.0, 0.7),  # Not reliable (<=)
        ]
        result = FoodRecognitionResult(items=items)

        reliable = result.reliable_items()

        assert len(reliable) == 2
        assert reliable[0].label == "reliable1"
        assert reliable[1].label == "reliable2"

    def test_reliable_items_returns_empty_if_none_reliable(self) -> None:
        """Test that reliable_items returns empty list if no items are reliable."""
        items = [
            RecognizedFood("food1", "Food 1", 100.0, 0.5),
            RecognizedFood("food2", "Food 2", 100.0, 0.6),
        ]
        result = FoodRecognitionResult(items=items)

        reliable = result.reliable_items()

        assert len(reliable) == 0

    def test_reliable_items_returns_all_if_all_reliable(self) -> None:
        """Test that reliable_items returns all items if all are reliable."""
        items = [
            RecognizedFood("food1", "Food 1", 100.0, 0.9),
            RecognizedFood("food2", "Food 2", 100.0, 0.85),
        ]
        result = FoodRecognitionResult(items=items)

        reliable = result.reliable_items()

        assert len(reliable) == 2
