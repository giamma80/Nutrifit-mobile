"""Domain ports (interfaces for infrastructure adapters)."""

from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus
from domain.shared.ports.idempotency_cache import IIdempotencyCache

__all__ = [
    "IMealRepository",
    "IEventBus",
    "IIdempotencyCache",
]
