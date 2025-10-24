"""
In-memory idempotency cache implementation.

Simple in-memory cache for testing and development.
Production should use Redis or similar distributed cache.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)


class InMemoryIdempotencyCache:
    """In-memory implementation of idempotency cache.

    Stores meal IDs with expiration times to prevent duplicate operations.
    NOT suitable for production with multiple instances (use Redis instead).
    """

    def __init__(self) -> None:
        """Initialize empty cache."""
        # Storage: key -> (meal_id, expiration_time)
        self._cache: Dict[str, Tuple[UUID, datetime]] = {}
        logger.debug("InMemoryIdempotencyCache initialized")

    async def get(self, key: str) -> Optional[UUID]:
        """Get cached meal ID for an idempotency key.

        Args:
            key: The idempotency key

        Returns:
            The cached meal ID if found and not expired, None otherwise
        """
        if key not in self._cache:
            logger.debug(f"Cache miss for key: {key}")
            return None

        meal_id, expiration = self._cache[key]
        now = datetime.now(timezone.utc)

        if now > expiration:
            # Entry expired, remove it
            logger.debug(f"Cache entry expired for key: {key}")
            del self._cache[key]
            return None

        logger.debug(f"Cache hit for key: {key}, meal_id: {meal_id}")
        return meal_id

    async def set(self, key: str, meal_id: UUID, ttl_seconds: int = 3600) -> None:
        """Cache a meal ID for an idempotency key.

        Args:
            key: The idempotency key
            meal_id: The meal ID to cache
            ttl_seconds: Time-to-live in seconds (default: 1 hour)
        """
        expiration = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        self._cache[key] = (meal_id, expiration)
        logger.debug(
            f"Cached meal_id {meal_id} for key {key} with TTL {ttl_seconds}s"
        )

    async def exists(self, key: str) -> bool:
        """Check if an idempotency key exists in cache.

        Args:
            key: The idempotency key

        Returns:
            True if key exists and not expired, False otherwise
        """
        result = await self.get(key)
        return result is not None

    async def delete(self, key: str) -> None:
        """Delete an idempotency key from cache.

        Args:
            key: The idempotency key to delete
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Deleted cache entry for key: {key}")

    def clear(self) -> None:
        """Clear all cache entries (for testing)."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def cleanup_expired(self) -> int:
        """Remove all expired entries from cache.

        Returns:
            Number of expired entries removed
        """
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, (_, expiration) in self._cache.items() if now > expiration
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)
