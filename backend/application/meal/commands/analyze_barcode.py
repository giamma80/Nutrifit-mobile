"""Analyze meal barcode command and handler.

Handles barcode-based meal creation for packaged foods.
"""

from dataclasses import dataclass
from typing import Optional
import logging

from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_analyzed import MealAnalyzed
from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus
from ..orchestrators.barcode_orchestrator import BarcodeOrchestrator

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalyzeMealBarcodeCommand:
    """
    Command: Analyze meal from barcode.

    Creates a meal from a product barcode with specified quantity.
    Barcode products have 100% confidence (no AI guessing).

    Attributes:
        user_id: User ID who owns this meal
        barcode: Product barcode (EAN/UPC)
        quantity_g: Actual quantity consumed in grams
        meal_type: BREAKFAST | LUNCH | DINNER | SNACK
        idempotency_key: Optional key for idempotent processing
    """
    user_id: str
    barcode: str
    quantity_g: float
    meal_type: str = "SNACK"
    idempotency_key: Optional[str] = None


class AnalyzeMealBarcodeCommandHandler:
    """Handler for AnalyzeMealBarcodeCommand."""

    def __init__(
        self,
        orchestrator: BarcodeOrchestrator,
        repository: IMealRepository,
        event_bus: IEventBus
    ):
        """
        Initialize handler.

        Args:
            orchestrator: Barcode analysis orchestrator
            repository: Meal repository port
            event_bus: Event bus port
        """
        self._orchestrator = orchestrator
        self._repository = repository
        self._event_bus = event_bus

    async def handle(self, command: AnalyzeMealBarcodeCommand) -> Meal:
        """
        Execute barcode analysis command.

        Flow:
        1. Orchestrate barcode lookup + enrichment (via BarcodeOrchestrator)
        2. Persist analyzed meal
        3. Publish MealAnalyzed event

        Args:
            command: AnalyzeMealBarcodeCommand

        Returns:
            Analyzed Meal from barcode product

        Raises:
            ValueError: If barcode not found or invalid
            Exception: If orchestration or persistence fails

        Example:
            >>> handler = AnalyzeMealBarcodeCommandHandler(
            ...     orchestrator, repository, event_bus
            ... )
            >>> command = AnalyzeMealBarcodeCommand(
            ...     user_id="user123",
            ...     barcode="8001505005707",
            ...     quantity_g=150.0,
            ...     meal_type="SNACK"
            ... )
            >>> meal = await handler.handle(command)
            >>> meal.entries[0].confidence
            1.0
        """
        logger.info(
            "Analyzing meal barcode",
            extra={
                "user_id": command.user_id,
                "barcode": command.barcode,
                "quantity_g": command.quantity_g,
                "meal_type": command.meal_type,
                "idempotency_key": command.idempotency_key,
            },
        )

        # 1. Orchestrate barcode workflow (lookup + enrichment)
        meal = await self._orchestrator.analyze(
            user_id=command.user_id,
            barcode=command.barcode,
            quantity_g=command.quantity_g,
            meal_type=command.meal_type
        )

        # 2. Persist meal
        await self._repository.save(meal)

        # Extract product name from first entry
        product_name = meal.entries[0].display_name if meal.entries else "Unknown"

        logger.info(
            "Meal analyzed from barcode and persisted",
            extra={
                "meal_id": str(meal.id),
                "user_id": command.user_id,
                "product_name": product_name,
                "total_calories": meal.total_calories,
            },
        )

        # 3. Publish MealAnalyzed event
        # Barcode products always have confidence=1.0 (100%)
        event = MealAnalyzed.create(
            meal_id=meal.id,
            user_id=command.user_id,
            source="BARCODE",
            item_count=1,  # Barcode = single product
            average_confidence=1.0  # Barcode = 100% confidence
        )

        await self._event_bus.publish(event)

        return meal
