"""Delete meal command and handler.

Allows users to delete their meals. Implements authorization checks
to ensure users can only delete their own meals.
"""

from dataclasses import dataclass
from uuid import UUID
import logging

from domain.meal.core.events.meal_deleted import MealDeleted
from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeleteMealCommand:
    """
    Command: Delete meal.

    Soft delete - the meal is removed from user's view but may be
    retained for audit purposes.

    Attributes:
        meal_id: Meal to delete
        user_id: User ID (for authorization)
    """
    meal_id: UUID
    user_id: str


class DeleteMealCommandHandler:
    """Handler for DeleteMealCommand."""

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

    async def handle(self, command: DeleteMealCommand) -> bool:
        """
        Execute delete command.

        Flow:
        1. Verify meal exists and user owns it
        2. Delete meal from repository
        3. Publish MealDeleted event if successful

        Args:
            command: DeleteMealCommand

        Returns:
            True if deleted successfully, False if meal not found

        Raises:
            PermissionError: If user doesn't own the meal
        """
        logger.info(
            "Deleting meal",
            extra={
                "meal_id": str(command.meal_id),
                "user_id": command.user_id,
            },
        )

        # 1. Verify ownership before deletion
        meal = await self._repository.get_by_id(
            command.meal_id,
            command.user_id
        )

        if not meal:
            logger.info(
                "Meal not found for deletion",
                extra={
                    "meal_id": str(command.meal_id),
                    "user_id": command.user_id,
                },
            )
            return False

        # 2. Verify ownership (redundant check, already done by repo)
        if meal.user_id != command.user_id:
            raise PermissionError(
                f"User {command.user_id} doesn't own meal {command.meal_id}"
            )

        # 3. Delete from repository
        deleted = await self._repository.delete(
            command.meal_id,
            command.user_id
        )

        if deleted:
            logger.info(
                "Meal deleted",
                extra={"meal_id": str(command.meal_id)},
            )

            # 4. Publish MealDeleted event
            event = MealDeleted.create(
                meal_id=command.meal_id,
                user_id=command.user_id,
            )

            await self._event_bus.publish(event)
        else:
            logger.warning(
                "Meal deletion failed",
                extra={"meal_id": str(command.meal_id)},
            )

        return deleted
