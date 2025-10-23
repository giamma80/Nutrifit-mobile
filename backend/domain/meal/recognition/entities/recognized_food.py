"""RecognizedFood entities - food items recognized from AI analysis.

These entities represent the output of food recognition from photos or text.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RecognizedFood:
    """
    Entity: Single food item recognized from photo or text.

    Represents one detected food item with its estimated quantity
    and confidence score from AI analysis.

    Example:
        RecognizedFood(
            label="pasta",
            display_name="Spaghetti al Pomodoro",
            quantity_g=150.0,
            confidence=0.92,
            category="grains"
        )
    """

    label: str  # Machine-readable label (e.g., "pasta", "chicken_breast")
    display_name: str  # User-friendly name (e.g., "Spaghetti al Pomodoro")
    quantity_g: float  # Estimated quantity in grams
    confidence: float  # Recognition confidence (0.0 - 1.0)
    category: Optional[str] = None  # USDA category (e.g., "vegetables", "meat")

    def __post_init__(self) -> None:
        """Validate invariants after initialization."""
        if self.quantity_g <= 0:
            raise ValueError(f"Quantity must be positive, got {self.quantity_g}")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

    def is_reliable(self) -> bool:
        """
        Check if recognition is reliable.

        A recognition is considered reliable if confidence is above 0.7.

        Returns:
            True if confidence > 0.7

        Example:
            >>> food = RecognizedFood("pasta", "Pasta", 150.0, 0.85)
            >>> food.is_reliable()
            True
        """
        return self.confidence > 0.7


@dataclass
class FoodRecognitionResult:
    """
    Entity: Complete recognition result from photo or text analysis.

    Aggregates multiple recognized food items with overall metadata.

    Invariants:
    - Must have at least one item
    - Average confidence is auto-calculated if not provided
    """

    items: list[RecognizedFood]
    dish_name: Optional[str] = None  # Overall dish name (e.g., "Lunch Plate")
    confidence: float = 0.0  # Average confidence (auto-calculated)
    processing_time_ms: int = 0  # AI processing time

    def __post_init__(self) -> None:
        """Validate invariants and calculate average confidence."""
        if not self.items:
            raise ValueError("Recognition must have at least one item")

        # Auto-calculate average confidence if not provided
        if self.confidence == 0.0:
            self.confidence = sum(item.confidence for item in self.items) / len(
                self.items
            )

    def is_reliable(self) -> bool:
        """
        Check if overall recognition is reliable.

        Returns:
            True if average confidence > 0.7

        Example:
            >>> items = [
            ...     RecognizedFood("pasta", "Pasta", 150.0, 0.9),
            ...     RecognizedFood("tomato", "Tomato Sauce", 50.0, 0.85)
            ... ]
            >>> result = FoodRecognitionResult(items)
            >>> result.is_reliable()
            True
        """
        return self.confidence > 0.7

    def total_quantity_g(self) -> float:
        """
        Calculate total quantity of all items.

        Returns:
            Sum of all item quantities in grams

        Example:
            >>> items = [
            ...     RecognizedFood("pasta", "Pasta", 150.0, 0.9),
            ...     RecognizedFood("chicken", "Chicken", 100.0, 0.85)
            ... ]
            >>> result = FoodRecognitionResult(items)
            >>> result.total_quantity_g()
            250.0
        """
        return sum(item.quantity_g for item in self.items)

    def item_count(self) -> int:
        """
        Get number of recognized items.

        Returns:
            Number of items in the result

        Example:
            >>> items = [RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
            >>> result = FoodRecognitionResult(items)
            >>> result.item_count()
            1
        """
        return len(self.items)

    def reliable_items(self) -> list[RecognizedFood]:
        """
        Get only reliable items (confidence > 0.7).

        Returns:
            List of items with confidence > 0.7

        Example:
            >>> items = [
            ...     RecognizedFood("pasta", "Pasta", 150.0, 0.9),  # Reliable
            ...     RecognizedFood("mystery", "Unknown", 50.0, 0.5)  # Not reliable
            ... ]
            >>> result = FoodRecognitionResult(items)
            >>> len(result.reliable_items())
            1
        """
        return [item for item in self.items if item.is_reliable()]
