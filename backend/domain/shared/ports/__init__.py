"""Domain ports (interfaces for infrastructure adapters)."""

from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus

__all__ = [
    "IMealRepository",
    "IEventBus",
]
