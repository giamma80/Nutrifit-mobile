"""In-memory implementation of IProfileRepository for testing."""

from copy import deepcopy
from typing import Optional

from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId


class InMemoryProfileRepository(IProfileRepository):
    """
    In-memory implementation of profile repository.

    Uses a dictionary to store profiles in memory. Suitable for testing
    and development. Data is lost when the application stops.
    """

    def __init__(self) -> None:
        """Initialize empty repository."""
        self._profiles: dict[str, NutritionalProfile] = {}

    async def save(self, profile: NutritionalProfile) -> None:
        """
        Save or update profile in memory.

        Args:
            profile: Nutritional profile to save
        """
        # Deep copy to prevent external mutations
        self._profiles[str(profile.profile_id)] = deepcopy(profile)

    async def find_by_id(self, profile_id: ProfileId) -> Optional[NutritionalProfile]:
        """
        Find profile by ID.

        Args:
            profile_id: Profile ID to search for

        Returns:
            Deep copy of profile if found, None otherwise
        """
        profile = self._profiles.get(str(profile_id))
        return deepcopy(profile) if profile else None

    async def find_by_user_id(self, user_id: str) -> Optional[NutritionalProfile]:
        """
        Find profile by user ID.

        Args:
            user_id: User ID to search for

        Returns:
            Deep copy of profile if found, None otherwise
        """
        for profile in self._profiles.values():
            if profile.user_id == user_id:
                return deepcopy(profile)
        return None

    async def delete(self, profile_id: ProfileId) -> None:
        """
        Delete profile by ID (soft delete).

        Args:
            profile_id: Profile ID to delete
        """
        profile_id_str = str(profile_id)
        if profile_id_str in self._profiles:
            del self._profiles[profile_id_str]

    async def exists(self, user_id: str) -> bool:
        """
        Check if profile exists for user.

        Args:
            user_id: User identifier

        Returns:
            True if profile exists, False otherwise
        """
        for profile in self._profiles.values():
            if profile.user_id == user_id:
                return True
        return False

    def clear(self) -> None:
        """
        Clear all profiles from memory.

        Useful for test cleanup.
        """
        self._profiles.clear()

    def count(self) -> int:
        """
        Get total number of profiles in memory.

        Returns:
            Number of profiles
        """
        return len(self._profiles)
