"""CQRS Queries for Meal domain."""

# Aggregate Queries
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
    DailySummary,
)

# Atomic Queries (Utility)
from application.meal.queries.recognize_food import (
    RecognizeFoodQuery,
    RecognizeFoodQueryHandler,
)
from application.meal.queries.enrich_nutrients import (
    EnrichNutrientsQuery,
    EnrichNutrientsQueryHandler,
)
from application.meal.queries.search_food_by_barcode import (
    SearchFoodByBarcodeQuery,
    SearchFoodByBarcodeQueryHandler,
)

__all__ = [
    # Aggregate Queries
    "GetMealQuery",
    "GetMealQueryHandler",
    "GetMealHistoryQuery",
    "GetMealHistoryQueryHandler",
    "SearchMealsQuery",
    "SearchMealsQueryHandler",
    "GetDailySummaryQuery",
    "GetDailySummaryQueryHandler",
    "DailySummary",
    # Atomic Queries
    "RecognizeFoodQuery",
    "RecognizeFoodQueryHandler",
    "EnrichNutrientsQuery",
    "EnrichNutrientsQueryHandler",
    "SearchFoodByBarcodeQuery",
    "SearchFoodByBarcodeQueryHandler",
]
