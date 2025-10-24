"""Unit tests for InMemoryEventBus.

Tests focus on:
- Event bus initialization
- Handler subscription and unsubscription
- Event publishing to handlers
- Handler execution order
- Error handling (failed handlers don't block others)
- Multiple handlers for same event
- Edge cases

Note: These are UNIT tests for in-memory event bus.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from typing import List

from infrastructure.events.in_memory_bus import InMemoryEventBus
from domain.meal.core.events.meal_analyzed import MealAnalyzed
from domain.meal.core.events.meal_confirmed import MealConfirmed


@pytest.fixture
def event_bus() -> InMemoryEventBus:
    """Fixture providing clean InMemoryEventBus."""
    return InMemoryEventBus()


@pytest.fixture
def sample_meal_analyzed() -> MealAnalyzed:
    """Fixture providing sample MealAnalyzed event."""
    return MealAnalyzed.create(
        meal_id=uuid4(),
        user_id="user123",
        source="PHOTO",
        item_count=3,
        average_confidence=0.85,
    )


@pytest.fixture
def sample_meal_confirmed() -> MealConfirmed:
    """Fixture providing sample MealConfirmed event."""
    return MealConfirmed(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        meal_id=uuid4(),
        user_id="user123",
        confirmed_entry_count=2,
        rejected_entry_count=1,
    )


class TestEventBusInit:
    """Test event bus initialization."""

    def test_init(self) -> None:
        """Test event bus initializes with empty handlers."""
        bus = InMemoryEventBus()
        assert bus._handlers == {}


class TestSubscribe:
    """Test subscribe method."""

    @pytest.mark.asyncio
    async def test_subscribe_single_handler(self, event_bus: InMemoryEventBus) -> None:
        """Test subscribing a single handler."""
        calls: List[MealAnalyzed] = []

        async def handler(event: MealAnalyzed) -> None:
            calls.append(event)

        event_bus.subscribe(MealAnalyzed, handler)

        assert event_bus.get_handler_count(MealAnalyzed) == 1

    @pytest.mark.asyncio
    async def test_subscribe_multiple_handlers_same_event(
        self, event_bus: InMemoryEventBus
    ) -> None:
        """Test subscribing multiple handlers to same event."""
        calls1: List[MealAnalyzed] = []
        calls2: List[MealAnalyzed] = []

        async def handler1(event: MealAnalyzed) -> None:
            calls1.append(event)

        async def handler2(event: MealAnalyzed) -> None:
            calls2.append(event)

        event_bus.subscribe(MealAnalyzed, handler1)
        event_bus.subscribe(MealAnalyzed, handler2)

        assert event_bus.get_handler_count(MealAnalyzed) == 2

    @pytest.mark.asyncio
    async def test_subscribe_different_events(self, event_bus: InMemoryEventBus) -> None:
        """Test subscribing handlers to different events."""
        calls1: List[MealAnalyzed] = []
        calls2: List[MealConfirmed] = []

        async def handler1(event: MealAnalyzed) -> None:
            calls1.append(event)

        async def handler2(event: MealConfirmed) -> None:
            calls2.append(event)

        event_bus.subscribe(MealAnalyzed, handler1)
        event_bus.subscribe(MealConfirmed, handler2)

        assert event_bus.get_handler_count(MealAnalyzed) == 1
        assert event_bus.get_handler_count(MealConfirmed) == 1


class TestPublish:
    """Test publish method."""

    @pytest.mark.asyncio
    async def test_publish_calls_handler(
        self,
        event_bus: InMemoryEventBus,
        sample_meal_analyzed: MealAnalyzed,
    ) -> None:
        """Test publishing event calls subscribed handler."""
        calls: List[MealAnalyzed] = []

        async def handler(event: MealAnalyzed) -> None:
            calls.append(event)

        event_bus.subscribe(MealAnalyzed, handler)
        await event_bus.publish(sample_meal_analyzed)

        assert len(calls) == 1
        assert calls[0] == sample_meal_analyzed

    @pytest.mark.asyncio
    async def test_publish_calls_multiple_handlers(
        self,
        event_bus: InMemoryEventBus,
        sample_meal_analyzed: MealAnalyzed,
    ) -> None:
        """Test publishing event calls all subscribed handlers."""
        calls1: List[MealAnalyzed] = []
        calls2: List[MealAnalyzed] = []

        async def handler1(event: MealAnalyzed) -> None:
            calls1.append(event)

        async def handler2(event: MealAnalyzed) -> None:
            calls2.append(event)

        event_bus.subscribe(MealAnalyzed, handler1)
        event_bus.subscribe(MealAnalyzed, handler2)
        await event_bus.publish(sample_meal_analyzed)

        assert len(calls1) == 1
        assert len(calls2) == 1

    @pytest.mark.asyncio
    async def test_publish_handler_execution_order(
        self,
        event_bus: InMemoryEventBus,
        sample_meal_analyzed: MealAnalyzed,
    ) -> None:
        """Test handlers execute in subscription order."""
        execution_order: List[int] = []

        async def handler1(event: MealAnalyzed) -> None:
            execution_order.append(1)

        async def handler2(event: MealAnalyzed) -> None:
            execution_order.append(2)

        async def handler3(event: MealAnalyzed) -> None:
            execution_order.append(3)

        event_bus.subscribe(MealAnalyzed, handler1)
        event_bus.subscribe(MealAnalyzed, handler2)
        event_bus.subscribe(MealAnalyzed, handler3)
        await event_bus.publish(sample_meal_analyzed)

        assert execution_order == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_publish_no_handlers(
        self,
        event_bus: InMemoryEventBus,
        sample_meal_analyzed: MealAnalyzed,
    ) -> None:
        """Test publishing event with no handlers doesn't fail."""
        # Should not raise exception
        await event_bus.publish(sample_meal_analyzed)

    @pytest.mark.asyncio
    async def test_publish_only_matching_event_handlers_called(
        self,
        event_bus: InMemoryEventBus,
        sample_meal_analyzed: MealAnalyzed,
        sample_meal_confirmed: MealConfirmed,
    ) -> None:
        """Test only handlers for published event type are called."""
        analyzed_calls: List[MealAnalyzed] = []
        confirmed_calls: List[MealConfirmed] = []

        async def analyzed_handler(event: MealAnalyzed) -> None:
            analyzed_calls.append(event)

        async def confirmed_handler(event: MealConfirmed) -> None:
            confirmed_calls.append(event)

        event_bus.subscribe(MealAnalyzed, analyzed_handler)
        event_bus.subscribe(MealConfirmed, confirmed_handler)

        # Publish MealAnalyzed - only analyzed_handler should be called
        await event_bus.publish(sample_meal_analyzed)

        assert len(analyzed_calls) == 1
        assert len(confirmed_calls) == 0

    @pytest.mark.asyncio
    async def test_publish_failed_handler_doesnt_block_others(
        self,
        event_bus: InMemoryEventBus,
        sample_meal_analyzed: MealAnalyzed,
    ) -> None:
        """Test failed handler doesn't prevent other handlers from executing."""
        calls: List[str] = []

        async def failing_handler(event: MealAnalyzed) -> None:
            calls.append("failing")
            raise Exception("Handler failed")

        async def succeeding_handler(event: MealAnalyzed) -> None:
            calls.append("succeeding")

        event_bus.subscribe(MealAnalyzed, failing_handler)
        event_bus.subscribe(MealAnalyzed, succeeding_handler)
        await event_bus.publish(sample_meal_analyzed)

        # Both handlers should have been called
        assert "failing" in calls
        assert "succeeding" in calls


class TestUnsubscribe:
    """Test unsubscribe method."""

    @pytest.mark.asyncio
    async def test_unsubscribe_existing_handler(self, event_bus: InMemoryEventBus) -> None:
        """Test unsubscribing an existing handler."""

        async def handler(event: MealAnalyzed) -> None:
            pass

        event_bus.subscribe(MealAnalyzed, handler)
        result = event_bus.unsubscribe(MealAnalyzed, handler)

        assert result is True
        assert event_bus.get_handler_count(MealAnalyzed) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_non_existent_handler(self, event_bus: InMemoryEventBus) -> None:
        """Test unsubscribing non-existent handler returns False."""

        async def handler(event: MealAnalyzed) -> None:
            pass

        result = event_bus.unsubscribe(MealAnalyzed, handler)
        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe_one_of_multiple_handlers(self, event_bus: InMemoryEventBus) -> None:
        """Test unsubscribing one handler leaves others."""

        async def handler1(event: MealAnalyzed) -> None:
            pass

        async def handler2(event: MealAnalyzed) -> None:
            pass

        event_bus.subscribe(MealAnalyzed, handler1)
        event_bus.subscribe(MealAnalyzed, handler2)

        event_bus.unsubscribe(MealAnalyzed, handler1)

        assert event_bus.get_handler_count(MealAnalyzed) == 1

    @pytest.mark.asyncio
    async def test_unsubscribed_handler_not_called(
        self,
        event_bus: InMemoryEventBus,
        sample_meal_analyzed: MealAnalyzed,
    ) -> None:
        """Test unsubscribed handler is not called on publish."""
        calls: List[MealAnalyzed] = []

        async def handler(event: MealAnalyzed) -> None:
            calls.append(event)

        event_bus.subscribe(MealAnalyzed, handler)
        event_bus.unsubscribe(MealAnalyzed, handler)
        await event_bus.publish(sample_meal_analyzed)

        assert len(calls) == 0


class TestClear:
    """Test clear method."""

    @pytest.mark.asyncio
    async def test_clear_removes_all_handlers(self, event_bus: InMemoryEventBus) -> None:
        """Test clear removes all handlers for all events."""

        async def handler1(event: MealAnalyzed) -> None:
            pass

        async def handler2(event: MealConfirmed) -> None:
            pass

        event_bus.subscribe(MealAnalyzed, handler1)
        event_bus.subscribe(MealConfirmed, handler2)

        event_bus.clear()

        assert event_bus.get_handler_count(MealAnalyzed) == 0
        assert event_bus.get_handler_count(MealConfirmed) == 0

    @pytest.mark.asyncio
    async def test_clear_prevents_handler_execution(
        self,
        event_bus: InMemoryEventBus,
        sample_meal_analyzed: MealAnalyzed,
    ) -> None:
        """Test handlers don't execute after clear."""
        calls: List[MealAnalyzed] = []

        async def handler(event: MealAnalyzed) -> None:
            calls.append(event)

        event_bus.subscribe(MealAnalyzed, handler)
        event_bus.clear()
        await event_bus.publish(sample_meal_analyzed)

        assert len(calls) == 0
