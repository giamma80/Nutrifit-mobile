from __future__ import annotations

from typing import Optional, List
import strawberry
from enum import Enum

from .types_meal import MealEntry  # import runtime per risoluzione Strawberry


@strawberry.enum
class MealPhotoAnalysisStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@strawberry.type
class MealPhotoItemPrediction:
    label: str
    confidence: float
    quantity_g: Optional[float] = None
    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    enrichment_source: Optional[str] = None
    calorie_corrected: Optional[bool] = None


@strawberry.enum
class MealPhotoErrorSeverity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@strawberry.enum
class MealPhotoAnalysisErrorCode(Enum):
    INVALID_IMAGE = "INVALID_IMAGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    BARCODE_DETECTION_FAILED = "BARCODE_DETECTION_FAILED"
    PARSE_EMPTY = "PARSE_EMPTY"
    PORTION_INFERENCE_FAILED = "PORTION_INFERENCE_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@strawberry.type
class MealPhotoAnalysisError:
    code: MealPhotoAnalysisErrorCode
    message: str
    severity: MealPhotoErrorSeverity
    debug_id: Optional[str] = None
    fallback_applied: bool = False


@strawberry.type
@strawberry.type
class MealPhotoAnalysis:
    id: str
    user_id: str
    status: MealPhotoAnalysisStatus
    created_at: str
    source: str
    # Alias GraphQL camelCase tramite 'name' per evitare mismatch schema vs runtime
    photo_url: Optional[str] = strawberry.field(name="photoUrl", default=None)
    dish_name: Optional[str] = strawberry.field(name="dishName", default=None)
    items: List[MealPhotoItemPrediction]
    raw_json: Optional[str] = None
    idempotency_key_used: Optional[str] = None
    total_calories: Optional[int] = None
    analysis_errors: List["MealPhotoAnalysisError"] = strawberry.field(
        default_factory=list
    )
    failure_reason: Optional["MealPhotoAnalysisErrorCode"] = None


@strawberry.type
class ConfirmMealPhotoResult:
    analysis_id: str
    created_meals: List[MealEntry]


@strawberry.input
class AnalyzeMealPhotoInput:
    photo_id: Optional[str] = None
    photo_url: Optional[str] = None
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@strawberry.input
class ConfirmMealPhotoInput:
    analysis_id: str
    accepted_indexes: List[int]
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None


__all__ = [
    "MealPhotoAnalysisStatus",
    "MealPhotoItemPrediction",
    "MealPhotoErrorSeverity",
    "MealPhotoAnalysisErrorCode",
    "MealPhotoAnalysisError",
    "MealPhotoAnalysis",
    "ConfirmMealPhotoResult",
    "AnalyzeMealPhotoInput",
    "ConfirmMealPhotoInput",
]
