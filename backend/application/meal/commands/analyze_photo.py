"""Analyze meal photo command and handler.

This implements step 1 of the 2-step meal creation flow:
1. analyzeMealPhoto → creates meal in "analyzed" state
2. confirmMealAnalysis → user confirms/rejects items
"""

from dataclasses import dataclass
from typing import Optional
import logging

from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_analyzed import MealAnalyzed
from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus
from ..orchestrators.photo_orchestrator import PhotoOrchestrator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalyzeMealPhotoCommand:
    """
    Command: Analyze meal from photo.

    This creates a meal in "analyzed" state with AI-recognized items.
    User must then confirm which items to keep via ConfirmAnalysisCommand.

    Attributes:
        user_id: User ID who owns this meal
        photo_url: URL of the meal photo
        dish_hint: Optional hint about the dish
        meal_type: BREAKFAST | LUNCH | DINNER | SNACK
        idempotency_key: Optional key for idempotent processing
    """
    user_id: str
    photo_url: str
    dish_hint: Optional[str] = None
    meal_type: str = "SNACK"
    idempotency_key: Optional[str] = None


class AnalyzeMealPhotoCommandHandler:
    """Handler for AnalyzeMealPhotoCommand."""

    def __init__(
        self,
        orchestrator: PhotoOrchestrator,
        repository: IMealRepository,
        event_bus: IEventBus
    ):
        """
        Initialize handler.

        Args:
            orchestrator: Photo analysis orchestrator
            repository: Meal repository port
            event_bus: Event bus port
        """
        self._orchestrator = orchestrator
        self._repository = repository
        self._event_bus = event_bus

    async def handle(self, command: AnalyzeMealPhotoCommand) -> Meal:
        """
        Execute photo analysis command.

        Flow:
        1. Orchestrate recognition + enrichment (via PhotoOrchestrator)
        2. Persist analyzed meal
        3. Publish MealAnalyzed event

        Args:
            command: AnalyzeMealPhotoCommand

        Returns:
            Analyzed Meal (not yet confirmed by user)

        Raises:
            ValueError: If photo analysis fails
            Exception: If orchestration or persistence fails

        Example:
            >>> handler = AnalyzeMealPhotoCommandHandler(
            ...     orchestrator, repository, event_bus
            ... )
            >>> command = AnalyzeMealPhotoCommand(
            ...     user_id="user123",
            ...     photo_url="https://example.com/pasta.jpg",
            ...     meal_type="LUNCH"
            ... )
            >>> meal = await handler.handle(command)
            >>> len(meal.entries) >= 1
            True
        """
        logger.info(
            "Analyzing meal photo",
            extra={
                "user_id": command.user_id,
                "photo_url": command.photo_url,
                "meal_type": command.meal_type,
                "dish_hint": command.dish_hint,
                "idempotency_key": command.idempotency_key,
            },
        )

        # 1. Orchestrate analysis workflow (recognition + enrichment)
        meal = await self._orchestrator.analyze(
            user_id=command.user_id,
            photo_url=command.photo_url,
            dish_hint=command.dish_hint,
            meal_type=command.meal_type
        )

        # 2. Persist meal
        await self._repository.save(meal)

        logger.info(
            "Meal analyzed and persisted",
            extra={
                "meal_id": str(meal.id),
                "user_id": command.user_id,
                "entry_count": len(meal.entries),
                "total_calories": meal.total_calories,
                "average_confidence": meal.average_confidence(),
            },
        )

        # 3. Publish MealAnalyzed event
        event = MealAnalyzed.create(
            meal_id=meal.id,
            user_id=command.user_id,
            source="PHOTO",
            item_count=len(meal.entries),
            average_confidence=meal.average_confidence()
        )

        await self._event_bus.publish(event)

        return meal
