"""Pydantic models for OpenAI structured outputs.

These models define the schema for structured outputs from OpenAI API.
Used with beta.chat.completions.parse() for native Pydantic support.
"""

from pydantic import BaseModel, Field
from typing import List


class RecognizedFoodItem(BaseModel):
    """
    Single food item recognized from photo or text.

    This is the Pydantic model for OpenAI structured outputs.
    Maps to domain entity RecognizedFood.
    """

    label: str = Field(
        ...,
        description="USDA-compatible food label in English (e.g., 'chicken breast, roasted')",
    )
    display_name: str = Field(
        ...,
        description="User-friendly name in Italian (e.g., 'Petto di pollo alla griglia')",
    )
    quantity_g: float = Field(
        ...,
        gt=0,
        description="Quantity in grams",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
    )


class FoodRecognitionResponse(BaseModel):
    """
    Complete response from food recognition.

    This is the root model for OpenAI structured outputs.
    """

    dish_title: str = Field(
        default="",
        description="Italian name of the complete dish (e.g., 'Spaghetti alla Carbonara')",
    )
    items: List[RecognizedFoodItem] = Field(
        default_factory=list,
        max_length=5,
        description="List of recognized food items (max 5)",
    )
