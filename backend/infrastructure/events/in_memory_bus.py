"""In-memory event bus implementation.

Provides an in-memory implementation of IEventBus port for testing and simple applications.
Handlers are stored in memory and called synchronously in subscription order.
"""

import logging
from typing import Dict, List, Type, TypeVar, Callable, Awaitable, Any
from domain.meal.core.events.base import DomainEvent

logger = logging.getLogger(__name__)

TEvent = TypeVar("TEvent", bound=DomainEvent)


class InMemoryEventBus:
    """
    In-memory implementation of IEventBus port.

    This adapter provides a dictionary-based storage for event handlers,
    implementing the IEventBus port defined by the domain layer.

    Thread safety: NOT thread-safe (use locks if needed in production)
    Persistence: Handlers lost on process restart (in-memory only)
    Error handling: Failed handlers log errors but don't prevent other handlers

    Example:
        >>> bus = InMemoryEventBus()
        >>>
        >>> async def log_event(event: MealAnalyzed) -> None:
        ...     print(f"Meal analyzed: {event.meal_id}")
        >>>
        >>> bus.subscribe(MealAnalyzed, log_event)
        >>> await bus.publish(MealAnalyzed(...))
    """

    def __init__(self) -> None:
        """Initialize event bus with empty handler registry."""
        self._handlers: Dict[Type[DomainEvent], List[Callable[[Any], Awaitable[None]]]] = {}

    def subscribe(
        self,
        event_type: Type[TEvent],
        handler: Callable[[TEvent], Awaitable[None]],
    ) -> None:
        """
        Subscribe a handler to an event type.

        Args:
            event_type: Type of event to listen for
            handler: Async function to call when event is published

        Note:
            - Same handler can be subscribed multiple times (will be called multiple times)
            - Handlers are called in subscription order
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)

        logger.debug(
            "Handler subscribed",
            extra={
                "event_type": event_type.__name__,
                "handler": handler.__name__,
            },
        )

    async def publish(self, event: TEvent) -> None:
        """
        Publish an event to all subscribed handlers.

        Args:
            event: Domain event to publish

        Note:
            - Handlers are called in subscription order
            - If a handler fails, it logs an error but other handlers still execute
            - This ensures one failing handler doesn't prevent others from running
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            logger.debug(
                "No handlers for event",
                extra={"event_type": event_type.__name__},
            )
            return

        logger.info(
            "Publishing event",
            extra={
                "event_type": event_type.__name__,
                "event_id": event.event_id,
                "handler_count": len(handlers),
            },
        )

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                # Log error but don't prevent other handlers from running
                logger.error(
                    "Event handler failed",
                    extra={
                        "event_type": event_type.__name__,
                        "event_id": event.event_id,
                        "handler": handler.__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )

    def unsubscribe(
        self,
        event_type: Type[TEvent],
        handler: Callable[[TEvent], Awaitable[None]],
    ) -> bool:
        """
        Unsubscribe a handler from an event type.

        Args:
            event_type: Type of event
            handler: Handler to remove

        Returns:
            True if handler was found and removed, False otherwise

        Note:
            - If handler was subscribed multiple times, only first occurrence is removed
        """
        if event_type not in self._handlers:
            return False

        handlers = self._handlers[event_type]
        try:
            handlers.remove(handler)
            logger.debug(
                "Handler unsubscribed",
                extra={
                    "event_type": event_type.__name__,
                    "handler": handler.__name__,
                },
            )
            return True
        except ValueError:
            # Handler not in list
            return False

    def clear(self) -> None:
        """
        Clear all event subscriptions.

        Note: Utility method for testing - removes all handlers
        """
        self._handlers.clear()
        logger.debug("All event handlers cleared")

    def get_handler_count(self, event_type: Type[TEvent]) -> int:
        """
        Get number of handlers for an event type.

        Args:
            event_type: Type of event

        Returns:
            Number of handlers subscribed to event type

        Note: Utility method for testing/debugging
        """
        return len(self._handlers.get(event_type, []))
