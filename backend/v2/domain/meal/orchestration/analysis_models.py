"""
Meal analysis domain models.

Temporary analysis results with 24h TTL for meal processing workflow.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic import ValidationInfo

from backend.v2.domain.shared.value_objects import UserId, AnalysisId
from backend.v2.domain.meal.nutrition.models import NutrientProfile


class AnalysisSource(str, Enum):
    """
    Source of meal analysis.

    Indicates which method was used to analyze the meal.
    """

    AI_VISION = "AI_VISION"  # Photo analyzed with AI
    BARCODE_SCAN = "BARCODE_SCAN"  # Barcode scanned
    USDA_SEARCH = "USDA_SEARCH"  # USDA manual search
    CATEGORY_PROFILE = "CATEGORY"  # Category profile fallback
    MANUAL_ENTRY = "MANUAL"  # Manual user entry


class AnalysisStatus(str, Enum):
    """
    Status of meal analysis processing.

    Tracks lifecycle from creation to conversion or expiration.
    """

    PENDING = "PENDING"  # Awaiting processing
    PROCESSING = "PROCESSING"  # Currently being processed
    COMPLETED = "COMPLETED"  # Successfully completed
    PARTIAL = "PARTIAL"  # Partially completed (fallback used)
    FAILED = "FAILED"  # Processing failed
    EXPIRED = "EXPIRED"  # Expired (>24h old)


class MealAnalysisMetadata(BaseModel):
    """
    Metadata for meal analysis.

    Tracks provenance, performance, and quality metrics.
    """

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    source: AnalysisSource = Field(..., description="Primary source of analysis")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    processing_time_ms: int = Field(..., ge=0, description="Processing time in milliseconds")

    # Optional contextual data
    ai_model_version: Optional[str] = Field(None, description="AI model version if AI_VISION used")
    image_url: Optional[str] = Field(None, description="Image URL if photo analysis")
    barcode_value: Optional[str] = Field(None, description="Barcode value if barcode scan")
    fallback_reason: Optional[str] = Field(None, description="Reason for fallback if used")

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        """Round confidence to 2 decimal places."""
        return round(v, 2)


class MealAnalysis(BaseModel):
    """
    Temporary meal analysis result.

    Represents a temporary analysis valid for 24h before expiration.
    Can be converted to a permanent MealEntry or expire.

    Supports idempotency: same analysis_id returns same result.

    Attributes:
        analysis_id: Unique identifier for this analysis
        user_id: User who requested the analysis
        meal_name: Name/description of the meal
        nutrient_profile: Nutritional information
        quantity_g: Quantity in grams
        metadata: Analysis provenance and metrics
        status: Current processing status
        created_at: When analysis was created
        expires_at: When analysis expires (created_at + 24h)
        converted_to_meal_at: When converted to meal (None if not yet)

    Example:
        >>> from datetime import datetime, timezone, timedelta
        >>> analysis = MealAnalysis(
        ...     analysis_id=AnalysisId(value="ana123"),
        ...     user_id=UserId(value="user456"),
        ...     meal_name="Banana",
        ...     nutrient_profile=NutrientProfile(...),
        ...     quantity_g=118.0,
        ...     metadata=MealAnalysisMetadata(
        ...         source=AnalysisSource.BARCODE_SCAN,
        ...         confidence=0.95,
        ...         processing_time_ms=250,
        ...         barcode_value="3017620422003",
        ...     ),
        ...     created_at=datetime.now(timezone.utc),
        ...     expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        ... )
        >>> assert analysis.is_convertible()
        >>> assert not analysis.is_expired()
    """

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    # Identity
    analysis_id: AnalysisId = Field(..., description="Unique analysis ID")
    user_id: UserId = Field(..., description="User who owns this analysis")

    # Content
    meal_name: str = Field(..., min_length=1, max_length=200, description="Name of meal/food")
    nutrient_profile: NutrientProfile = Field(..., description="Nutritional information")
    quantity_g: float = Field(..., gt=0, description="Quantity in grams")

    # Metadata
    metadata: MealAnalysisMetadata = Field(..., description="Analysis provenance and metrics")
    status: AnalysisStatus = Field(
        default=AnalysisStatus.COMPLETED,
        description="Current processing status",
    )

    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    expires_at: datetime = Field(..., description="Expiration timestamp (created_at + 24h)")
    converted_to_meal_at: Optional[datetime] = Field(
        None, description="Conversion timestamp (None if not converted)"
    )

    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, v: datetime, info: ValidationInfo) -> datetime:
        """Ensure expires_at is after created_at."""
        values = info.data
        created_at = values.get("created_at")
        if created_at and v <= created_at:
            raise ValueError("expires_at must be after created_at")
        return v

    @field_validator("converted_to_meal_at")
    @classmethod
    def validate_conversion_time(
        cls, v: Optional[datetime], info: ValidationInfo
    ) -> Optional[datetime]:
        """Ensure converted_to_meal_at is after created_at if present."""
        if v is None:
            return v

        values = info.data
        created_at = values.get("created_at")
        if created_at and v < created_at:
            raise ValueError("converted_to_meal_at must be after created_at")
        return v

    def is_expired(self) -> bool:
        """
        Check if analysis has expired.

        Returns:
            True if current time > expires_at
        """
        return datetime.now(timezone.utc) > self.expires_at

    def is_convertible(self) -> bool:
        """
        Check if analysis can be converted to meal entry.

        Requirements:
        - Status must be COMPLETED
        - Must not be expired
        - Must not already be converted

        Returns:
            True if all requirements met
        """
        return (
            self.status == AnalysisStatus.COMPLETED
            and not self.is_expired()
            and self.converted_to_meal_at is None
        )

    def time_until_expiration(self) -> timedelta:
        """
        Calculate time remaining until expiration.

        Returns:
            Timedelta (can be negative if already expired)
        """
        now = datetime.now(timezone.utc)
        return self.expires_at - now

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return self.model_dump()

    @staticmethod
    def create_new(
        user_id: UserId,
        meal_name: str,
        nutrient_profile: NutrientProfile,
        quantity_g: float,
        metadata: MealAnalysisMetadata,
        analysis_id: Optional[AnalysisId] = None,
        ttl_hours: int = 24,
    ) -> "MealAnalysis":
        """
        Factory method to create new analysis with automatic timestamps.

        Args:
            user_id: User who owns the analysis
            meal_name: Name of the meal
            nutrient_profile: Nutritional information
            quantity_g: Quantity in grams
            metadata: Analysis metadata
            analysis_id: Optional ID (auto-generated if None)
            ttl_hours: Time-to-live in hours (default 24)

        Returns:
            New MealAnalysis instance

        Example:
            >>> analysis = MealAnalysis.create_new(
            ...     user_id=UserId(value="user123"),
            ...     meal_name="Chicken Breast",
            ...     nutrient_profile=profile,
            ...     quantity_g=150.0,
            ...     metadata=metadata,
            ... )
        """
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=ttl_hours)

        if analysis_id is None:
            analysis_id = AnalysisId.generate()

        return MealAnalysis(
            analysis_id=analysis_id,
            user_id=user_id,
            meal_name=meal_name,
            nutrient_profile=nutrient_profile,
            quantity_g=quantity_g,
            metadata=metadata,
            status=AnalysisStatus.COMPLETED,
            created_at=now,
            expires_at=expires,
            converted_to_meal_at=None,
        )
