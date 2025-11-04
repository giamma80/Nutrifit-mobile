"""Activity query resolvers.

Groups activity-related queries:
- entries: List activity events
- syncEntries: List health totals sync deltas
- aggregateRange: Aggregate activity data by period
"""

import dataclasses
from typing import List, Optional, Any
import strawberry
from strawberry.types import Info

from graphql.types_activity_health import (
    ActivityEvent,
    HealthTotalsDelta,
    ActivityPeriodSummary,
    ActivityRangeResult,
    GroupByPeriod,
)
from repository.activities import activity_repo
from repository.health_totals import health_totals_repo
from domain.activity.application.get_aggregate_range import (
    GetAggregateRangeQuery,
    GetAggregateRangeQueryHandler,
    GroupByPeriod as QueryGroupByPeriod,
)
from graphql.utils.datetime_helpers import parse_datetime_to_naive_utc

DEFAULT_USER_ID = "default"


@strawberry.type
class ActivityQueries:
    """Activity data queries."""

    @strawberry.field(description="Lista eventi attività con paginazione")  # type: ignore[misc]
    def entries(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        limit: int = 100,
        after: Optional[str] = None,
        before: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[ActivityEvent]:
        """List activity events with pagination.

        Args:
            limit: Max results (default 100, max 500)
            after: Start timestamp (optional)
            before: End timestamp (optional)
            user_id: User ID (defaults to "default")

        Returns:
            List of activity events

        Example:
            query {
              activity {
                entries(userId: "user123", limit: 10) {
                  id, timestamp, source, steps
                }
              }
            }
        """
        if limit <= 0:
            limit = 100
        if limit > 500:
            limit = 500
        uid = user_id or DEFAULT_USER_ID
        events = activity_repo.list(
            uid,
            start_ts=after,
            end_ts=before,
            limit=limit,
        )
        return [ActivityEvent(**dataclasses.asdict(e)) for e in events]

    @strawberry.field(description="Lista delta sync health totals per giorno")  # type: ignore[misc]
    def sync_entries(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        date: str,
        user_id: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 200,
    ) -> List[HealthTotalsDelta]:
        """List health totals sync deltas for a date.

        Args:
            date: Date in YYYY-MM-DD format
            user_id: User ID (defaults to "default")
            after: After timestamp (optional)
            limit: Max results (default 200, max 500)

        Returns:
            List of sync deltas

        Example:
            query {
              activity {
                syncEntries(date: "2025-10-25", userId: "user123") {
                  timestamp, steps, caloriesOut
                }
              }
            }
        """
        if limit <= 0:
            limit = 50
        if limit > 500:
            limit = 500
        uid = user_id or DEFAULT_USER_ID
        records = health_totals_repo.list_deltas(
            user_id=uid, date=date, after_ts=after, limit=limit
        )
        return [HealthTotalsDelta(**dataclasses.asdict(r)) for r in records]

    @strawberry.field(  # type: ignore[misc]
        description="Aggrega attività per range con raggruppamento"
    )
    def aggregate_range(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        user_id: str,
        start_date: str,
        end_date: str,
        group_by: GroupByPeriod = GroupByPeriod.DAY,
    ) -> ActivityRangeResult:
        """Aggregate activity data by period (DAY/WEEK/MONTH).

        Efficiently aggregates activity data without expensive loops.
        Server-side aggregation for dashboard views. Returns both per-period
        breakdown and total aggregate across entire range.

        Args:
            user_id: User ID
            start_date: Range start (ISO format)
            end_date: Range end (ISO format)
            group_by: Grouping period (DAY, WEEK, MONTH)

        Returns:
            List of period summaries with activity totals

        Example - Last 7 days grouped by day:
            query {
              activity {
                aggregateRange(
                  userId: "user123"
                  startDate: "2025-10-21T00:00:00Z"
                  endDate: "2025-10-27T23:59:59Z"
                  groupBy: DAY
                ) {
                  period
                  totalSteps
                  totalCaloriesOut
                  avgDailySteps
                  hasActivity
                }
              }
            }

        Example - Last 4 weeks grouped by week:
            query {
              activity {
                aggregateRange(
                  userId: "user123"
                  startDate: "2025-10-01T00:00:00Z"
                  endDate: "2025-10-28T23:59:59Z"
                  groupBy: WEEK
                ) {
                  period
                  totalSteps
                  avgDailySteps
                }
              }
            }
        """
        # Parse dates to naive UTC
        start_dt = parse_datetime_to_naive_utc(start_date)
        end_dt = parse_datetime_to_naive_utc(end_date)

        # Map GraphQL enum to query enum
        query_group_by = QueryGroupByPeriod(group_by.value)

        # Create and execute query
        query = GetAggregateRangeQuery(
            user_id=user_id,
            start_date=start_dt,
            end_date=end_dt,
            group_by=query_group_by,
        )

        handler = GetAggregateRangeQueryHandler()
        results = handler.handle(query)

        # Convert to GraphQL types - construct manually
        graphql_results: List[ActivityPeriodSummary] = []
        for result in results:
            # Create instance and set attributes
            summary = object.__new__(ActivityPeriodSummary)
            summary.period = result.period
            summary.start_date = result.start_date.isoformat() + "Z"
            summary.end_date = result.end_date.isoformat() + "Z"
            summary.total_steps = result.total_steps
            summary.total_calories_out = result.total_calories_out
            summary.total_active_minutes = result.total_active_minutes
            summary.avg_heart_rate = result.avg_heart_rate
            summary.event_count = result.event_count
            graphql_results.append(summary)

        # Calculate total aggregate across all periods
        total_steps = sum(r.total_steps for r in results)
        total_calories = sum(r.total_calories_out for r in results)
        total_minutes = sum(r.total_active_minutes for r in results)
        total_events = sum(r.event_count for r in results)

        # Average heart rate (weighted by event count)
        hr_sum = sum(
            r.avg_heart_rate * r.event_count for r in results if r.avg_heart_rate is not None
        )
        hr_events = sum(r.event_count for r in results if r.avg_heart_rate is not None)
        avg_hr = hr_sum / hr_events if hr_events > 0 else None

        total_summary = object.__new__(ActivityPeriodSummary)
        total_summary.period = "TOTAL"
        total_summary.start_date = start_dt.isoformat() + "Z"
        total_summary.end_date = end_dt.isoformat() + "Z"
        total_summary.total_steps = total_steps
        total_summary.total_calories_out = total_calories
        total_summary.total_active_minutes = total_minutes
        total_summary.avg_heart_rate = avg_hr
        total_summary.event_count = total_events

        result_wrapper = object.__new__(ActivityRangeResult)
        result_wrapper.periods = graphql_results
        result_wrapper.total = total_summary
        return result_wrapper
