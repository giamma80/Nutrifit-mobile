"""RecordProgressCommand - record weight/progress measurement."""

from dataclasses import dataclass
from datetime import date as DateType
from typing import Optional

from domain.nutritional_profile.core.entities.progress_record import (
    ProgressRecord,
)
from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId


@dataclass(frozen=True)
class RecordProgressCommand:
    """Command to record a progress measurement.

    Attributes:
        profile_id: Profile to add measurement to
        measurement_date: Date of measurement
        weight: Current weight in kg
        consumed_calories: Optional consumed calories for the day
        consumed_protein_g: Optional consumed protein in grams
        consumed_carbs_g: Optional consumed carbs in grams
        consumed_fat_g: Optional consumed fat in grams
        calories_burned_bmr: Optional BMR calories burned
        calories_burned_active: Optional active calories burned
        notes: Optional notes about measurement
    """

    profile_id: ProfileId
    measurement_date: DateType
    weight: float
    consumed_calories: Optional[float] = None
    consumed_protein_g: Optional[float] = None
    consumed_carbs_g: Optional[float] = None
    consumed_fat_g: Optional[float] = None
    calories_burned_bmr: Optional[float] = None
    calories_burned_active: Optional[float] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class RecordProgressResult:
    """Result of progress recording.

    Attributes:
        progress_record: Newly created progress record
        weight_delta: Weight change since last measurement
        days_tracked: Total number of measurements
    """

    progress_record: ProgressRecord
    weight_delta: float
    days_tracked: int


class RecordProgressHandler:
    """Handler for RecordProgressCommand.

    Records progress by:
    1. Loading profile from repository
    2. Adding progress record to profile
    3. Persisting updated profile
    """

    def __init__(self, repository: IProfileRepository):
        self._repository = repository

    async def handle(self, command: RecordProgressCommand) -> RecordProgressResult:  # noqa: E501
        """
        Handle progress recording command.

        Args:
            command: RecordProgressCommand with measurement data

        Returns:
            RecordProgressResult with created record and statistics

        Raises:
            ProfileNotFoundError: If profile doesn't exist
            InvalidProgressRecordError: If record validation fails
        """
        # Step 1: Load existing profile
        profile = await self._repository.find_by_id(command.profile_id)
        if profile is None:
            from domain.nutritional_profile.core.exceptions.domain_errors import (  # noqa: E501
                ProfileNotFoundError,
            )

            raise ProfileNotFoundError(f"Profile {command.profile_id} not found")  # noqa: E501

        # Step 2: Record progress
        record = profile.record_progress(
            measurement_date=command.measurement_date,
            weight=command.weight,
            consumed_calories=command.consumed_calories,
            notes=command.notes or "",
        )

        # Step 2b: Update macros if provided
        if command.consumed_protein_g is not None:
            record.update_consumed_macros(
                protein_g=command.consumed_protein_g,
                carbs_g=command.consumed_carbs_g or 0.0,
                fat_g=command.consumed_fat_g or 0.0,
            )

        # Step 2c: Update calories burned if provided
        if command.calories_burned_bmr is not None:
            record.update_burned_calories(
                bmr_calories=command.calories_burned_bmr,
                active_calories=command.calories_burned_active or 0.0,
            )

        # Step 3: Persist updated profile
        await self._repository.save(profile)

        # Get the newly created record (last in history)
        new_record = profile.progress_history[-1]

        # Calculate statistics
        # Weight delta: first to latest measurement
        if len(profile.progress_history) >= 2:
            first_record = profile.progress_history[0]
            weight_delta = new_record.weight - first_record.weight
        else:
            weight_delta = 0.0

        days_tracked = len(profile.progress_history)

        return RecordProgressResult(
            progress_record=new_record,
            weight_delta=weight_delta,
            days_tracked=days_tracked,
        )
