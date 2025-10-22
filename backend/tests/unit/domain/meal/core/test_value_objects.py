"""Unit tests for core value objects.

Tests immutability, validation, and behavior of domain value objects.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4

from domain.meal.core.value_objects import (
    Confidence,
    MealId,
    Quantity,
    Timestamp,
    Unit,
)


class TestMealId:
    """Test suite for MealId value object."""

    def test_generate_creates_valid_uuid(self) -> None:
        """Test that generate() creates valid UUID."""
        meal_id = MealId.generate()
        assert isinstance(meal_id.value, UUID)

    def test_generate_creates_unique_ids(self) -> None:
        """Test that generate() creates unique IDs."""
        id1 = MealId.generate()
        id2 = MealId.generate()
        assert id1 != id2

    def test_from_string_valid_uuid(self) -> None:
        """Test creating MealId from valid UUID string."""
        uuid_str = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        meal_id = MealId.from_string(uuid_str)
        assert str(meal_id) == uuid_str

    def test_from_string_invalid_uuid_raises(self) -> None:
        """Test that invalid UUID string raises ValueError."""
        with pytest.raises(ValueError):
            MealId.from_string("not-a-uuid")

    def test_str_representation(self) -> None:
        """Test string representation."""
        uuid_val = uuid4()
        meal_id = MealId(uuid_val)
        assert str(meal_id) == str(uuid_val)

    def test_equality_by_value(self) -> None:
        """Test that equality is by value, not identity."""
        uuid_val = uuid4()
        id1 = MealId(uuid_val)
        id2 = MealId(uuid_val)
        assert id1 == id2
        assert id1 is not id2  # Different instances

    def test_immutability(self) -> None:
        """Test that MealId is immutable (frozen)."""
        meal_id = MealId.generate()
        with pytest.raises(AttributeError):
            meal_id.value = uuid4()  # type: ignore


class TestQuantity:
    """Test suite for Quantity value object."""

    def test_valid_quantity_grams(self) -> None:
        """Test creating valid quantity in grams."""
        q = Quantity(100.0, "g")
        assert q.value == 100.0
        assert q.unit == "g"

    def test_quantity_must_be_positive(self) -> None:
        """Test that zero or negative quantities raise ValueError."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            Quantity(0.0, "g")

        with pytest.raises(ValueError, match="Quantity must be positive"):
            Quantity(-10.0, "g")

    def test_invalid_unit_raises(self) -> None:
        """Test that invalid unit raises ValueError."""
        with pytest.raises(ValueError, match="Invalid unit"):
            Quantity(100.0, "kg")  # type: ignore

    def test_to_grams_conversion(self) -> None:
        """Test conversion to grams for all units."""
        assert Quantity(100.0, "g").to_grams() == 100.0
        assert Quantity(100.0, "ml").to_grams() == 100.0  # Density ~1
        assert Quantity(1.0, "oz").to_grams() == 28.35
        assert Quantity(1.0, "cup").to_grams() == 240.0
        assert Quantity(1.0, "tbsp").to_grams() == 15.0
        assert Quantity(1.0, "tsp").to_grams() == 5.0

    def test_scale_quantity(self) -> None:
        """Test scaling quantity by factor."""
        q = Quantity(100.0, "g")
        q_doubled = q.scale(2.0)

        assert q_doubled.value == 200.0
        assert q_doubled.unit == "g"
        assert q.value == 100.0  # Original unchanged (immutable)

    def test_str_representation(self) -> None:
        """Test string representation."""
        q = Quantity(125.5, "g")
        assert str(q) == "125.5g"

    def test_immutability(self) -> None:
        """Test that Quantity is immutable (frozen)."""
        q = Quantity(100.0, "g")
        with pytest.raises(AttributeError):
            q.value = 200.0  # type: ignore


class TestTimestamp:
    """Test suite for Timestamp value object."""

    def test_now_creates_utc_timestamp(self) -> None:
        """Test that now() creates UTC timestamp."""
        ts = Timestamp.now()
        assert ts.value.tzinfo == timezone.utc

    def test_now_is_close_to_current_time(self) -> None:
        """Test that now() timestamp is within 1 second of actual time."""
        before = datetime.now(timezone.utc)
        ts = Timestamp.now()
        after = datetime.now(timezone.utc)

        assert before <= ts.value <= after

    def test_from_iso_valid_string(self) -> None:
        """Test creating Timestamp from ISO string."""
        iso_str = "2025-01-15T10:30:00Z"
        ts = Timestamp.from_iso(iso_str)

        assert ts.value.year == 2025
        assert ts.value.month == 1
        assert ts.value.day == 15
        assert ts.value.hour == 10
        assert ts.value.minute == 30

    def test_from_iso_with_timezone_offset(self) -> None:
        """Test creating Timestamp from ISO string with timezone."""
        iso_str = "2025-01-15T10:30:00+02:00"
        ts = Timestamp.from_iso(iso_str)

        # Should have timezone info
        assert ts.value.tzinfo is not None

    def test_timezone_must_be_aware(self) -> None:
        """Test that naive datetime (no timezone) raises ValueError."""
        naive_dt = datetime(2025, 1, 15, 10, 30)  # No timezone

        with pytest.raises(ValueError, match="timezone-aware"):
            Timestamp(naive_dt)

    def test_future_timestamp_raises(self) -> None:
        """Test that future timestamps raise ValueError."""
        future_dt = datetime.now(timezone.utc) + timedelta(hours=1)

        with pytest.raises(ValueError, match="cannot be in the future"):
            Timestamp(future_dt)

    def test_to_iso_conversion(self) -> None:
        """Test conversion to ISO string."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        ts = Timestamp(dt)
        iso_str = ts.to_iso()

        assert "2025-01-15" in iso_str
        assert "10:30:00" in iso_str

    def test_is_today(self) -> None:
        """Test is_today() check."""
        ts_now = Timestamp.now()
        assert ts_now.is_today()

        # Yesterday should not be today
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        ts_yesterday = Timestamp(yesterday)
        assert not ts_yesterday.is_today()

    def test_immutability(self) -> None:
        """Test that Timestamp is immutable (frozen)."""
        ts = Timestamp.now()
        with pytest.raises(AttributeError):
            ts.value = datetime.now(timezone.utc)  # type: ignore


class TestConfidence:
    """Test suite for Confidence value object."""

    def test_valid_confidence_values(self) -> None:
        """Test creating valid confidence scores."""
        c1 = Confidence(0.0)
        assert c1.value == 0.0

        c2 = Confidence(0.5)
        assert c2.value == 0.5

        c3 = Confidence(1.0)
        assert c3.value == 1.0

    def test_confidence_below_zero_raises(self) -> None:
        """Test that confidence < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            Confidence(-0.1)

    def test_confidence_above_one_raises(self) -> None:
        """Test that confidence > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            Confidence(1.1)

    def test_high_confidence_constructor(self) -> None:
        """Test high() constructor."""
        c = Confidence.high()
        assert c.value == 0.9
        assert c.is_reliable()

    def test_medium_confidence_constructor(self) -> None:
        """Test medium() constructor."""
        c = Confidence.medium()
        assert c.value == 0.7
        # medium (0.7) is NOT reliable because is_reliable() requires > 0.7
        assert not c.is_reliable()

    def test_low_confidence_constructor(self) -> None:
        """Test low() constructor."""
        c = Confidence.low()
        assert c.value == 0.4
        assert not c.is_reliable()

    def test_is_reliable_threshold(self) -> None:
        """Test is_reliable() threshold at 0.7."""
        c_below = Confidence(0.69)
        assert not c_below.is_reliable()

        c_above = Confidence(0.71)
        assert c_above.is_reliable()

        c_exact = Confidence(0.7)
        assert not c_exact.is_reliable()  # > 0.7, not >= 0.7

    def test_float_conversion(self) -> None:
        """Test conversion to float."""
        c = Confidence(0.85)
        assert float(c) == 0.85

    def test_str_representation_as_percentage(self) -> None:
        """Test string representation as percentage."""
        c = Confidence(0.85)
        assert str(c) == "85.0%"

    def test_immutability(self) -> None:
        """Test that Confidence is immutable (frozen)."""
        c = Confidence(0.8)
        with pytest.raises(AttributeError):
            c.value = 0.9  # type: ignore
