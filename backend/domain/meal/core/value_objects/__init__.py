"""Core value objects for meal domain.

Immutable value objects that form the building blocks of domain entities.
All value objects are frozen dataclasses with value-based equality.
"""

from .confidence import Confidence
from .meal_id import MealId
from .quantity import Quantity, Unit
from .timestamp import Timestamp

__all__ = [
    "Confidence",
    "MealId",
    "Quantity",
    "Timestamp",
    "Unit",
]
