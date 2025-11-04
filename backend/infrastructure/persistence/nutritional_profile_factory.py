"""Factory for creating profile repository instances."""

import os
from typing import Optional

from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)
from infrastructure.persistence.in_memory.profile_repository import (
    InMemoryProfileRepository,
)


# Singleton instance
_profile_repository: Optional[IProfileRepository] = None


def create_profile_repository() -> IProfileRepository:
    """
    Create profile repository based on global REPOSITORY_BACKEND configuration.

    Environment Variables:
        REPOSITORY_BACKEND: Global repository type ('inmemory' or 'mongodb')
        MONGODB_URI: MongoDB connection URI (required if type='mongodb')

    Returns:
        IProfileRepository implementation

    Raises:
        ValueError: If REPOSITORY_BACKEND='mongodb' but MONGODB_URI not set
        NotImplementedError: If REPOSITORY_BACKEND='mongodb'
            (Phase 7.1 pending)

    Default:
        Returns InMemoryProfileRepository if REPOSITORY_BACKEND not set
    """
    repo_type = os.getenv("REPOSITORY_BACKEND", "inmemory").lower()

    if repo_type == "inmemory":
        return InMemoryProfileRepository()

    elif repo_type == "mongodb":
        # Validate MongoDB URI is provided
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            raise ValueError("REPOSITORY_BACKEND='mongodb' requires MONGODB_URI env var")

        # MongoDB implementation pending (Phase 7.1)
        raise NotImplementedError(
            "MongoProfileRepository not yet implemented. "
            "Use REPOSITORY_BACKEND='inmemory' for now. "
            "MongoDB support will be added in Phase 7.1 (cross-domain)."
        )

    else:
        # Unknown type - graceful fallback to inmemory
        return InMemoryProfileRepository()


def get_profile_repository() -> IProfileRepository:
    """
    Get singleton profile repository instance.

    Lazy initialization on first call.

    Returns:
        IProfileRepository singleton
    """
    global _profile_repository
    if _profile_repository is None:
        _profile_repository = create_profile_repository()
    return _profile_repository


def reset_profile_repository() -> None:
    """
    Reset singleton instance.

    Useful for testing to ensure clean state.
    """
    global _profile_repository
    _profile_repository = None
