"""Search meals query - full-text search."""

from dataclasses import dataclass
from typing import List
import logging

from domain.meal.core.entities.meal import Meal
from domain.shared.ports.meal_repository import IMealRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchMealsQuery:
    """
    Query: Search meals by text query.

    Searches in meal entry names, display names, and notes.
    Returns paginated results ordered by timestamp desc.

    Attributes:
        user_id: User ID to filter meals
        query_text: Text to search for
        limit: Max number of results (default: 50)
        offset: Pagination offset (default: 0)
    """

    user_id: str
    query_text: str
    limit: int = 50
    offset: int = 0


class SearchMealsQueryHandler:
    """Handler for SearchMealsQuery."""

    def __init__(self, repository: IMealRepository):
        """
        Initialize handler.

        Args:
            repository: Meal repository port
        """
        self._repository = repository

    async def handle(self, query: SearchMealsQuery) -> List[Meal]:
        """
        Execute search query and return matching meals.

        Search logic:
        - Searches in meal entry names and display names
        - Searches in meal notes
        - Case-insensitive matching
        - Returns meals ordered by timestamp desc

        Args:
            query: SearchMealsQuery

        Returns:
            List of meals matching search query

        Example:
            >>> handler = SearchMealsQueryHandler(repository)
            >>> query = SearchMealsQuery(
            ...     user_id="user123",
            ...     query_text="pasta",
            ...     limit=10
            ... )
            >>> meals = await handler.handle(query)
            >>> any("pasta" in m.entries[0].display_name.lower() for m in meals)
            True
        """
        # Get all user meals (in production, this would use a search index)
        all_meals = await self._repository.get_by_user(
            user_id=query.user_id, limit=1000, offset=0  # High limit to search across all meals
        )

        # Filter by search query (case-insensitive)
        search_term = query.query_text.lower().strip()
        matching_meals = []

        for meal in all_meals:
            # Search in entry names/display names
            entry_match = any(
                search_term in entry.name.lower() or search_term in entry.display_name.lower()
                for entry in meal.entries
            )

            # Search in meal notes
            notes_match = meal.notes and search_term in meal.notes.lower()

            if entry_match or notes_match:
                matching_meals.append(meal)

        # Apply pagination
        paginated_meals = matching_meals[query.offset : query.offset + query.limit]

        logger.info(
            "Meal search executed",
            extra={
                "user_id": query.user_id,
                "query_text": query.query_text,
                "total_matches": len(matching_meals),
                "returned_count": len(paginated_meals),
                "limit": query.limit,
                "offset": query.offset,
            },
        )

        return paginated_meals
