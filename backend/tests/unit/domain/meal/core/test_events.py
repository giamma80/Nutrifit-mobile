"""Unit tests for domain events.

Tests immutability, validation, and factory methods of domain events.
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from domain.meal.core.events import (
    DomainEvent,
    MealAnalyzed,
    MealConfirmed,
    MealDeleted,
    MealUpdated,
)


class TestDomainEvent:
    """Test suite for base DomainEvent."""

    def test_creates_with_valid_timezone_aware_datetime(self) -> None:
        """Test creating event with timezone-aware datetime."""
        event_id = uuid4()
        occurred_at = datetime.now(timezone.utc)

        event = DomainEvent(event_id=event_id, occurred_at=occurred_at)

        assert event.event_id == event_id
        assert event.occurred_at == occurred_at

    def test_rejects_naive_datetime(self) -> None:
        """Test that naive datetime (no timezone) raises ValueError."""
        event_id = uuid4()
        naive_dt = datetime.now()  # No timezone

        with pytest.raises(ValueError, match="timezone-aware"):
            DomainEvent(event_id=event_id, occurred_at=naive_dt)

    def test_immutability(self) -> None:
        """Test that DomainEvent is immutable (frozen)."""
        event = DomainEvent(event_id=uuid4(), occurred_at=datetime.now(timezone.utc))

        with pytest.raises(AttributeError):
            event.event_id = uuid4()  # type: ignore


class TestMealAnalyzed:
    """Test suite for MealAnalyzed event."""

    def test_create_with_valid_data(self) -> None:
        """Test creating MealAnalyzed event with valid data."""
        meal_id = uuid4()
        user_id = "user-123"

        event = MealAnalyzed.create(
            meal_id=meal_id,
            user_id=user_id,
            source="PHOTO",
            item_count=3,
            average_confidence=0.85,
        )

        assert event.meal_id == meal_id
        assert event.user_id == user_id
        assert event.source == "PHOTO"
        assert event.item_count == 3
        assert event.average_confidence == 0.85
        assert isinstance(event.event_id, UUID)
        assert event.occurred_at.tzinfo == timezone.utc

    def test_create_generates_unique_event_ids(self) -> None:
        """Test that create() generates unique event IDs."""
        event1 = MealAnalyzed.create(
            meal_id=uuid4(),
            user_id="user-123",
            source="PHOTO",
            item_count=1,
            average_confidence=0.8,
        )
        event2 = MealAnalyzed.create(
            meal_id=uuid4(),
            user_id="user-123",
            source="PHOTO",
            item_count=1,
            average_confidence=0.8,
        )

        assert event1.event_id != event2.event_id

    def test_validates_item_count_positive(self) -> None:
        """Test that item_count must be positive."""
        with pytest.raises(ValueError, match="item_count must be positive"):
            MealAnalyzed.create(
                meal_id=uuid4(),
                user_id="user-123",
                source="PHOTO",
                item_count=0,  # Invalid
                average_confidence=0.8,
            )

        with pytest.raises(ValueError, match="item_count must be positive"):
            MealAnalyzed.create(
                meal_id=uuid4(),
                user_id="user-123",
                source="PHOTO",
                item_count=-1,  # Invalid
                average_confidence=0.8,
            )

    def test_validates_average_confidence_range(self) -> None:
        """Test that average_confidence must be in [0.0, 1.0]."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            MealAnalyzed.create(
                meal_id=uuid4(),
                user_id="user-123",
                source="PHOTO",
                item_count=1,
                average_confidence=-0.1,  # Invalid
            )

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            MealAnalyzed.create(
                meal_id=uuid4(),
                user_id="user-123",
                source="PHOTO",
                item_count=1,
                average_confidence=1.5,  # Invalid
            )

    def test_validates_source_values(self) -> None:
        """Test that source must be PHOTO, BARCODE, or DESCRIPTION."""
        # Valid sources
        for source in ["PHOTO", "BARCODE", "DESCRIPTION"]:
            event = MealAnalyzed.create(
                meal_id=uuid4(),
                user_id="user-123",
                source=source,
                item_count=1,
                average_confidence=0.8,
            )
            assert event.source == source

        # Invalid source
        with pytest.raises(ValueError, match="Invalid source"):
            MealAnalyzed.create(
                meal_id=uuid4(),
                user_id="user-123",
                source="INVALID",
                item_count=1,
                average_confidence=0.8,
            )

    def test_immutability(self) -> None:
        """Test that MealAnalyzed is immutable."""
        event = MealAnalyzed.create(
            meal_id=uuid4(),
            user_id="user-123",
            source="PHOTO",
            item_count=1,
            average_confidence=0.8,
        )

        with pytest.raises(AttributeError):
            event.meal_id = uuid4()  # type: ignore


class TestMealConfirmed:
    """Test suite for MealConfirmed event."""

    def test_create_with_valid_data(self) -> None:
        """Test creating MealConfirmed event with valid data."""
        meal_id = uuid4()
        user_id = "user-123"

        event = MealConfirmed.create(
            meal_id=meal_id,
            user_id=user_id,
            confirmed_entry_count=2,
            rejected_entry_count=1,
        )

        assert event.meal_id == meal_id
        assert event.user_id == user_id
        assert event.confirmed_entry_count == 2
        assert event.rejected_entry_count == 1
        assert isinstance(event.event_id, UUID)
        assert event.occurred_at.tzinfo == timezone.utc

    def test_allows_zero_counts(self) -> None:
        """Test that zero counts are allowed."""
        event = MealConfirmed.create(
            meal_id=uuid4(),
            user_id="user-123",
            confirmed_entry_count=0,
            rejected_entry_count=0,
        )

        assert event.confirmed_entry_count == 0
        assert event.rejected_entry_count == 0

    def test_validates_confirmed_count_not_negative(self) -> None:
        """Test that confirmed_entry_count cannot be negative."""
        with pytest.raises(ValueError, match="confirmed_entry_count cannot be negative"):
            MealConfirmed.create(
                meal_id=uuid4(),
                user_id="user-123",
                confirmed_entry_count=-1,
                rejected_entry_count=0,
            )

    def test_validates_rejected_count_not_negative(self) -> None:
        """Test that rejected_entry_count cannot be negative."""
        with pytest.raises(ValueError, match="rejected_entry_count cannot be negative"):
            MealConfirmed.create(
                meal_id=uuid4(),
                user_id="user-123",
                confirmed_entry_count=0,
                rejected_entry_count=-1,
            )

    def test_immutability(self) -> None:
        """Test that MealConfirmed is immutable."""
        event = MealConfirmed.create(
            meal_id=uuid4(),
            user_id="user-123",
            confirmed_entry_count=1,
            rejected_entry_count=0,
        )

        with pytest.raises(AttributeError):
            event.confirmed_entry_count = 5  # type: ignore


class TestMealUpdated:
    """Test suite for MealUpdated event."""

    def test_create_with_valid_data(self) -> None:
        """Test creating MealUpdated event with valid data."""
        meal_id = uuid4()
        user_id = "user-123"
        updated_fields = ["quantity_g", "calories"]

        event = MealUpdated.create(
            meal_id=meal_id,
            user_id=user_id,
            updated_fields=updated_fields,
        )

        assert event.meal_id == meal_id
        assert event.user_id == user_id
        assert event.updated_fields == updated_fields
        assert isinstance(event.event_id, UUID)
        assert event.occurred_at.tzinfo == timezone.utc

    def test_validates_updated_fields_not_empty(self) -> None:
        """Test that updated_fields cannot be empty."""
        with pytest.raises(ValueError, match="updated_fields cannot be empty"):
            MealUpdated.create(
                meal_id=uuid4(),
                user_id="user-123",
                updated_fields=[],  # Invalid
            )

    def test_copies_updated_fields_list(self) -> None:
        """Test that updated_fields is copied (not referenced)."""
        original_list = ["field1"]
        event = MealUpdated.create(
            meal_id=uuid4(),
            user_id="user-123",
            updated_fields=original_list,
        )

        # Modify original list
        original_list.append("field2")

        # Event should not be affected
        assert len(event.updated_fields) == 1
        assert event.updated_fields == ["field1"]

    def test_immutability(self) -> None:
        """Test that MealUpdated is immutable."""
        event = MealUpdated.create(
            meal_id=uuid4(),
            user_id="user-123",
            updated_fields=["field1"],
        )

        with pytest.raises(AttributeError):
            event.meal_id = uuid4()  # type: ignore


class TestMealDeleted:
    """Test suite for MealDeleted event."""

    def test_create_with_valid_data(self) -> None:
        """Test creating MealDeleted event with valid data."""
        meal_id = uuid4()
        user_id = "user-123"

        event = MealDeleted.create(
            meal_id=meal_id,
            user_id=user_id,
        )

        assert event.meal_id == meal_id
        assert event.user_id == user_id
        assert isinstance(event.event_id, UUID)
        assert event.occurred_at.tzinfo == timezone.utc

    def test_immutability(self) -> None:
        """Test that MealDeleted is immutable."""
        event = MealDeleted.create(
            meal_id=uuid4(),
            user_id="user-123",
        )

        with pytest.raises(AttributeError):
            event.user_id = "other-user"  # type: ignore
