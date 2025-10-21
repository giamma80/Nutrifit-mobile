"""
Unit tests for USDA cache.

Tests based on actual implementation.
"""

import time

import pytest

from backend.v2.domain.meal.nutrition.usda_models import (
    USDADataType,
    USDAFoodItem,
    USDANutrient,
)
from backend.v2.domain.shared.value_objects import Barcode
from backend.v2.infrastructure.usda.cache import USDACache


class TestUSDACache:
    """Test USDA cache functionality."""

    @pytest.fixture
    def sample_food_item(self) -> USDAFoodItem:
        """Create a sample USDA food item."""
        return USDAFoodItem(
            fdc_id="123456",
            description="Apple, raw",
            data_type=USDADataType.SR_LEGACY,
            nutrients=[
                USDANutrient(
                    number="1008",
                    name="Energy",
                    unit="kcal",
                    amount=52.0,
                ),
                USDANutrient(
                    number="1003",
                    name="Protein",
                    unit="g",
                    amount=0.26,
                ),
            ],
        )

    @pytest.fixture
    def cache(self) -> USDACache:
        """Create a fresh cache instance."""
        return USDACache(default_ttl_seconds=3600)

    def test_cache_initialization(self) -> None:
        """Test cache is initialized with correct default TTL."""
        cache = USDACache()
        assert cache.default_ttl == 604800  # 7 days
        assert cache.size() == 0

        cache_custom = USDACache(default_ttl_seconds=1800)
        assert cache_custom.default_ttl == 1800
        assert cache_custom.size() == 0

    def test_make_key(self, cache: USDACache) -> None:
        """Test cache key generation."""
        key = cache._make_key("barcode", "123456")
        assert key == "barcode:123456"

        key_desc = cache._make_key("desc", "apple")
        assert key_desc == "desc:apple"

    def test_get_by_barcode_miss(self, cache: USDACache) -> None:
        """Test cache miss for non-existent barcode."""
        barcode = Barcode(value="9999999999999")
        result = cache.get_by_barcode(barcode)
        assert result is None

    def test_set_and_get_by_barcode(self, cache: USDACache, sample_food_item: USDAFoodItem) -> None:
        """Test caching and retrieval by barcode."""
        barcode = Barcode(value="3017620422003")

        # Set cache
        cache.set_by_barcode(barcode, sample_food_item)
        assert cache.size() == 1

        # Get cache
        result = cache.get_by_barcode(barcode)
        assert result is not None
        assert result.fdc_id == sample_food_item.fdc_id
        assert result.description == sample_food_item.description
        assert len(result.nutrients) == 2

    def test_get_by_barcode_expired(self, cache: USDACache, sample_food_item: USDAFoodItem) -> None:
        """Test expired cache entry is removed and returns None."""
        barcode = Barcode(value="3017620422003")

        # Set cache with 1 second TTL
        cache_short = USDACache(default_ttl_seconds=1)
        cache_short.set_by_barcode(barcode, sample_food_item)

        # Verify item is cached
        assert cache_short.size() == 1

        # Wait for expiry
        time.sleep(1.1)

        # Should return None and remove from cache
        result = cache_short.get_by_barcode(barcode)
        assert result is None
        assert cache_short.size() == 0

    def test_get_by_description_miss(self, cache: USDACache) -> None:
        """Test cache miss for non-existent description."""
        result = cache.get_by_description("nonexistent food")
        assert result is None

    def test_set_and_get_by_description(
        self, cache: USDACache, sample_food_item: USDAFoodItem
    ) -> None:
        """Test caching and retrieval by description."""
        description = "Apple, raw"

        # Set cache
        cache.set_by_description(description, sample_food_item)
        assert cache.size() == 1

        # Get cache (case insensitive)
        result = cache.get_by_description(description)
        assert result is not None
        assert result.fdc_id == sample_food_item.fdc_id

        # Test case insensitivity
        result_upper = cache.get_by_description("APPLE, RAW")
        assert result_upper is not None
        assert result_upper.fdc_id == sample_food_item.fdc_id

    def test_get_by_description_expired(
        self, cache: USDACache, sample_food_item: USDAFoodItem
    ) -> None:
        """Test expired description cache entry."""
        description = "Apple, raw"

        # Set cache with 1 second TTL
        cache_short = USDACache(default_ttl_seconds=1)
        cache_short.set_by_description(description, sample_food_item)

        # Verify cached
        assert cache_short.size() == 1

        # Wait for expiry
        time.sleep(1.1)

        # Should return None and remove from cache
        result = cache_short.get_by_description(description)
        assert result is None
        assert cache_short.size() == 0

    def test_clear_cache(self, cache: USDACache, sample_food_item: USDAFoodItem) -> None:
        """Test clearing all cache entries."""
        # Add multiple entries
        cache.set_by_barcode(Barcode(value="12345678"), sample_food_item)
        cache.set_by_barcode(Barcode(value="87654321"), sample_food_item)
        cache.set_by_description("apple", sample_food_item)

        assert cache.size() == 3

        # Clear cache
        cache.clear()
        assert cache.size() == 0

        # Verify entries are gone
        assert cache.get_by_barcode(Barcode(value="12345678")) is None
        assert cache.get_by_description("apple") is None

    def test_remove_expired_entries(self, sample_food_item: USDAFoodItem) -> None:
        """Test removing only expired entries."""
        # Create cache with 2 second TTL
        cache = USDACache(default_ttl_seconds=2)

        # Add first entry
        cache.set_by_barcode(Barcode(value="12345678"), sample_food_item)

        # Wait 1 second
        time.sleep(1)

        # Add second entry (won't expire yet)
        cache.set_by_barcode(Barcode(value="87654321"), sample_food_item)

        # Wait another 1.5 seconds (total 2.5s)
        # First entry will be expired, second won't
        time.sleep(1.5)

        # Remove expired
        removed_count = cache.remove_expired()

        assert removed_count == 1
        assert cache.size() == 1

        # Verify correct entry removed
        assert cache.get_by_barcode(Barcode(value="12345678")) is None
        assert cache.get_by_barcode(Barcode(value="87654321")) is not None

    def test_remove_expired_no_expired_entries(
        self, cache: USDACache, sample_food_item: USDAFoodItem
    ) -> None:
        """Test remove_expired when no entries are expired."""
        cache.set_by_barcode(Barcode(value="12345678"), sample_food_item)
        cache.set_by_barcode(Barcode(value="87654321"), sample_food_item)

        removed_count = cache.remove_expired()

        assert removed_count == 0
        assert cache.size() == 2

    def test_cache_size(self, cache: USDACache, sample_food_item: USDAFoodItem) -> None:
        """Test cache size tracking."""
        assert cache.size() == 0

        cache.set_by_barcode(Barcode(value="12345678"), sample_food_item)
        assert cache.size() == 1

        cache.set_by_barcode(Barcode(value="87654321"), sample_food_item)
        assert cache.size() == 2

        cache.set_by_description("apple", sample_food_item)
        assert cache.size() == 3

        cache.clear()
        assert cache.size() == 0

    def test_cache_overwrites_duplicate_keys(
        self, cache: USDACache, sample_food_item: USDAFoodItem
    ) -> None:
        """Test that setting the same key twice overwrites."""
        barcode = Barcode(value="8076804215898")

        # First set
        cache.set_by_barcode(barcode, sample_food_item)
        assert cache.size() == 1

        # Create different food item
        new_item = USDAFoodItem(
            fdc_id="999999",
            description="Different food",
            data_type=USDADataType.FOUNDATION,
            nutrients=[],
        )

        # Set again with same barcode
        cache.set_by_barcode(barcode, new_item)
        assert cache.size() == 1  # Still 1 entry

        # Verify it's the new item
        result = cache.get_by_barcode(barcode)
        assert result is not None
        assert result.fdc_id == "999999"
        assert result.description == "Different food"

    def test_barcode_and_description_separate_namespaces(
        self, cache: USDACache, sample_food_item: USDAFoodItem
    ) -> None:
        """Test that barcode and description use different namespaces."""
        # Use valid barcode
        barcode_value = "8076804215898"

        cache.set_by_barcode(Barcode(value=barcode_value), sample_food_item)
        cache.set_by_description(barcode_value, sample_food_item)

        # Should have 2 separate entries
        assert cache.size() == 2

        # Both should be retrievable
        assert cache.get_by_barcode(Barcode(value=barcode_value)) is not None
        assert cache.get_by_description(barcode_value) is not None
