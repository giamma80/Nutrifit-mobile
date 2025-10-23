"""Unit tests for domain exceptions.

Tests exception hierarchy, messages, and inheritance.
"""

import pytest

from domain.meal.core.exceptions import (
    EntryNotFoundError,
    InvalidMealError,
    InvalidQuantityError,
    InvalidTimestampError,
    MealDomainError,
    MealNotFoundError,
)


class TestMealDomainError:
    """Test suite for MealDomainError base exception."""

    def test_is_exception(self) -> None:
        """Test that MealDomainError is an Exception."""
        assert issubclass(MealDomainError, Exception)

    def test_can_be_raised(self) -> None:
        """Test that MealDomainError can be raised."""
        with pytest.raises(MealDomainError):
            raise MealDomainError("test error")

    def test_custom_message(self) -> None:
        """Test that custom message is preserved."""
        message = "Custom error message"
        with pytest.raises(MealDomainError, match=message):
            raise MealDomainError(message)

    def test_str_representation(self) -> None:
        """Test string representation of error."""
        message = "Test error"
        error = MealDomainError(message)
        assert str(error) == message


class TestInvalidMealError:
    """Test suite for InvalidMealError."""

    def test_inherits_from_meal_domain_error(self) -> None:
        """Test that InvalidMealError inherits from MealDomainError."""
        assert issubclass(InvalidMealError, MealDomainError)

    def test_can_be_raised(self) -> None:
        """Test that InvalidMealError can be raised."""
        with pytest.raises(InvalidMealError):
            raise InvalidMealError("Meal has no entries")

    def test_can_be_caught_as_meal_domain_error(self) -> None:
        """Test that InvalidMealError can be caught as MealDomainError."""
        with pytest.raises(MealDomainError):
            raise InvalidMealError("test")

    def test_custom_message(self) -> None:
        """Test custom error message."""
        message = "Meal invariants violated: no entries"
        with pytest.raises(InvalidMealError, match=message):
            raise InvalidMealError(message)


class TestMealNotFoundError:
    """Test suite for MealNotFoundError."""

    def test_inherits_from_meal_domain_error(self) -> None:
        """Test that MealNotFoundError inherits from MealDomainError."""
        assert issubclass(MealNotFoundError, MealDomainError)

    def test_can_be_raised(self) -> None:
        """Test that MealNotFoundError can be raised."""
        with pytest.raises(MealNotFoundError):
            raise MealNotFoundError("Meal with id 123 not found")

    def test_can_be_caught_as_meal_domain_error(self) -> None:
        """Test that MealNotFoundError can be caught as MealDomainError."""
        with pytest.raises(MealDomainError):
            raise MealNotFoundError("test")


class TestEntryNotFoundError:
    """Test suite for EntryNotFoundError."""

    def test_inherits_from_meal_domain_error(self) -> None:
        """Test that EntryNotFoundError inherits from MealDomainError."""
        assert issubclass(EntryNotFoundError, MealDomainError)

    def test_can_be_raised(self) -> None:
        """Test that EntryNotFoundError can be raised."""
        with pytest.raises(EntryNotFoundError):
            raise EntryNotFoundError("Entry 0 not found in meal")

    def test_can_be_caught_as_meal_domain_error(self) -> None:
        """Test that EntryNotFoundError can be caught as MealDomainError."""
        with pytest.raises(MealDomainError):
            raise EntryNotFoundError("test")


class TestInvalidQuantityError:
    """Test suite for InvalidQuantityError."""

    def test_inherits_from_meal_domain_error(self) -> None:
        """Test that InvalidQuantityError inherits from MealDomainError."""
        assert issubclass(InvalidQuantityError, MealDomainError)

    def test_can_be_raised(self) -> None:
        """Test that InvalidQuantityError can be raised."""
        with pytest.raises(InvalidQuantityError):
            raise InvalidQuantityError("Quantity must be positive")

    def test_can_be_caught_as_meal_domain_error(self) -> None:
        """Test that InvalidQuantityError can be caught as MealDomainError."""
        with pytest.raises(MealDomainError):
            raise InvalidQuantityError("test")

    def test_custom_message_negative_quantity(self) -> None:
        """Test error message for negative quantity."""
        message = "Quantity -10.0 must be positive"
        with pytest.raises(InvalidQuantityError, match=message):
            raise InvalidQuantityError(message)

    def test_custom_message_invalid_unit(self) -> None:
        """Test error message for invalid unit."""
        message = "Invalid unit: kg"
        with pytest.raises(InvalidQuantityError, match=message):
            raise InvalidQuantityError(message)


class TestInvalidTimestampError:
    """Test suite for InvalidTimestampError."""

    def test_inherits_from_meal_domain_error(self) -> None:
        """Test that InvalidTimestampError inherits from MealDomainError."""
        assert issubclass(InvalidTimestampError, MealDomainError)

    def test_can_be_raised(self) -> None:
        """Test that InvalidTimestampError can be raised."""
        with pytest.raises(InvalidTimestampError):
            raise InvalidTimestampError("Timestamp cannot be in the future")

    def test_can_be_caught_as_meal_domain_error(self) -> None:
        """Test that InvalidTimestampError can be caught as MealDomainError."""
        with pytest.raises(MealDomainError):
            raise InvalidTimestampError("test")

    def test_custom_message_future_timestamp(self) -> None:
        """Test error message for future timestamp."""
        message = "Timestamp 2030-01-01 cannot be in the future"
        with pytest.raises(InvalidTimestampError, match=message):
            raise InvalidTimestampError(message)

    def test_custom_message_naive_datetime(self) -> None:
        """Test error message for naive datetime."""
        message = "Timestamp must be timezone-aware"
        with pytest.raises(InvalidTimestampError, match=message):
            raise InvalidTimestampError(message)


class TestExceptionHierarchy:
    """Test suite for exception hierarchy and polymorphism."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Test that all specific exceptions inherit from MealDomainError."""
        exceptions = [
            InvalidMealError,
            MealNotFoundError,
            EntryNotFoundError,
            InvalidQuantityError,
            InvalidTimestampError,
        ]

        for exc_class in exceptions:
            assert issubclass(exc_class, MealDomainError)

    def test_catch_all_domain_errors(self) -> None:
        """Test catching all domain errors with base exception."""
        exceptions_to_test = [
            InvalidMealError("test"),
            MealNotFoundError("test"),
            EntryNotFoundError("test"),
            InvalidQuantityError("test"),
            InvalidTimestampError("test"),
        ]

        for exc in exceptions_to_test:
            with pytest.raises(MealDomainError):
                raise exc

    def test_specific_exception_not_caught_by_other_specific(self) -> None:
        """Test that specific exceptions are not caught by other specific exceptions."""
        # MealNotFoundError should not be caught by InvalidMealError
        with pytest.raises(MealNotFoundError):
            try:
                raise MealNotFoundError("test")
            except InvalidMealError:
                pytest.fail("Should not catch MealNotFoundError with InvalidMealError")
