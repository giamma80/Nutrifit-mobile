"""Domain events for nutritional profile."""

from .base import DomainEvent
from .profile_created import ProfileCreated
from .profile_updated import ProfileUpdated
from .progress_recorded import ProgressRecorded

__all__ = [
    "DomainEvent",
    "ProfileCreated",
    "ProfileUpdated",
    "ProgressRecorded",
]
