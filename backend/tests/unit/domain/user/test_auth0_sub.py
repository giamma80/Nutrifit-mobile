"""Unit tests for Auth0Sub value object."""

import pytest

from domain.user.core.value_objects.auth0_sub import Auth0Sub


class TestAuth0Sub:
    """Test Auth0Sub value object."""

    def test_create_with_valid_auth0_format(self):
        """Test creating Auth0Sub with valid auth0|id format."""
        auth0_sub = Auth0Sub("auth0|123456789")

        assert auth0_sub.value == "auth0|123456789"
        assert auth0_sub.provider == "auth0"
        assert auth0_sub.external_id == "123456789"

    def test_create_with_google_oauth2_format(self):
        """Test creating Auth0Sub with google-oauth2 provider."""
        auth0_sub = Auth0Sub("google-oauth2|987654321")

        assert auth0_sub.value == "google-oauth2|987654321"
        assert auth0_sub.provider == "google-oauth2"
        assert auth0_sub.external_id == "987654321"

    def test_create_with_facebook_format(self):
        """Test creating Auth0Sub with facebook provider."""
        auth0_sub = Auth0Sub("facebook|111222333")

        assert auth0_sub.provider == "facebook"
        assert auth0_sub.external_id == "111222333"

    def test_create_with_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Auth0 sub cannot be empty"):
            Auth0Sub("")

    def test_create_without_pipe_raises_error(self):
        """Test that missing pipe character raises ValueError."""
        with pytest.raises(ValueError, match="Invalid Auth0 sub format"):
            Auth0Sub("auth0_123456789")

    def test_create_with_too_long_value_raises_error(self):
        """Test that value over 255 chars raises ValueError."""
        long_value = "auth0|" + "a" * 250

        with pytest.raises(ValueError, match="Auth0 sub too long"):
            Auth0Sub(long_value)

    def test_create_with_multiple_pipes(self):
        """Test handling Auth0 sub with multiple pipes (takes first split)."""
        auth0_sub = Auth0Sub("auth0|user|with|pipes")

        assert auth0_sub.provider == "auth0"
        assert auth0_sub.external_id == "user|with|pipes"

    def test_str_returns_value(self):
        """Test that __str__ returns the full value."""
        auth0_sub = Auth0Sub("auth0|123456789")

        assert str(auth0_sub) == "auth0|123456789"

    def test_repr_returns_formatted_string(self):
        """Test that __repr__ returns formatted representation."""
        auth0_sub = Auth0Sub("auth0|123456789")

        assert repr(auth0_sub) == "Auth0Sub('auth0|123456789')"

    def test_equality(self):
        """Test that two Auth0Subs with same value are equal."""
        auth0_sub1 = Auth0Sub("auth0|123456789")
        auth0_sub2 = Auth0Sub("auth0|123456789")

        assert auth0_sub1 == auth0_sub2

    def test_inequality(self):
        """Test that two Auth0Subs with different values are not equal."""
        auth0_sub1 = Auth0Sub("auth0|123456789")
        auth0_sub2 = Auth0Sub("auth0|987654321")

        assert auth0_sub1 != auth0_sub2

    def test_immutability(self):
        """Test that Auth0Sub is immutable."""
        auth0_sub = Auth0Sub("auth0|123456789")

        with pytest.raises(Exception):  # FrozenInstanceError
            auth0_sub.value = "new-value"  # type: ignore

    def test_hashable(self):
        """Test that Auth0Sub can be used in sets/dicts."""
        auth0_sub1 = Auth0Sub("auth0|123456789")
        auth0_sub2 = Auth0Sub("google-oauth2|987654321")

        auth0_sub_set = {auth0_sub1, auth0_sub2}
        assert len(auth0_sub_set) == 2

        auth0_sub_dict = {auth0_sub1: "user1", auth0_sub2: "user2"}
        assert len(auth0_sub_dict) == 2

    def test_provider_property_edge_cases(self):
        """Test provider extraction with edge cases."""
        # Provider with hyphen
        auth0_sub = Auth0Sub("apple-oauth2|123")
        assert auth0_sub.provider == "apple-oauth2"

        # Single character provider
        auth0_sub = Auth0Sub("x|123")
        assert auth0_sub.provider == "x"

    def test_external_id_property_edge_cases(self):
        """Test external_id extraction with edge cases."""
        # Long external ID
        long_id = "a" * 100
        auth0_sub = Auth0Sub(f"auth0|{long_id}")
        assert auth0_sub.external_id == long_id

        # External ID with special characters
        auth0_sub = Auth0Sub("auth0|user@example.com")
        assert auth0_sub.external_id == "user@example.com"
