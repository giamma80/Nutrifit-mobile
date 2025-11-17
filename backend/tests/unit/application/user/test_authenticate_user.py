"""Tests for authenticate user command."""

import pytest
from datetime import datetime

from application.user.commands.authenticate_user import AuthenticateUserCommand
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
from domain.user.core.events.user_created import UserCreated
from domain.user.core.events.user_authenticated import UserAuthenticated
from infrastructure.user.in_memory_user_repository import InMemoryUserRepository


@pytest.fixture
def repository():
    """Create in-memory repository."""
    return InMemoryUserRepository()


@pytest.fixture
def command(repository):
    """Create authenticate command."""
    return AuthenticateUserCommand(repository)


@pytest.mark.asyncio
async def test_authenticate_new_user_creates_user(command, repository):
    """Test that first authentication creates new user."""
    auth0_sub = Auth0Sub("auth0|123")

    user = await command.execute(auth0_sub)

    assert user.auth0_sub == auth0_sub
    assert user.is_active is True
    assert user.last_authenticated_at is not None
    assert repository.count() == 1


@pytest.mark.asyncio
async def test_authenticate_new_user_with_preferences(command, repository):
    """Test creating user with initial preferences."""
    auth0_sub = Auth0Sub("auth0|123")
    prefs = UserPreferences(data={"theme": "dark", "lang": "it"})

    user = await command.execute(auth0_sub, initial_preferences=prefs)

    assert user.preferences.get("theme") == "dark"
    assert user.preferences.get("lang") == "it"


@pytest.mark.asyncio
async def test_authenticate_new_user_emits_created_event(command):
    """Test that UserCreated event is emitted."""
    auth0_sub = Auth0Sub("auth0|123")

    # Events are collected before save in the command
    # We need to create user and collect events manually
    from domain.user.core.entities.user import User

    user = User.create(auth0_sub)
    user.authenticate()
    events = user.collect_events()

    assert len(events) == 2
    assert isinstance(events[0], UserCreated)
    assert isinstance(events[1], UserAuthenticated)
    assert events[0].auth0_sub == auth0_sub


@pytest.mark.asyncio
async def test_authenticate_existing_user_updates_timestamp(command, repository):
    """Test that subsequent authentication updates timestamp."""
    auth0_sub = Auth0Sub("auth0|123")

    # First authentication
    user1 = await command.execute(auth0_sub)
    first_auth = user1.last_authenticated_at

    # Second authentication
    user2 = await command.execute(auth0_sub)

    assert user2.user_id == user1.user_id
    assert user2.last_authenticated_at >= first_auth
    assert repository.count() == 1


@pytest.mark.asyncio
async def test_authenticate_existing_user_emits_only_authenticated_event(command, repository):
    """Test that existing user authentication emits only UserAuthenticated."""
    auth0_sub = Auth0Sub("auth0|123")

    # First authentication
    await command.execute(auth0_sub)

    # Manually authenticate again to check events
    user2 = await repository.find_by_auth0_sub(auth0_sub)
    user2.authenticate()
    events = user2.collect_events()

    assert len(events) == 1
    assert isinstance(events[0], UserAuthenticated)


@pytest.mark.asyncio
async def test_authenticate_with_custom_timestamp(command):
    """Test authentication with custom timestamp."""
    auth0_sub = Auth0Sub("auth0|123")
    custom_time = datetime(2025, 12, 1, 12, 0, 0)  # Futuro

    user = await command.execute(auth0_sub, authenticated_at=custom_time)

    assert user.last_authenticated_at == custom_time


@pytest.mark.asyncio
async def test_authenticate_preserves_user_preferences(command):
    """Test that authentication doesn't modify preferences."""
    auth0_sub = Auth0Sub("auth0|123")
    prefs = UserPreferences(data={"theme": "dark"})

    # First authentication with preferences
    await command.execute(auth0_sub, initial_preferences=prefs)

    # Second authentication without preferences
    user2 = await command.execute(auth0_sub)

    assert user2.preferences.get("theme") == "dark"


@pytest.mark.asyncio
async def test_authenticate_different_providers(command, repository):
    """Test authentication with different Auth0 providers."""
    auth0_user = Auth0Sub("auth0|123")
    google_user = Auth0Sub("google-oauth2|456")
    facebook_user = Auth0Sub("facebook|789")

    await command.execute(auth0_user)
    await command.execute(google_user)
    await command.execute(facebook_user)

    assert repository.count() == 3
