"""Base domain event.

Base class for all domain events in the meal domain.
Events are immutable records of facts that occurred.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events.

    All domain events must:
    - Be immutable (frozen dataclass)
    - Have unique event_id (UUID)
    - Have timezone-aware occurred_at timestamp
    - Represent past facts (not commands or intentions)

    Attributes:
        event_id: Unique identifier for this event instance.
        occurred_at: When the event occurred (UTC timezone-aware).

    Raises:
        ValueError: If occurred_at is not timezone-aware.
    """

    event_id: UUID
    occurred_at: datetime

    def __post_init__(self) -> None:
        """Validate event invariants."""
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware (use UTC)")
