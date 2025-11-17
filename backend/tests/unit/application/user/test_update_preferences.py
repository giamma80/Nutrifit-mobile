"""Tests for update preferences command."""

import pytest

from application.user.commands.authenticate_user import AuthenticateUserCommand
from application.user.commands.update_preferences import UpdatePreferencesCommand
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
from domain.user.core.events.user_updated import UserProfileUpdated
from domain.user.core.exceptions.user_errors import UserNotFoundError, InactiveUserError
from infrastructure.user.in_memory_user_repository import InMemoryUserRepository


@pytest.fixture
def repository():
    """Create in-memory repository."""
    return InMemoryUserRepository()


@pytest.fixture
def auth_command(repository):
    """Create authenticate command."""
    return AuthenticateUserCommand(repository)


@pytest.fixture
def update_command(repository):
    """Create update preferences command."""
    return UpdatePreferencesCommand(repository)


@pytest.mark.asyncio
async def test_update_preferences_success(auth_command, update_command):
    """Test successful preferences update."""
    auth0_sub = Auth0Sub("auth0|123")
    await auth_command.execute(auth0_sub)

    new_prefs = UserPreferences(data={"theme": "dark", "lang": "it"})
    user = await update_command.execute(auth0_sub, new_prefs)

    assert user.preferences.get("theme") == "dark"
    assert user.preferences.get("lang") == "it"


@pytest.mark.asyncio
async def test_update_preferences_emits_event(auth_command, update_command, repository):
    """Test that UserProfileUpdated event is emitted."""
    auth0_sub = Auth0Sub("auth0|123")
    await auth_command.execute(auth0_sub)

    # Manually update to check events
    user = await repository.find_by_auth0_sub(auth0_sub)
    new_prefs = UserPreferences(data={"theme": "dark"})
    user.update_preferences(new_prefs)
    events = user.collect_events()

    assert len(events) == 1
    assert isinstance(events[0], UserProfileUpdated)


@pytest.mark.asyncio
async def test_update_preferences_updates_timestamp(auth_command, update_command):
    """Test that updated_at is updated."""
    auth0_sub = Auth0Sub("auth0|123")
    user1 = await auth_command.execute(auth0_sub)
    initial_updated_at = user1.updated_at

    new_prefs = UserPreferences(data={"theme": "dark"})
    user2 = await update_command.execute(auth0_sub, new_prefs)

    assert user2.updated_at >= initial_updated_at


@pytest.mark.asyncio
async def test_update_preferences_nonexistent_user_raises_error(update_command):
    """Test that updating non-existent user raises error."""
    auth0_sub = Auth0Sub("auth0|999")
    new_prefs = UserPreferences(data={"theme": "dark"})

    with pytest.raises(UserNotFoundError) as exc_info:
        await update_command.execute(auth0_sub, new_prefs)

    assert "auth0|999" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_preferences_inactive_user_raises_error(
    auth_command, update_command, repository
):
    """Test that updating inactive user raises error."""
    auth0_sub = Auth0Sub("auth0|123")
    user = await auth_command.execute(auth0_sub)

    # Deactivate user
    user.deactivate()
    await repository.save(user)

    # Try to update preferences
    new_prefs = UserPreferences(data={"theme": "dark"})

    with pytest.raises(InactiveUserError):
        await update_command.execute(auth0_sub, new_prefs)


@pytest.mark.asyncio
async def test_update_preferences_replaces_existing_preferences(auth_command, update_command):
    """Test that new preferences replace old ones."""
    auth0_sub = Auth0Sub("auth0|123")
    initial_prefs = UserPreferences(data={"theme": "light", "lang": "en"})
    await auth_command.execute(auth0_sub, initial_preferences=initial_prefs)

    new_prefs = UserPreferences(data={"theme": "dark", "notifications": True})
    user = await update_command.execute(auth0_sub, new_prefs)

    # update_preferences sostituisce completamente le preferenze
    assert user.preferences.get("theme") == "dark"
    assert user.preferences.get("notifications") is True
    assert user.preferences.get("lang") is None  # Old value NOT preserved


@pytest.mark.asyncio
async def test_update_preferences_with_empty_preferences(auth_command, update_command):
    """Test updating with empty preferences."""
    auth0_sub = Auth0Sub("auth0|123")
    await auth_command.execute(auth0_sub)

    empty_prefs = UserPreferences(data={})
    user = await update_command.execute(auth0_sub, empty_prefs)

    assert user.preferences.data == {}


@pytest.mark.asyncio
async def test_update_preferences_multiple_users(auth_command, update_command):
    """Test updating preferences for multiple users."""
    auth0_sub1 = Auth0Sub("auth0|111")
    auth0_sub2 = Auth0Sub("auth0|222")

    await auth_command.execute(auth0_sub1)
    await auth_command.execute(auth0_sub2)

    prefs1 = UserPreferences(data={"theme": "dark"})
    prefs2 = UserPreferences(data={"theme": "light"})

    user1 = await update_command.execute(auth0_sub1, prefs1)
    user2 = await update_command.execute(auth0_sub2, prefs2)

    assert user1.preferences.get("theme") == "dark"
    assert user2.preferences.get("theme") == "light"
