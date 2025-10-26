"""Analyze meal photo command and handler.

This implements step 1 of the 2-step meal creation flow:
1. analyzeMealPhoto → creates meal in "analyzed" state
2. confirmMealAnalysis → user confirms/rejects items
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import logging

from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_analyzed import MealAnalyzed
from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus
from domain.shared.ports.idempotency_cache import IIdempotencyCache
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
        timestamp: Meal timestamp (defaults to current time if not provided)
        idempotency_key: Optional key for idempotent processing
    """

    user_id: str
    photo_url: str
    dish_hint: Optional[str] = None
    meal_type: str = "SNACK"
    timestamp: Optional[datetime] = None
    idempotency_key: Optional[str] = None


class AnalyzeMealPhotoCommandHandler:
    """Handler for AnalyzeMealPhotoCommand."""

    def __init__(
        self,
        orchestrator: PhotoOrchestrator,
        repository: IMealRepository,
        event_bus: IEventBus,
        idempotency_cache: IIdempotencyCache,
    ):
        """
        Initialize handler.

        Args:
            orchestrator: Photo analysis orchestrator
            repository: Meal repository port
            event_bus: Event bus port
            idempotency_cache: Idempotency cache port
        """
        self._orchestrator = orchestrator
        self._repository = repository
        self._event_bus = event_bus
        self._idempotency_cache = idempotency_cache

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

        # Check idempotency cache if key provided
        if command.idempotency_key:
            cached_meal_id = await self._idempotency_cache.get(command.idempotency_key)
            if cached_meal_id:
                logger.info(
                    "Idempotency cache hit - returning existing meal",
                    extra={
                        "idempotency_key": command.idempotency_key,
                        "cached_meal_id": str(cached_meal_id),
                    },
                )
                meal = await self._repository.get_by_id(cached_meal_id, command.user_id)
                if meal:
                    return meal
                # If meal not found in repository, proceed with analysis
                logger.warning(
                    "Cached meal not found in repository, re-analyzing",
                    extra={"cached_meal_id": str(cached_meal_id)},
                )

        # 1. Orchestrate analysis workflow (recognition + enrichment)
        meal = await self._orchestrator.analyze(
            user_id=command.user_id,
            photo_url=command.photo_url,
            dish_hint=command.dish_hint,
            meal_type=command.meal_type,
            timestamp=command.timestamp,
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
            average_confidence=meal.average_confidence(),
        )

        await self._event_bus.publish(event)

        # 4. Cache meal ID for idempotency (1 hour TTL)
        if command.idempotency_key:
            await self._idempotency_cache.set(command.idempotency_key, meal.id, ttl_seconds=3600)
            logger.debug(
                "Cached meal ID for idempotency",
                extra={
                    "idempotency_key": command.idempotency_key,
                    "meal_id": str(meal.id),
                },
            )

        return meal
