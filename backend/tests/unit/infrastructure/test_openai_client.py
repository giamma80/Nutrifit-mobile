"""Unit tests for OpenAI Vision Client.

Tests focus on:
- Client initialization
- Pydantic model mapping to domain entities
- Error handling
- Cache statistics tracking

Note: These are UNIT tests with mocked OpenAI API calls.
For integration tests with real API, see tests/integration/infrastructure/test_openai_integration.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Iterator

from infrastructure.ai.openai.client import OpenAIVisionClient
from infrastructure.ai.openai.models import (
    FoodRecognitionResponse,
    RecognizedFoodItem,
)
from domain.meal.recognition.entities.recognized_food import (
    FoodRecognitionResult,
    RecognizedFood,
)


@pytest.fixture
def mock_openai_client() -> Iterator[Any]:
    """Fixture providing mocked OpenAI AsyncClient."""
    with patch("infrastructure.ai.openai.client.AsyncOpenAI") as mock:
        yield mock


@pytest.fixture
def openai_client(mock_openai_client: Any) -> OpenAIVisionClient:
    """Fixture providing OpenAIVisionClient with mocked API."""
    return OpenAIVisionClient(api_key="test-key")


@pytest.fixture
def sample_openai_response() -> Any:
    """Sample OpenAI API response for structured outputs."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                parsed=FoodRecognitionResponse(
                    dish_title="Spaghetti alla Carbonara",
                    items=[
                        RecognizedFoodItem(
                            label="pasta, cooked",
                            display_name="Pasta cotta",
                            quantity_g=250.0,
                            confidence=0.9,
                        ),
                        RecognizedFoodItem(
                            label="eggs",
                            display_name="Uova",
                            quantity_g=50.0,
                            confidence=0.8,
                        ),
                    ],
                )
            )
        )
    ]
    # Mock usage without prompt_tokens_details (cache miss)
    mock_response.usage = MagicMock(
        total_tokens=1200,
        prompt_tokens=1000,
        completion_tokens=200,
    )
    mock_response.usage.prompt_tokens_details = MagicMock(cached_tokens=0)
    return mock_response


@pytest.fixture
def sample_empty_response() -> Any:
    """Sample OpenAI response with no items detected."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                parsed=FoodRecognitionResponse(
                    dish_title="",
                    items=[],
                )
            )
        )
    ]
    mock_response.usage = MagicMock(
        total_tokens=800,
        prompt_tokens=700,
        completion_tokens=100,
        prompt_tokens_details=None,
    )
    return mock_response


class TestOpenAIVisionClientInit:
    """Test client initialization."""

    def test_init_with_defaults(self, mock_openai_client) -> None:
        """Test initialization with default parameters."""
        client = OpenAIVisionClient(api_key="test-key")

        assert client._model == "gpt-4o-2024-08-06"
        assert client._temperature == 0.1
        assert client._cache_stats == {"hits": 0, "misses": 0}

    def test_init_with_custom_params(self, mock_openai_client) -> None:
        """Test initialization with custom parameters."""
        client = OpenAIVisionClient(
            api_key="test-key",
            model="gpt-4o-mini",
            temperature=0.5,
        )

        assert client._model == "gpt-4o-mini"
        assert client._temperature == 0.5


class TestAnalyzePhoto:
    """Test analyze_photo method."""

    @pytest.mark.asyncio
    async def test_analyze_photo_success(
        self,
        openai_client,
        sample_openai_response,
    ):
        """Test successful photo analysis."""
        # Mock OpenAI API call
        openai_client._client.beta.chat.completions.parse = AsyncMock(
            return_value=sample_openai_response
        )

        # Execute
        result = await openai_client.analyze_photo(
            photo_url="https://example.com/food.jpg"
        )

        # Assert
        assert isinstance(result, FoodRecognitionResult)
        assert len(result.items) == 2
        assert result.items[0].label == "pasta, cooked"
        assert result.items[0].display_name == "Pasta cotta"
        assert result.items[0].quantity_g == 250.0
        assert result.items[0].confidence == 0.9
        assert result.dish_name == "Spaghetti alla Carbonara"
        assert result.processing_time_ms >= 0  # May be 0 in fast mocked tests

    @pytest.mark.asyncio
    async def test_analyze_photo_with_hint(
        self,
        openai_client,
        sample_openai_response,
    ):
        """Test photo analysis with hint."""
        # Mock OpenAI API call
        mock_parse = AsyncMock(return_value=sample_openai_response)
        openai_client._client.beta.chat.completions.parse = mock_parse

        # Execute with hint
        await openai_client.analyze_photo(
            photo_url="https://example.com/food.jpg",
            hint="pasta carbonara",
        )

        # Verify hint was included in messages
        call_args = mock_parse.call_args
        messages = call_args.kwargs["messages"]
        user_message = messages[1]  # After system message
        assert any(
            item.get("text") == "Dish hint: pasta carbonara"
            for item in user_message["content"]
        )

    @pytest.mark.asyncio
    async def test_analyze_photo_empty_result(
        self,
        openai_client,
        sample_empty_response,
    ):
        """Test photo analysis with no items detected."""
        # Mock OpenAI API call
        openai_client._client.beta.chat.completions.parse = AsyncMock(
            return_value=sample_empty_response
        )

        # Execute
        result = await openai_client.analyze_photo(
            photo_url="https://example.com/empty.jpg"
        )

        # Assert - should return placeholder item for empty result
        assert isinstance(result, FoodRecognitionResult)
        assert len(result.items) == 1
        assert result.items[0].label == "unknown"
        assert result.items[0].confidence == 0.1


class TestAnalyzeText:
    """Test analyze_text method."""

    @pytest.mark.asyncio
    async def test_analyze_text_success(
        self,
        openai_client,
        sample_openai_response,
    ):
        """Test successful text analysis."""
        # Mock OpenAI API call
        openai_client._client.beta.chat.completions.parse = AsyncMock(
            return_value=sample_openai_response
        )

        # Execute
        result = await openai_client.analyze_text(
            description="I ate spaghetti carbonara with eggs and bacon"
        )

        # Assert
        assert isinstance(result, FoodRecognitionResult)
        assert len(result.items) == 2
        assert result.items[0].label == "pasta, cooked"
        assert result.dish_name == "Spaghetti alla Carbonara"
        assert result.processing_time_ms >= 0  # May be 0 in fast mocked tests


class TestPydanticToDomain:
    """Test Pydantic model to domain entity conversion."""

    def test_to_domain_result_success(self, openai_client) -> None:
        """Test successful conversion from Pydantic to domain."""
        pydantic_response = FoodRecognitionResponse(
            dish_title="Test Dish",
            items=[
                RecognizedFoodItem(
                    label="chicken breast, grilled",
                    display_name="Pollo grigliato",
                    quantity_g=200.0,
                    confidence=0.95,
                ),
            ],
        )

        domain_result = openai_client._to_domain_result(pydantic_response)

        assert isinstance(domain_result, FoodRecognitionResult)
        assert len(domain_result.items) == 1
        assert isinstance(domain_result.items[0], RecognizedFood)
        assert domain_result.items[0].label == "chicken breast, grilled"
        assert domain_result.items[0].display_name == "Pollo grigliato"
        assert domain_result.items[0].quantity_g == 200.0
        assert domain_result.items[0].confidence == 0.95

    def test_to_domain_result_empty_items(self, openai_client) -> None:
        """Test conversion with empty items list."""
        pydantic_response = FoodRecognitionResponse(
            dish_title="",
            items=[],
        )

        domain_result = openai_client._to_domain_result(pydantic_response)

        # Should return placeholder item
        assert isinstance(domain_result, FoodRecognitionResult)
        assert len(domain_result.items) == 1
        assert domain_result.items[0].label == "unknown"
        assert domain_result.items[0].confidence == 0.1


class TestCacheStats:
    """Test cache statistics tracking."""

    def test_get_cache_stats_initial(self, openai_client) -> None:
        """Test initial cache stats."""
        stats = openai_client.get_cache_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 0.0

    @pytest.mark.asyncio
    async def test_cache_hit_tracking(
        self,
        openai_client,
    ):
        """Test cache hit is tracked correctly."""
        # Mock response with cache hit
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    parsed=FoodRecognitionResponse(
                        dish_title="Test",
                        items=[
                            RecognizedFoodItem(
                                label="test",
                                display_name="Test",
                                quantity_g=100.0,
                                confidence=0.8,
                            )
                        ],
                    )
                )
            )
        ]
        mock_response.usage = MagicMock(
            total_tokens=1000,
            prompt_tokens=800,
            completion_tokens=200,
            prompt_tokens_details=MagicMock(cached_tokens=500),
        )

        openai_client._client.beta.chat.completions.parse = AsyncMock(
            return_value=mock_response
        )

        # Execute
        await openai_client.analyze_text("test food")

        # Check stats
        stats = openai_client.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["hit_rate_percent"] == 100.0

    @pytest.mark.asyncio
    async def test_cache_miss_tracking(
        self,
        openai_client,
        sample_openai_response,
    ):
        """Test cache miss is tracked correctly."""
        openai_client._client.beta.chat.completions.parse = AsyncMock(
            return_value=sample_openai_response
        )

        # Execute (no cached_tokens → miss)
        await openai_client.analyze_text("test food")

        # Check stats
        stats = openai_client.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 0.0


class TestErrorHandling:
    """Test error handling and circuit breaker."""

    @pytest.mark.asyncio
    async def test_analyze_photo_api_error(self, openai_client) -> None:
        """Test handling of OpenAI API errors."""
        from tenacity import RetryError

        # Mock API error with generic Exception
        # (OpenAI APIError requires complex initialization)
        error = ConnectionError("API connection failed")
        openai_client._client.beta.chat.completions.parse = AsyncMock(
            side_effect=error
        )

        # Should raise RetryError after retries (tenacity wraps the original exception)
        with pytest.raises(RetryError):
            await openai_client.analyze_photo("https://example.com/food.jpg")

    @pytest.mark.asyncio
    async def test_analyze_photo_empty_parsed(self, openai_client) -> None:
        """Test handling of empty parsed response."""
        # Mock response with no parsed data
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(parsed=None))
        ]
        mock_response.usage = MagicMock(
            total_tokens=1000,
            prompt_tokens=800,
            completion_tokens=200,
        )

        openai_client._client.beta.chat.completions.parse = AsyncMock(
            return_value=mock_response
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="empty parsed response"):
            await openai_client.analyze_photo("https://example.com/food.jpg")
