"""
Unit tests for meal persistence domain models.

Tests MealEntry validation, validators, and field constraints.
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from v2.domain.meal.persistence.models import MealEntry


class TestMealEntry:
    """Test suite for MealEntry domain model."""

    def test_meal_entry_minimal_valid(self) -> None:
        """Test MealEntry creation with minimal required fields."""
        timestamp = datetime(2025, 1, 15, 12, 30, tzinfo=timezone.utc)

        meal = MealEntry(
            user_id="user_123",
            name="Apple",
            quantity_g=100.0,
            timestamp=timestamp,
            source="PHOTO",
        )

        assert meal.user_id == "user_123"
        assert meal.name == "Apple"
        assert meal.quantity_g == 100.0
        assert meal.timestamp == timestamp
        assert meal.source == "PHOTO"
        assert meal.created_at is not None
        assert meal.created_at.tzinfo == timezone.utc

    def test_meal_entry_all_fields(self) -> None:
        """Test MealEntry with all fields populated."""
        timestamp = datetime(2025, 1, 15, 12, 30, tzinfo=timezone.utc)
        created = datetime(2025, 1, 15, 12, 31, tzinfo=timezone.utc)

        meal = MealEntry(
            user_id="user_456",
            name="Grilled Chicken Breast",
            quantity_g=150.0,
            timestamp=timestamp,
            source="BARCODE",
            calories=248,
            protein=46.5,
            carbs=0.0,
            fat=5.4,
            fiber=0.0,
            sugar=0.0,
            sodium=74.0,
            id="507f1f77bcf86cd799439011",
            barcode="1234567890123",
            image_url="https://example.com/meal.jpg",
            analysis_id="analysis_789",
            idempotency_key="hash_abc123",
            created_at=created,
        )

        assert meal.user_id == "user_456"
        assert meal.name == "Grilled Chicken Breast"
        assert meal.quantity_g == 150.0
        assert meal.calories == 248
        assert meal.protein == 46.5
        assert meal.carbs == 0.0
        assert meal.fat == 5.4
        assert meal.fiber == 0.0
        assert meal.sugar == 0.0
        assert meal.sodium == 74.0
        assert meal.barcode == "1234567890123"
        assert meal.image_url == "https://example.com/meal.jpg"
        assert meal.created_at == created

    def test_meal_entry_name_whitespace_stripped(self) -> None:
        """Test name validator strips whitespace."""
        meal = MealEntry(
            user_id="user_123",
            name="  Apple  ",
            quantity_g=100.0,
            timestamp=datetime.now(timezone.utc),
            source="MANUAL",
        )

        assert meal.name == "Apple"

    def test_meal_entry_name_empty_raises_error(self) -> None:
        """Test name cannot be empty or only whitespace."""
        with pytest.raises(ValidationError) as exc_info:
            MealEntry(
                user_id="user_123",
                name="   ",
                quantity_g=100.0,
                timestamp=datetime.now(timezone.utc),
                source="MANUAL",
            )

        errors = exc_info.value.errors()
        assert any("name cannot be empty" in str(e).lower() for e in errors)

    def test_meal_entry_name_too_long_raises_error(self) -> None:
        """Test name exceeding max_length raises error."""
        long_name = "A" * 201  # Exceeds 200 char limit

        with pytest.raises(ValidationError) as exc_info:
            MealEntry(
                user_id="user_123",
                name=long_name,
                quantity_g=100.0,
                timestamp=datetime.now(timezone.utc),
                source="MANUAL",
            )

        errors = exc_info.value.errors()
        assert any(e["type"] == "string_too_long" for e in errors)

    def test_meal_entry_source_valid_values(self) -> None:
        """Test source accepts only valid enum values."""
        valid_sources = ["PHOTO", "BARCODE", "DESCRIPTION", "MANUAL"]

        for source in valid_sources:
            meal = MealEntry(
                user_id="user_123",
                name="Test Food",
                quantity_g=100.0,
                timestamp=datetime.now(timezone.utc),
                source=source,
            )
            assert meal.source == source

    def test_meal_entry_source_invalid_raises_error(self) -> None:
        """Test source rejects invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            MealEntry(
                user_id="user_123",
                name="Test Food",
                quantity_g=100.0,
                timestamp=datetime.now(timezone.utc),
                source="INVALID_SOURCE",
            )

        errors = exc_info.value.errors()
        assert any(e["type"] == "string_pattern_mismatch" for e in errors)

    def test_meal_entry_quantity_positive(self) -> None:
        """Test quantity_g must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            MealEntry(
                user_id="user_123",
                name="Apple",
                quantity_g=0.0,
                timestamp=datetime.now(timezone.utc),
                source="MANUAL",
            )

        errors = exc_info.value.errors()
        assert any(e["type"] == "greater_than" for e in errors)

    def test_meal_entry_quantity_negative_raises_error(self) -> None:
        """Test negative quantity raises error."""
        with pytest.raises(ValidationError) as exc_info:
            MealEntry(
                user_id="user_123",
                name="Apple",
                quantity_g=-10.0,
                timestamp=datetime.now(timezone.utc),
                source="MANUAL",
            )

        errors = exc_info.value.errors()
        assert any(e["type"] == "greater_than" for e in errors)

    def test_meal_entry_timestamp_naive_converted_to_utc(self) -> None:
        """Test naive datetime is converted to UTC."""
        naive_dt = datetime(2025, 1, 15, 12, 30)  # No timezone

        meal = MealEntry(
            user_id="user_123",
            name="Apple",
            quantity_g=100.0,
            timestamp=naive_dt,
            source="MANUAL",
        )

        assert meal.timestamp.tzinfo == timezone.utc
        expected_ts = datetime(2025, 1, 15, 12, 30, tzinfo=timezone.utc)
        assert meal.timestamp == expected_ts

    def test_meal_entry_timestamp_aware_preserved(self) -> None:
        """Test timezone-aware datetime is preserved."""
        aware_dt = datetime(2025, 1, 15, 12, 30, tzinfo=timezone.utc)

        meal = MealEntry(
            user_id="user_123",
            name="Apple",
            quantity_g=100.0,
            timestamp=aware_dt,
            source="MANUAL",
        )

        assert meal.timestamp == aware_dt
        assert meal.timestamp.tzinfo == timezone.utc

    def test_meal_entry_created_at_auto_set(self) -> None:
        """Test created_at is automatically set if not provided."""
        before = datetime.now(timezone.utc)

        meal = MealEntry(
            user_id="user_123",
            name="Apple",
            quantity_g=100.0,
            timestamp=datetime.now(timezone.utc),
            source="MANUAL",
        )

        after = datetime.now(timezone.utc)

        assert meal.created_at is not None
        assert before <= meal.created_at <= after
        assert meal.created_at.tzinfo == timezone.utc

    def test_meal_entry_created_at_explicit_preserved(self) -> None:
        """Test explicit created_at is preserved."""
        explicit_created = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)

        meal = MealEntry(
            user_id="user_123",
            name="Apple",
            quantity_g=100.0,
            timestamp=datetime.now(timezone.utc),
            source="MANUAL",
            created_at=explicit_created,
        )

        assert meal.created_at == explicit_created

    def test_meal_entry_created_at_naive_converted_to_utc(self) -> None:
        """Test naive created_at is converted to UTC."""
        naive_created = datetime(2025, 1, 15, 10, 0)

        meal = MealEntry(
            user_id="user_123",
            name="Apple",
            quantity_g=100.0,
            timestamp=datetime.now(timezone.utc),
            source="MANUAL",
            created_at=naive_created,
        )

        assert meal.created_at is not None
        assert meal.created_at.tzinfo == timezone.utc
        expected_created = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
        assert meal.created_at == expected_created

    def test_meal_entry_barcode_valid_formats(self) -> None:
        """Test barcode accepts valid formats (8-13 digits)."""
        valid_barcodes = [
            "12345678",  # 8 digits (EAN-8)
            "1234567890123",  # 13 digits (EAN-13)
            "123456789012",  # 12 digits (UPC)
        ]

        for barcode in valid_barcodes:
            meal = MealEntry(
                user_id="user_123",
                name="Product",
                quantity_g=100.0,
                timestamp=datetime.now(timezone.utc),
                source="BARCODE",
                barcode=barcode,
            )
            assert meal.barcode == barcode

    def test_meal_entry_barcode_invalid_raises_error(self) -> None:
        """Test barcode rejects invalid formats."""
        invalid_barcodes = [
            "123",  # Too short
            "12345678901234567890",  # Too long
            "abc123456789",  # Contains letters
        ]

        for barcode in invalid_barcodes:
            with pytest.raises(ValidationError):
                MealEntry(
                    user_id="user_123",
                    name="Product",
                    quantity_g=100.0,
                    timestamp=datetime.now(timezone.utc),
                    source="BARCODE",
                    barcode=barcode,
                )

    def test_meal_entry_nutrients_non_negative(self) -> None:
        """Test nutrient fields must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            MealEntry(
                user_id="user_123",
                name="Apple",
                quantity_g=100.0,
                timestamp=datetime.now(timezone.utc),
                source="MANUAL",
                calories=-10,
            )

        errors = exc_info.value.errors()
        assert any(e["type"] == "greater_than_equal" for e in errors)

    def test_meal_entry_nutrients_optional(self) -> None:
        """Test nutrient fields are optional."""
        meal = MealEntry(
            user_id="user_123",
            name="Unknown Food",
            quantity_g=100.0,
            timestamp=datetime.now(timezone.utc),
            source="MANUAL",
        )

        assert meal.calories is None
        assert meal.protein is None
        assert meal.carbs is None
        assert meal.fat is None
        assert meal.fiber is None
        assert meal.sugar is None
        assert meal.sodium is None

    def test_meal_entry_user_id_empty_raises_error(self) -> None:
        """Test user_id cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            MealEntry(
                user_id="",
                name="Apple",
                quantity_g=100.0,
                timestamp=datetime.now(timezone.utc),
                source="MANUAL",
            )

        errors = exc_info.value.errors()
        assert any(e["type"] == "string_too_short" for e in errors)

    def test_meal_entry_validate_assignment(self) -> None:
        """Test validate_assignment is enabled for field updates."""
        meal = MealEntry(
            user_id="user_123",
            name="Apple",
            quantity_g=100.0,
            timestamp=datetime.now(timezone.utc),
            source="MANUAL",
        )

        # Valid update
        meal.name = "Banana"
        assert meal.name == "Banana"

        # Invalid update should raise error
        with pytest.raises(ValidationError):
            meal.quantity_g = -10.0

    def test_meal_entry_json_serialization(self) -> None:
        """Test MealEntry can be serialized to JSON."""
        timestamp = datetime(2025, 1, 15, 12, 30, tzinfo=timezone.utc)

        meal = MealEntry(
            user_id="user_123",
            name="Apple",
            quantity_g=100.0,
            timestamp=timestamp,
            source="PHOTO",
            calories=52,
        )

        json_data = meal.model_dump()

        assert json_data["user_id"] == "user_123"
        assert json_data["name"] == "Apple"
        assert json_data["quantity_g"] == 100.0
        assert json_data["source"] == "PHOTO"
        assert json_data["calories"] == 52

    def test_meal_entry_immutable_after_validation(self) -> None:
        """Test fields maintain validation after assignment."""
        meal = MealEntry(
            user_id="user_123",
            name="Apple",
            quantity_g=100.0,
            timestamp=datetime.now(timezone.utc),
            source="MANUAL",
        )

        # Update with whitespace - should be stripped
        meal.name = "  Banana  "
        assert meal.name == "Banana"

        # Update with empty name - should raise error
        with pytest.raises(ValidationError):
            meal.name = "   "
