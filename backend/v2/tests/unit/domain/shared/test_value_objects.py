"""
Unit tests for value objects.

Testing immutability, validation, and equality.
"""

import pytest
from backend.v2.domain.shared.value_objects import (
    UserId,
    Barcode,
    AnalysisId,
    MealId,
    IdempotencyKey,
)


class TestUserId:
    """Test UserId value object."""

    def test_create_valid(self) -> None:
        """Should create valid UserId."""
        user_id = UserId(value="user_123")
        assert user_id.value == "user_123"
        assert str(user_id) == "user_123"

    def test_from_string(self) -> None:
        """Should create from string."""
        user_id = UserId.from_string("user_456")
        assert user_id.value == "user_456"

    def test_reject_empty(self) -> None:
        """Should reject empty string."""
        with pytest.raises(ValueError):
            UserId(value="")

    def test_reject_whitespace(self) -> None:
        """Should reject whitespace-only string."""
        with pytest.raises(ValueError):
            UserId(value="   ")

    def test_immutable(self) -> None:
        """Should be immutable."""
        user_id = UserId(value="user_123")
        with pytest.raises((AttributeError, ValueError)):
            user_id.value = "user_456"  # noqa: SLF001

    def test_hashable(self) -> None:
        """Should be hashable."""
        user_id = UserId(value="user_123")
        assert hash(user_id) == hash("user_123")

        # Can be used as dict key
        d = {user_id: "data"}
        assert d[user_id] == "data"


class TestBarcode:
    """Test Barcode value object."""

    def test_create_valid_ean13(self) -> None:
        """Should create valid EAN-13 barcode."""
        barcode = Barcode(value="3017620422003")
        assert barcode.value == "3017620422003"
        assert len(barcode.value) == 13

    def test_create_valid_ean8(self) -> None:
        """Should create valid EAN-8 barcode."""
        barcode = Barcode(value="12345678")
        assert barcode.value == "12345678"
        assert len(barcode.value) == 8

    def test_is_valid(self) -> None:
        """Should validate format."""
        barcode = Barcode(value="3017620422003")
        assert barcode.is_valid() is True

    def test_reject_too_short(self) -> None:
        """Should reject barcode too short."""
        with pytest.raises(ValueError):
            Barcode(value="1234567")  # 7 digits

    def test_reject_too_long(self) -> None:
        """Should reject barcode too long."""
        with pytest.raises(ValueError):
            Barcode(value="12345678901234")  # 14 digits

    def test_reject_non_digits(self) -> None:
        """Should reject non-digit characters."""
        with pytest.raises(ValueError):
            Barcode(value="123456789ABC")

    def test_immutable(self) -> None:
        """Should be immutable."""
        barcode = Barcode(value="3017620422003")
        with pytest.raises(Exception):
            barcode.value = "1234567890"  # noqa: SLF001


class TestAnalysisId:
    """Test AnalysisId value object."""

    def test_generate(self) -> None:
        """Should generate valid analysis ID."""
        analysis_id = AnalysisId.generate()
        assert analysis_id.value.startswith("analysis_")
        assert len(analysis_id.value) == 21  # "analysis_" + 12 hex

    def test_generate_unique(self) -> None:
        """Should generate unique IDs."""
        id1 = AnalysisId.generate()
        id2 = AnalysisId.generate()
        assert id1.value != id2.value

    def test_create_from_string(self) -> None:
        """Should create from valid string."""
        analysis_id = AnalysisId.from_string("analysis_abc123def456")
        assert analysis_id.value == "analysis_abc123def456"

    def test_reject_invalid_format(self) -> None:
        """Should reject invalid format."""
        with pytest.raises(ValueError):
            AnalysisId(value="invalid_format")

    def test_reject_wrong_prefix(self) -> None:
        """Should reject wrong prefix."""
        with pytest.raises(ValueError):
            AnalysisId(value="meal_abc123def456")

    def test_reject_wrong_length(self) -> None:
        """Should reject wrong hex length."""
        with pytest.raises(ValueError):
            AnalysisId(value="analysis_abc")  # Too short


class TestMealId:
    """Test MealId value object."""

    def test_create_valid(self) -> None:
        """Should create valid meal ID."""
        meal_id = MealId(value="507f1f77bcf86cd799439011")
        assert len(meal_id.value) == 24

    def test_generate(self) -> None:
        """Should generate valid ID."""
        meal_id = MealId.generate()
        assert len(meal_id.value) > 0

    def test_from_string(self) -> None:
        """Should create from string."""
        meal_id = MealId.from_string("abc123")
        assert meal_id.value == "abc123"


class TestIdempotencyKey:
    """Test IdempotencyKey value object."""

    def test_create_valid(self) -> None:
        """Should create valid key."""
        key = IdempotencyKey(value="meal_abc123")
        assert key.value == "meal_abc123"

    def test_from_string(self) -> None:
        """Should create from string."""
        key = IdempotencyKey.from_string("request_xyz789")
        assert key.value == "request_xyz789"

    def test_reject_empty(self) -> None:
        """Should reject empty string."""
        with pytest.raises(ValueError):
            IdempotencyKey(value="")

    def test_reject_too_long(self) -> None:
        """Should reject keys >100 chars."""
        long_key = "x" * 101
        with pytest.raises(ValueError):
            IdempotencyKey(value=long_key)
