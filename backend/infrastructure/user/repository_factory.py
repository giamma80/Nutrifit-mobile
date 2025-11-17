"""User repository factory for environment-based selection.

This factory creates the appropriate repository implementation based on
the USER_REPOSITORY environment variable:
- "inmemory": InMemoryUserRepository (for testing)
- "mongodb": MongoUserRepository (for production)

Default: inmemory
"""

import os
from domain.user.ports.repository import IUserRepository
from infrastructure.user.in_memory_user_repository import (
    InMemoryUserRepository,
)
from infrastructure.user.mongo_user_repository import MongoUserRepository
from motor.motor_asyncio import AsyncIOMotorClient


def create_user_repository() -> IUserRepository:
    """Create user repository based on environment configuration.

    Returns:
        IUserRepository: The configured repository implementation

    Environment Variables:
        USER_REPOSITORY: "inmemory" | "mongodb" (default: inmemory)
        MONGODB_URL: MongoDB connection string (required for mongodb)
        MONGODB_DATABASE: Database name (default: nutrifit)
    """
    repo_type = os.getenv("USER_REPOSITORY", "inmemory").lower()

    if repo_type == "mongodb":
        # MongoDB repository for production
        mongo_url = os.getenv("MONGODB_URL")
        if not mongo_url:
            raise ValueError(
                "MONGODB_URL environment variable is required "
                "when USER_REPOSITORY=mongodb"
            )

        db_name = os.getenv("MONGODB_DATABASE", "nutrifit")
        client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_url)  # type: ignore
        db = client[db_name]

        return MongoUserRepository(db.users)

    elif repo_type == "inmemory":
        # In-memory repository for testing
        return InMemoryUserRepository()

    else:
        raise ValueError(
            f"Invalid USER_REPOSITORY value: {repo_type}. "
            "Expected 'inmemory' or 'mongodb'"
        )


# Singleton instance
_user_repository: IUserRepository | None = None


def get_user_repository() -> IUserRepository:
    """Get singleton user repository instance.

    Returns:
        IUserRepository: The singleton repository
    """
    global _user_repository

    if _user_repository is None:
        _user_repository = create_user_repository()

    return _user_repository


def reset_user_repository() -> None:
    """Reset the singleton (for testing purposes)."""
    global _user_repository
    _user_repository = None
