"""Tests for user event handlers."""

import pytest
from datetime import datetime
from unittest.mock import patch

from application.user.handlers.user_created_handler import UserCreatedHandler
from application.user.handlers.user_authenticated_handler import UserAuthenticatedHandler
from application.user.handlers.user_profile_updated_handler import UserProfileUpdatedHandler
from domain.user.core.events.user_created import UserCreated
from domain.user.core.events.user_authenticated import UserAuthenticated
from domain.user.core.events.user_updated import UserProfileUpdated
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub


@pytest.fixture
def user_created_handler():
    """Create UserCreatedHandler."""
    return UserCreatedHandler()


@pytest.fixture
def user_authenticated_handler():
    """Create UserAuthenticatedHandler."""
    return UserAuthenticatedHandler()


@pytest.fixture
def user_profile_updated_handler():
    """Create UserProfileUpdatedHandler."""
    return UserProfileUpdatedHandler()


@pytest.mark.asyncio
async def test_user_created_handler_logs_event(user_created_handler):
    """Test that UserCreatedHandler logs the event."""
    event = UserCreated(
        user_id=UserId("550e8400-e29b-41d4-a716-446655440000"),
        auth0_sub=Auth0Sub("auth0|123"),
        created_at=datetime(2025, 11, 17, 12, 0, 0),
    )

    with patch("application.user.handlers.user_created_handler.logger") as mock_logger:
        await user_created_handler.handle(event)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "User created" in call_args[0]
        assert "user_id" in call_args[1]["extra"]
        assert "auth0_sub" in call_args[1]["extra"]
        assert "created_at" in call_args[1]["extra"]


@pytest.mark.asyncio
async def test_user_authenticated_handler_logs_event(user_authenticated_handler):
    """Test that UserAuthenticatedHandler logs the event."""
    event = UserAuthenticated(
        user_id=UserId("550e8400-e29b-41d4-a716-446655440000"),
        auth0_sub=Auth0Sub("auth0|123"),
        authenticated_at=datetime(2025, 11, 17, 12, 0, 0),
    )

    with patch("application.user.handlers.user_authenticated_handler.logger") as mock_logger:
        await user_authenticated_handler.handle(event)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "User authenticated" in call_args[0]
        assert "user_id" in call_args[1]["extra"]
        assert "authenticated_at" in call_args[1]["extra"]


@pytest.mark.asyncio
async def test_user_profile_updated_handler_logs_event(user_profile_updated_handler):
    """Test that UserProfileUpdatedHandler logs the event."""
    from domain.user.core.value_objects.user_preferences import UserPreferences

    event = UserProfileUpdated(
        user_id=UserId("550e8400-e29b-41d4-a716-446655440000"),
        auth0_sub=Auth0Sub("auth0|123"),
        old_preferences=UserPreferences.default(),
        new_preferences=UserPreferences(data={"theme": "dark"}),
        updated_at=datetime(2025, 11, 17, 12, 0, 0),
    )

    with patch("application.user.handlers.user_profile_updated_handler.logger") as mock_logger:
        await user_profile_updated_handler.handle(event)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "User profile updated" in call_args[0]
        assert "user_id" in call_args[1]["extra"]
        assert "updated_at" in call_args[1]["extra"]


@pytest.mark.asyncio
async def test_handlers_are_async(
    user_created_handler,
    user_authenticated_handler,
    user_profile_updated_handler,
):
    """Test that all handlers are async."""
    import inspect

    assert inspect.iscoroutinefunction(user_created_handler.handle)
    assert inspect.iscoroutinefunction(user_authenticated_handler.handle)
    assert inspect.iscoroutinefunction(user_profile_updated_handler.handle)
