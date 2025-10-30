"""ProfileUpdated domain event."""

from dataclasses import dataclass
from uuid import UUID

from .base import DomainEvent


@dataclass(frozen=True)
class ProfileUpdated(DomainEvent):
    """Event emitted when nutritional profile is updated.
    
    Tracks which fields were updated (e.g., weight, goal, activity).
    
    Attributes:
        profile_id: ID of updated profile
        user_id: User the profile belongs to
        updated_fields: List of field names that changed
    """
    
    profile_id: UUID
    user_id: str
    updated_fields: tuple[str, ...]
    
    @staticmethod
    def create(
        profile_id: UUID,
        user_id: str,
        updated_fields: list[str]
    ) -> "ProfileUpdated":
        """Factory method to create event.
        
        Args:
            profile_id: Profile ID
            user_id: User ID
            updated_fields: List of changed fields
            
        Returns:
            ProfileUpdated: New event
        """
        return ProfileUpdated(
            event_id=DomainEvent._generate_event_id(),
            occurred_at=DomainEvent._now(),
            profile_id=profile_id,
            user_id=user_id,
            updated_fields=tuple(updated_fields)
        )
