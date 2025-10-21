"""
Unit tests for OpenAI client.

Tests vision and text completion with mocked OpenAI API.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from v2.infrastructure.ai.openai_client import OpenAIClient


@pytest.fixture
def mock_openai_response() -> MagicMock:
    """Mock OpenAI ChatCompletion response."""
    response = MagicMock()

    # Mock choice
    choice = MagicMock()
    choice.message.content = '{"items": [{"label": "Apple", "quantity_g": 150}]}'
    choice.finish_reason = "stop"

    # Mock usage
    usage = MagicMock()
    usage.prompt_tokens = 100
    usage.completion_tokens = 50
    usage.total_tokens = 150

    response.choices = [choice]
    response.usage = usage

    return response


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    """Mock AsyncOpenAI client."""
    client = AsyncMock()
    client.close = AsyncMock()
    return client


class TestOpenAIClient:
    """Test suite for OpenAI client."""

    def test_init_with_api_key(self) -> None:
        """Test initialization with explicit API key."""
        client = OpenAIClient(api_key="test-key-123")

        assert client.api_key == "test-key-123"
        assert client.model == "gpt-4o"
        assert client.max_retries == 3
        assert client.timeout == 30
        assert client.rpm_limit == 60

    def test_init_with_custom_params(self) -> None:
        """Test initialization with custom parameters."""
        client = OpenAIClient(
            api_key="test-key",
            model="gpt-4-turbo",
            max_retries=5,
            timeout=60,
            rpm_limit=100,
        )

        assert client.model == "gpt-4-turbo"
        assert client.max_retries == 5
        assert client.timeout == 60
        assert client.rpm_limit == 100

    def test_init_without_api_key_raises_error(self) -> None:
        """Test initialization without API key raises ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY not found"):
                OpenAIClient()

    def test_init_reads_from_env(self) -> None:
        """Test initialization reads API key from environment."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "env-key-456"}):
            client = OpenAIClient()
            assert client.api_key == "env-key-456"

    @pytest.mark.asyncio
    async def test_context_manager_initializes_client(self, mock_openai_client: AsyncMock) -> None:
        """Test async context manager with injected client."""
        # Use DI to inject mock client
        async with OpenAIClient(client=mock_openai_client) as client:
            # Client should be the injected one
            assert client._client is mock_openai_client

        # Verify client was closed
        mock_openai_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_basic_request(
        self, mock_openai_client: AsyncMock, mock_openai_response: MagicMock
    ) -> None:
        """Test basic completion request."""
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        async with OpenAIClient(client=mock_openai_client) as client:
            messages = [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ]

            response = await client.complete(messages=messages)

            assert "content" in response
            assert "usage" in response
            assert "finish_reason" in response
            assert response["finish_reason"] == "stop"
            assert response["usage"]["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_complete_with_json_format(
        self, mock_openai_client: AsyncMock, mock_openai_response: MagicMock
    ) -> None:
        """Test completion with JSON response format."""
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        async with OpenAIClient(client=mock_openai_client) as client:
            messages = [{"role": "user", "content": "Generate JSON"}]
            response_format = {"type": "json_object"}

            response = await client.complete(messages=messages, response_format=response_format)

            call_args = mock_openai_client.chat.completions.create.call_args
            call_kwargs = call_args[1]
            assert call_kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_complete_without_context_manager_raises_error(
        self,
    ) -> None:
        """Test calling complete without context manager raises error."""
        client = OpenAIClient(api_key="test-key")

        with pytest.raises(RuntimeError, match="Client not initialized"):
            await client.complete(messages=[])

    @pytest.mark.asyncio
    async def test_complete_handles_none_usage(self, mock_openai_client: AsyncMock) -> None:
        """Test completion handles response with None usage."""
        response = MagicMock()
        choice = MagicMock()
        choice.message.content = "Response text"
        choice.finish_reason = "stop"
        response.choices = [choice]
        response.usage = None  # No usage info

        mock_openai_client.chat.completions.create = AsyncMock(return_value=response)

        async with OpenAIClient(client=mock_openai_client) as client:
            result = await client.complete(messages=[{"role": "user", "content": "Hi"}])

            # Should return 0 for all token counts
            assert result["usage"]["prompt_tokens"] == 0
            assert result["usage"]["completion_tokens"] == 0
            assert result["usage"]["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_recognize_food_returns_parsed_json(
        self, mock_openai_client: AsyncMock, mock_openai_response: MagicMock
    ) -> None:
        """Test food recognition returns parsed JSON."""
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        async with OpenAIClient(client=mock_openai_client) as client:
            messages = [
                {"role": "system", "content": "Identify foods"},
                {"role": "user", "content": "Image of apple"},
            ]
            schema = {"items": [{"label": "str", "quantity_g": "float"}]}

            result = await client.recognize_food(messages, schema)

            assert "items" in result
            assert len(result["items"]) == 1
            assert result["items"][0]["label"] == "Apple"
            assert result["items"][0]["quantity_g"] == 150

    @pytest.mark.asyncio
    async def test_recognize_food_uses_low_temperature(
        self, mock_openai_client: AsyncMock, mock_openai_response: MagicMock
    ) -> None:
        """Test food recognition uses low temperature for consistency."""
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        async with OpenAIClient(client=mock_openai_client) as client:
            await client.recognize_food(
                messages=[{"role": "user", "content": "Image"}],
                json_schema={},
            )

            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_recognize_food_invalid_json_raises_exception(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test food recognition raises exception on invalid JSON."""
        # Response with invalid JSON
        response = MagicMock()
        choice = MagicMock()
        choice.message.content = "Not valid JSON {{"
        choice.finish_reason = "stop"
        response.choices = [choice]
        response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        mock_openai_client.chat.completions.create = AsyncMock(return_value=response)

        async with OpenAIClient(client=mock_openai_client) as client:
            with pytest.raises(Exception, match="Invalid JSON response"):
                await client.recognize_food(
                    messages=[{"role": "user", "content": "Test"}],
                    json_schema={},
                )

    @pytest.mark.asyncio
    async def test_extract_foods_from_text_returns_parsed_json(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test text extraction returns parsed JSON."""
        response = MagicMock()
        choice = MagicMock()
        choice.message.content = '{"items": [{"label": "Pasta"}, {"label": "Salad"}]}'
        choice.finish_reason = "stop"
        response.choices = [choice]
        response.usage = MagicMock(prompt_tokens=50, completion_tokens=30, total_tokens=80)

        mock_openai_client.chat.completions.create = AsyncMock(return_value=response)

        async with OpenAIClient(client=mock_openai_client) as client:
            messages = [
                {"role": "system", "content": "Extract foods"},
                {"role": "user", "content": "I ate pasta and salad"},
            ]

            result = await client.extract_foods_from_text(messages, {})

            assert len(result["items"]) == 2
            assert result["items"][0]["label"] == "Pasta"
            assert result["items"][1]["label"] == "Salad"

    @pytest.mark.asyncio
    async def test_extract_foods_uses_low_temperature(
        self, mock_openai_client: AsyncMock, mock_openai_response: MagicMock
    ) -> None:
        """Test text extraction uses low temperature for consistency."""
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        async with OpenAIClient(client=mock_openai_client) as client:
            await client.extract_foods_from_text(
                messages=[{"role": "user", "content": "Text"}],
                json_schema={},
            )

            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs["temperature"] == 0.3
            assert call_kwargs["max_tokens"] == 1500

    @pytest.mark.asyncio
    async def test_extract_foods_invalid_json_raises_exception(
        self, mock_openai_client: AsyncMock
    ) -> None:
        """Test text extraction raises exception on invalid JSON."""
        response = MagicMock()
        choice = MagicMock()
        choice.message.content = "Invalid JSON ["
        choice.finish_reason = "stop"
        response.choices = [choice]
        response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        mock_openai_client.chat.completions.create = AsyncMock(return_value=response)

        async with OpenAIClient(client=mock_openai_client) as client:
            with pytest.raises(Exception, match="Invalid JSON response"):
                await client.extract_foods_from_text(
                    messages=[{"role": "user", "content": "Test"}],
                    json_schema={},
                )

    @pytest.mark.asyncio
    async def test_rate_limit_enforces_rpm_limit(self) -> None:
        """Test rate limiting enforces RPM limit."""
        client = OpenAIClient(api_key="test-key", rpm_limit=2)

        # Simulate 2 requests (at limit)
        await client._rate_limit()
        await client._rate_limit()

        # Third request should be delayed
        assert len(client._request_times) == 2

    @pytest.mark.asyncio
    async def test_rate_limit_removes_old_requests(self) -> None:
        """Test rate limiting removes requests older than 60 seconds."""
        client = OpenAIClient(api_key="test-key", rpm_limit=10)

        # Add old request (65 seconds ago)
        import time

        old_time = time.time() - 65.0
        client._request_times.append(old_time)

        # Make new request
        await client._rate_limit()

        # Old request should be removed
        assert old_time not in client._request_times
        assert len(client._request_times) == 1

    @pytest.mark.asyncio
    async def test_rate_limit_waits_when_at_limit(self) -> None:
        """Test rate limiting sleeps when at RPM limit."""
        import time
        from unittest.mock import patch

        client = OpenAIClient(api_key="test-key", rpm_limit=2)

        # Add 2 requests at current time (at limit)
        now = time.time()
        client._request_times = [now - 30.0, now - 15.0]  # Within 60s window

        # Mock asyncio.sleep to verify it's called
        with patch("asyncio.sleep") as mock_sleep:
            await client._rate_limit()
            # Should have called sleep since at limit
            mock_sleep.assert_called_once()
            # Wait time should be positive (60 - time_since_oldest)
            wait_time = mock_sleep.call_args[0][0]
            assert wait_time > 0

    def test_get_stats_returns_client_info(self) -> None:
        """Test get_stats returns client statistics."""
        client = OpenAIClient(
            api_key="test-key",
            model="gpt-4-turbo",
            rpm_limit=100,
        )

        stats = client.get_stats()

        assert stats["model"] == "gpt-4-turbo"
        assert stats["rpm_limit"] == 100
        assert stats["requests_last_minute"] == 0

    def test_get_stats_counts_recent_requests(self) -> None:
        """Test get_stats counts recent requests correctly."""
        import time

        client = OpenAIClient(api_key="test-key")

        # Add recent requests
        now = time.time()
        client._request_times = [now - 30, now - 20, now - 10]

        stats = client.get_stats()
        assert stats["requests_last_minute"] == 3

    def test_get_stats_excludes_old_requests(self) -> None:
        """Test get_stats excludes requests older than 60 seconds."""
        import time

        client = OpenAIClient(api_key="test-key")

        # Add mix of old and recent
        now = time.time()
        client._request_times = [
            now - 70,  # Old (excluded)
            now - 30,  # Recent
            now - 10,  # Recent
        ]

        stats = client.get_stats()
        assert stats["requests_last_minute"] == 2
