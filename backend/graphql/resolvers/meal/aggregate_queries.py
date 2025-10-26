"""Aggregate query resolvers for meal domain.

These resolvers operate on meal data using CQRS query handlers:
- getMeal: Single meal by ID
- mealHistory: List meals with filters
- searchMeals: Full-text search
- dailySummary: Daily nutrition aggregation
"""

from typing import Optional, Any
from datetime import datetime
from uuid import UUID
import json
import strawberry

from application.meal.queries.get_meal import GetMealQuery, GetMealQueryHandler
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
from graphql.types_meal_aggregate import (
    Meal,
    MealEntry,
    MealType,
    MealHistoryResult,
    MealSearchResult,
    DailySummary,
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
            confidence=entry.confidence if hasattr(entry, "confidence") else 1.0,
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

        # Get total count of filtered meals (without pagination)
        # Need to query again without limit/offset to get accurate count
        count_query = GetMealHistoryQuery(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            meal_type=meal_type,
            limit=10000,  # High limit to get all results for counting
            offset=0,
        )
        all_meals = await handler.handle(count_query)
        total_count = len(all_meals)
        has_more = offset + len(graphql_meals) < total_count

        return MealHistoryResult(meals=graphql_meals, total_count=total_count, has_more=has_more)

    @strawberry.field
    async def search_meals(
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
              searchMeals(userId: "user123", queryText: "chicken") {
                meals { id, entries { name } }
                totalCount
              }
            }
        """
        context = info.context
        repository = context.get("meal_repository")

        if not repository:
            raise ValueError("MealRepository not available in context")

        # Create query
        query = SearchMealsQuery(user_id=user_id, query_text=query_text, limit=limit, offset=offset)

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
            date: Date for summary (defaults to today)

        Returns:
            DailySummary with totals and breakdown

        Example:
            query {
              dailySummary(userId: "user123", date: "2025-10-25") {
                totalCalories, totalProtein
                mealCount
                breakdownByType
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
            meal_count=summary.meal_count,
            breakdown_by_type=breakdown_json,
        )
