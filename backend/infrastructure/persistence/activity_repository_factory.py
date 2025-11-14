"""Factory for creating activity repositories.

Centralized factory following the same pattern as meal and profile domains.
Uses REPOSITORY_BACKEND environment variable for consistency.
"""

import os

from domain.activity.repository import IActivityRepository


# Singleton per riutilizzo repository
_repository_instance: IActivityRepository | None = None


def create_activity_repository() -> IActivityRepository:
    """Create activity repository based on REPOSITORY_BACKEND env var.

    Uses global REPOSITORY_BACKEND variable for consistency across domains:
    - inmemory: InMemoryActivityRepository (wraps legacy repos)
    - mongodb: MongoActivityRepository (future implementation)

    Returns:
        IActivityRepository: Repository instance (singleton pattern)

    Raises:
        ValueError: If REPOSITORY_BACKEND has unsupported value

    Environment Variables:
        REPOSITORY_BACKEND: Repository type (inmemory | mongodb)
            Default: inmemory

    Examples:
        >>> # .env
        >>> REPOSITORY_BACKEND=inmemory
        >>>
        >>> repo = create_activity_repository()
        >>> events = repo.list_events(user_id="user_123")
    """
    global _repository_instance

    if _repository_instance is not None:
        return _repository_instance

    mode = os.getenv("REPOSITORY_BACKEND", "inmemory").lower()

    if mode == "inmemory":
        from infrastructure.persistence.inmemory.activity_repository import (
            InMemoryActivityRepository,
        )

        _repository_instance = InMemoryActivityRepository()
        return _repository_instance

    if mode == "mongodb":
        from infrastructure.persistence.mongodb import MongoActivityRepository

        _repository_instance = MongoActivityRepository()
        return _repository_instance

    raise ValueError(
        f"Unknown REPOSITORY_BACKEND value: '{mode}'. " f"Supported values: inmemory, mongodb"
    )


def reset_activity_repository() -> None:
    """Reset singleton for testing purposes.

    Useful in test suites to ensure clean state between tests.
    """
    global _repository_instance
    _repository_instance = None


__all__ = [
    "create_activity_repository",
    "reset_activity_repository",
]
