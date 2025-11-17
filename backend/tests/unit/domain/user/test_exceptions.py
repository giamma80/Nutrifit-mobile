"""Unit tests for user domain exceptions."""

import pytest

from domain.user.core.exceptions.user_errors import (
    UserDomainError,
    UserNotFoundError,
    InvalidAuth0SubError,
    UserAlreadyExistsError,
    InactiveUserError,
)
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub


class TestUserDomainExceptions:
    """Test user domain exception hierarchy."""

    def test_user_domain_error_base_class(self):
        """Test UserDomainError base exception."""
        error = UserDomainError("Test error")

        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_user_not_found_by_id(self):
        """Test UserNotFoundError with user_id."""
        user_id = UserId.generate()
        error = UserNotFoundError(str(user_id))

        assert isinstance(error, UserDomainError)
        assert str(user_id.value) in str(error)
        assert error.identifier == str(user_id)

    def test_user_not_found_by_auth0_sub(self):
        """Test UserNotFoundError with auth0_sub."""
        auth0_sub = Auth0Sub("auth0|123456789")
        error = UserNotFoundError(str(auth0_sub))

        assert isinstance(error, UserDomainError)
        assert "auth0|123456789" in str(error)
        assert error.identifier == "auth0|123456789"

    def test_user_not_found_with_custom_message(self):
        """Test UserNotFoundError with custom identifier."""
        error = UserNotFoundError("custom-id-123")

        assert isinstance(error, UserDomainError)
        assert "custom-id-123" in str(error)
        assert "not found" in str(error).lower()

    def test_invalid_auth0_sub_error(self):
        """Test InvalidAuth0SubError."""
        error = InvalidAuth0SubError("invalid-format", "missing pipe separator")

        assert isinstance(error, UserDomainError)
        assert "invalid-format" in str(error)
        assert "missing pipe separator" in str(error)
        assert error.auth0_sub == "invalid-format"
        assert error.reason == "missing pipe separator"

    def test_user_already_exists_error(self):
        """Test UserAlreadyExistsError."""
        auth0_sub = Auth0Sub("auth0|123456789")
        error = UserAlreadyExistsError(str(auth0_sub))

        assert isinstance(error, UserDomainError)
        assert "auth0|123456789" in str(error)
        assert "already exists" in str(error).lower()
        assert error.identifier == "auth0|123456789"

    def test_inactive_user_error(self):
        """Test InactiveUserError."""
        user_id = UserId.generate()
        error = InactiveUserError(str(user_id))

        assert isinstance(error, UserDomainError)
        assert str(user_id.value) in str(error)
        assert "inactive" in str(error).lower()
        assert error.user_id == str(user_id)

    def test_exception_can_be_raised_and_caught(self):
        """Test that exceptions can be raised and caught properly."""
        with pytest.raises(UserNotFoundError):
            raise UserNotFoundError(str(UserId.generate()))

    def test_exception_inheritance_chain(self):
        """Test exception inheritance hierarchy."""
        # All custom exceptions inherit from UserDomainError
        assert issubclass(UserNotFoundError, UserDomainError)
        assert issubclass(InvalidAuth0SubError, UserDomainError)
        assert issubclass(UserAlreadyExistsError, UserDomainError)
        assert issubclass(InactiveUserError, UserDomainError)

        # UserDomainError inherits from Exception
        assert issubclass(UserDomainError, Exception)

    def test_catch_any_user_domain_error(self):
        """Test catching any user domain error with base class."""
        with pytest.raises(UserDomainError):
            raise UserNotFoundError(str(UserId.generate()))

        with pytest.raises(UserDomainError):
            raise InvalidAuth0SubError("invalid", "test reason")

        with pytest.raises(UserDomainError):
            raise UserAlreadyExistsError("auth0|123")
