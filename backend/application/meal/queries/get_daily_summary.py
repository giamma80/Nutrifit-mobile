"""Get daily summary query - aggregate daily nutrition totals."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional
import logging

from domain.shared.ports.meal_repository import IMealRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailySummary:
    """
    Daily nutrition summary.

    Aggregates all meals for a given date.

    Attributes:
        date: Date of summary
        total_calories: Total calories for the day
        total_protein: Total protein (g)
        total_carbs: Total carbohydrates (g)
        total_fat: Total fat (g)
        total_fiber: Total fiber (g)
        meal_count: Number of meals logged
        breakdown_by_type: Calories by meal type
    """

    date: datetime
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    meal_count: int
    breakdown_by_type: Dict[str, float]  # meal_type -> calories


@dataclass(frozen=True)
class GetDailySummaryQuery:
    """
    Query: Get daily nutrition summary.

    Aggregates all meals for a specific date.

    Attributes:
        user_id: User ID to filter meals
        date: Date to summarize (if None, defaults to today in handler)
    """

    user_id: str
    date: Optional[datetime] = None


class GetDailySummaryQueryHandler:
    """Handler for GetDailySummaryQuery."""

    def __init__(self, repository: IMealRepository):
        """
        Initialize handler.

        Args:
            repository: Meal repository port
        """
        self._repository = repository

    async def handle(self, query: GetDailySummaryQuery) -> DailySummary:
        """
        Execute query and aggregate daily totals.

        Args:
            query: GetDailySummaryQuery

        Returns:
            DailySummary with aggregated nutrition data

        Example:
            >>> handler = GetDailySummaryQueryHandler(repository)
            >>> query = GetDailySummaryQuery(user_id="user123")
            >>> summary = await handler.handle(query)
            >>> summary.total_calories >= 0
            True
        """
        # Get start/end of day (00:00:00 to 23:59:59)
        # Use today if date not provided
        query_date = query.date if query.date else datetime.now(timezone.utc)
        date = query_date.replace(hour=0, minute=0, second=0, microsecond=0)
        start = date
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Fetch all meals for the day
        meals = await self._repository.get_by_user_and_date_range(
            user_id=query.user_id, start_date=start, end_date=end
        )

        # Aggregate totals
        total_calories = sum(m.total_calories for m in meals)
        total_protein = sum(m.total_protein for m in meals)
        total_carbs = sum(m.total_carbs for m in meals)
        total_fat = sum(m.total_fat for m in meals)
        total_fiber = sum(m.total_fiber for m in meals)

        # Breakdown by meal type
        breakdown: Dict[str, float] = {
            "BREAKFAST": 0.0,
            "LUNCH": 0.0,
            "DINNER": 0.0,
            "SNACK": 0.0,
        }

        for meal in meals:
            if meal.meal_type in breakdown:
                breakdown[meal.meal_type] += meal.total_calories

        summary = DailySummary(
            date=date,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
            total_fiber=total_fiber,
            meal_count=len(meals),
            breakdown_by_type=breakdown,
        )

        logger.info(
            "Daily summary calculated",
            extra={
                "user_id": query.user_id,
                "date": date.date().isoformat(),
                "total_calories": total_calories,
                "meal_count": len(meals),
            },
        )

        return summary
