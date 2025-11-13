"""Aggregate query resolvers for meal domain.

These resolvers operate on meal data using CQRS query handlers:
- meal: Single meal by ID
- mealHistory: List meals with filters
- search: Full-text search in meals
- dailySummary: Daily nutrition summary
- summaryRange: Nutrition summaries for date ranges with grouping
"""

from typing import Optional, Any
from datetime import datetime
from uuid import UUID
import json
import strawberry

from application.meal.queries.get_meal import (
    GetMealQuery,
    GetMealQueryHandler,
)
from application.meal.queries.get_meal_history import (
    GetMealHistoryQuery,
    GetMealHistoryQueryHandler,
)
from application.meal.queries.search_meals import (
    SearchMealsQuery,
    SearchMealsQueryHandler,
)
from application.meal.queries.get_daily_summary import (
    GetDailySummaryQuery,
    GetDailySummaryQueryHandler,
)
from application.meal.queries.get_summary_range import (
    GetSummaryRangeQuery,
    GetSummaryRangeQueryHandler,
    GroupByPeriod as QueryGroupByPeriod,
)
from graphql.types_meal_aggregate import (
    MealType,
    GroupByPeriod,
    Meal,
    MealEntry,
    MealHistoryResult,
    MealSearchResult,
    DailySummary,
    PeriodSummary,
    RangeSummaryResult,
)


def map_meal_to_graphql(meal: Any) -> Meal:
    """Map domain Meal entity to GraphQL Meal type."""
    # Map entries
    entries = [
        MealEntry(
            id=str(entry.id),
            name=entry.name,
            display_name=entry.display_name,
            quantity_g=entry.quantity_g,
            calories=entry.calories,
            protein=entry.protein,
            carbs=entry.carbs,
            fat=entry.fat,
            fiber=entry.fiber,
            sugar=entry.sugar,
            sodium=entry.sodium,
            confidence=(entry.confidence if hasattr(entry, "confidence") else 1.0),
            barcode=entry.barcode if hasattr(entry, "barcode") else None,
        )
        for entry in meal.entries
    ]

    # Map meal type enum
    meal_type_map = {
        "BREAKFAST": MealType.BREAKFAST,
        "LUNCH": MealType.LUNCH,
        "DINNER": MealType.DINNER,
        "SNACK": MealType.SNACK,
    }
    meal_type = meal_type_map.get(meal.meal_type, MealType.LUNCH)

    return Meal(
        id=str(meal.id),
        user_id=meal.user_id,
        timestamp=meal.timestamp,
        meal_type=meal_type,
        # Recognition metadata
        dish_name=meal.dish_name if hasattr(meal, "dish_name") else "Meal",
        image_url=meal.image_url if hasattr(meal, "image_url") else None,
        source=meal.source if hasattr(meal, "source") else "MANUAL",
        confidence=meal.confidence if hasattr(meal, "confidence") else 1.0,
        # Content
        entries=entries,
        notes=meal.notes,
        analysis_id=meal.analysis_id if hasattr(meal, "analysis_id") else None,
        # Totals
        total_calories=meal.total_calories,
        total_protein=meal.total_protein,
        total_carbs=meal.total_carbs,
        total_fat=meal.total_fat,
        total_fiber=meal.total_fiber,
        total_sugar=meal.total_sugar,
        total_sodium=meal.total_sodium,
        # Timestamps
        created_at=meal.created_at,
        updated_at=meal.updated_at if hasattr(meal, "updated_at") else None,
    )


@strawberry.type
class AggregateQueries:
    """Aggregate queries for meal data operations."""

    @strawberry.field
    async def meal(self, info: strawberry.types.Info, meal_id: str, user_id: str) -> Optional[Meal]:
        """Get single meal by ID.

        Args:
            info: Strawberry field info (injected)
            meal_id: Meal ID (UUID)
            user_id: User ID for authorization

        Returns:
            Meal or None if not found/unauthorized

        Example:
            query {
              meal(mealId: "...", userId: "user123") {
                id, timestamp, mealType
                entries { name, calories }
                totalCalories
              }
            }
        """
        context = info.context
        repository = context.get("meal_repository")

        if not repository:
            raise ValueError("MealRepository not available in context")

        # Create query
        query = GetMealQuery(meal_id=UUID(meal_id), user_id=user_id)

        # Execute via handler
        handler = GetMealQueryHandler(repository=repository)
        meal = await handler.handle(query)

        if not meal:
            return None

        # Map domain entity → GraphQL type
        return map_meal_to_graphql(meal)

    @strawberry.field
    async def meal_history(
        self,
        info: strawberry.types.Info,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        meal_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> MealHistoryResult:
        """Get meal history with filters and pagination.

        Args:
            info: Strawberry field info (injected)
            user_id: User ID
            start_date: Filter by start date (optional)
            end_date: Filter by end date (optional)
            meal_type: Filter by meal type (optional)
            limit: Results per page
            offset: Pagination offset

        Returns:
            MealHistoryResult with meals and pagination info

        Example:
            query {
              mealHistory(userId: "user123", limit: 10) {
                meals { id, timestamp, totalCalories }
                totalCount
                hasMore
              }
            }
        """
        context = info.context
        repository = context.get("meal_repository")

        if not repository:
            raise ValueError("MealRepository not available in context")

        # Create query
        query = GetMealHistoryQuery(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            meal_type=meal_type,
            limit=limit,
            offset=offset,
        )

        # Execute via handler
        handler = GetMealHistoryQueryHandler(repository=repository)
        meals = await handler.handle(query)

        # Map domain entities → GraphQL types
        graphql_meals = [map_meal_to_graphql(meal) for meal in meals]

        # Calculate total count and pagination
        # For date range queries, we need full count (optimization needed)
        # For simple queries, use repository count method
        if start_date and end_date:
            # Full count requires fetching all results
            count_query = GetMealHistoryQuery(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                meal_type=meal_type,
                limit=10000,  # High limit for counting
                offset=0,
            )
            all_meals = await handler.handle(count_query)
            total_count = len(all_meals)
        else:
            # Use repository count method (optimized)
            total_count = await repository.count_by_user(user_id=user_id)
            # Apply meal_type filter to count if present
            if meal_type:
                all_meals_query = GetMealHistoryQuery(
                    user_id=user_id,
                    meal_type=meal_type,
                    limit=10000,
                    offset=0,
                )
                all_meals = await handler.handle(all_meals_query)
                total_count = len(all_meals)

        has_more = offset + len(graphql_meals) < total_count

        return MealHistoryResult(meals=graphql_meals, total_count=total_count, has_more=has_more)

    @strawberry.field
    async def search(
        self,
        info: strawberry.types.Info,
        user_id: str,
        query_text: str,
        limit: int = 20,
        offset: int = 0,
    ) -> MealSearchResult:
        """Search meals by text (full-text search in entries and notes).

        Args:
            info: Strawberry field info (injected)
            user_id: User ID
            query_text: Search text
            limit: Results limit
            offset: Pagination offset

        Returns:
            MealSearchResult with matching meals

        Example:
            query {
              meals {
                search(userId: "user123", queryText: "chicken") {
                  meals { id, entries { name } }
                  totalCount
                }
              }
            }
        """
        context = info.context
        repository = context.get("meal_repository")

        if not repository:
            raise ValueError("MealRepository not available in context")

        # Create query
        query = SearchMealsQuery(
            user_id=user_id,
            query_text=query_text,
            limit=limit,
            offset=offset,
        )

        # Execute via handler
        handler = SearchMealsQueryHandler(repository=repository)
        meals = await handler.handle(query)

        # Map domain entities → GraphQL types
        graphql_meals = [map_meal_to_graphql(meal) for meal in meals]

        return MealSearchResult(meals=graphql_meals, total_count=len(graphql_meals))

    @strawberry.field
    async def daily_summary(
        self, info: strawberry.types.Info, user_id: str, date: datetime
    ) -> DailySummary:
        """Get daily nutrition summary with breakdown by meal type.

        Args:
            info: Strawberry field info (injected)
            user_id: User ID
            date: Date for summary

        Returns:
            DailySummary with totals and breakdown by meal type

        Example:
            query {
              meals {
                dailySummary(userId: "user123", date: "2025-10-25") {
                  totalCalories, totalProtein
                  mealCount
                  breakdownByType
                }
              }
            }
        """
        context = info.context
        repository = context.get("meal_repository")

        if not repository:
            raise ValueError("MealRepository not available in context")

        # Ensure date has timezone (Strawberry may parse without it)
        if date and date.tzinfo is None:
            from datetime import timezone as tz

            date = date.replace(tzinfo=tz.utc)

        # Create query
        query = GetDailySummaryQuery(user_id=user_id, date=date)

        # Execute via handler
        handler = GetDailySummaryQueryHandler(repository=repository)
        summary = await handler.handle(query)

        # Map domain entity → GraphQL type
        # Convert breakdown dict to JSON string for GraphQL
        breakdown_json = json.dumps(summary.breakdown_by_type)

        return DailySummary(
            date=summary.date,
            total_calories=summary.total_calories,
            total_protein=summary.total_protein,
            total_carbs=summary.total_carbs,
            total_fat=summary.total_fat,
            total_fiber=summary.total_fiber,
            total_sugar=summary.total_sugar,
            total_sodium=summary.total_sodium,
            meal_count=summary.meal_count,
            breakdown_by_type=breakdown_json,
        )

    @strawberry.field
    async def summary_range(
        self,
        info: strawberry.types.Info,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        group_by: GroupByPeriod = GroupByPeriod.DAY,
    ) -> RangeSummaryResult:
        """Get nutrition summaries for date range with flexible grouping.

        This query enables efficient dashboard queries over custom date
        ranges without needing to loop through individual days. Returns both
        per-period breakdown and total aggregate across entire range.

        Args:
            info: Strawberry field info (injected)
            user_id: User ID
            start_date: Range start (inclusive)
            end_date: Range end (inclusive)
            group_by: Group results by DAY, WEEK, or MONTH

        Returns:
            List of PeriodSummary, one per period in range

        Example:
            # Last 7 days grouped by day
            query {
              meals {
                summaryRange(
                  userId: "user123"
                  startDate: "2025-10-21T00:00:00Z"
                  endDate: "2025-10-27T23:59:59Z"
                  groupBy: DAY
                ) {
                  period
                  totalCalories
                  totalProtein
                  mealCount
                  avgDailyCalories
                }
              }
            }

            # Last 4 weeks grouped by week
            query {
              meals {
                summaryRange(
                  userId: "user123"
                  startDate: "2025-10-01T00:00:00Z"
                  endDate: "2025-10-28T23:59:59Z"
                  groupBy: WEEK
                ) {
                  period        # "2025-W40", "2025-W41", etc
                  totalCalories
                  breakdownByType
                }
              }
            }
        """
        context = info.context
        repository = context.get("meal_repository")

        if not repository:
            raise ValueError("MealRepository not available in context")

        # Keep timezone-aware datetimes (MongoDB requirement)
        # Both InMemory and MongoDB repositories handle timezone-aware
        # datetimes correctly

        # Map GraphQL enum to query enum
        group_by_map = {
            GroupByPeriod.DAY: QueryGroupByPeriod.DAY,
            GroupByPeriod.WEEK: QueryGroupByPeriod.WEEK,
            GroupByPeriod.MONTH: QueryGroupByPeriod.MONTH,
        }
        query_group_by = group_by_map[group_by]

        # Create query
        query = GetSummaryRangeQuery(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            group_by=query_group_by,
        )

        # Execute via handler
        handler = GetSummaryRangeQueryHandler(repository=repository)
        summaries = await handler.handle(query)

        # Map domain entities → GraphQL types
        graphql_summaries = []
        for s in summaries:
            period_summary = object.__new__(PeriodSummary)
            period_summary.period = s.period
            period_summary.start_date = s.start_date
            period_summary.end_date = s.end_date
            period_summary.total_calories = s.total_calories
            period_summary.total_protein = s.total_protein
            period_summary.total_carbs = s.total_carbs
            period_summary.total_fat = s.total_fat
            period_summary.total_fiber = s.total_fiber
            period_summary.total_sugar = s.total_sugar
            period_summary.total_sodium = s.total_sodium
            period_summary.meal_count = s.meal_count
            period_summary.breakdown_by_type = json.dumps(s.breakdown_by_type)
            graphql_summaries.append(period_summary)

        # Calculate total aggregate across all periods
        total_calories = sum(s.total_calories for s in summaries)
        total_protein = sum(s.total_protein for s in summaries)
        total_carbs = sum(s.total_carbs for s in summaries)
        total_fat = sum(s.total_fat for s in summaries)
        total_fiber = sum(s.total_fiber for s in summaries)
        total_sugar = sum(s.total_sugar for s in summaries)
        total_sodium = sum(s.total_sodium for s in summaries)
        total_meal_count = sum(s.meal_count for s in summaries)

        # Merge breakdown dictionaries
        total_breakdown: dict[str, float] = {}
        for s in summaries:
            for meal_type, calories in s.breakdown_by_type.items():
                total_breakdown[meal_type] = total_breakdown.get(meal_type, 0.0) + calories

        total_summary = object.__new__(PeriodSummary)
        total_summary.period = "TOTAL"
        total_summary.start_date = start_date
        total_summary.end_date = end_date
        total_summary.total_calories = total_calories
        total_summary.total_protein = total_protein
        total_summary.total_carbs = total_carbs
        total_summary.total_fat = total_fat
        total_summary.total_fiber = total_fiber
        total_summary.total_sugar = total_sugar
        total_summary.total_sodium = total_sodium
        total_summary.meal_count = total_meal_count
        total_summary.breakdown_by_type = json.dumps(total_breakdown)

        result = object.__new__(RangeSummaryResult)
        result.periods = graphql_summaries
        result.total = total_summary
        return result
