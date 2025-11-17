"""Tests for get user query."""

import pytest

from application.user.commands.authenticate_user import AuthenticateUserCommand
from application.user.queries.get_user import GetUserQuery
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
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
def query(repository):
    """Create get user query."""
    return GetUserQuery(repository)


@pytest.mark.asyncio
async def test_get_user_by_auth0_sub_success(auth_command, query):
    """Test getting user by Auth0 subject."""
    auth0_sub = Auth0Sub("auth0|123")
    created_user = await auth_command.execute(auth0_sub)

    user = await query.by_auth0_sub(auth0_sub)

    assert user is not None
    assert user.user_id == created_user.user_id
    assert user.auth0_sub == auth0_sub


@pytest.mark.asyncio
async def test_get_user_by_auth0_sub_not_found(query):
    """Test getting non-existent user returns None."""
    auth0_sub = Auth0Sub("auth0|999")

    user = await query.by_auth0_sub(auth0_sub)

    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_id_success(auth_command, query):
    """Test getting user by internal user ID."""
    auth0_sub = Auth0Sub("auth0|123")
    created_user = await auth_command.execute(auth0_sub)

    user = await query.by_id(created_user.user_id)

    assert user is not None
    assert user.user_id == created_user.user_id
    assert user.auth0_sub == auth0_sub


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(query):
    """Test getting non-existent user by ID returns None."""
    from domain.user.core.value_objects.user_id import UserId
    import uuid

    user_id = UserId(str(uuid.uuid4()))

    user = await query.by_id(user_id)

    assert user is None


@pytest.mark.asyncio
async def test_exists_returns_true_for_existing_user(auth_command, query):
    """Test exists returns True for existing user."""
    auth0_sub = Auth0Sub("auth0|123")
    await auth_command.execute(auth0_sub)

    exists = await query.exists(auth0_sub)

    assert exists is True


@pytest.mark.asyncio
async def test_exists_returns_false_for_nonexistent_user(query):
    """Test exists returns False for non-existent user."""
    auth0_sub = Auth0Sub("auth0|999")

    exists = await query.exists(auth0_sub)

    assert exists is False


@pytest.mark.asyncio
async def test_get_user_retrieves_all_data(auth_command, query):
    """Test that query retrieves all user data."""
    auth0_sub = Auth0Sub("auth0|123")
    prefs = UserPreferences(data={"theme": "dark", "lang": "it"})
    await auth_command.execute(auth0_sub, initial_preferences=prefs)

    user = await query.by_auth0_sub(auth0_sub)

    assert user is not None
    assert user.preferences.get("theme") == "dark"
    assert user.preferences.get("lang") == "it"
    assert user.created_at is not None
    assert user.updated_at is not None
    assert user.last_authenticated_at is not None
    assert user.is_active is True


@pytest.mark.asyncio
async def test_get_multiple_users(auth_command, query):
    """Test querying multiple users."""
    auth0_sub1 = Auth0Sub("auth0|111")
    auth0_sub2 = Auth0Sub("google-oauth2|222")

    user1_created = await auth_command.execute(auth0_sub1)
    user2_created = await auth_command.execute(auth0_sub2)

    user1 = await query.by_auth0_sub(auth0_sub1)
    user2 = await query.by_auth0_sub(auth0_sub2)

    assert user1 is not None
    assert user2 is not None
    assert user1.user_id == user1_created.user_id
    assert user2.user_id == user2_created.user_id


@pytest.mark.asyncio
async def test_get_user_after_deactivation(auth_command, query, repository):
    """Test getting deactivated user."""
    auth0_sub = Auth0Sub("auth0|123")
    user = await auth_command.execute(auth0_sub)

    user.deactivate()
    await repository.save(user)

    retrieved_user = await query.by_auth0_sub(auth0_sub)

    assert retrieved_user is not None
    assert retrieved_user.is_active is False
