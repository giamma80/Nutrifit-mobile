"""Global query resolvers.

Queries that span multiple domains or provide cross-domain aggregations:
- dailySummary: Daily nutrition summary (spans meals, activity, health)
"""

import json
from datetime import datetime
import strawberry

from application.meal.queries.get_daily_summary import (
    GetDailySummaryQuery,
    GetDailySummaryQueryHandler,
)
from graphql.types_meal_aggregate import DailySummary


async def resolve_daily_summary(
    info: strawberry.types.Info, user_id: str, date: datetime
) -> DailySummary:
    """Get daily nutrition summary with breakdown by meal type.

    This is a global query that aggregates data from multiple domains:
    - Meals (nutrition totals)
    - Activity (steps, calories out)
    - Health (sync data)

    Args:
        info: Strawberry field info (injected)
        user_id: User ID
        date: Date for summary

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
        total_sugar=summary.total_sugar,
        total_sodium=summary.total_sodium,
        meal_count=summary.meal_count,
        breakdown_by_type=breakdown_json,
    )
