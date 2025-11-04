"""ProfileCreated domain event."""

from dataclasses import dataclass
from uuid import UUID

from .base import DomainEvent


@dataclass(frozen=True)
class ProfileCreated(DomainEvent):
    """Event emitted when nutritional profile is created.

    Attributes:
        profile_id: ID of created profile
        user_id: User the profile belongs to
        goal: Initial goal (cut/maintain/bulk)
        bmr: Calculated BMR
        tdee: Calculated TDEE
        calories_target: Goal-adjusted calorie target
    """

    profile_id: UUID
    user_id: str
    goal: str
    bmr: float
    tdee: float
    calories_target: float

    @staticmethod
    def create(
        profile_id: UUID, user_id: str, goal: str, bmr: float, tdee: float, calories_target: float
    ) -> "ProfileCreated":
        """Factory method to create event.

        Args:
            profile_id: Profile ID
            user_id: User ID
            goal: Goal value
            bmr: BMR value
            tdee: TDEE value
            calories_target: Calorie target

        Returns:
            ProfileCreated: New event
        """
        return ProfileCreated(
            event_id=DomainEvent._generate_event_id(),
            occurred_at=DomainEvent._now(),
            profile_id=profile_id,
            user_id=user_id,
            goal=goal,
            bmr=bmr,
            tdee=tdee,
            calories_target=calories_target,
        )
