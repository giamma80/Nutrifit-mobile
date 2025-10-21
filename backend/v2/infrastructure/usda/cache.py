"""
USDA data cache with TTL support.

Caches USDA API responses to reduce API calls.
"""

import time
from typing import Optional

import structlog

from backend.v2.domain.meal.nutrition.usda_models import (
    USDACacheEntry,
    USDAFoodItem,
)
from backend.v2.domain.shared.value_objects import Barcode

logger = structlog.get_logger(__name__)


class USDACache:
    """In-memory USDA data cache with TTL."""

    def __init__(self, default_ttl_seconds: int = 604800) -> None:
        """Initialize cache.

        Args:
            default_ttl_seconds: Cache TTL (default 7 days)
        """
        self.default_ttl = default_ttl_seconds
        self._cache: dict[str, USDACacheEntry] = {}

    def _make_key(self, prefix: str, value: str) -> str:
        """Generate cache key.

        Args:
            prefix: Key prefix (e.g., 'barcode', 'description')
            value: Key value

        Returns:
            Cache key string
        """
        return f"{prefix}:{value}"

    def get_by_barcode(self, barcode: Barcode) -> Optional[USDAFoodItem]:
        """Get cached food item by barcode.

        Args:
            barcode: Product barcode

        Returns:
            Cached food item or None

        Example:
            >>> cache = USDACache()
            >>> barcode = Barcode(value="3017620422003")
            >>> result = cache.get_by_barcode(barcode)
            >>> assert result is None  # Cache is empty
        """
        key = self._make_key("barcode", barcode.value)
        entry = self._cache.get(key)

        if entry is None:
            logger.debug("Cache miss", key=key)
            return None

        if entry.is_expired():
            logger.debug("Cache expired", key=key)
            del self._cache[key]
            return None

        logger.debug("Cache hit", key=key)
        return entry.food_item

    def set_by_barcode(self, barcode: Barcode, food_item: USDAFoodItem) -> None:
        """Cache food item by barcode.

        Args:
            barcode: Product barcode
            food_item: USDA food item to cache
        """
        key = self._make_key("barcode", barcode.value)
        expires_at = time.time() + self.default_ttl

        entry = USDACacheEntry(key=key, food_item=food_item, expires_at=expires_at)

        self._cache[key] = entry
        logger.debug(
            "Cached item",
            key=key,
            ttl=self.default_ttl,
        )

    def get_by_description(self, description: str) -> Optional[USDAFoodItem]:
        """Get cached food item by description.

        Args:
            description: Food description

        Returns:
            Cached food item or None
        """
        key = self._make_key("desc", description.lower())
        entry = self._cache.get(key)

        if entry is None:
            return None

        if entry.is_expired():
            del self._cache[key]
            return None

        return entry.food_item

    def set_by_description(self, description: str, food_item: USDAFoodItem) -> None:
        """Cache food item by description.

        Args:
            description: Food description
            food_item: USDA food item to cache
        """
        key = self._make_key("desc", description.lower())
        expires_at = time.time() + self.default_ttl

        entry = USDACacheEntry(key=key, food_item=food_item, expires_at=expires_at)

        self._cache[key] = entry

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    def remove_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.info("Removed expired entries", count=len(expired_keys))

        return len(expired_keys)

    def size(self) -> int:
        """Get cache size.

        Returns:
            Number of cached entries
        """
        return len(self._cache)
