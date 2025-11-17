"""Integration tests for InMemoryUserRepository."""

import pytest

from infrastructure.user.in_memory_user_repository import InMemoryUserRepository
from domain.user.core.entities.user import User
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
from domain.user.core.exceptions.user_errors import UserNotFoundError


class TestInMemoryUserRepository:
    """Test InMemoryUserRepository implementation."""

    @pytest.fixture
    def repository(self):
        """Create fresh repository for each test."""
        return InMemoryUserRepository()

    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return User.create(Auth0Sub("auth0|123456789"))

    @pytest.mark.asyncio
    async def test_save_and_find_by_auth0_sub(self, repository, sample_user):
        """Test saving and retrieving user by auth0_sub."""
        await repository.save(sample_user)

        found = await repository.find_by_auth0_sub(sample_user.auth0_sub)

        assert found is not None
        assert found.user_id == sample_user.user_id
        assert found.auth0_sub == sample_user.auth0_sub

    @pytest.mark.asyncio
    async def test_save_and_find_by_id(self, repository, sample_user):
        """Test saving and retrieving user by user_id."""
        await repository.save(sample_user)

        found = await repository.find_by_id(sample_user.user_id)

        assert found is not None
        assert found.user_id == sample_user.user_id

    @pytest.mark.asyncio
    async def test_find_non_existent_returns_none(self, repository):
        """Test finding non-existent user returns None."""
        result = await repository.find_by_auth0_sub(Auth0Sub("auth0|nonexistent"))

        assert result is None

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing_user(self, repository, sample_user):
        """Test exists() returns True for existing user."""
        await repository.save(sample_user)

        exists = await repository.exists(sample_user.auth0_sub)

        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_non_existent(self, repository):
        """Test exists() returns False for non-existent user."""
        exists = await repository.exists(Auth0Sub("auth0|nonexistent"))

        assert exists is False

    @pytest.mark.asyncio
    async def test_update_existing_user(self, repository, sample_user):
        """Test updating existing user."""
        await repository.save(sample_user)

        # Update preferences
        new_prefs = UserPreferences(data={"theme": "dark"})
        sample_user.update_preferences(new_prefs)
        await repository.save(sample_user)

        # Retrieve and verify
        found = await repository.find_by_auth0_sub(sample_user.auth0_sub)
        assert found.preferences.get("theme") == "dark"

    @pytest.mark.asyncio
    async def test_delete_existing_user(self, repository, sample_user):
        """Test deleting existing user."""
        await repository.save(sample_user)

        await repository.delete(sample_user.auth0_sub)

        # Verify deleted
        found = await repository.find_by_auth0_sub(sample_user.auth0_sub)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_non_existent_raises_error(self, repository):
        """Test deleting non-existent user raises error."""
        with pytest.raises(UserNotFoundError):
            await repository.delete(Auth0Sub("auth0|nonexistent"))

    @pytest.mark.asyncio
    async def test_clear_removes_all_users(self, repository):
        """Test clear() removes all users."""
        # Add multiple users
        user1 = User.create(Auth0Sub("auth0|111"))
        user2 = User.create(Auth0Sub("auth0|222"))
        await repository.save(user1)
        await repository.save(user2)

        assert repository.count() == 2

        repository.clear()

        assert repository.count() == 0

    @pytest.mark.asyncio
    async def test_count_returns_correct_number(self, repository):
        """Test count() returns correct number of users."""
        assert repository.count() == 0

        user1 = User.create(Auth0Sub("auth0|111"))
        user2 = User.create(Auth0Sub("auth0|222"))
        await repository.save(user1)
        await repository.save(user2)

        assert repository.count() == 2

    @pytest.mark.asyncio
    async def test_save_preserves_all_user_data(self, repository):
        """Test that save preserves all user entity data."""
        user = User.create(
            Auth0Sub("auth0|123456789"), UserPreferences(data={"theme": "dark", "lang": "it"})
        )
        user.authenticate()

        await repository.save(user)

        found = await repository.find_by_auth0_sub(user.auth0_sub)
        assert found.user_id == user.user_id
        assert found.auth0_sub == user.auth0_sub
        assert found.preferences.data == user.preferences.data
        assert found.created_at == user.created_at
        assert found.updated_at == user.updated_at
        assert found.last_authenticated_at == user.last_authenticated_at
        assert found.is_active == user.is_active

    @pytest.mark.asyncio
    async def test_multiple_users_with_different_providers(self, repository):
        """Test storing users from different Auth0 providers."""
        user1 = User.create(Auth0Sub("auth0|111"))
        user2 = User.create(Auth0Sub("google-oauth2|222"))
        user3 = User.create(Auth0Sub("facebook|333"))

        await repository.save(user1)
        await repository.save(user2)
        await repository.save(user3)

        assert repository.count() == 3
        assert await repository.exists(user1.auth0_sub)
        assert await repository.exists(user2.auth0_sub)
        assert await repository.exists(user3.auth0_sub)
