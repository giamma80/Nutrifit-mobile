"""Get activity aggregate range query handler.

Handles date range queries with flexible grouping (DAY, WEEK, MONTH) for
efficient dashboard queries without expensive loops.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

from repository.activities import activity_repo
from domain.shared.types import GroupByPeriod


__all__ = [
    "GroupByPeriod",
    "GetAggregateRangeQuery",
    "ActivityPeriodData",
    "GetAggregateRangeQueryHandler",
]


@dataclass
class GetAggregateRangeQuery:
    """Query for activity aggregates in date range."""

    user_id: str
    start_date: datetime
    end_date: datetime
    group_by: GroupByPeriod = GroupByPeriod.DAY


@dataclass
class ActivityPeriodData:
    """Activity data for a period."""

    period: str  # "2025-10-28" or "2025-W43" or "2025-10"
    start_date: datetime
    end_date: datetime
    total_steps: int
    total_calories_out: float
    total_active_minutes: int
    avg_heart_rate: float | None
    event_count: int


class GetAggregateRangeQueryHandler:
    """Handler for activity aggregate range queries."""

    def handle(self, query: GetAggregateRangeQuery) -> List[ActivityPeriodData]:
        """Execute query and return aggregated periods.

        Args:
            query: Query with date range and grouping

        Returns:
            List of period summaries with activity data
        """
        periods = self._split_range_into_periods(query.start_date, query.end_date, query.group_by)

        results: List[ActivityPeriodData] = []
        for period_start, period_end in periods:
            period_data = self._calculate_period_aggregate(query.user_id, period_start, period_end)
            period_label = self._format_period_label(period_start, query.group_by)
            # Type assertions for mypy
            total_steps = period_data["total_steps"]
            total_calories = period_data["total_calories_out"]
            total_minutes = period_data["total_active_minutes"]
            event_cnt = period_data["event_count"]
            assert isinstance(total_steps, int)
            assert isinstance(total_calories, (int, float))
            assert isinstance(total_minutes, int)
            assert isinstance(event_cnt, int)

            results.append(
                ActivityPeriodData(
                    period=period_label,
                    start_date=period_start,
                    end_date=period_end,
                    total_steps=total_steps,
                    total_calories_out=float(total_calories),
                    total_active_minutes=total_minutes,
                    avg_heart_rate=period_data["avg_heart_rate"],
                    event_count=event_cnt,
                )
            )

        return results

    def _split_range_into_periods(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: GroupByPeriod,
    ) -> List[tuple[datetime, datetime]]:
        """Split date range into periods based on grouping.

        Args:
            start_date: Range start
            end_date: Range end
            group_by: Grouping period (DAY, WEEK, MONTH)

        Returns:
            List of (period_start, period_end) tuples
        """
        periods: List[tuple[datetime, datetime]] = []

        if group_by == GroupByPeriod.DAY:
            # Split by day
            current = start_date
            while current <= end_date:
                day_start = current.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = current.replace(hour=23, minute=59, second=59, microsecond=999999)
                # Clip to range boundaries
                actual_start = max(day_start, start_date)
                actual_end = min(day_end, end_date)
                periods.append((actual_start, actual_end))
                current += timedelta(days=1)

        elif group_by == GroupByPeriod.WEEK:
            # Split by ISO week (Monday-Sunday)
            current = start_date
            while current <= end_date:
                # Get Monday of current week
                week_start = current - timedelta(days=current.weekday())
                week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                # Sunday is 6 days after Monday
                week_end = week_start + timedelta(days=6)
                week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)
                # Clip to range boundaries
                actual_start = max(week_start, start_date)
                actual_end = min(week_end, end_date)
                periods.append((actual_start, actual_end))
                # Move to next Monday
                current = week_end + timedelta(days=1)

        elif group_by == GroupByPeriod.MONTH:
            # Split by calendar month
            current = start_date
            while current <= end_date:
                # First day of month
                month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                # Last day of month
                if current.month == 12:
                    next_month = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    next_month = current.replace(month=current.month + 1, day=1)
                month_end = (next_month - timedelta(days=1)).replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
                # Clip to range boundaries
                actual_start = max(month_start, start_date)
                actual_end = min(month_end, end_date)
                periods.append((actual_start, actual_end))
                # Move to next month
                current = next_month

        return periods

    def _calculate_period_aggregate(
        self, user_id: str, start_date: datetime, end_date: datetime
    ) -> dict[str, int | float | None]:
        """Calculate activity aggregates for a period.

        Args:
            user_id: User ID
            start_date: Period start
            end_date: Period end

        Returns:
            Dict with activity totals
        """
        # Aggregate activity events
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()

        events = activity_repo.list_events(
            user_id=user_id,
            start_ts=start_iso,
            end_ts=end_iso,
            limit=10000,  # Large limit for aggregation
        )

        total_steps = 0
        total_calories = 0.0
        total_hr_sum = 0.0
        hr_count = 0
        active_minutes = 0

        for event in events:
            if event.steps is not None:
                total_steps += event.steps
            if event.calories_out is not None:
                total_calories += event.calories_out
            if event.hr_avg is not None:
                total_hr_sum += event.hr_avg
                hr_count += 1
            # Each event represents 1 minute
            if event.steps and event.steps > 0:
                active_minutes += 1

        avg_hr = total_hr_sum / hr_count if hr_count > 0 else None

        return {
            "total_steps": total_steps,
            "total_calories_out": total_calories,
            "total_active_minutes": active_minutes,
            "avg_heart_rate": avg_hr,
            "event_count": len(events),
        }

    def _format_period_label(self, period_start: datetime, group_by: GroupByPeriod) -> str:
        """Format period label for display.

        Args:
            period_start: Start of period
            group_by: Grouping type

        Returns:
            Formatted label (ISO 8601)
            - DAY: "2025-10-28"
            - WEEK: "2025-W43"
            - MONTH: "2025-10"
        """
        if group_by == GroupByPeriod.DAY:
            return period_start.strftime("%Y-%m-%d")
        elif group_by == GroupByPeriod.WEEK:
            # ISO week number
            year, week, _ = period_start.isocalendar()
            return f"{year}-W{week:02d}"
        elif group_by == GroupByPeriod.MONTH:
            return period_start.strftime("%Y-%m")
        return period_start.strftime("%Y-%m-%d")
