"""
Domain models for food recognition.

Models for AI-powered food identification from photos and text.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field, validator


class RecognitionStatus(str, Enum):
    """Status of food recognition operation."""

    SUCCESS = "SUCCESS"  # Completed successfully
    PARTIAL = "PARTIAL"  # Partial results
    FAILED = "FAILED"  # Recognition failed
    TIMEOUT = "TIMEOUT"  # API timeout
    RATE_LIMITED = "RATE_LIMITED"  # API rate limit hit


class RecognizedFoodItem(BaseModel):
    """
    Single food item recognized from photo/text.

    Represents AI-identified food before nutrient enrichment.

    Attributes:
        label: Machine-readable identifier (e.g., "pasta")
        display_name: User-friendly name (e.g., "Spaghetti")
        quantity_g: Estimated quantity in grams
        confidence: Recognition confidence (0.0 - 1.0)
        category: USDA food category (optional)

    Example:
        >>> item = RecognizedFoodItem(
        ...     label="chicken",
        ...     display_name="Grilled Chicken Breast",
        ...     quantity_g=150.0,
        ...     confidence=0.92,
        ...     category="meat",
        ... )
        >>> assert item.confidence > 0.9
    """

    label: str = Field(..., min_length=1, max_length=100, description="Internal identifier")
    display_name: str = Field(..., min_length=1, max_length=200, description="User-friendly name")
    quantity_g: float = Field(..., gt=0, description="Estimated quantity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recognition confidence")
    category: Optional[str] = Field(None, description="USDA category")

    @validator("label", "display_name")
    def not_empty(cls, v: str) -> str:
        """Ensure not just whitespace."""
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace")
        return v.strip()

    @validator("confidence")
    def round_confidence(cls, v: float) -> float:
        """Round to 2 decimal places."""
        return round(v, 2)

    class Config:
        """Pydantic configuration."""

        frozen = True  # Immutable


class FoodRecognitionResult(BaseModel):
    """
    Complete food recognition result from AI.

    Aggregates multiple recognized items with metadata.

    Attributes:
        items: List of recognized food items
        dish_name: Overall dish name if identifiable (Italian)
        image_url: URL of analyzed image (for persistence)
        confidence: Average confidence across items
        processing_time_ms: API call duration
        status: Operation status
        raw_response: Raw AI response (for debugging)

    Example:
        >>> result = FoodRecognitionResult(
        ...     items=[
        ...         RecognizedFoodItem(
        ...             label="pasta",
        ...             display_name="Spaghetti Carbonara",
        ...             quantity_g=200.0,
        ...             confidence=0.95,
        ...         ),
        ...     ],
        ...     dish_name="Spaghetti alla Carbonara",
        ...     image_url="https://example.com/meal.jpg",
        ...     confidence=0.95,
        ...     processing_time_ms=1250,
        ...     status=RecognitionStatus.SUCCESS,
        ... )
        >>> assert result.image_url is not None
    """

    items: List[RecognizedFoodItem] = Field(
        default_factory=list, description="Recognized food items"
    )
    dish_name: Optional[str] = Field(None, description="Nome del piatto in italiano")
    image_url: Optional[str] = Field(None, description="URL of analyzed image")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Average confidence")
    processing_time_ms: int = Field(0, ge=0, description="Processing duration")
    status: RecognitionStatus = Field(RecognitionStatus.SUCCESS, description="Operation status")
    raw_response: Optional[str] = Field(None, description="Raw AI response")

    @validator("confidence")
    def round_confidence(cls, v: float) -> float:
        """Round to 2 decimal places."""
        return round(v, 2)

    @validator("items")
    def at_least_one_on_success(
        cls, v: List[RecognizedFoodItem], values: dict[str, Any]
    ) -> List[RecognizedFoodItem]:
        """Ensure SUCCESS status has items."""
        status = values.get("status")
        if status == RecognitionStatus.SUCCESS and len(v) == 0:
            raise ValueError("SUCCESS status requires at least one item")
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class RecognitionRequest(BaseModel):
    """
    Request for food recognition.

    Input for FoodRecognitionService.

    Attributes:
        image_url: URL to food photo
        user_id: User making request
        dish_hint: Optional hint for better recognition

    Example:
        >>> request = RecognitionRequest(
        ...     image_url="https://example.com/meal.jpg",
        ...     user_id="user_123",
        ...     dish_hint="sushi",
        ... )
    """

    image_url: str = Field(..., min_length=1, description="Food photo URL")
    user_id: str = Field(..., min_length=1, description="User identifier")
    dish_hint: Optional[str] = Field(None, max_length=100, description="Recognition hint")

    @validator("image_url")
    def valid_url(cls, v: str) -> str:
        """Ensure URL is valid HTTP/HTTPS."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Image URL must be HTTP/HTTPS")
        return v

    @validator("dish_hint")
    def hint_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Clean hint if provided."""
        if v and not v.strip():
            return None
        return v.strip() if v else None

    class Config:
        """Pydantic configuration."""

        frozen = True
