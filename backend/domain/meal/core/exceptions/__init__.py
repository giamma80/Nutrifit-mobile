"""Domain exceptions for the Meal bounded context."""

from domain.meal.core.exceptions.domain_errors import (
    EntryNotFoundError,
    InvalidMealError,
    InvalidQuantityError,
    InvalidTimestampError,
    MealDomainError,
    MealNotFoundError,
)

__all__ = [
    "MealDomainError",
    "InvalidMealError",
    "MealNotFoundError",
    "EntryNotFoundError",
    "InvalidQuantityError",
    "InvalidTimestampError",
]
