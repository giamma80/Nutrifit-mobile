"""Get meal history query - list meals with filters."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import logging

from domain.meal.core.entities.meal import Meal
from domain.shared.ports.meal_repository import IMealRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GetMealHistoryQuery:
    """
    Query: Get meal history for user with optional filters.

    Returns paginated list of meals ordered by timestamp desc (newest first).

    Attributes:
        user_id: User ID to filter meals
        start_date: Optional start date filter (inclusive)
        end_date: Optional end date filter (inclusive)
        meal_type: Optional meal type filter (BREAKFAST, LUNCH, DINNER, SNACK)
        limit: Max number of results (default: 100)
        offset: Pagination offset (default: 0)
    """
    user_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    meal_type: Optional[str] = None
    limit: int = 100
    offset: int = 0


class GetMealHistoryQueryHandler:
    """Handler for GetMealHistoryQuery."""

    def __init__(self, repository: IMealRepository):
        """
        Initialize handler.

        Args:
            repository: Meal repository port
        """
        self._repository = repository

    async def handle(self, query: GetMealHistoryQuery) -> List[Meal]:
        """
        Execute query and return filtered meal list.

        Args:
            query: GetMealHistoryQuery

        Returns:
            List of meals matching filters, ordered by timestamp desc

        Example:
            >>> handler = GetMealHistoryQueryHandler(repository)
            >>> query = GetMealHistoryQuery(
            ...     user_id="user123",
            ...     meal_type="LUNCH",
            ...     limit=10
            ... )
            >>> meals = await handler.handle(query)
            >>> all(m.meal_type == "LUNCH" for m in meals)
            True
        """
        # Get meals with date range filter
        if query.start_date and query.end_date:
            meals = await self._repository.get_by_user_and_date_range(
                user_id=query.user_id,
                start_date=query.start_date,
                end_date=query.end_date
            )
            # Apply pagination manually since get_by_user_and_date_range doesn't support it
            meals = meals[query.offset:query.offset + query.limit]
        else:
            meals = await self._repository.get_by_user(
                user_id=query.user_id,
                limit=query.limit,
                offset=query.offset
            )

        # Apply meal_type filter if specified
        if query.meal_type:
            meals = [m for m in meals if m.meal_type == query.meal_type]

        logger.info(
            "Meal history retrieved",
            extra={
                "user_id": query.user_id,
                "result_count": len(meals),
                "filters": {
                    "start_date": query.start_date.isoformat() if query.start_date else None,
                    "end_date": query.end_date.isoformat() if query.end_date else None,
                    "meal_type": query.meal_type,
                },
                "limit": query.limit,
                "offset": query.offset,
            },
        )

        return meals
