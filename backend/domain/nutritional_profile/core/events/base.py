"""Base domain event for nutritional profile."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.
    
    Domain events represent facts about changes that happened
    in the domain. They are immutable and include timestamp.
    
    Attributes:
        event_id: Unique event identifier
        occurred_at: When the event occurred
    """
    
    event_id: UUID
    occurred_at: datetime
    
    @staticmethod
    def _generate_event_id() -> UUID:
        """Generate new event ID.
        
        Returns:
            UUID: New unique identifier
        """
        return uuid4()
    
    @staticmethod
    def _now() -> datetime:
        """Get current UTC timestamp.
        
        Returns:
            datetime: Current time in UTC
        """
        return datetime.utcnow()
