"""Unit tests for nutritional_profile_factory.

Tests focus on:
- Repository creation with different env vars
- Singleton behavior
- Reset functionality for testing
- MongoDB validation
"""

import os
import pytest

from infrastructure.persistence.nutritional_profile_factory import (
    create_profile_repository,
    get_profile_repository,
    reset_profile_repository,
)
from infrastructure.persistence.in_memory.profile_repository import (
    InMemoryProfileRepository,
)
from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)


class TestCreateProfileRepository:
    """Test create_profile_repository factory function."""

    def test_create_inmemory_default(self) -> None:
        """Test default creates InMemoryProfileRepository."""
        # No env var set - should default to inmemory
        if "PROFILE_REPOSITORY" in os.environ:
            del os.environ["PROFILE_REPOSITORY"]

        repository = create_profile_repository()

        assert isinstance(repository, InMemoryProfileRepository)
        assert isinstance(repository, IProfileRepository)

    def test_create_inmemory_explicit(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: E501
        """Test explicit inmemory env var."""
        monkeypatch.setenv("PROFILE_REPOSITORY", "inmemory")

        repository = create_profile_repository()

        assert isinstance(repository, InMemoryProfileRepository)

    def test_create_inmemory_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test env var is case insensitive."""
        monkeypatch.setenv("PROFILE_REPOSITORY", "INMEMORY")

        repository = create_profile_repository()

        assert isinstance(repository, InMemoryProfileRepository)

    def test_create_mongodb_creates_mongo_repository(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test mongodb creates MongoProfileRepository."""
        from infrastructure.persistence.mongodb.profile_repository import (
            MongoProfileRepository,
        )

        monkeypatch.setenv("REPOSITORY_BACKEND", "mongodb")
        monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")

        repository = create_profile_repository()

        assert isinstance(repository, MongoProfileRepository)
        assert isinstance(repository, IProfileRepository)

    def test_create_mongodb_missing_uri_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test mongodb without URI raises ValueError."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "mongodb")
        if "MONGODB_URI" in os.environ:
            monkeypatch.delenv("MONGODB_URI")

        with pytest.raises(ValueError) as exc_info:
            create_profile_repository()

        assert "MONGODB_URI" in str(exc_info.value)

    def test_create_unknown_type_defaults_to_inmemory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test unknown type gracefully defaults to inmemory."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "unknown_type")

        repository = create_profile_repository()

        assert isinstance(repository, InMemoryProfileRepository)


class TestGetProfileRepository:
    """Test get_profile_repository singleton pattern."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        reset_profile_repository()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        reset_profile_repository()

    def test_get_returns_repository(self) -> None:
        """Test get_profile_repository returns repository."""
        repository = get_profile_repository()

        assert repository is not None
        assert isinstance(repository, IProfileRepository)

    def test_get_returns_same_instance(self) -> None:
        """Test singleton pattern - same instance on multiple calls."""
        repo1 = get_profile_repository()
        repo2 = get_profile_repository()

        assert repo1 is repo2

    def test_get_creates_only_once(self) -> None:
        """Test repository is created only once."""
        # First call creates
        repo1 = get_profile_repository()

        # Second call returns same instance
        repo2 = get_profile_repository()

        assert repo1 is repo2
        assert isinstance(repo1, InMemoryProfileRepository)


class TestResetProfileRepository:
    """Test reset_profile_repository for testing."""

    def test_reset_clears_singleton(self) -> None:
        """Test reset clears singleton instance."""
        # Create first instance
        repo1 = get_profile_repository()

        # Reset
        reset_profile_repository()

        # Get new instance
        repo2 = get_profile_repository()

        # Should be different instances
        assert repo1 is not repo2

    def test_reset_allows_env_change(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reset allows switching repository type via env var."""
        # Get default (inmemory)
        repo1 = get_profile_repository()
        assert isinstance(repo1, InMemoryProfileRepository)

        # Reset and change env
        reset_profile_repository()
        monkeypatch.setenv("PROFILE_REPOSITORY", "inmemory")

        # Get new instance (still inmemory but new instance)
        repo2 = get_profile_repository()
        assert isinstance(repo2, InMemoryProfileRepository)
        assert repo1 is not repo2

    def test_reset_on_empty_singleton(self) -> None:
        """Test reset on empty singleton does not raise error."""
        reset_profile_repository()

        # Should not raise error
        reset_profile_repository()
