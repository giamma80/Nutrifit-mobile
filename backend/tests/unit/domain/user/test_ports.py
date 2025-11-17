"""Unit tests for user domain ports (interfaces).

Note: Ports are interfaces/protocols that define contracts.
Full coverage is achieved through tests of concrete implementations:
- IUserRepository: tested via MongoUserRepository and InMemoryUserRepository tests
- IAuthProvider: tested via Auth0Provider tests

These tests verify the interface structure and documentation.
"""

from domain.user.core.ports.user_repository import IUserRepository
from domain.user.auth.ports.auth_provider import (
    IAuthProvider,
    InvalidTokenError,
    JWKSError,
    Auth0APIError,
)


class TestUserRepositoryPort:
    """Test IUserRepository interface structure."""

    def test_interface_has_required_methods(self):
        """Test that IUserRepository defines all required methods."""
        # Verify interface has all expected methods
        assert hasattr(IUserRepository, "save")
        assert hasattr(IUserRepository, "find_by_id")
        assert hasattr(IUserRepository, "find_by_auth0_sub")
        assert hasattr(IUserRepository, "exists")
        assert hasattr(IUserRepository, "delete")

    def test_interface_is_documented(self):
        """Test that IUserRepository has docstring."""
        assert IUserRepository.__doc__ is not None
        assert "Repository" in IUserRepository.__doc__


class TestAuthProviderPort:
    """Test IAuthProvider interface structure."""

    def test_interface_has_required_methods(self):
        """Test that IAuthProvider defines all required methods."""
        assert hasattr(IAuthProvider, "verify_token")
        assert hasattr(IAuthProvider, "get_user_info")

    def test_interface_is_documented(self):
        """Test that IAuthProvider has docstring."""
        assert IAuthProvider.__doc__ is not None

    def test_invalid_token_error(self):
        """Test InvalidTokenError exception."""
        error = InvalidTokenError("Token expired")

        assert "Token expired" in str(error)
        assert isinstance(error, Exception)

    def test_jwks_error(self):
        """Test JWKSError exception."""
        error = JWKSError("Failed to fetch JWKS")

        assert "Failed to fetch JWKS" in str(error)
        assert isinstance(error, Exception)

    def test_auth0_api_error(self):
        """Test Auth0APIError exception."""
        error = Auth0APIError("/api/v2/users", 500, "Internal Server Error")

        assert "/api/v2/users" in str(error)
        assert "500" in str(error)
        assert "Internal Server Error" in str(error)
        assert error.endpoint == "/api/v2/users"
        assert error.status_code == 500
        assert error.message == "Internal Server Error"
        assert isinstance(error, Exception)

    def test_auth0_api_error_with_different_status(self):
        """Test Auth0APIError with 401 Unauthorized."""
        error = Auth0APIError("/oauth/token", 401, "Unauthorized")

        assert error.status_code == 401
        assert "401" in str(error)
        assert "Unauthorized" in str(error)
