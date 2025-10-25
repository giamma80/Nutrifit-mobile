"""GraphQL types for aggregate meal queries.

These types support CQRS queries that operate on meal data:
- Get single meal
- List meals with filters
- Search meals
- Daily summary
"""

from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from enum import Enum
import strawberry


__all__ = [
    "MealType",
    "MealEntry",
    "Meal",
    "MealHistoryResult",
    "MealSearchResult",
    "DailySummary",
    "MealHistoryInput",
    "SearchMealsInput",
    "DailySummaryInput",
]


# ============================================
# MEAL TYPES
# ============================================


@strawberry.enum
class MealType(Enum):
    """Meal type classification."""

    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"
    SNACK = "SNACK"


@strawberry.type
class MealEntry:
    """Individual food entry within a meal."""

    id: str
    name: str
    display_name: str
    quantity_g: float
    calories: int
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    confidence: float = 1.0
    barcode: Optional[str] = None


@strawberry.type
class Meal:
    """Complete meal with entries and nutrition totals."""

    id: str
    user_id: str
    timestamp: datetime
    meal_type: MealType
    entries: List[MealEntry]
    notes: Optional[str] = None
    source: str = "MANUAL"
    analysis_id: Optional[str] = None

    # Calculated totals
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    total_sugar: float
    total_sodium: float

    created_at: datetime
    updated_at: Optional[datetime] = None

    @strawberry.field
    def entry_count(self) -> int:
        """Number of entries in meal."""
        return len(self.entries)

    @strawberry.field
    def average_confidence(self) -> float:
        """Average confidence across all entries."""
        if not self.entries:
            return 0.0
        total = sum(entry.confidence for entry in self.entries)
        return total / len(self.entries)


# ============================================
# QUERY RESULT TYPES
# ============================================


@strawberry.type
class MealHistoryResult:
    """Result of meal history query with pagination."""

    meals: List[Meal]
    total_count: int
    has_more: bool


@strawberry.type
class MealSearchResult:
    """Result of meal search query."""

    meals: List[Meal]
    total_count: int


@strawberry.type
class DailySummary:
    """Daily nutrition summary with breakdown."""

    date: datetime
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    meal_count: int
    breakdown_by_type: str  # JSON string: {"BREAKFAST": 450, "LUNCH": 650, ...}

    @strawberry.field
    def has_meals(self) -> bool:
        """Check if user logged any meals today."""
        return self.meal_count > 0


# ============================================
# INPUT TYPES
# ============================================


@strawberry.input
class MealHistoryInput:
    """Input for meal history query with filters."""

    user_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    meal_type: Optional[MealType] = None
    limit: int = 20
    offset: int = 0


@strawberry.input
class SearchMealsInput:
    """Input for meal search query."""

    user_id: str
    query_text: str
    limit: int = 20
    offset: int = 0


@strawberry.input
class DailySummaryInput:
    """Input for daily summary query."""

    user_id: str
    date: datetime  # Date to get summary for (defaults to today)
