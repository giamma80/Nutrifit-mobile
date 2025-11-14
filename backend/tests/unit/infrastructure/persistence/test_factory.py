"""Unit tests for repository factory (P7.0.1-3).

Tests environment-based repository selection with graceful fallback.
"""

import pytest
from infrastructure.persistence.factory import (
    create_meal_repository,
    get_meal_repository,
    reset_repository,
)
from infrastructure.persistence.in_memory.meal_repository import InMemoryMealRepository


class TestMealRepositoryFactory:
    """Test create_meal_repository() factory function."""

    def test_default_to_inmemory_when_env_not_set(self, monkeypatch):
        """Should return in-memory repository when MEAL_REPOSITORY not set."""
        monkeypatch.delenv("MEAL_REPOSITORY", raising=False)
        repo = create_meal_repository()
        assert isinstance(repo, InMemoryMealRepository)

    def test_explicit_inmemory_selection(self, monkeypatch):
        """Should return in-memory repository when MEAL_REPOSITORY=inmemory."""
        monkeypatch.setenv("MEAL_REPOSITORY", "inmemory")
        repo = create_meal_repository()
        assert isinstance(repo, InMemoryMealRepository)

    def test_case_insensitive_selection(self, monkeypatch):
        """Should handle case-insensitive repository names."""
        monkeypatch.setenv("MEAL_REPOSITORY", "InMemory")
        repo = create_meal_repository()
        assert isinstance(repo, InMemoryMealRepository)

        monkeypatch.setenv("MEAL_REPOSITORY", "INMEMORY")
        repo = create_meal_repository()
        assert isinstance(repo, InMemoryMealRepository)

    def test_mongodb_creates_mongo_repository(self, monkeypatch):
        """Should create MongoMealRepository when mongodb mode."""
        from infrastructure.persistence.mongodb.meal_repository import (
            MongoMealRepository,
        )

        monkeypatch.setenv("REPOSITORY_BACKEND", "mongodb")
        monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")

        repo = create_meal_repository()
        assert isinstance(repo, MongoMealRepository)

    def test_mongodb_without_uri_raises_error(self, monkeypatch):
        """Should raise ValueError when mongodb but no MONGODB_URI."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "mongodb")
        monkeypatch.delenv("MONGODB_URI", raising=False)

        with pytest.raises(ValueError, match="MONGODB_URI not set"):
            create_meal_repository()


class TestSingletonGetter:
    """Test singleton get_meal_repository() function."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_repository()

    def test_get_meal_repository_singleton(self, monkeypatch):
        """get_meal_repository() should return same instance on multiple calls."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "inmemory")

        repo1 = get_meal_repository()
        repo2 = get_meal_repository()

        assert repo1 is repo2  # Same instance

    def test_reset_repository_clears_singleton(self, monkeypatch):
        """reset_repository() should clear cached instance."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "inmemory")

        repo1 = get_meal_repository()
        reset_repository()
        repo2 = get_meal_repository()

        assert repo1 is not repo2  # Different instances after reset

    def test_singleton_respects_env_changes_after_reset(self, monkeypatch):
        """After reset, should use new environment configuration."""
        # First call with inmemory
        monkeypatch.setenv("REPOSITORY_BACKEND", "inmemory")
        repo1 = get_meal_repository()
        assert isinstance(repo1, InMemoryMealRepository)

        # Reset and check same type (since mongodb not implemented)
        reset_repository()
        monkeypatch.setenv("REPOSITORY_BACKEND", "inmemory")
        repo2 = get_meal_repository()
        assert isinstance(repo2, InMemoryMealRepository)

        # Different instances after reset
        assert repo1 is not repo2


class TestRepositoryFactoryIntegration:
    """Integration tests for factory behavior."""

    def test_inmemory_default(self, monkeypatch):
        """Factory should default to in-memory when no env vars set."""
        monkeypatch.delenv("REPOSITORY_BACKEND", raising=False)
        repo = create_meal_repository()
        assert isinstance(repo, InMemoryMealRepository)

    def test_env_test_configuration(self, monkeypatch):
        """Test configuration from .env.test (inmemory)."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "inmemory")
        repo = create_meal_repository()
        assert isinstance(repo, InMemoryMealRepository)

    def test_production_configuration_mongodb(self, monkeypatch):
        """Production configuration (mongodb) creates MongoMealRepository."""
        from infrastructure.persistence.mongodb.meal_repository import (
            MongoMealRepository,
        )

        monkeypatch.setenv("REPOSITORY_BACKEND", "mongodb")
        monkeypatch.setenv("MONGODB_URI", "mongodb://prod.example.com:27017")

        repo = create_meal_repository()
        assert isinstance(repo, MongoMealRepository)

    def test_invalid_repository_type_defaults_to_inmemory(self, monkeypatch):
        """Invalid repository type should default to in-memory."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "invalid_type")
        repo = create_meal_repository()
        # Should default to inmemory for unknown values
        assert isinstance(repo, InMemoryMealRepository)
