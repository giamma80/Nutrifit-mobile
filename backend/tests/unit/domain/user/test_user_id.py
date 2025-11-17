"""Unit tests for UserId value object."""

import pytest
import uuid

from domain.user.core.value_objects.user_id import UserId


class TestUserId:
    """Test UserId value object."""

    def test_generate_creates_valid_uuid(self):
        """Test that generate() creates valid UUID."""
        user_id = UserId.generate()

        assert user_id is not None
        assert user_id.value is not None
        # Validate it's a valid UUID
        uuid.UUID(user_id.value)

    def test_generate_creates_unique_ids(self):
        """Test that generate() creates unique IDs."""
        user_id1 = UserId.generate()
        user_id2 = UserId.generate()

        assert user_id1 != user_id2
        assert user_id1.value != user_id2.value

    def test_create_with_valid_uuid(self):
        """Test creating UserId with valid UUID string."""
        uuid_str = str(uuid.uuid4())
        user_id = UserId(uuid_str)

        assert user_id.value == uuid_str

    def test_create_with_invalid_uuid_raises_error(self):
        """Test that invalid UUID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            UserId("not-a-valid-uuid")

    def test_create_with_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            UserId("")

    def test_str_returns_value(self):
        """Test that __str__ returns the UUID value."""
        uuid_str = str(uuid.uuid4())
        user_id = UserId(uuid_str)

        assert str(user_id) == uuid_str

    def test_repr_returns_formatted_string(self):
        """Test that __repr__ returns formatted representation."""
        uuid_str = str(uuid.uuid4())
        user_id = UserId(uuid_str)

        assert repr(user_id) == f"UserId('{uuid_str}')"

    def test_equality(self):
        """Test that two UserIds with same value are equal."""
        uuid_str = str(uuid.uuid4())
        user_id1 = UserId(uuid_str)
        user_id2 = UserId(uuid_str)

        assert user_id1 == user_id2

    def test_inequality(self):
        """Test that two UserIds with different values are not equal."""
        user_id1 = UserId.generate()
        user_id2 = UserId.generate()

        assert user_id1 != user_id2

    def test_immutability(self):
        """Test that UserId is immutable."""
        user_id = UserId.generate()

        with pytest.raises(Exception):  # FrozenInstanceError
            user_id.value = "new-value"  # type: ignore

    def test_hashable(self):
        """Test that UserId can be used in sets/dicts."""
        user_id1 = UserId.generate()
        user_id2 = UserId.generate()

        user_id_set = {user_id1, user_id2}
        assert len(user_id_set) == 2

        user_id_dict = {user_id1: "user1", user_id2: "user2"}
        assert len(user_id_dict) == 2
