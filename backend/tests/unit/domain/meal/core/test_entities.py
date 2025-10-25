"""Unit tests for domain entities.

Tests MealEntry and Meal aggregate root business logic, invariants, and methods.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from domain.meal.core.entities import MealEntry, Meal


class TestMealEntry:
    """Test suite for MealEntry entity."""

    def test_creates_with_valid_data(self) -> None:
        """Test creating MealEntry with all required fields."""
        entry_id = uuid4()
        meal_id = uuid4()

        entry = MealEntry(
            id=entry_id,
            meal_id=meal_id,
            name="pasta",
            display_name="Pasta al Pomodoro",
            quantity_g=150.0,
            calories=300,
            protein=12.0,
            carbs=55.0,
            fat=3.5,
        )

        assert entry.id == entry_id
        assert entry.meal_id == meal_id
        assert entry.name == "pasta"
        assert entry.display_name == "Pasta al Pomodoro"
        assert entry.quantity_g == 150.0
        assert entry.calories == 300
        assert entry.protein == 12.0
        assert entry.carbs == 55.0
        assert entry.fat == 3.5
        assert entry.source == "MANUAL"  # default
        assert entry.confidence == 1.0  # default

    def test_creates_with_optional_micronutrients(self) -> None:
        """Test creating MealEntry with optional micronutrients."""
        entry = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="apple",
            display_name="Apple",
            quantity_g=100.0,
            calories=52,
            protein=0.3,
            carbs=14.0,
            fat=0.2,
            fiber=2.4,
            sugar=10.3,
            sodium=1.0,
        )

        assert entry.fiber == 2.4
        assert entry.sugar == 10.3
        assert entry.sodium == 1.0

    def test_creates_with_metadata(self) -> None:
        """Test creating MealEntry with metadata fields."""
        entry = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="banana",
            display_name="Banana",
            quantity_g=120.0,
            calories=105,
            protein=1.3,
            carbs=27.0,
            fat=0.4,
            source="PHOTO",
            confidence=0.85,
            category="fruits",
            barcode="123456789",
            image_url="https://example.com/banana.jpg",
        )

        assert entry.source == "PHOTO"
        assert entry.confidence == 0.85
        assert entry.category == "fruits"
        assert entry.barcode == "123456789"
        assert entry.image_url == "https://example.com/banana.jpg"

    def test_validates_quantity_positive(self) -> None:
        """Test that quantity_g must be positive."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            MealEntry(
                id=uuid4(),
                meal_id=uuid4(),
                name="test",
                display_name="Test",
                quantity_g=0.0,  # Invalid
                calories=100,
                protein=5.0,
                carbs=10.0,
                fat=2.0,
            )

        with pytest.raises(ValueError, match="Quantity must be positive"):
            MealEntry(
                id=uuid4(),
                meal_id=uuid4(),
                name="test",
                display_name="Test",
                quantity_g=-50.0,  # Invalid
                calories=100,
                protein=5.0,
                carbs=10.0,
                fat=2.0,
            )

    def test_validates_calories_non_negative(self) -> None:
        """Test that calories cannot be negative."""
        with pytest.raises(ValueError, match="Calories cannot be negative"):
            MealEntry(
                id=uuid4(),
                meal_id=uuid4(),
                name="test",
                display_name="Test",
                quantity_g=100.0,
                calories=-10,  # Invalid
                protein=5.0,
                carbs=10.0,
                fat=2.0,
            )

    def test_validates_confidence_range(self) -> None:
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            MealEntry(
                id=uuid4(),
                meal_id=uuid4(),
                name="test",
                display_name="Test",
                quantity_g=100.0,
                calories=100,
                protein=5.0,
                carbs=10.0,
                fat=2.0,
                confidence=-0.1,  # Invalid
            )

        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            MealEntry(
                id=uuid4(),
                meal_id=uuid4(),
                name="test",
                display_name="Test",
                quantity_g=100.0,
                calories=100,
                protein=5.0,
                carbs=10.0,
                fat=2.0,
                confidence=1.5,  # Invalid
            )

    def test_validates_source_values(self) -> None:
        """Test that source must be valid."""
        # Valid sources
        for source in ["PHOTO", "BARCODE", "DESCRIPTION", "MANUAL"]:
            entry = MealEntry(
                id=uuid4(),
                meal_id=uuid4(),
                name="test",
                display_name="Test",
                quantity_g=100.0,
                calories=100,
                protein=5.0,
                carbs=10.0,
                fat=2.0,
                source=source,
            )
            assert entry.source == source

        # Invalid source
        with pytest.raises(ValueError, match="Invalid source"):
            MealEntry(
                id=uuid4(),
                meal_id=uuid4(),
                name="test",
                display_name="Test",
                quantity_g=100.0,
                calories=100,
                protein=5.0,
                carbs=10.0,
                fat=2.0,
                source="INVALID",  # Invalid
            )

    def test_validates_timezone_aware_datetime(self) -> None:
        """Test that created_at must be timezone-aware."""
        with pytest.raises(ValueError, match="timezone-aware"):
            MealEntry(
                id=uuid4(),
                meal_id=uuid4(),
                name="test",
                display_name="Test",
                quantity_g=100.0,
                calories=100,
                protein=5.0,
                carbs=10.0,
                fat=2.0,
                created_at=datetime.now(),  # Naive datetime - invalid
            )

    def test_scale_nutrients(self) -> None:
        """Test scaling nutrients to different quantity."""
        original = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="rice",
            display_name="Rice",
            quantity_g=100.0,
            calories=130,
            protein=2.7,
            carbs=28.0,
            fat=0.3,
            fiber=0.4,
            sugar=0.1,
            sodium=1.0,
        )

        # Scale to 200g (double)
        scaled = original.scale_nutrients(200.0)

        # New entry with different ID
        assert scaled.id != original.id
        assert scaled.meal_id == original.meal_id
        assert scaled.name == original.name
        assert scaled.display_name == original.display_name

        # Scaled nutrients
        assert scaled.quantity_g == 200.0
        assert scaled.calories == 260  # 130 * 2
        assert scaled.protein == 5.4  # 2.7 * 2
        assert scaled.carbs == 56.0  # 28 * 2
        assert scaled.fat == 0.6  # 0.3 * 2
        assert scaled.fiber == 0.8  # 0.4 * 2
        assert scaled.sugar == 0.2  # 0.1 * 2
        assert scaled.sodium == 2.0  # 1.0 * 2

        # Original unchanged
        assert original.quantity_g == 100.0
        assert original.calories == 130

    def test_scale_nutrients_preserves_none_values(self) -> None:
        """Test that scaling preserves None micronutrients."""
        original = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
            # fiber, sugar, sodium not set (None)
        )

        scaled = original.scale_nutrients(200.0)

        assert scaled.fiber is None
        assert scaled.sugar is None
        assert scaled.sodium is None

    def test_scale_nutrients_validates_target_quantity(self) -> None:
        """Test that scale_nutrients validates target quantity."""
        entry = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
        )

        with pytest.raises(ValueError, match="Target quantity must be positive"):
            entry.scale_nutrients(0.0)

        with pytest.raises(ValueError, match="Target quantity must be positive"):
            entry.scale_nutrients(-50.0)

    def test_update_quantity(self) -> None:
        """Test updating quantity in place."""
        entry = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="chicken",
            display_name="Chicken Breast",
            quantity_g=100.0,
            calories=165,
            protein=31.0,
            carbs=0.0,
            fat=3.6,
            fiber=0.0,
            sodium=74.0,
        )

        # Update to 150g
        entry.update_quantity(150.0)

        # Same ID (mutation in place)
        assert entry.quantity_g == 150.0
        assert entry.calories == int(165 * 1.5)  # 247
        assert entry.protein == 31.0 * 1.5  # 46.5
        assert entry.fat == 3.6 * 1.5  # 5.4
        assert entry.sodium == 74.0 * 1.5  # 111.0

    def test_update_quantity_validates_positive(self) -> None:
        """Test that update_quantity validates positive values."""
        entry = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
        )

        with pytest.raises(ValueError, match="Quantity must be positive"):
            entry.update_quantity(0.0)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            entry.update_quantity(-50.0)

    def test_update_quantity_scales_optional_nutrients(self) -> None:
        """Test that update_quantity scales optional micronutrients."""
        entry = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="banana",
            display_name="Banana",
            quantity_g=100.0,
            calories=89,
            protein=1.1,
            carbs=22.8,
            fat=0.3,
            fiber=2.6,
            sugar=12.2,
            sodium=1.0,
        )

        # Scale to 150g
        entry.update_quantity(150.0)

        assert entry.quantity_g == 150.0
        assert entry.fiber == 2.6 * 1.5  # 3.9
        assert entry.sugar == 12.2 * 1.5  # 18.3
        assert entry.sodium == 1.0 * 1.5  # 1.5

    def test_is_reliable(self) -> None:
        """Test is_reliable method."""
        reliable = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
            confidence=0.85,
        )
        assert reliable.is_reliable() is True

        unreliable = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
            confidence=0.65,
        )
        assert unreliable.is_reliable() is False


class TestMeal:
    """Test suite for Meal aggregate root."""

    def test_creates_with_valid_data(self) -> None:
        """Test creating Meal with required fields."""
        meal_id = uuid4()
        timestamp = datetime.now(timezone.utc)

        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=timestamp,
            meal_type="LUNCH",
        )

        assert meal.id == meal_id
        assert meal.user_id == "user-123"
        assert meal.timestamp == timestamp
        assert meal.meal_type == "LUNCH"
        assert meal.entries == []
        assert meal.total_calories == 0
        assert meal.total_protein == 0.0

    def test_validates_meal_type(self) -> None:
        """Test that meal_type must be valid."""
        # Valid types
        for meal_type in ["BREAKFAST", "LUNCH", "DINNER", "SNACK"]:
            meal = Meal(
                id=uuid4(),
                user_id="user-123",
                timestamp=datetime.now(timezone.utc),
                meal_type=meal_type,
            )
            assert meal.meal_type == meal_type

        # Invalid type
        with pytest.raises(ValueError, match="Invalid meal_type"):
            Meal(
                id=uuid4(),
                user_id="user-123",
                timestamp=datetime.now(timezone.utc),
                meal_type="INVALID",
            )

    def test_validates_timezone_aware_timestamp(self) -> None:
        """Test that timestamp must be timezone-aware."""
        with pytest.raises(ValueError, match="timezone-aware"):
            Meal(
                id=uuid4(),
                user_id="user-123",
                timestamp=datetime.now(),  # Naive - invalid
                meal_type="LUNCH",
            )

    def test_validates_timezone_aware_created_at(self) -> None:
        """Test that created_at must be timezone-aware."""
        with pytest.raises(ValueError, match="created_at must be timezone-aware"):
            Meal(
                id=uuid4(),
                user_id="user-123",
                timestamp=datetime.now(timezone.utc),
                meal_type="LUNCH",
                created_at=datetime.now(),  # Naive - invalid
            )

    def test_validates_timezone_aware_updated_at(self) -> None:
        """Test that updated_at must be timezone-aware."""
        with pytest.raises(ValueError, match="updated_at must be timezone-aware"):
            Meal(
                id=uuid4(),
                user_id="user-123",
                timestamp=datetime.now(timezone.utc),
                meal_type="LUNCH",
                updated_at=datetime.now(),  # Naive - invalid
            )

    def test_add_entry(self) -> None:
        """Test adding entry to meal."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="pasta",
            display_name="Pasta",
            quantity_g=150.0,
            calories=300,
            protein=12.0,
            carbs=55.0,
            fat=3.5,
        )

        meal.add_entry(entry)

        assert len(meal.entries) == 1
        assert meal.entries[0] == entry
        assert meal.total_calories == 300
        assert meal.total_protein == 12.0
        assert meal.total_carbs == 55.0
        assert meal.total_fat == 3.5

    def test_add_entry_validates_meal_id_match(self) -> None:
        """Test that add_entry validates entry.meal_id matches meal.id."""
        meal = Meal(
            id=uuid4(),
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry = MealEntry(
            id=uuid4(),
            meal_id=uuid4(),  # Different meal_id - invalid
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
        )

        with pytest.raises(ValueError, match="doesn't match"):
            meal.add_entry(entry)

    def test_add_multiple_entries_recalculates_totals(self) -> None:
        """Test that adding multiple entries correctly calculates totals."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry1 = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="pasta",
            display_name="Pasta",
            quantity_g=150.0,
            calories=300,
            protein=12.0,
            carbs=55.0,
            fat=3.5,
            fiber=2.0,
        )

        entry2 = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="chicken",
            display_name="Chicken",
            quantity_g=100.0,
            calories=165,
            protein=31.0,
            carbs=0.0,
            fat=3.6,
            fiber=0.0,
        )

        meal.add_entry(entry1)
        meal.add_entry(entry2)

        assert len(meal.entries) == 2
        assert meal.total_calories == 465  # 300 + 165
        assert meal.total_protein == 43.0  # 12 + 31
        assert meal.total_carbs == 55.0  # 55 + 0
        assert meal.total_fat == 7.1  # 3.5 + 3.6
        assert meal.total_fiber == 2.0  # 2.0 + 0.0

    def test_remove_entry(self) -> None:
        """Test removing entry from meal."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry1_id = uuid4()
        entry1 = MealEntry(
            id=entry1_id,
            meal_id=meal_id,
            name="pasta",
            display_name="Pasta",
            quantity_g=150.0,
            calories=300,
            protein=12.0,
            carbs=55.0,
            fat=3.5,
        )

        entry2 = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="salad",
            display_name="Salad",
            quantity_g=100.0,
            calories=50,
            protein=2.0,
            carbs=8.0,
            fat=1.0,
        )

        meal.add_entry(entry1)
        meal.add_entry(entry2)

        # Remove entry1
        meal.remove_entry(entry1_id)

        assert len(meal.entries) == 1
        assert meal.entries[0].name == "salad"
        assert meal.total_calories == 50
        assert meal.total_protein == 2.0

    def test_remove_entry_validates_at_least_one_entry(self) -> None:
        """Test that removing last entry raises ValueError."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry_id = uuid4()
        entry = MealEntry(
            id=entry_id,
            meal_id=meal_id,
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
        )

        meal.add_entry(entry)

        # Try to remove the only entry
        with pytest.raises(ValueError, match="Meal must have at least one entry"):
            meal.remove_entry(entry_id)

    def test_update_entry(self) -> None:
        """Test updating entry fields."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry_id = uuid4()
        entry = MealEntry(
            id=entry_id,
            meal_id=meal_id,
            name="pasta",
            display_name="Pasta",
            quantity_g=150.0,
            calories=300,
            protein=12.0,
            carbs=55.0,
            fat=3.5,
        )

        meal.add_entry(entry)

        # Update quantity
        meal.update_entry(entry_id, quantity_g=200.0)

        assert meal.entries[0].quantity_g == 200.0

    def test_update_entry_validates_entry_exists(self) -> None:
        """Test that update_entry validates entry exists."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
        )

        meal.add_entry(entry)

        # Try to update non-existent entry
        with pytest.raises(ValueError, match="not found in meal"):
            meal.update_entry(uuid4(), quantity_g=200.0)

    def test_update_entry_validates_field_names(self) -> None:
        """Test that update_entry validates field names."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry_id = uuid4()
        entry = MealEntry(
            id=entry_id,
            meal_id=meal_id,
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
        )

        meal.add_entry(entry)

        # Try to update invalid field
        with pytest.raises(ValueError, match="Invalid field"):
            meal.update_entry(entry_id, invalid_field="value")

    def test_validate_invariants_empty_entries(self) -> None:
        """Test that validate_invariants catches empty entries."""
        meal = Meal(
            id=uuid4(),
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        with pytest.raises(ValueError, match="Meal must have at least one entry"):
            meal.validate_invariants()

    def test_validate_invariants_future_timestamp(self) -> None:
        """Test that validate_invariants catches future timestamp."""
        meal_id = uuid4()
        future = datetime.now(timezone.utc) + timedelta(days=1)
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=future,
            meal_type="LUNCH",
        )

        entry = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
        )

        meal.add_entry(entry)

        with pytest.raises(ValueError, match="Timestamp cannot be in the future"):
            meal.validate_invariants()

    def test_validate_invariants_totals_mismatch(self) -> None:
        """Test that validate_invariants catches totals mismatch."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=2.0,
        )

        meal.add_entry(entry)

        # Manually corrupt totals
        meal.total_calories = 999

        with pytest.raises(ValueError, match="Total calories mismatch"):
            meal.validate_invariants()

    def test_get_nutrient_distribution(self) -> None:
        """Test get_nutrient_distribution calculation."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        # Entry: 40g protein (160 cal), 50g carbs (200 cal), 10g fat (90 cal)
        # Total: 450 cal from macros
        # Protein: 160/450 = 35.6%
        # Carbs: 200/450 = 44.4%
        # Fat: 90/450 = 20.0%
        entry = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="test",
            display_name="Test",
            quantity_g=100.0,
            calories=450,
            protein=40.0,
            carbs=50.0,
            fat=10.0,
        )

        meal.add_entry(entry)

        distribution = meal.get_nutrient_distribution()

        assert abs(distribution["protein_pct"] - 35.6) < 0.1
        assert abs(distribution["carbs_pct"] - 44.4) < 0.1
        assert abs(distribution["fat_pct"] - 20.0) < 0.1

    def test_get_nutrient_distribution_empty_meal(self) -> None:
        """Test get_nutrient_distribution with no entries."""
        meal = Meal(
            id=uuid4(),
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        distribution = meal.get_nutrient_distribution()

        assert distribution["protein_pct"] == 0.0
        assert distribution["carbs_pct"] == 0.0
        assert distribution["fat_pct"] == 0.0

    def test_is_high_protein(self) -> None:
        """Test is_high_protein method."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        # High protein: 50g protein (200 cal), 20g carbs (80 cal), 5g fat (45 cal)
        # Total: 325 cal from macros
        # Protein: 200/325 = 61.5% > 30%
        high_protein_entry = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="chicken",
            display_name="Chicken",
            quantity_g=200.0,
            calories=325,
            protein=50.0,
            carbs=20.0,
            fat=5.0,
        )

        meal.add_entry(high_protein_entry)

        assert meal.is_high_protein() is True

        # Low protein meal
        meal2_id = uuid4()
        meal2 = Meal(
            id=meal2_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        # 10g protein (40 cal), 60g carbs (240 cal), 10g fat (90 cal)
        # Total: 370 cal
        # Protein: 40/370 = 10.8% < 30%
        low_protein_entry = MealEntry(
            id=uuid4(),
            meal_id=meal2_id,
            name="pasta",
            display_name="Pasta",
            quantity_g=200.0,
            calories=370,
            protein=10.0,
            carbs=60.0,
            fat=10.0,
        )

        meal2.add_entry(low_protein_entry)

        assert meal2.is_high_protein() is False

    def test_average_confidence(self) -> None:
        """Test average_confidence calculation."""
        meal_id = uuid4()
        meal = Meal(
            id=meal_id,
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        entry1 = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="pasta",
            display_name="Pasta",
            quantity_g=150.0,
            calories=300,
            protein=12.0,
            carbs=55.0,
            fat=3.5,
            confidence=0.9,
        )

        entry2 = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name="salad",
            display_name="Salad",
            quantity_g=100.0,
            calories=50,
            protein=2.0,
            carbs=8.0,
            fat=1.0,
            confidence=0.7,
        )

        meal.add_entry(entry1)
        meal.add_entry(entry2)

        # Average: (0.9 + 0.7) / 2 = 0.8
        assert meal.average_confidence() == 0.8

    def test_average_confidence_empty_meal(self) -> None:
        """Test average_confidence with no entries."""
        meal = Meal(
            id=uuid4(),
            user_id="user-123",
            timestamp=datetime.now(timezone.utc),
            meal_type="LUNCH",
        )

        assert meal.average_confidence() == 0.0
