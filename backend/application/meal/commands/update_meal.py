"""Update meal command and handler.

Allows updating meal properties like meal_type, timestamp, notes, etc.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from uuid import UUID
import logging

from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_updated import MealUpdated
from domain.meal.core.exceptions.domain_errors import MealNotFoundError
from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpdateMealCommand:
    """
    Command: Update meal fields.

    Allows updating mutable meal properties. Common updates:
    - meal_type (BREAKFAST, LUNCH, DINNER, SNACK)
    - timestamp (meal time)
    - notes (user notes)

    Attributes:
        meal_id: Meal to update
        user_id: User ID (for authorization)
        updates: Dictionary of field name → new value
    """
    meal_id: UUID
    user_id: str
    updates: Dict[str, Any]


class UpdateMealCommandHandler:
    """Handler for UpdateMealCommand."""

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

    async def handle(self, command: UpdateMealCommand) -> Meal:
        """
        Execute update command.

        Flow:
        1. Load meal from repository
        2. Verify user ownership
        3. Apply updates to allowed fields
        4. Validate meal invariants
        5. Persist updated meal
        6. Publish MealUpdated event

        Allowed updates:
        - meal_type
        - timestamp
        - notes

        Args:
            command: UpdateMealCommand

        Returns:
            Updated Meal

        Raises:
            MealNotFoundError: If meal doesn't exist
            PermissionError: If user doesn't own the meal
            ValueError: If updates violate domain invariants
        """
        logger.info(
            "Updating meal",
            extra={
                "meal_id": str(command.meal_id),
                "user_id": command.user_id,
                "update_fields": list(command.updates.keys()),
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

        # 3. Apply updates to allowed fields
        updated_fields: List[str] = []

        # Allowed mutable fields
        allowed_fields = {"meal_type", "timestamp", "notes"}

        for field, value in command.updates.items():
            if field not in allowed_fields:
                logger.warning(
                    "Field not allowed for update",
                    extra={
                        "field": field,
                        "allowed_fields": list(allowed_fields),
                    },
                )
                continue

            if hasattr(meal, field):
                setattr(meal, field, value)
                updated_fields.append(field)
                logger.debug(
                    "Field updated",
                    extra={
                        "field": field,
                        "new_value": str(value),
                    },
                )
            else:
                logger.warning(
                    "Field not found on meal entity",
                    extra={"field": field},
                )

        # 4. Validate invariants
        if updated_fields:
            meal.validate_invariants()

        # 5. Persist updated meal
        await self._repository.save(meal)

        logger.info(
            "Meal updated",
            extra={
                "meal_id": str(meal.id),
                "updated_fields": updated_fields,
            },
        )

        # 6. Publish MealUpdated event (only if something was actually updated)
        if updated_fields:
            event = MealUpdated.create(
                meal_id=meal.id,
                user_id=command.user_id,
                updated_fields=updated_fields,
            )

            await self._event_bus.publish(event)

        return meal
