"""Test Auth0Sub value object."""

import pytest

from domain.user.core.value_objects.auth0_sub import Auth0Sub


class TestAuth0SubUserFormat:
    """Test Auth0Sub with standard user authentication format (provider|id)."""

    def test_auth0_provider(self) -> None:
        """Test Auth0 native provider format."""
        sub = Auth0Sub("auth0|123456789")
        assert sub.value == "auth0|123456789"
        assert sub.provider == "auth0"
        assert sub.external_id == "123456789"
        assert sub.is_client is False
        assert str(sub) == "auth0|123456789"

    def test_google_oauth2_provider(self) -> None:
        """Test Google OAuth2 provider format."""
        sub = Auth0Sub("google-oauth2|987654321")
        assert sub.value == "google-oauth2|987654321"
        assert sub.provider == "google-oauth2"
        assert sub.external_id == "987654321"
        assert sub.is_client is False

    def test_facebook_provider(self) -> None:
        """Test Facebook provider format."""
        sub = Auth0Sub("facebook|111222333")
        assert sub.provider == "facebook"
        assert sub.external_id == "111222333"
        assert sub.is_client is False


class TestAuth0SubClientCredentials:
    """Test Auth0Sub with client_credentials (M2M) format (client_id@clients)."""

    def test_client_credentials_format(self) -> None:
        """Test client_credentials format is accepted."""
        sub = Auth0Sub("4Po4EMtD5sQn4pu86u3eNzLg31FICnS4@clients")
        assert sub.value == "4Po4EMtD5sQn4pu86u3eNzLg31FICnS4@clients"
        assert sub.provider == "clients"
        assert sub.external_id == "4Po4EMtD5sQn4pu86u3eNzLg31FICnS4"
        assert sub.is_client is True

    def test_short_client_id(self) -> None:
        """Test short client ID format."""
        sub = Auth0Sub("abc123@clients")
        assert sub.provider == "clients"
        assert sub.external_id == "abc123"
        assert sub.is_client is True

    def test_client_string_representation(self) -> None:
        """Test string representation maintains original format."""
        original = "test_client_id@clients"
        sub = Auth0Sub(original)
        assert str(sub) == original


class TestAuth0SubValidation:
    """Test Auth0Sub validation rules."""

    def test_empty_value_raises(self) -> None:
        """Test empty sub raises ValueError."""
        with pytest.raises(ValueError, match="Auth0 sub cannot be empty"):
            Auth0Sub("")

    def test_invalid_format_no_separator(self) -> None:
        """Test sub without | or @clients raises ValueError."""
        with pytest.raises(
            ValueError,
            match=(
                "Invalid Auth0 sub format.*"
                "Expected format: <provider>\\|<id> or <client_id>@clients"
            ),
        ):
            Auth0Sub("invalid_format_no_separator")

    def test_too_long_raises(self) -> None:
        """Test sub longer than 255 chars raises ValueError."""
        long_sub = "auth0|" + "x" * 250
        with pytest.raises(ValueError, match="Auth0 sub too long.*Maximum 255 characters allowed"):
            Auth0Sub(long_sub)

    def test_max_length_accepted(self) -> None:
        """Test sub at exactly 255 chars is accepted."""
        # 249 chars for id + "auth0|" (6 chars) = 255 total
        max_sub = "auth0|" + "x" * 249
        sub = Auth0Sub(max_sub)
        assert len(sub.value) == 255


class TestAuth0SubRepr:
    """Test Auth0Sub string representations."""

    def test_str_returns_value(self) -> None:
        """Test __str__ returns the value."""
        sub = Auth0Sub("auth0|123")
        assert str(sub) == "auth0|123"

    def test_repr_includes_class_and_value(self) -> None:
        """Test __repr__ is developer-friendly."""
        sub = Auth0Sub("auth0|456")
        assert repr(sub) == "Auth0Sub('auth0|456')"

    def test_repr_client_format(self) -> None:
        """Test __repr__ with client format."""
        sub = Auth0Sub("client@clients")
        assert repr(sub) == "Auth0Sub('client@clients')"


class TestAuth0SubEdgeCases:
    """Test Auth0Sub edge cases and special scenarios."""

    def test_multiple_pipes(self) -> None:
        """Test sub with multiple pipes uses first as separator."""
        sub = Auth0Sub("provider|id|extra")
        assert sub.provider == "provider"
        assert sub.external_id == "id|extra"  # Everything after first pipe

    def test_pipe_at_end(self) -> None:
        """Test sub with pipe at end."""
        sub = Auth0Sub("provider|")
        assert sub.provider == "provider"
        assert sub.external_id == ""

    def test_special_characters_in_id(self) -> None:
        """Test sub with special characters in ID part."""
        sub = Auth0Sub("auth0|user-123_test@example.com")
        assert sub.provider == "auth0"
        assert sub.external_id == "user-123_test@example.com"

    def test_unicode_characters(self) -> None:
        """Test sub with unicode characters."""
        sub = Auth0Sub("auth0|用户123")
        assert sub.provider == "auth0"
        assert sub.external_id == "用户123"
