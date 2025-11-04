"""IProfileRepository port - repository interface."""

from abc import ABC, abstractmethod
from typing import Optional

from ..entities.nutritional_profile import NutritionalProfile
from ..value_objects.profile_id import ProfileId


class IProfileRepository(ABC):
    """Port for nutritional profile persistence.

    Defines interface that infrastructure adapters must implement.
    Domain layer depends on this abstraction, not on concrete
    implementations (Dependency Inversion Principle).
    """

    @abstractmethod
    async def save(self, profile: NutritionalProfile) -> None:
        """Save profile (create or update).

        Args:
            profile: Profile to save
        """
        pass

    @abstractmethod
    async def find_by_id(self, profile_id: ProfileId) -> Optional[NutritionalProfile]:
        """Find profile by ID.

        Args:
            profile_id: Profile identifier

        Returns:
            Optional[NutritionalProfile]: Profile if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: str) -> Optional[NutritionalProfile]:
        """Find profile by user ID.

        Args:
            user_id: User identifier

        Returns:
            Optional[NutritionalProfile]: Profile if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, profile_id: ProfileId) -> None:
        """Delete profile (soft delete).

        Args:
            profile_id: Profile identifier
        """
        pass

    @abstractmethod
    async def exists(self, user_id: str) -> bool:
        """Check if profile exists for user.

        Args:
            user_id: User identifier

        Returns:
            bool: True if profile exists
        """
        pass
