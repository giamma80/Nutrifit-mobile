"""Domain exceptions for the Meal bounded context.

This module defines the exception hierarchy for meal domain errors.
All domain exceptions inherit from MealDomainError.
"""


class MealDomainError(Exception):
    """Base exception for meal domain.

    All domain-specific exceptions should inherit from this class.
    This allows application layer to catch and handle all meal domain errors uniformly.
    """

    pass


class InvalidMealError(MealDomainError):
    """Raised when meal invariants are violated.

    Examples:
    - Meal has no entries
    - Meal has negative total calories
    - Invalid meal_type
    """

    pass


class MealNotFoundError(MealDomainError):
    """Raised when a meal is not found by its identifier.

    This is typically raised by repository implementations when
    a meal with the given ID does not exist.
    """

    pass


class EntryNotFoundError(MealDomainError):
    """Raised when an entry is not found in a meal.

    This occurs when attempting to update or remove an entry
    that does not exist in the meal's entries collection.
    """

    pass


class InvalidQuantityError(MealDomainError):
    """Raised when an invalid quantity is specified.

    Examples:
    - Negative quantity
    - Zero quantity
    - Invalid unit
    """

    pass


class InvalidTimestampError(MealDomainError):
    """Raised when an invalid timestamp is specified.

    Examples:
    - Future timestamp (meals cannot be logged in the future)
    - Naive datetime without timezone
    """

    pass
