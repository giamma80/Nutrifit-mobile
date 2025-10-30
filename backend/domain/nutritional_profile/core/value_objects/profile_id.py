"""ProfileId value object - unique identifier for nutritional profiles."""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ProfileId:
    """Unique identifier for a nutritional profile.
    
    Immutable value object representing a profile's UUID.
    """
    
    value: UUID
    
    @staticmethod
    def generate() -> "ProfileId":
        """Generate a new unique profile ID.
        
        Returns:
            ProfileId: New profile ID with generated UUID
        """
        return ProfileId(value=uuid4())
    
    @staticmethod
    def from_string(id_str: str) -> "ProfileId":
        """Create ProfileId from string representation.
        
        Args:
            id_str: String representation of UUID
            
        Returns:
            ProfileId: Profile ID from parsed UUID
            
        Raises:
            ValueError: If string is not a valid UUID
        """
        try:
            return ProfileId(value=UUID(id_str))
        except ValueError as e:
            raise ValueError(f"Invalid profile ID format: {id_str}") from e
    
    def __str__(self) -> str:
        """String representation of profile ID.
        
        Returns:
            str: UUID as string
        """
        return str(self.value)
    
    def __repr__(self) -> str:
        """Developer-friendly representation.
        
        Returns:
            str: ProfileId with UUID
        """
        return f"ProfileId(value={self.value})"
