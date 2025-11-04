"""Handler for MealConfirmed domain event.

Handles side effects when a meal confirmation is completed, such as:
- Structured logging for user feedback tracking
- Metrics for confirmation/rejection rates
- Analytics for ML model performance evaluation
"""

import logging

from domain.meal.core.events.meal_confirmed import MealConfirmed

logger = logging.getLogger(__name__)


class MealConfirmedHandler:
    """Handler for MealConfirmed domain events.

    Responsibilities:
    - Log meal confirmation events with user feedback
    - Track user acceptance/rejection rates
    - Enable ML model performance monitoring

    Side effects only - does NOT modify system state.
    """

    async def handle(self, event: MealConfirmed) -> None:
        """Handle MealConfirmed event.

        Performs read-only side effects:
        - Structured logging with confirmation details
        - Future: send metrics to monitoring system
        - Future: track confirmation rates for ML evaluation

        Args:
            event: MealConfirmed domain event

        Example:
            >>> handler = MealConfirmedHandler()
            >>> event = MealConfirmed.create(
            ...     meal_id=uuid4(),
            ...     user_id="user-123",
            ...     confirmed_entry_count=2,
            ...     rejected_entry_count=1
            ... )
            >>> await handler.handle(event)
            # Logs: "meal_confirmed" with structured extra fields
        """
        total_entries = event.confirmed_entry_count + event.rejected_entry_count
        acceptance_rate = event.confirmed_entry_count / total_entries if total_entries > 0 else 0.0

        logger.info(
            "meal_confirmed",
            extra={
                "event_type": "MealConfirmed",
                "event_id": str(event.event_id),
                "occurred_at": event.occurred_at.isoformat(),
                "meal_id": str(event.meal_id),
                "user_id": event.user_id,
                "confirmed_entry_count": event.confirmed_entry_count,
                "rejected_entry_count": event.rejected_entry_count,
                "total_entries": total_entries,
                "acceptance_rate": round(acceptance_rate, 2),
            },
        )

        # Future enhancement: send metrics to monitoring system
        # await self._metrics.gauge(
        #     "meal.confirmation_rate",
        #     acceptance_rate,
        #     tags={"user_id": event.user_id}
        # )

        # Future enhancement: track for ML model evaluation
        # await self._ml_tracker.record_user_feedback(
        #     meal_id=event.meal_id,
        #     acceptance_rate=acceptance_rate
        # )
