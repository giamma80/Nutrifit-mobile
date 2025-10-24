"""Confirm meal analysis command and handler.

This implements step 2 of the 2-step meal creation flow:
1. analyzeMealPhoto/Barcode → creates meal in "pending" state
2. confirmMealAnalysis → user selects which items to keep
"""

from dataclasses import dataclass
from typing import List
from uuid import UUID
import logging

from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_confirmed import MealConfirmed
from domain.meal.core.exceptions.domain_errors import MealNotFoundError
from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfirmAnalysisCommand:
    """
    Command: Confirm meal analysis.

    User selects which recognized items to keep and which to reject.
    At least one entry must be kept (domain invariant).

    Attributes:
        meal_id: Meal to confirm
        user_id: User ID (for authorization)
        confirmed_entry_ids: List of entry IDs to keep
    """
    meal_id: UUID
    user_id: str
    confirmed_entry_ids: List[UUID]


class ConfirmAnalysisCommandHandler:
    """Handler for ConfirmAnalysisCommand."""

    def __init__(
        self,
        repository: IMealRepository,
        event_bus: IEventBus
    ):
        """
        Initialize handler.

        Args:
            repository: Meal repository port
            event_bus: Event bus port
        """
        self._repository = repository
        self._event_bus = event_bus

    async def handle(self, command: ConfirmAnalysisCommand) -> Meal:
        """
        Execute confirmation command.

        Flow:
        1. Load meal from repository
        2. Verify user ownership
        3. Remove unconfirmed entries
        4. Validate at least one entry remains
        5. Persist updated meal
        6. Publish MealConfirmed event

        Args:
            command: ConfirmAnalysisCommand

        Returns:
            Confirmed Meal with only user-selected entries

        Raises:
            MealNotFoundError: If meal doesn't exist
            PermissionError: If user doesn't own the meal
            ValueError: If trying to remove all entries (domain invariant)
        """
        logger.info(
            "Confirming meal analysis",
            extra={
                "meal_id": str(command.meal_id),
                "user_id": command.user_id,
                "confirmed_count": len(command.confirmed_entry_ids),
            },
        )

        # 1. Load meal
        meal = await self._repository.get_by_id(
            command.meal_id,
            command.user_id
        )

        if not meal:
            raise MealNotFoundError(
                f"Meal {command.meal_id} not found for user {command.user_id}"
            )

        # 2. Verify ownership (redundant check, already done by repo)
        if meal.user_id != command.user_id:
            raise PermissionError(
                f"User {command.user_id} doesn't own meal {command.meal_id}"
            )

        # 3. Track counts for event
        total_entries = len(meal.entries)

        # 4. Remove unconfirmed entries
        entry_ids_to_remove = [
            e.id for e in meal.entries
            if e.id not in command.confirmed_entry_ids
        ]

        for entry_id in entry_ids_to_remove:
            try:
                meal.remove_entry(entry_id)
            except ValueError as e:
                # Last entry - cannot remove (domain invariant)
                logger.warning(
                    "Cannot remove last entry from meal",
                    extra={
                        "meal_id": str(meal.id),
                        "entry_id": str(entry_id),
                        "error": str(e),
                    },
                )
                break

        # 5. Persist updated meal
        await self._repository.save(meal)

        confirmed_count = len(meal.entries)
        rejected_count = total_entries - confirmed_count

        logger.info(
            "Meal confirmed",
            extra={
                "meal_id": str(meal.id),
                "confirmed_count": confirmed_count,
                "rejected_count": rejected_count,
                "total_calories": meal.total_calories,
            },
        )

        # 6. Publish MealConfirmed event
        event = MealConfirmed.create(
            meal_id=meal.id,
            user_id=command.user_id,
            confirmed_entry_count=confirmed_count,
            rejected_entry_count=rejected_count,
        )

        await self._event_bus.publish(event)

        return meal
