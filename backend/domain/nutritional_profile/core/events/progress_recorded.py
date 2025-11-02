"""ProgressRecorded domain event."""

from dataclasses import dataclass
from datetime import date
from typing import Optional
from uuid import UUID

from .base import DomainEvent


@dataclass(frozen=True)
class ProgressRecorded(DomainEvent):
    """Event emitted when progress measurement is recorded.

    Attributes:
        profile_id: ID of profile
        record_id: ID of created progress record
        measurement_date: Date of measurement
        weight: Weight in kg
        consumed_calories: Optional calories consumed
    """

    profile_id: UUID
    record_id: UUID
    measurement_date: date
    weight: float
    consumed_calories: Optional[float]

    @staticmethod
    def create(
        profile_id: UUID,
        record_id: UUID,
        measurement_date: date,
        weight: float,
        consumed_calories: Optional[float] = None,
    ) -> "ProgressRecorded":
        """Factory method to create event.

        Args:
            profile_id: Profile ID
            record_id: Progress record ID
            measurement_date: Measurement date
            weight: Weight in kg
            consumed_calories: Optional calories

        Returns:
            ProgressRecorded: New event
        """
        return ProgressRecorded(
            event_id=DomainEvent._generate_event_id(),
            occurred_at=DomainEvent._now(),
            profile_id=profile_id,
            record_id=record_id,
            measurement_date=measurement_date,
            weight=weight,
            consumed_calories=consumed_calories,
        )
