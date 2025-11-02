"""GraphQL types for meal mutations.

These types support CQRS commands:
- Analyze meal (photo/barcode/text)
- Confirm analysis (2-step process)
- Update meal
- Delete meal
"""

from __future__ import annotations

from typing import Optional, List, Annotated, Union
from datetime import datetime
import strawberry

from graphql.types_meal_aggregate import Meal, MealType


__all__ = [
    # Re-exported from types_meal_aggregate
    "Meal",
    "MealType",
    # Input types
    "AnalyzeMealPhotoInput",
    "AnalyzeMealTextInput",
    "AnalyzeMealBarcodeInput",
    "ConfirmAnalysisInput",
    "UpdateMealInput",
    "DeleteMealInput",
    # Success types
    "MealAnalysisSuccess",
    "ConfirmAnalysisSuccess",
    "UpdateMealSuccess",
    "DeleteMealSuccess",
    # Error types
    "MealAnalysisError",
    "ConfirmAnalysisError",
    "UpdateMealError",
    "DeleteMealError",
    # Union types
    "MealAnalysisResult",
    "ConfirmAnalysisResult",
    "UpdateMealResult",
    "DeleteMealResult",
]


# ============================================
# MUTATION INPUT TYPES
# ============================================


@strawberry.input
class AnalyzeMealPhotoInput:
    """Input for analyze meal photo mutation."""

    user_id: str
    photo_url: str
    dish_hint: Optional[str] = None
    meal_type: MealType = MealType.LUNCH
    timestamp: Optional[datetime] = None
    idempotency_key: Optional[str] = None


@strawberry.input
class AnalyzeMealTextInput:
    """Input for analyze meal text mutation."""

    user_id: str
    text_description: str
    meal_type: MealType = MealType.LUNCH
    timestamp: Optional[datetime] = None
    idempotency_key: Optional[str] = None


@strawberry.input
class AnalyzeMealBarcodeInput:
    """Input for analyze meal barcode mutation."""

    user_id: str
    barcode: str
    quantity_g: float
    meal_type: MealType = MealType.SNACK
    timestamp: Optional[datetime] = None
    idempotency_key: Optional[str] = None


@strawberry.input
class ConfirmAnalysisInput:
    """Input for confirm analysis mutation (2-step process).

    Use meal.id from analyzeMealPhoto response (NOT analysis_id).

    Example workflow:
        # Step 1: Analyze
        mutation {
          analyzeMealPhoto(input: {...}) {
            ... on MealAnalysisSuccess {
              meal {
                id  # ← Use this as meal_id in step 2
                entries { id, name, calories }
              }
            }
          }
        }

        # Step 2: Confirm selected entries
        mutation {
          confirmMealAnalysis(input: {
            meal_id: "abc-123"  # ← From meal.id above
            user_id: "user123"
            confirmed_entry_ids: ["entry1", "entry2"]
          }) { ... }
        }
    """

    meal_id: str  # Use meal.id from analyzeMealPhoto response
    user_id: str
    confirmed_entry_ids: List[str]  # IDs of entries to keep


@strawberry.input
class UpdateMealInput:
    """Input for update meal mutation."""

    meal_id: str
    user_id: str
    meal_type: Optional[MealType] = None
    timestamp: Optional[datetime] = None
    notes: Optional[str] = None


@strawberry.input
class DeleteMealInput:
    """Input for delete meal mutation."""

    meal_id: str
    user_id: str


# ============================================
# MUTATION RESULT TYPES
# ============================================


@strawberry.type
class MealAnalysisSuccess:
    """Successful meal analysis result.

    Use meal.id (NOT analysis_id) for confirmMealAnalysis mutation.

    Fields:
        meal: Complete meal with entries and totals
        analysis_id: Optional tracking ID (not used for confirmation)
        processing_time_ms: Analysis duration in milliseconds
    """

    meal: Meal  # Use meal.id for confirmMealAnalysis
    analysis_id: Optional[str] = None  # For tracking, not for confirmation
    processing_time_ms: Optional[int] = None


@strawberry.type
class MealAnalysisError:
    """Meal analysis error result."""

    message: str
    code: str = "ANALYSIS_FAILED"


@strawberry.type
class ConfirmAnalysisSuccess:
    """Successful confirmation result."""

    meal: Meal
    confirmed_count: int
    rejected_count: int


@strawberry.type
class ConfirmAnalysisError:
    """Confirmation error result."""

    message: str
    code: str = "CONFIRMATION_FAILED"


@strawberry.type
class UpdateMealSuccess:
    """Successful update result."""

    meal: Meal


@strawberry.type
class UpdateMealError:
    """Update error result."""

    message: str
    code: str = "UPDATE_FAILED"


@strawberry.type
class DeleteMealSuccess:
    """Successful delete result."""

    meal_id: str
    message: str = "Meal deleted successfully"


@strawberry.type
class DeleteMealError:
    """Delete error result."""

    message: str
    code: str = "DELETE_FAILED"


# ============================================
# UNION RESULT TYPES
# ============================================

MealAnalysisResult = Annotated[
    Union[MealAnalysisSuccess, MealAnalysisError],
    strawberry.union("MealAnalysisResult"),
]

ConfirmAnalysisResult = Annotated[
    Union[ConfirmAnalysisSuccess, ConfirmAnalysisError],
    strawberry.union("ConfirmAnalysisResult"),
]

UpdateMealResult = Annotated[
    Union[UpdateMealSuccess, UpdateMealError],
    strawberry.union("UpdateMealResult"),
]

DeleteMealResult = Annotated[
    Union[DeleteMealSuccess, DeleteMealError],
    strawberry.union("DeleteMealResult"),
]
