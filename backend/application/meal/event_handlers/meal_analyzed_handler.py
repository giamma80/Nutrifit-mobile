"""Handler for MealAnalyzed domain event.

Handles side effects when a meal is analyzed, such as:
- Structured logging for observability
- Metrics/telemetry for monitoring
- Analytics tracking for ML feedback loop
"""

import logging

from domain.meal.core.events.meal_analyzed import MealAnalyzed

logger = logging.getLogger(__name__)


class MealAnalyzedHandler:
    """Handler for MealAnalyzed domain events.

    Responsibilities:
    - Log meal analysis events with structured data
    - Track analysis metrics (source, confidence, item count)
    - Enable observability and debugging

    Side effects only - does NOT modify system state.
    """

    async def handle(self, event: MealAnalyzed) -> None:
        """Handle MealAnalyzed event.

        Performs read-only side effects:
        - Structured logging with event details
        - Future: send metrics to monitoring system
        - Future: track confidence scores for ML feedback

        Args:
            event: MealAnalyzed domain event

        Example:
            >>> handler = MealAnalyzedHandler()
            >>> event = MealAnalyzed.create(
            ...     meal_id=uuid4(),
            ...     user_id="user-123",
            ...     source="PHOTO",
            ...     item_count=3,
            ...     average_confidence=0.85
            ... )
            >>> await handler.handle(event)
            # Logs: "meal_analyzed" with structured extra fields
        """
        logger.info(
            "meal_analyzed",
            extra={
                "event_type": "MealAnalyzed",
                "event_id": str(event.event_id),
                "occurred_at": event.occurred_at.isoformat(),
                "meal_id": str(event.meal_id),
                "user_id": event.user_id,
                "source": event.source,
                "item_count": event.item_count,
                "average_confidence": event.average_confidence,
            },
        )

        # Future enhancement: send metrics to monitoring system
        # await self._metrics.increment(
        #     "meal.analyzed",
        #     tags={"source": event.source}
        # )

        # Future enhancement: track confidence for ML feedback
        # await self._ml_tracker.record_confidence(
        #     source=event.source,
        #     confidence=event.average_confidence
        # )
