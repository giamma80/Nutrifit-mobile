"""
Idempotency cache port.

This port defines the contract for caching command results to ensure idempotent operations.
Used primarily for commands that can be retried (HTTP requests, network failures, etc.).
"""

from typing import Optional, Protocol
from uuid import UUID


class IIdempotencyCache(Protocol):
    """Port for idempotency cache implementation.

    Ensures commands can be safely retried without creating duplicate resources.
    Implementations should provide TTL support to prevent infinite cache growth.
    """

    async def get(self, key: str) -> Optional[UUID]:
        """Get cached meal ID for an idempotency key.

        Args:
            key: The idempotency key (typically a UUID string)

        Returns:
            The cached meal ID if found, None otherwise
        """
        ...

    async def set(self, key: str, meal_id: UUID, ttl_seconds: int = 3600) -> None:
        """Cache a meal ID for an idempotency key.

        Args:
            key: The idempotency key
            meal_id: The meal ID to cache
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
        """
        ...

    async def exists(self, key: str) -> bool:
        """Check if an idempotency key exists in cache.

        Args:
            key: The idempotency key

        Returns:
            True if key exists, False otherwise
        """
        ...

    async def delete(self, key: str) -> None:
        """Delete an idempotency key from cache.

        Args:
            key: The idempotency key to delete
        """
        ...
