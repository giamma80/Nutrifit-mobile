"""Tests for deactivate user command."""

import pytest

from application.user.commands.authenticate_user import AuthenticateUserCommand
from application.user.commands.deactivate_user import DeactivateUserCommand
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.exceptions.user_errors import UserNotFoundError
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
def deactivate_command(repository):
    """Create deactivate command."""
    return DeactivateUserCommand(repository)


@pytest.mark.asyncio
async def test_deactivate_user_success(auth_command, deactivate_command):
    """Test successful user deactivation."""
    auth0_sub = Auth0Sub("auth0|123")
    await auth_command.execute(auth0_sub)

    user = await deactivate_command.execute(auth0_sub)

    assert user.is_active is False


@pytest.mark.asyncio
async def test_deactivate_nonexistent_user_raises_error(deactivate_command):
    """Test that deactivating non-existent user raises error."""
    auth0_sub = Auth0Sub("auth0|999")

    with pytest.raises(UserNotFoundError) as exc_info:
        await deactivate_command.execute(auth0_sub)

    assert "auth0|999" in str(exc_info.value)


@pytest.mark.asyncio
async def test_deactivate_already_inactive_user(auth_command, deactivate_command, repository):
    """Test deactivating already inactive user."""
    auth0_sub = Auth0Sub("auth0|123")
    user = await auth_command.execute(auth0_sub)

    # Deactivate once
    user.deactivate()
    await repository.save(user)

    # Deactivate again
    user = await deactivate_command.execute(auth0_sub)

    assert user.is_active is False


@pytest.mark.asyncio
async def test_deactivate_preserves_user_data(auth_command, deactivate_command):
    """Test that deactivation preserves user data."""
    auth0_sub = Auth0Sub("auth0|123")
    created_user = await auth_command.execute(auth0_sub)

    user = await deactivate_command.execute(auth0_sub)

    assert user.user_id == created_user.user_id
    assert user.auth0_sub == created_user.auth0_sub
    assert user.created_at == created_user.created_at
    assert user.preferences == created_user.preferences


@pytest.mark.asyncio
async def test_deactivate_persists_to_repository(auth_command, deactivate_command, repository):
    """Test that deactivation is persisted."""
    auth0_sub = Auth0Sub("auth0|123")
    await auth_command.execute(auth0_sub)

    await deactivate_command.execute(auth0_sub)

    # Retrieve user from repository
    user = await repository.find_by_auth0_sub(auth0_sub)

    assert user is not None
    assert user.is_active is False
