"""Repository Factory for Persistence Layer.

Environment-based repository selection with graceful fallback to in-memory.
Strategy:
- .env (runtime): MEAL_REPOSITORY=mongodb (production persistence)
- .env.test (pytest): MEAL_REPOSITORY=inmemory (fast, isolated tests)
- Default: inmemory (safe fallback if env vars not set)

Usage:
    from infrastructure.persistence.factory import (
        create_meal_repository,
        get_meal_repository,
    )

    repo = create_meal_repository()  # Returns inmemory or mongodb based on env
    repo = get_meal_repository()     # Singleton instance
"""

import os
from typing import Optional

# Protocol interface (Dependency Inversion)
from domain.shared.ports.meal_repository import IMealRepository

# In-memory repository (fast, transient)
from infrastructure.persistence.in_memory.meal_repository import InMemoryMealRepository

# MongoDB repository (persistent, requires connection)
# Will be implemented in P7.1
# from infrastructure.persistence.mongodb.meal_repository import MongoMealRepository


def create_meal_repository() -> IMealRepository:
    """Create meal repository based on MEAL_REPOSITORY env var.

    Environment variable: MEAL_REPOSITORY
    Values:
        - "inmemory": In-memory repository (default, fast, transient)
        - "mongodb": MongoDB repository (persistent, requires MONGODB_URI)

    Returns:
        IMealRepository: Repository instance

    Raises:
        NotImplementedError: If mongodb selected but not yet implemented
        ValueError: If mongodb selected but MONGODB_URI not set

    Example:
        # In .env (production):
        MEAL_REPOSITORY=mongodb
        MONGODB_URI=mongodb://localhost:27017

        # In .env.test (testing):
        MEAL_REPOSITORY=inmemory
    """
    mode = os.getenv("MEAL_REPOSITORY", "inmemory").lower()

    if mode == "mongodb":
        # Check if MongoDB URI is set
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError(
                "MEAL_REPOSITORY=mongodb but MONGODB_URI not set. "
                "Set MONGODB_URI in .env or use MEAL_REPOSITORY=inmemory"
            )

        # MongoDB repository not yet implemented (P7.1)
        raise NotImplementedError(
            "MongoDB repository not yet implemented. "
            "Use MEAL_REPOSITORY=inmemory or implement P7.1 first."
        )

        # Future implementation (P7.1):
        # return MongoMealRepository(uri=mongodb_uri)

    # Default: inmemory (safe fallback)
    return InMemoryMealRepository()


# Singleton instance (lazy initialization)
_meal_repository: Optional[IMealRepository] = None


def get_meal_repository() -> IMealRepository:
    """Get singleton meal repository instance.

    Returns:
        IMealRepository: Cached repository instance

    Example:
        repo = get_meal_repository()
        meals = await repo.get_by_user(user_id="user123")
    """
    global _meal_repository
    if _meal_repository is None:
        _meal_repository = create_meal_repository()
    return _meal_repository


def reset_repository() -> None:
    """Reset singleton repository instance.

    Useful for testing to force re-creation with different env vars.

    Example:
        # In tests:
        reset_repository()
        os.environ["MEAL_REPOSITORY"] = "inmemory"
        repo = get_meal_repository()  # Creates new instance
    """
    global _meal_repository
    _meal_repository = None
