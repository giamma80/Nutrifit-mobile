"""Unit tests for UserPreferences value object."""

import pytest
import json

from domain.user.core.value_objects.user_preferences import UserPreferences


class TestUserPreferences:
    """Test UserPreferences value object."""

    def test_default_creates_empty_preferences(self):
        """Test that default() creates empty preferences."""
        prefs = UserPreferences.default()

        assert prefs.data == {}
        assert len(prefs) == 0

    def test_create_with_data(self):
        """Test creating UserPreferences with data."""
        data = {"theme": "dark", "language": "it"}
        prefs = UserPreferences(data=data)

        assert prefs.data == data
        assert len(prefs) == 2

    def test_create_with_non_dict_raises_error(self):
        """Test that non-dict data raises TypeError."""
        with pytest.raises(TypeError, match="must be a dictionary"):
            UserPreferences(data="not-a-dict")  # type: ignore

    def test_create_with_non_json_serializable_raises_error(self):
        """Test that non-JSON-serializable data raises ValueError."""

        class NotSerializable:
            pass

        with pytest.raises(ValueError, match="must be JSON-serializable"):
            UserPreferences(data={"obj": NotSerializable()})

    def test_get_existing_key(self):
        """Test getting existing preference value."""
        prefs = UserPreferences(data={"theme": "dark"})

        assert prefs.get("theme") == "dark"

    def test_get_missing_key_returns_default(self):
        """Test getting missing key returns default value."""
        prefs = UserPreferences(data={"theme": "dark"})

        assert prefs.get("missing") is None
        assert prefs.get("missing", "default") == "default"

    def test_with_value_returns_new_instance(self):
        """Test that with_value() returns new instance (immutability)."""
        prefs1 = UserPreferences.default()
        prefs2 = prefs1.with_value("theme", "dark")

        assert prefs1.data == {}
        assert prefs2.data == {"theme": "dark"}
        assert prefs1 is not prefs2

    def test_with_value_updates_existing_key(self):
        """Test that with_value() can update existing key."""
        prefs1 = UserPreferences(data={"theme": "light"})
        prefs2 = prefs1.with_value("theme", "dark")

        assert prefs1.get("theme") == "light"
        assert prefs2.get("theme") == "dark"

    def test_with_values_updates_multiple_keys(self):
        """Test that with_values() updates multiple preferences."""
        prefs1 = UserPreferences.default()
        updates = {"theme": "dark", "language": "it", "notifications": True}
        prefs2 = prefs1.with_values(updates)

        assert prefs1.data == {}
        assert prefs2.data == updates

    def test_with_values_merges_with_existing(self):
        """Test that with_values() merges with existing data."""
        prefs1 = UserPreferences(data={"theme": "dark"})
        prefs2 = prefs1.with_values({"language": "it"})

        assert prefs2.data == {"theme": "dark", "language": "it"}

    def test_without_key_removes_key(self):
        """Test that without_key() removes preference."""
        prefs1 = UserPreferences(data={"theme": "dark", "language": "it"})
        prefs2 = prefs1.without_key("theme")

        assert prefs1.data == {"theme": "dark", "language": "it"}
        assert prefs2.data == {"language": "it"}

    def test_without_key_missing_key_no_error(self):
        """Test that without_key() with missing key doesn't raise error."""
        prefs1 = UserPreferences(data={"theme": "dark"})
        prefs2 = prefs1.without_key("missing")

        assert prefs2.data == {"theme": "dark"}

    def test_contains_operator(self):
        """Test that 'in' operator works."""
        prefs = UserPreferences(data={"theme": "dark"})

        assert "theme" in prefs
        assert "missing" not in prefs

    def test_len_returns_correct_count(self):
        """Test that len() returns correct count."""
        prefs = UserPreferences(data={"theme": "dark", "language": "it"})

        assert len(prefs) == 2

    def test_immutability(self):
        """Test that UserPreferences is immutable."""
        prefs = UserPreferences(data={"theme": "dark"})

        with pytest.raises(Exception):  # FrozenInstanceError
            prefs.data = {}  # type: ignore

    def test_json_serializable_validation(self):
        """Test that only JSON-serializable values are accepted."""
        # Valid JSON types
        valid_data = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }
        prefs = UserPreferences(data=valid_data)

        # Ensure it's actually JSON serializable
        json_str = json.dumps(prefs.data)
        assert json_str is not None

    def test_nested_preferences(self):
        """Test handling nested preference structures."""
        nested_data = {
            "notifications": {"email": True, "push": False, "sms": True},
            "privacy": {"profile_visible": True, "show_activity": False},
        }
        prefs = UserPreferences(data=nested_data)

        assert prefs.get("notifications") == nested_data["notifications"]
        assert prefs.get("privacy")["profile_visible"] is True

    def test_chaining_modifications(self):
        """Test chaining multiple modifications."""
        prefs = (
            UserPreferences.default()
            .with_value("theme", "dark")
            .with_value("language", "it")
            .with_value("notifications", True)
        )

        assert prefs.data == {"theme": "dark", "language": "it", "notifications": True}

    def test_equality(self):
        """Test that two UserPreferences with same data are equal."""
        prefs1 = UserPreferences(data={"theme": "dark"})
        prefs2 = UserPreferences(data={"theme": "dark"})

        assert prefs1 == prefs2

    def test_inequality(self):
        """Test that two UserPreferences with different data are not equal."""
        prefs1 = UserPreferences(data={"theme": "dark"})
        prefs2 = UserPreferences(data={"theme": "light"})

        assert prefs1 != prefs2
