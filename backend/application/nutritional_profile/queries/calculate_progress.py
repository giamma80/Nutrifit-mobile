"""CalculateProgressQuery - calculate progress statistics."""

from dataclasses import dataclass
from datetime import date as DateType
from typing import Optional

from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId


@dataclass(frozen=True)
class ProgressStatistics:
    """Progress statistics over a date range.

    Attributes:
        weight_delta: Weight change (kg) from start to end
        target_weight_delta: Expected weight change based on goal
        average_daily_calories: Average consumed calories per day
        days_on_track: Number of days within calorie target
        total_measurements: Total number of measurements in range
        adherence_rate: Percentage of days on track (0-100)
    """

    weight_delta: float
    target_weight_delta: float
    average_daily_calories: float
    days_on_track: int
    total_measurements: int
    adherence_rate: float


@dataclass(frozen=True)
class CalculateProgressQuery:
    """Query to calculate progress statistics.

    Attributes:
        profile_id: Profile identifier
        start_date: Start of date range
        end_date: End of date range
    """

    profile_id: ProfileId
    start_date: DateType
    end_date: DateType


class CalculateProgressQueryHandler:
    """Handler for CalculateProgressQuery.

    Calculates progress statistics using profile analytics methods.
    """

    def __init__(self, repository: IProfileRepository):
        self._repository = repository

    async def handle(self, query: CalculateProgressQuery) -> Optional[ProgressStatistics]:
        """
        Handle progress calculation query.

        Args:
            query: CalculateProgressQuery with date range

        Returns:
            Optional[ProgressStatistics]: Statistics if profile found,
                                         None otherwise
        """
        # Load profile
        profile = await self._repository.find_by_id(query.profile_id)
        if profile is None:
            return None

        # Calculate number of days in range
        days_in_range = (query.end_date - query.start_date).days + 1

        # Calculate statistics using domain methods
        weight_delta = profile.calculate_weight_delta(
            start_date=query.start_date,
            end_date=query.end_date,
        )

        target_weight_delta = profile.calculate_target_weight_delta(days=days_in_range)

        avg_calories = profile.average_daily_calories(
            start_date=query.start_date,
            end_date=query.end_date,
        )

        days_on_track = profile.days_on_track(
            start_date=query.start_date,
            end_date=query.end_date,
        )

        # Get total measurements in range
        progress_range = profile.get_progress_range(
            start_date=query.start_date,
            end_date=query.end_date,
        )
        total_measurements = len(progress_range)

        # Calculate adherence rate
        adherence_rate = (
            (days_on_track / total_measurements * 100) if total_measurements > 0 else 0.0
        )

        return ProgressStatistics(
            weight_delta=weight_delta or 0.0,
            target_weight_delta=target_weight_delta or 0.0,
            average_daily_calories=avg_calories or 0.0,
            days_on_track=days_on_track,
            total_measurements=total_measurements,
            adherence_rate=adherence_rate,
        )
