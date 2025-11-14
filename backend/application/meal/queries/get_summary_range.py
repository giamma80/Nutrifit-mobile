"""Query handler for getting meal summary over date ranges.

Supports grouping by day, week, or month for efficient dashboard queries.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.types import GroupByPeriod


__all__ = [
    "GroupByPeriod",
    "GetSummaryRangeQuery",
    "PeriodSummaryData",
    "GetSummaryRangeQueryHandler",
]


@dataclass(frozen=True)
class GetSummaryRangeQuery:
    """Query to get meal summaries for a date range.

    Attributes:
        user_id: User ID to filter meals
        start_date: Range start (inclusive)
        end_date: Range end (inclusive)
        group_by: Group results by DAY, WEEK, or MONTH
    """

    user_id: str
    start_date: datetime
    end_date: datetime
    group_by: GroupByPeriod = GroupByPeriod.DAY


@dataclass
class PeriodSummaryData:
    """Summary data for a single period."""

    period: str  # ISO format: "2025-10-28" (day), "2025-W43" (week), etc
    start_date: datetime
    end_date: datetime
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    total_sugar: float
    total_sodium: float
    meal_count: int
    breakdown_by_type: dict[str, float]  # {"BREAKFAST": 450, "LUNCH": 650}


class GetSummaryRangeQueryHandler:
    """Handler for GetSummaryRangeQuery."""

    def __init__(self, repository: IMealRepository):
        """Initialize handler with repository.

        Args:
            repository: Meal repository for data access
        """
        self.repository = repository

    async def handle(self, query: GetSummaryRangeQuery) -> List[PeriodSummaryData]:
        """Execute summary range query.

        Args:
            query: Query parameters

        Returns:
            List of PeriodSummaryData, one per period in range

        Algorithm:
            1. Split date range into periods based on group_by
            2. For each period, calculate summary using existing logic
            3. Return aggregated results
        """
        # Split range into periods
        periods = self._split_range_into_periods(
            start_date=query.start_date,
            end_date=query.end_date,
            group_by=query.group_by,
        )

        # Calculate summary for each period
        summaries: List[PeriodSummaryData] = []
        for period_start, period_end in periods:
            summary = await self._calculate_period_summary(
                user_id=query.user_id,
                start_date=period_start,
                end_date=period_end,
                group_by=query.group_by,
            )
            summaries.append(summary)

        return summaries

    def _split_range_into_periods(
        self, start_date: datetime, end_date: datetime, group_by: GroupByPeriod
    ) -> List[tuple[datetime, datetime]]:
        """Split date range into periods.

        Args:
            start_date: Range start
            end_date: Range end
            group_by: Grouping period

        Returns:
            List of (period_start, period_end) tuples
        """
        periods: List[tuple[datetime, datetime]] = []

        if group_by == GroupByPeriod.DAY:
            # Split by days (preserve timezone)
            tzinfo = start_date.tzinfo
            current = start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tzinfo)
            while current <= end_date:
                day_end = current.replace(hour=23, minute=59, second=59, tzinfo=tzinfo)
                periods.append((current, day_end))
                current += timedelta(days=1)

        elif group_by == GroupByPeriod.WEEK:
            # Split by weeks (Monday to Sunday, preserve timezone)
            tzinfo = start_date.tzinfo
            current = start_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tzinfo)
            # Move to Monday of current week
            days_to_monday = current.weekday()
            week_start = current - timedelta(days=days_to_monday)

            while week_start <= end_date:
                week_end = (week_start + timedelta(days=6)).replace(
                    hour=23, minute=59, second=59, tzinfo=tzinfo
                )
                # Only include if overlaps with query range
                if week_end >= start_date:
                    periods.append((max(week_start, start_date), min(week_end, end_date)))
                week_start += timedelta(days=7)

        elif group_by == GroupByPeriod.MONTH:
            # Split by months (preserve timezone)
            tzinfo = start_date.tzinfo
            current = start_date.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=tzinfo
            )

            while current <= end_date:
                # Calculate last day of month
                if current.month == 12:
                    next_month = current.replace(year=current.year + 1, month=1, tzinfo=tzinfo)
                else:
                    next_month = current.replace(month=current.month + 1, tzinfo=tzinfo)
                month_end = (next_month - timedelta(days=1)).replace(
                    hour=23, minute=59, second=59, tzinfo=tzinfo
                )

                # Only include if overlaps with query range
                if month_end >= start_date:
                    periods.append((max(current, start_date), min(month_end, end_date)))

                current = next_month

        return periods

    async def _calculate_period_summary(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        group_by: GroupByPeriod,
    ) -> PeriodSummaryData:
        """Calculate summary for a single period.

        Args:
            user_id: User ID
            start_date: Period start
            end_date: Period end
            group_by: Grouping period (for label formatting)

        Returns:
            PeriodSummaryData with aggregated values
        """
        # Get all meals in period
        meals = await self.repository.get_by_user_and_date_range(
            user_id=user_id, start_date=start_date, end_date=end_date
        )

        # Aggregate nutrition values
        total_calories = sum(meal.total_calories for meal in meals)
        total_protein = sum(meal.total_protein for meal in meals)
        total_carbs = sum(meal.total_carbs for meal in meals)
        total_fat = sum(meal.total_fat for meal in meals)
        total_fiber = sum(meal.total_fiber for meal in meals)
        total_sugar = sum(meal.total_sugar for meal in meals)
        total_sodium = sum(meal.total_sodium for meal in meals)
        meal_count = len(meals)

        # Calculate breakdown by meal type
        breakdown: dict[str, float] = {}
        for meal in meals:
            meal_type = meal.meal_type
            if meal_type not in breakdown:
                breakdown[meal_type] = 0.0
            breakdown[meal_type] += float(meal.total_calories)

        # Format period label
        period_label = self._format_period_label(start_date, group_by)

        return PeriodSummaryData(
            period=period_label,
            start_date=start_date,
            end_date=end_date,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
            total_fiber=total_fiber,
            total_sugar=total_sugar,
            total_sodium=total_sodium,
            meal_count=meal_count,
            breakdown_by_type=breakdown,
        )

    def _format_period_label(self, date: datetime, group_by: GroupByPeriod) -> str:
        """Format period label based on grouping.

        Args:
            date: Date in period
            group_by: Grouping period

        Returns:
            ISO format label: "2025-10-28" (day), "2025-W43" (week),
            "2025-10" (month)
        """
        if group_by == GroupByPeriod.DAY:
            return date.strftime("%Y-%m-%d")
        elif group_by == GroupByPeriod.WEEK:
            # ISO week format: YYYY-Www
            iso_year, iso_week, _ = date.isocalendar()
            return f"{iso_year}-W{iso_week:02d}"
        elif group_by == GroupByPeriod.MONTH:
            return date.strftime("%Y-%m")
        else:
            return date.strftime("%Y-%m-%d")
