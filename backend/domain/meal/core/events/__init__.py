"""Domain events for meal core domain.

Events represent facts that have occurred in the domain.
All events are immutable and have unique identifiers.
"""

from .base import DomainEvent
from .meal_analyzed import MealAnalyzed
from .meal_confirmed import MealConfirmed
from .meal_deleted import MealDeleted
from .meal_updated import MealUpdated

__all__ = [
    "DomainEvent",
    "MealAnalyzed",
    "MealConfirmed",
    "MealDeleted",
    "MealUpdated",
]
