"""GetProfileQuery - retrieve nutritional profile."""

from dataclasses import dataclass
from typing import Optional

from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId


@dataclass(frozen=True)
class GetProfileByIdQuery:
    """Query to retrieve profile by ID.

    Attributes:
        profile_id: Profile identifier
    """

    profile_id: ProfileId


@dataclass(frozen=True)
class GetProfileByUserIdQuery:
    """Query to retrieve profile by user ID.

    Attributes:
        user_id: User identifier
    """

    user_id: str


class GetProfileQueryHandler:
    """Handler for GetProfile queries.

    Provides read-only access to profiles via repository.
    """

    def __init__(self, repository: IProfileRepository):
        self._repository = repository

    async def handle_by_id(self, query: GetProfileByIdQuery) -> Optional[NutritionalProfile]:
        """
        Handle get profile by ID query.

        Args:
            query: GetProfileByIdQuery with profile ID

        Returns:
            Optional[NutritionalProfile]: Profile if found, None otherwise
        """
        return await self._repository.find_by_id(query.profile_id)

    async def handle_by_user_id(
        self, query: GetProfileByUserIdQuery
    ) -> Optional[NutritionalProfile]:
        """
        Handle get profile by user ID query.

        Args:
            query: GetProfileByUserIdQuery with user ID

        Returns:
            Optional[NutritionalProfile]: Profile if found, None otherwise
        """
        return await self._repository.find_by_user_id(query.user_id)
