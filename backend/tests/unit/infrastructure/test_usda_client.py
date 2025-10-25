"""Unit tests for USDA Client.

Tests focus on:
- Client initialization
- Food search functionality
- Nutrient extraction and mapping
- INutritionProvider port implementation
- Error handling

Note: These are UNIT tests with mocked USDA API calls.
For integration tests with real API, see tests/integration/infrastructure/test_usda_integration.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any

from infrastructure.external_apis.usda.client import USDAClient, normalize_food_label
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


@pytest.fixture
def usda_client() -> USDAClient:
    """Fixture providing USDAClient with mocked HTTP session."""
    client = USDAClient(api_key="test-key")
    # Mock the session directly (don't use async context manager in tests)
    client._session = AsyncMock()
    return client


@pytest.fixture
def sample_usda_search_response() -> dict[str, Any]:
    """Sample USDA search API response."""
    return {
        "foods": [
            {
                "fdcId": 173096,
                "description": "Chicken, broilers or fryers, breast, meat only, raw",
                "dataType": "SR Legacy",
                "foodNutrients": [
                    {"nutrientId": 1008, "value": 110},  # calories
                    {"nutrientId": 1003, "value": 23.09},  # protein
                    {"nutrientId": 1005, "value": 0.0},  # carbs
                    {"nutrientId": 1004, "value": 2.59},  # fat
                ],
            },
            {
                "fdcId": 173097,
                "description": "Chicken, broilers or fryers, breast, meat and skin, raw",
            },
        ]
    }


@pytest.fixture
def sample_usda_detail_response() -> dict[str, Any]:
    """Sample USDA food detail API response."""
    return {
        "fdcId": 173096,
        "description": "Chicken, broilers or fryers, breast, meat only, raw",
        "foodNutrients": [
            {
                "nutrient": {"id": 1008},
                "amount": 110,
            },  # calories
            {
                "nutrient": {"id": 1003},
                "amount": 23.09,
            },  # protein
            {
                "nutrient": {"id": 1005},
                "amount": 0.0,
            },  # carbs
            {
                "nutrient": {"id": 1004},
                "amount": 2.59,
            },  # fat
            {
                "nutrient": {"id": 1079},
                "amount": 0.0,
            },  # fiber
            {
                "nutrient": {"id": 1063},
                "amount": 0.0,
            },  # sugar
            {
                "nutrient": {"id": 1093},
                "amount": 63,
            },  # sodium
            {
                "nutrient": {"id": 1087},
                "amount": 5,
            },  # calcium
        ],
    }


class TestUSDAClientInit:
    """Test client initialization."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with API key."""
        client = USDAClient(api_key="custom-key")
        assert client.api_key == "custom-key"

    def test_init_with_env_key(self, monkeypatch: Any) -> None:
        """Test initialization with environment variable."""
        monkeypatch.setenv("AI_USDA_API_KEY", "env-key")
        client = USDAClient()
        assert client.api_key == "env-key"

    def test_init_with_default_key(self) -> None:
        """Test initialization falls back to default key."""
        client = USDAClient()
        assert client.api_key is not None
        assert len(client.api_key) > 0

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager."""
        async with USDAClient() as client:
            assert client._session is not None

    @pytest.mark.asyncio
    async def test_search_without_context_manager(self) -> None:
        """Test search raises error without context manager."""
        client = USDAClient()

        with pytest.raises(RuntimeError, match="Client not initialized"):
            await client.search_food("chicken")

    @pytest.mark.asyncio
    async def test_get_nutrients_by_id_without_context_manager(self) -> None:
        """Test get_nutrients_by_id raises error without context manager."""
        client = USDAClient()

        with pytest.raises(RuntimeError, match="Client not initialized"):
            await client.get_nutrients_by_id(173096)


class TestSearchFood:
    """Test search_food method."""

    @pytest.mark.asyncio
    async def test_search_food_success(
        self, usda_client: USDAClient, sample_usda_search_response: dict[str, Any]
    ) -> None:
        """Test successful food search."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=sample_usda_search_response)

        # Mock the async context manager
        usda_client._session.get = MagicMock(return_value=mock_response)
        usda_client._session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        usda_client._session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        foods = await usda_client.search_food("chicken breast")

        # Assert
        assert len(foods) == 2
        assert foods[0]["fdcId"] == 173096
        assert "chicken" in foods[0]["description"].lower()

    @pytest.mark.asyncio
    async def test_search_food_empty_results(self, usda_client: USDAClient) -> None:
        """Test search with no results."""
        # Mock HTTP response with empty results
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"foods": []})

        usda_client._session.get = MagicMock(return_value=mock_response)
        usda_client._session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        usda_client._session.get.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        foods = await usda_client.search_food("nonexistent food xyz")

        # Assert
        assert len(foods) == 0

    @pytest.mark.asyncio
    async def test_search_food_api_error(self, usda_client: USDAClient) -> None:
        """Test search with API error."""
        # Mock HTTP error
        mock_response = MagicMock()
        mock_response.status = 500

        usda_client._session.get = MagicMock(return_value=mock_response)
        usda_client._session.get.return_value.__aenter__ = AsyncMock(
            return_value=mock_response
        )
        usda_client._session.get.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        # Execute
        foods = await usda_client.search_food("chicken")

        # Assert - should return empty list on error
        assert len(foods) == 0

    @pytest.mark.asyncio
    async def test_search_food_timeout(self, usda_client: USDAClient) -> None:
        """Test search with timeout."""
        import asyncio

        # Mock timeout exception
        usda_client._session.get = MagicMock(
            side_effect=asyncio.TimeoutError("Timeout")
        )

        # Execute - should return empty list on timeout
        foods = await usda_client.search_food("chicken")

        assert len(foods) == 0

    @pytest.mark.asyncio
    async def test_search_food_generic_exception(
        self, usda_client: USDAClient
    ) -> None:
        """Test search with generic exception."""
        # Mock generic exception
        usda_client._session.get = MagicMock(
            side_effect=Exception("Connection error")
        )

        # Execute - should return empty list on error
        foods = await usda_client.search_food("chicken")

        assert len(foods) == 0


class TestGetNutrients:
    """Test get_nutrients method (INutritionProvider implementation)."""

    @pytest.mark.asyncio
    async def test_get_nutrients_success(
        self,
        usda_client: USDAClient,
        sample_usda_search_response: dict[str, Any],
        sample_usda_detail_response: dict[str, Any],
    ) -> None:
        """Test successful nutrient retrieval."""
        # Mock search response
        search_mock = MagicMock()
        search_mock.status = 200
        search_mock.json = AsyncMock(return_value=sample_usda_search_response)
        search_mock.__aenter__ = AsyncMock(return_value=search_mock)
        search_mock.__aexit__ = AsyncMock(return_value=None)

        # Mock detail response
        detail_mock = MagicMock()
        detail_mock.status = 200
        detail_mock.json = AsyncMock(return_value=sample_usda_detail_response)
        detail_mock.__aenter__ = AsyncMock(return_value=detail_mock)
        detail_mock.__aexit__ = AsyncMock(return_value=None)

        # Setup session to return different mocks for different endpoints
        def mock_get(url: str, **kwargs: Any) -> Any:
            if "search" in url:
                return search_mock
            else:
                return detail_mock

        usda_client._session.get = mock_get

        # Execute
        profile = await usda_client.get_nutrients("chicken breast", 100.0)

        # Assert
        assert profile is not None
        assert isinstance(profile, NutrientProfile)
        assert profile.calories == 110
        assert profile.protein == 23.09
        assert profile.carbs == 0.0
        assert profile.fat == 2.59
        assert profile.fiber == 0.0
        assert profile.sodium == 63
        assert profile.sodium == 63
        assert profile.source == "USDA"
        assert profile.confidence == 0.95
        assert profile.quantity_g == 100.0

    @pytest.mark.asyncio
    async def test_get_nutrients_no_search_results(
        self, usda_client: USDAClient
    ) -> None:
        """Test nutrient retrieval with no search results."""
        # Mock empty search response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"foods": []})

        usda_client._session.get = MagicMock(return_value=mock_response)
        usda_client._session.get.return_value.__aenter__ = AsyncMock(
            return_value=mock_response
        )
        usda_client._session.get.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        # Execute
        profile = await usda_client.get_nutrients("nonexistent", 100.0)

        # Assert
        assert profile is None

    @pytest.mark.asyncio
    async def test_get_nutrients_no_fdc_id(
        self, usda_client: USDAClient
    ) -> None:
        """Test nutrient retrieval with missing FDC ID."""
        # Mock search response without fdcId
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"foods": [{"description": "Test"}]}
        )

        usda_client._session.get = MagicMock(return_value=mock_response)
        usda_client._session.get.return_value.__aenter__ = AsyncMock(
            return_value=mock_response
        )
        usda_client._session.get.return_value.__aexit__ = AsyncMock(
            return_value=None
        )

        # Execute
        profile = await usda_client.get_nutrients("test", 100.0)

        # Assert
        assert profile is None

    @pytest.mark.asyncio
    async def test_get_nutrients_by_id_error(
        self, usda_client: USDAClient, sample_usda_search_response: dict[str, Any]
    ) -> None:
        """Test nutrient retrieval with get_nutrients_by_id failure."""
        # Mock search response
        search_mock = MagicMock()
        search_mock.status = 200
        search_mock.json = AsyncMock(return_value=sample_usda_search_response)
        search_mock.__aenter__ = AsyncMock(return_value=search_mock)
        search_mock.__aexit__ = AsyncMock(return_value=None)

        # Mock detail response with error
        detail_mock = MagicMock()
        detail_mock.status = 500
        detail_mock.__aenter__ = AsyncMock(return_value=detail_mock)
        detail_mock.__aexit__ = AsyncMock(return_value=None)

        # Setup session to return different mocks
        def mock_get(url: str, **kwargs: Any) -> Any:
            if "search" in url:
                return search_mock
            else:
                return detail_mock

        usda_client._session.get = mock_get

        # Execute
        profile = await usda_client.get_nutrients("chicken", 100.0)

        # Assert
        assert profile is None

    @pytest.mark.asyncio
    async def test_get_nutrients_by_id_exception(
        self, usda_client: USDAClient
    ) -> None:
        """Test get_nutrients_by_id with exception."""
        # Mock exception
        usda_client._session.get = MagicMock(
            side_effect=Exception("Connection error")
        )

        # Execute
        result = await usda_client.get_nutrients_by_id(173096)

        # Assert - should return None on exception
        assert result is None


class TestNutrientExtraction:
    """Test _extract_nutrients method."""

    def test_extract_nutrients_search_api_format(self) -> None:
        """Test extraction from Search API format."""
        client = USDAClient()

        food_data = {
            "foodNutrients": [
                {"nutrientId": 1008, "value": 150},  # calories
                {"nutrientId": 1003, "value": 5.0},  # protein
                {"nutrientId": 1005, "value": 30.0},  # carbs
                {"nutrientId": 1004, "value": 2.0},  # fat
            ]
        }

        nutrients = client._extract_nutrients(food_data)

        assert nutrients["calories"] == 150
        assert nutrients["protein"] == 5.0
        assert nutrients["carbs"] == 30.0
        assert nutrients["fat"] == 2.0

    def test_extract_nutrients_detail_api_format(self) -> None:
        """Test extraction from Detail API format."""
        client = USDAClient()

        food_data = {
            "foodNutrients": [
                {"nutrient": {"id": 1008}, "amount": 200},  # calories
                {"nutrient": {"id": 1003}, "amount": 10.0},  # protein
                {"nutrient": {"id": 1079}, "amount": 3.0},  # fiber
                {"nutrient": {"id": 1063}, "amount": 5.0},  # sugar
            ]
        }

        nutrients = client._extract_nutrients(food_data)

        assert nutrients["calories"] == 200
        assert nutrients["protein"] == 10.0
        assert nutrients["fiber"] == 3.0
        assert nutrients["sugar"] == 5.0


class TestLabelNormalization:
    """Test normalize_food_label function."""

    def test_normalize_basic(self) -> None:
        """Test basic normalization."""
        assert normalize_food_label("Chicken Breast") == "chicken breast"

    def test_normalize_with_special_chars(self) -> None:
        """Test normalization removes special characters."""
        assert normalize_food_label("Chicken, Breast!") == "chicken breast"

    def test_normalize_extra_spaces(self) -> None:
        """Test normalization removes extra spaces."""
        assert normalize_food_label("chicken   breast") == "chicken breast"

    def test_normalize_compound_terms(self) -> None:
        """Test compound terms are preserved."""
        assert normalize_food_label("ground beef") == "ground beef"
        assert normalize_food_label("olive oil") == "olive oil"

    def test_normalize_with_dashes(self) -> None:
        """Test dashes are preserved."""
        assert normalize_food_label("low-fat") == "low-fat"
