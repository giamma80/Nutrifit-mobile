"""Get meal query - retrieve single meal by ID."""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
import logging

from domain.meal.core.entities.meal import Meal
from domain.shared.ports.meal_repository import IMealRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GetMealQuery:
    """
    Query: Get single meal by ID.

    Read-only operation with authorization.

    Attributes:
        meal_id: Meal ID to retrieve
        user_id: User ID for authorization
    """

    meal_id: UUID
    user_id: str


class GetMealQueryHandler:
    """Handler for GetMealQuery."""

    def __init__(self, repository: IMealRepository):
        """
        Initialize handler.

        Args:
            repository: Meal repository port
        """
        self._repository = repository

    async def handle(self, query: GetMealQuery) -> Optional[Meal]:
        """
        Execute query and return meal if authorized.

        Args:
            query: GetMealQuery

        Returns:
            Meal if found and owned by user, None otherwise

        Example:
            >>> handler = GetMealQueryHandler(repository)
            >>> query = GetMealQuery(meal_id=meal_id, user_id="user123")
            >>> meal = await handler.handle(query)
            >>> meal.user_id == "user123"
            True
        """
        meal = await self._repository.get_by_id(query.meal_id, query.user_id)

        if meal:
            logger.debug(
                "Meal retrieved",
                extra={
                    "meal_id": str(query.meal_id),
                    "user_id": query.user_id,
                    "entry_count": len(meal.entries),
                },
            )
        else:
            logger.debug(
                "Meal not found or access denied",
                extra={
                    "meal_id": str(query.meal_id),
                    "user_id": query.user_id,
                },
            )

        return meal
