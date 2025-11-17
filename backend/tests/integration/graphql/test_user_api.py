"""Integration tests for User GraphQL API."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from graphql.resolvers.user.queries import UserQueries
from graphql.resolvers.user.mutations import UserMutations
from domain.user.core.entities.user import User
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
from infrastructure.user.in_memory_user_repository import InMemoryUserRepository
from graphql.types_user import UserPreferencesInput


class MockInfo:
    """Mock GraphQL Info object."""

    def __init__(self, repository, auth0_sub=None):
        self.context = {"user_repository": repository}
        if auth0_sub:
            mock_request = MagicMock()
            mock_request.state.auth_claims = {"sub": auth0_sub}
            self.context["request"] = mock_request


@pytest.fixture
def repository():
    """Create in-memory user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def queries():
    """Create UserQueries resolver."""
    return UserQueries()


@pytest.fixture
def mutations():
    """Create UserMutations resolver."""
    return UserMutations()


@pytest.mark.asyncio
async def test_me_query_returns_user(repository, queries):
    """Test me query returns authenticated user."""
    auth0_sub = "auth0|123"
    user = User.create(Auth0Sub(auth0_sub))
    await repository.save(user)

    info = MockInfo(repository, auth0_sub)
    result = await queries.me(info)

    assert result is not None
    assert str(result.auth0_sub) == auth0_sub
    assert result.is_active is True


@pytest.mark.asyncio
async def test_me_query_returns_none_when_not_authenticated(repository, queries):
    """Test me query returns None without authentication."""
    info = MockInfo(repository)
    result = await queries.me(info)

    assert result is None


@pytest.mark.asyncio
async def test_me_query_returns_none_when_user_not_exists(repository, queries):
    """Test me query returns None when user doesn't exist."""
    info = MockInfo(repository, "auth0|999")
    result = await queries.me(info)

    assert result is None


@pytest.mark.asyncio
async def test_exists_query_returns_true_for_existing_user(repository, queries):
    """Test exists query returns True for existing user."""
    auth0_sub = "auth0|123"
    user = User.create(Auth0Sub(auth0_sub))
    await repository.save(user)

    info = MockInfo(repository, auth0_sub)
    result = await queries.exists(info)

    assert result is True


@pytest.mark.asyncio
async def test_exists_query_returns_false_for_nonexistent_user(repository, queries):
    """Test exists query returns False for non-existent user."""
    info = MockInfo(repository, "auth0|999")
    result = await queries.exists(info)

    assert result is False


@pytest.mark.asyncio
async def test_exists_query_returns_false_without_auth(repository, queries):
    """Test exists query returns False without authentication."""
    info = MockInfo(repository)
    result = await queries.exists(info)

    assert result is False


@pytest.mark.asyncio
async def test_authenticate_mutation_creates_new_user(repository, mutations):
    """Test authenticate mutation creates new user."""
    auth0_sub = "auth0|123"
    info = MockInfo(repository, auth0_sub)

    result = await mutations.authenticate(info)

    assert result is not None
    assert str(result.auth0_sub) == auth0_sub
    assert result.is_active is True
    assert result.last_authenticated_at is not None


@pytest.mark.asyncio
async def test_authenticate_mutation_updates_existing_user(repository, mutations):
    """Test authenticate mutation updates existing user."""
    auth0_sub = "auth0|123"
    user = User.create(Auth0Sub(auth0_sub))
    await repository.save(user)

    info = MockInfo(repository, auth0_sub)
    result = await mutations.authenticate(info)

    assert result.user_id == user.user_id
    assert result.last_authenticated_at is not None


@pytest.mark.asyncio
async def test_authenticate_mutation_raises_without_auth(repository, mutations):
    """Test authenticate mutation raises without authentication."""
    info = MockInfo(repository)

    with pytest.raises(ValueError, match="Missing authentication"):
        await mutations.authenticate(info)


@pytest.mark.asyncio
async def test_update_preferences_mutation_success(repository, mutations):
    """Test update preferences mutation updates user."""
    auth0_sub = "auth0|123"
    user = User.create(Auth0Sub(auth0_sub))
    await repository.save(user)

    info = MockInfo(repository, auth0_sub)
    prefs = UserPreferencesInput(data={"theme": "dark", "lang": "it"})

    result = await mutations.update_preferences(info, prefs)

    assert result is not None
    assert result.preferences.get("theme") == "dark"
    assert result.preferences.get("lang") == "it"


@pytest.mark.asyncio
async def test_update_preferences_mutation_raises_without_auth(repository, mutations):
    """Test update preferences mutation raises without auth."""
    info = MockInfo(repository)
    prefs = UserPreferencesInput(data={"theme": "dark"})

    with pytest.raises(ValueError, match="Missing authentication"):
        await mutations.update_preferences(info, prefs)


@pytest.mark.asyncio
async def test_deactivate_mutation_success(repository, mutations):
    """Test deactivate mutation deactivates user."""
    auth0_sub = "auth0|123"
    user = User.create(Auth0Sub(auth0_sub))
    await repository.save(user)

    info = MockInfo(repository, auth0_sub)
    result = await mutations.deactivate(info)

    assert result is not None
    assert result.is_active is False


@pytest.mark.asyncio
async def test_deactivate_mutation_raises_without_auth(repository, mutations):
    """Test deactivate mutation raises without auth."""
    info = MockInfo(repository)

    with pytest.raises(ValueError, match="Missing authentication"):
        await mutations.deactivate(info)


@pytest.mark.asyncio
async def test_user_type_fields(repository, mutations):
    """Test UserType exposes all required fields."""
    auth0_sub = "auth0|123"
    prefs = UserPreferences(data={"theme": "dark"})
    user = User.create(Auth0Sub(auth0_sub), prefs)
    user.authenticate()
    await repository.save(user)

    info = MockInfo(repository, auth0_sub)
    result = await mutations.authenticate(info)

    # Verify all fields are accessible
    assert isinstance(str(result.user_id), str)
    assert isinstance(str(result.auth0_sub), str)
    assert result.preferences is not None
    assert isinstance(result.created_at, datetime)
    assert isinstance(result.updated_at, datetime)
    assert isinstance(result.last_authenticated_at, datetime)
    assert isinstance(result.is_active, bool)
