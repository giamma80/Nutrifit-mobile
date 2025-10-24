"""Event bus port (interface).

Defines contract for event publishing and subscription.
Follows the Dependency Inversion Principle: domain defines the port,
infrastructure provides the implementation.
"""

from typing import Protocol, Callable, Awaitable, Type, TypeVar
from domain.meal.core.events.base import DomainEvent

# Type variable for domain events
TEvent = TypeVar('TEvent', bound=DomainEvent)

# Event handler type: async function that takes an event and returns None
EventHandler = Callable[[TEvent], Awaitable[None]]


class IEventBus(Protocol):
    """
    Interface for event publishing and subscription.

    This port defines the contract that infrastructure adapters must implement
    to provide event bus functionality. Examples of implementations:
    - In-memory event bus (for testing/simple apps)
    - RabbitMQ event bus (for distributed systems)
    - Redis event bus (for pub/sub)

    Example implementation (infrastructure layer):
        >>> class InMemoryEventBus:
        ...     def __init__(self) -> None:
        ...         self._handlers: Dict[Type, List[EventHandler]] = {}
        ...
        ...     def subscribe(
        ...         self,
        ...         event_type: Type[TEvent],
        ...         handler: EventHandler[TEvent]
        ...     ) -> None:
        ...         if event_type not in self._handlers:
        ...             self._handlers[event_type] = []
        ...         self._handlers[event_type].append(handler)
        ...
        ...     async def publish(self, event: TEvent) -> None:
        ...         handlers = self._handlers.get(type(event), [])
        ...         for handler in handlers:
        ...             await handler(event)

    Example usage (application layer):
        >>> # Subscribe to events
        >>> async def on_meal_analyzed(event: MealAnalyzed) -> None:
        ...     print(f"Meal {event.meal_id} analyzed")
        ...
        >>> event_bus.subscribe(MealAnalyzed, on_meal_analyzed)
        ...
        >>> # Publish events
        >>> event = MealAnalyzed(...)
        >>> await event_bus.publish(event)
    """

    def subscribe(
        self,
        event_type: Type[TEvent],
        handler: EventHandler[TEvent],
    ) -> None:
        """
        Subscribe a handler to an event type.

        Args:
            event_type: Type of event to listen for (e.g., MealAnalyzed)
            handler: Async function to call when event is published

        Example:
            >>> async def log_meal_analyzed(event: MealAnalyzed) -> None:
            ...     logger.info(f"Meal analyzed: {event.meal_id}")
            ...
            >>> event_bus.subscribe(MealAnalyzed, log_meal_analyzed)
        """
        ...

    async def publish(self, event: TEvent) -> None:
        """
        Publish an event to all subscribed handlers.

        Args:
            event: Domain event to publish

        Note:
            - Handlers are called in subscription order
            - If a handler fails, other handlers still execute
            - Failed handlers should log errors but not raise

        Example:
            >>> event = MealAnalyzed.create(
            ...     meal_id=uuid4(),
            ...     user_id="user123",
            ...     source="PHOTO",
            ...     item_count=3,
            ...     average_confidence=0.85
            ... )
            >>> await event_bus.publish(event)
        """
        ...

    def unsubscribe(
        self,
        event_type: Type[TEvent],
        handler: EventHandler[TEvent],
    ) -> bool:
        """
        Unsubscribe a handler from an event type.

        Args:
            event_type: Type of event
            handler: Handler to remove

        Returns:
            True if handler was found and removed, False otherwise

        Example:
            >>> removed = event_bus.unsubscribe(MealAnalyzed, log_meal_analyzed)
            >>> if removed:
            ...     print("Handler unsubscribed")
        """
        ...

    def clear(self) -> None:
        """
        Clear all event subscriptions.

        Note: Utility method for testing - not always part of production implementations

        Example:
            >>> event_bus.clear()
            >>> # All handlers removed
        """
        ...
