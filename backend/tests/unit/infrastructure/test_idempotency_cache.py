"""
Tests for in-memory idempotency cache.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from infrastructure.cache.in_memory_idempotency_cache import (
    InMemoryIdempotencyCache,
)


@pytest.fixture
def cache() -> InMemoryIdempotencyCache:
    """Create a fresh cache for each test."""
    return InMemoryIdempotencyCache()


class TestInMemoryIdempotencyCache:
    """Tests for InMemoryIdempotencyCache."""

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache: InMemoryIdempotencyCache) -> None:
        """Test basic set and get operations."""
        key = "test-key-123"
        meal_id = uuid4()

        await cache.set(key, meal_id, ttl_seconds=3600)
        result = await cache.get(key)

        assert result == meal_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache: InMemoryIdempotencyCache) -> None:
        """Test getting a key that doesn't exist."""
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, cache: InMemoryIdempotencyCache) -> None:
        """Test checking if a key exists."""
        key = "test-key-456"
        meal_id = uuid4()

        # Before setting
        assert await cache.exists(key) is False

        # After setting
        await cache.set(key, meal_id)
        assert await cache.exists(key) is True

    @pytest.mark.asyncio
    async def test_delete(self, cache: InMemoryIdempotencyCache) -> None:
        """Test deleting a key."""
        key = "test-key-789"
        meal_id = uuid4()

        await cache.set(key, meal_id)
        assert await cache.exists(key) is True

        await cache.delete(key)
        assert await cache.exists(key) is False

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache: InMemoryIdempotencyCache) -> None:
        """Test that entries expire after TTL."""
        key = "test-key-ttl"
        meal_id = uuid4()

        # Set with very short TTL (1 second)
        await cache.set(key, meal_id, ttl_seconds=1)

        # Should exist immediately
        assert await cache.exists(key) is True

        # Manually manipulate expiration time to simulate passage of time
        # (instead of sleeping for real time in tests)
        if key in cache._cache:
            cached_meal_id, _ = cache._cache[key]
            # Set expiration to past
            cache._cache[key] = (
                cached_meal_id,
                datetime.now(timezone.utc) - timedelta(seconds=10),
            )

        # Should now be expired
        result = await cache.get(key)
        assert result is None
        assert await cache.exists(key) is False

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self, cache: InMemoryIdempotencyCache) -> None:
        """Test overwriting an existing key."""
        key = "test-key-overwrite"
        meal_id_1 = uuid4()
        meal_id_2 = uuid4()

        await cache.set(key, meal_id_1)
        result_1 = await cache.get(key)
        assert result_1 == meal_id_1

        # Overwrite with new meal ID
        await cache.set(key, meal_id_2)
        result_2 = await cache.get(key)
        assert result_2 == meal_id_2
        assert result_2 != meal_id_1

    def test_clear(self, cache: InMemoryIdempotencyCache) -> None:
        """Test clearing all cache entries."""
        # Add some entries
        cache._cache["key1"] = (uuid4(), datetime.now(timezone.utc))
        cache._cache["key2"] = (uuid4(), datetime.now(timezone.utc))

        assert len(cache._cache) == 2

        cache.clear()
        assert len(cache._cache) == 0

    def test_cleanup_expired(self, cache: InMemoryIdempotencyCache) -> None:
        """Test cleaning up expired entries."""
        now = datetime.now(timezone.utc)

        # Add 3 entries: 2 expired, 1 valid
        cache._cache["expired1"] = (uuid4(), now - timedelta(seconds=10))
        cache._cache["expired2"] = (uuid4(), now - timedelta(seconds=5))
        cache._cache["valid"] = (uuid4(), now + timedelta(seconds=3600))

        assert len(cache._cache) == 3

        # Cleanup should remove 2 expired entries
        removed_count = cache.cleanup_expired()

        assert removed_count == 2
        assert len(cache._cache) == 1
        assert "valid" in cache._cache
        assert "expired1" not in cache._cache
        assert "expired2" not in cache._cache

    @pytest.mark.asyncio
    async def test_multiple_keys(self, cache: InMemoryIdempotencyCache) -> None:
        """Test storing multiple different keys."""
        keys_and_ids = [
            ("key1", uuid4()),
            ("key2", uuid4()),
            ("key3", uuid4()),
        ]

        # Set all
        for key, meal_id in keys_and_ids:
            await cache.set(key, meal_id)

        # Verify all
        for key, expected_meal_id in keys_and_ids:
            result = await cache.get(key)
            assert result == expected_meal_id

    @pytest.mark.asyncio
    async def test_custom_ttl(self, cache: InMemoryIdempotencyCache) -> None:
        """Test setting custom TTL values."""
        key = "test-custom-ttl"
        meal_id = uuid4()

        # Set with 2 hour TTL
        await cache.set(key, meal_id, ttl_seconds=7200)

        # Verify it was set
        result = await cache.get(key)
        assert result == meal_id

        # Check that expiration is approximately 2 hours from now
        if key in cache._cache:
            _, expiration = cache._cache[key]
            now = datetime.now(timezone.utc)
            delta = expiration - now

            # Should be close to 2 hours (within 1 second tolerance)
            assert 7199 <= delta.total_seconds() <= 7200
