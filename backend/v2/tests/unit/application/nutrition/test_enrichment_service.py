"""
Unit tests for Nutrition Enrichment Service.

Tests the orchestration of USDA API, caching, and fallback logic.
"""

from unittest.mock import AsyncMock

import pytest

from backend.v2.application.nutrition.enrichment_service import (
    NutritionEnrichmentService,
)
from backend.v2.domain.meal.nutrition.models import NutrientSource
from backend.v2.domain.meal.nutrition.usda_models import (
    USDADataType,
    USDAFoodItem,
    USDANutrient,
    USDASearchResult,
)
from backend.v2.domain.shared.value_objects import Barcode
from backend.v2.infrastructure.usda.api_client import USDAApiClient
from backend.v2.infrastructure.usda.cache import USDACache


class TestNutritionEnrichmentService:
    """Test Nutrition Enrichment Service."""

    @pytest.fixture
    def mock_api_client(self) -> AsyncMock:
        """Create mock USDA API client."""
        client = AsyncMock(spec=USDAApiClient)
        return client

    @pytest.fixture
    def cache(self) -> USDACache:
        """Create fresh cache instance."""
        return USDACache(default_ttl_seconds=3600)

    @pytest.fixture
    def sample_food_item(self) -> USDAFoodItem:
        """Create sample USDA food item with correct nutrient numbers."""
        return USDAFoodItem(
            fdc_id="123456",
            description="Apple, raw",
            data_type=USDADataType.SR_LEGACY,
            nutrients=[
                USDANutrient(number="208", name="Energy", amount=52.0, unit="kcal"),
                USDANutrient(number="203", name="Protein", amount=0.26, unit="g"),
                USDANutrient(number="205", name="Carbohydrate", amount=13.81, unit="g"),
                USDANutrient(number="204", name="Total lipid (fat)", amount=0.17, unit="g"),
                USDANutrient(number="291", name="Fiber", amount=2.4, unit="g"),
                USDANutrient(number="269", name="Sugars, total", amount=10.39, unit="g"),
            ],
        )

    @pytest.fixture
    def service(self, mock_api_client: AsyncMock, cache: USDACache) -> NutritionEnrichmentService:
        """Create service instance."""
        return NutritionEnrichmentService(api_client=mock_api_client, cache=cache)

    async def test_service_initialization(
        self, mock_api_client: AsyncMock, cache: USDACache
    ) -> None:
        """Test service initializes with API client and cache."""
        service = NutritionEnrichmentService(api_client=mock_api_client, cache=cache)

        assert service.api_client == mock_api_client
        assert service.cache == cache

    async def test_service_initialization_without_cache(self, mock_api_client: AsyncMock) -> None:
        """Test service creates default cache if not provided."""
        service = NutritionEnrichmentService(api_client=mock_api_client)

        assert service.cache is not None
        assert isinstance(service.cache, USDACache)
        assert service.cache.default_ttl == 604800  # 7 days

    async def test_enrich_by_barcode_from_cache(
        self,
        service: NutritionEnrichmentService,
        cache: USDACache,
        sample_food_item: USDAFoodItem,
    ) -> None:
        """Test enrichment returns cached data when available."""
        barcode = Barcode(value="3017620422003")

        # Pre-populate cache
        cache.set_by_barcode(barcode, sample_food_item)

        # Enrich should use cache
        profile = await service.enrich_by_barcode(barcode)

        assert profile is not None
        assert profile.calories == 52.0
        assert profile.protein == 0.26
        assert profile.source == NutrientSource.USDA

        # API should not have been called
        service.api_client.search_by_barcode.assert_not_called()

    async def test_enrich_by_barcode_from_api(
        self,
        service: NutritionEnrichmentService,
        mock_api_client: AsyncMock,
        sample_food_item: USDAFoodItem,
    ) -> None:
        """Test enrichment queries API when cache is empty."""
        barcode = Barcode(value="3017620422003")

        # Mock API response
        mock_result = USDASearchResult(
            total_hits=1, current_page=1, total_pages=1, foods=[sample_food_item]
        )
        mock_api_client.search_by_barcode.return_value = mock_result

        # Enrich
        profile = await service.enrich_by_barcode(barcode)

        assert profile is not None
        assert profile.calories == 52.0
        assert profile.protein == 0.26

        # Verify API was called
        mock_api_client.search_by_barcode.assert_called_once_with(barcode)

        # Verify item was cached
        cached = service.cache.get_by_barcode(barcode)
        assert cached is not None
        assert cached.fdc_id == sample_food_item.fdc_id

    async def test_enrich_by_barcode_not_found(
        self, service: NutritionEnrichmentService, mock_api_client: AsyncMock
    ) -> None:
        """Test enrichment returns None when barcode not found."""
        barcode = Barcode(value="9999999999999")

        # Mock empty API response
        mock_result = USDASearchResult(total_hits=0, current_page=1, total_pages=0, foods=[])
        mock_api_client.search_by_barcode.return_value = mock_result

        # Enrich
        profile = await service.enrich_by_barcode(barcode)

        assert profile is None

    async def test_enrich_by_barcode_api_error(
        self, service: NutritionEnrichmentService, mock_api_client: AsyncMock
    ) -> None:
        """Test enrichment handles API errors gracefully."""
        barcode = Barcode(value="3017620422003")

        # Mock API error
        mock_api_client.search_by_barcode.side_effect = Exception("API Error")

        # Enrich should return None
        profile = await service.enrich_by_barcode(barcode)

        assert profile is None

    async def test_enrich_by_description_from_cache(
        self,
        service: NutritionEnrichmentService,
        cache: USDACache,
        sample_food_item: USDAFoodItem,
    ) -> None:
        """Test description enrichment uses cache."""
        description = "Apple, raw"

        # Pre-populate cache
        cache.set_by_description(description, sample_food_item)

        # Enrich
        profile = await service.enrich_by_description(description, quantity_g=150.0)

        assert profile is not None
        assert profile.calories == 78.0  # 52 * 1.5
        assert profile.protein == 0.4  # 0.26 * 1.5 = 0.39, rounded to 0.4

        # API should not be called
        service.api_client.search_by_description.assert_not_called()

    async def test_enrich_by_description_from_api(
        self,
        service: NutritionEnrichmentService,
        mock_api_client: AsyncMock,
        sample_food_item: USDAFoodItem,
    ) -> None:
        """Test description enrichment queries API."""
        description = "Apple, raw"

        # Mock API response
        mock_result = USDASearchResult(
            total_hits=1, current_page=1, total_pages=1, foods=[sample_food_item]
        )
        mock_api_client.search_by_description.return_value = mock_result

        # Enrich
        profile = await service.enrich_by_description(description, quantity_g=100.0)

        assert profile is not None
        assert profile.calories == 52.0
        assert profile.protein == 0.3  # 0.26 rounded to 0.3

        # Verify API was called
        mock_api_client.search_by_description.assert_called_once_with(description, max_results=1)

        # Verify item was cached
        cached = service.cache.get_by_description(description)
        assert cached is not None

    async def test_enrich_by_description_fallback_to_category(
        self, service: NutritionEnrichmentService, mock_api_client: AsyncMock
    ) -> None:
        """Test fallback to category profile when API fails."""
        description = "Apple"

        # Mock empty API response
        mock_result = USDASearchResult(total_hits=0, current_page=1, total_pages=0, foods=[])
        mock_api_client.search_by_description.return_value = mock_result

        # Enrich should use category fallback
        profile = await service.enrich_by_description(description, quantity_g=100.0)

        assert profile is not None
        assert profile.source == NutrientSource.ESTIMATED
        # Apple should be categorized as FRUIT
        assert profile.calories == 52.0  # FRUIT category default
        assert profile.carbs == 14.0

    async def test_enrich_by_description_api_error_fallback(
        self, service: NutritionEnrichmentService, mock_api_client: AsyncMock
    ) -> None:
        """Test fallback when API throws error."""
        description = "Chicken breast"

        # Mock API error
        mock_api_client.search_by_description.side_effect = Exception("API Error")

        # Should fallback to category profile
        profile = await service.enrich_by_description(description, quantity_g=100.0)

        assert profile is not None
        assert profile.source == NutrientSource.ESTIMATED
        # Chicken should be categorized as PROTEIN
        assert profile.protein == 25.0  # PROTEIN category default

    async def test_enrich_by_description_quantity_scaling(
        self,
        service: NutritionEnrichmentService,
        mock_api_client: AsyncMock,
        sample_food_item: USDAFoodItem,
    ) -> None:
        """Test nutrient values scale with quantity."""
        description = "Apple"

        # Mock API response
        mock_result = USDASearchResult(
            total_hits=1, current_page=1, total_pages=1, foods=[sample_food_item]
        )
        mock_api_client.search_by_description.return_value = mock_result

        # Test different quantities
        profile_100 = await service.enrich_by_description(description, quantity_g=100.0)
        profile_200 = await service.enrich_by_description(description, quantity_g=200.0)
        profile_50 = await service.enrich_by_description(description, quantity_g=50.0)

        assert profile_100.calories == 52.0
        assert profile_200.calories == 104.0  # Double
        assert profile_50.calories == 26.0  # Half

    async def test_enrich_batch_multiple_descriptions(
        self,
        service: NutritionEnrichmentService,
        mock_api_client: AsyncMock,
        sample_food_item: USDAFoodItem,
    ) -> None:
        """Test batch enrichment of multiple descriptions."""
        descriptions = ["Apple", "Banana", "Orange"]

        # Mock API response for all
        mock_result = USDASearchResult(
            total_hits=1, current_page=1, total_pages=1, foods=[sample_food_item]
        )
        mock_api_client.search_by_description.return_value = mock_result

        # Enrich batch
        profiles = await service.enrich_batch(descriptions)

        assert len(profiles) == 3
        assert all(p is not None for p in profiles)
        assert all(p.calories > 0 for p in profiles)

        # Verify API was called for each
        assert mock_api_client.search_by_description.call_count == 3

    async def test_enrich_batch_empty_list(self, service: NutritionEnrichmentService) -> None:
        """Test batch enrichment with empty list."""
        profiles = await service.enrich_batch([])

        assert profiles == []

    async def test_enrich_batch_mixed_success_fallback(
        self, service: NutritionEnrichmentService, mock_api_client: AsyncMock
    ) -> None:
        """Test batch handles mixed API success and fallback."""
        descriptions = ["Apple", "UnknownFood123"]

        # Mock API: first succeeds, second fails
        def mock_search(desc: str, max_results: int = 1) -> USDASearchResult:
            if "Apple" in desc:
                return USDASearchResult(
                    total_hits=1,
                    current_page=1,
                    total_pages=1,
                    foods=[
                        USDAFoodItem(
                            fdc_id="123",
                            description="Apple",
                            data_type=USDADataType.SR_LEGACY,
                            nutrients=[
                                USDANutrient(
                                    number="1008", name="Energy", amount=52.0, unit="kcal"
                                ),
                            ],
                        )
                    ],
                )
            return USDASearchResult(total_hits=0, current_page=1, total_pages=0, foods=[])

        mock_api_client.search_by_description.side_effect = mock_search

        # Enrich batch
        profiles = await service.enrich_batch(descriptions)

        assert len(profiles) == 2
        assert profiles[0].source == NutrientSource.USDA
        assert profiles[1].source == NutrientSource.ESTIMATED
