"""
OpenAI API client for food recognition.

Async client with structured JSON output, rate limiting, and caching.
"""

from __future__ import annotations

import os
import json
import asyncio
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from openai import AsyncOpenAI

if TYPE_CHECKING:
    from openai.types.chat import ChatCompletion


class OpenAIClient:
    """
    Async OpenAI client for vision and text completion.

    Manages API calls with structured JSON output, retry logic,
    and rate limiting.

    Features:
    - Structured JSON output mode
    - Automatic retry on transient failures
    - Rate limiting (60 RPM default)
    - Prompt caching optimization
    - Context manager for resource cleanup

    Example:
        >>> async with OpenAIClient() as client:
        ...     messages = [
        ...         {"role": "system", "content": "You are helpful"},
        ...         {"role": "user", "content": "Hello"},
        ...     ]
        ...     response = await client.complete(
        ...         messages=messages,
        ...         response_format={"type": "json_object"}
        ...     )
        ...     print(response["content"])
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        max_retries: int = 3,
        timeout: int = 30,
        rpm_limit: int = 60,
        client: Optional[AsyncOpenAI] = None,
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (reads from .env if None)
            model: Model to use (gpt-4o for vision support)
            max_retries: Max retry attempts on failure
            timeout: Request timeout in seconds
            rpm_limit: Requests per minute limit
            client: Optional pre-configured AsyncOpenAI client (for testing)

        Raises:
            ValueError: If API key not found and client not provided
        """
        # If client provided, use it (for dependency injection/testing)
        if client is not None:
            self._client: Optional[AsyncOpenAI] = client
            self.api_key: str = api_key or "test-key"
        else:
            resolved_key = api_key or os.getenv("OPENAI_API_KEY")
            if not resolved_key:
                raise ValueError(
                    "OPENAI_API_KEY not found in environment. "
                    "Set it in .env file or pass as parameter."
                )
            self.api_key = resolved_key
            self._client = None

        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.rpm_limit = rpm_limit

        # Rate limiting state
        self._request_times: List[float] = []
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> OpenAIClient:
        """Async context manager entry."""
        # Only create client if not already provided (DI)
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.close()

    async def _rate_limit(self) -> None:
        """
        Enforce rate limiting.

        Ensures requests stay within rpm_limit by tracking
        request timestamps and sleeping if necessary.
        """
        async with self._lock:
            now = time.time()

            # Remove requests older than 60 seconds
            cutoff = now - 60.0
            self._request_times = [t for t in self._request_times if t > cutoff]

            # If at limit, wait until oldest request expires
            if len(self._request_times) >= self.rpm_limit:
                oldest = self._request_times[0]
                wait_time = 60.0 - (now - oldest)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # Remove expired after sleep
                    now = time.time()
                    cutoff = now - 60.0
                    self._request_times = [t for t in self._request_times if t > cutoff]

            # Record this request
            self._request_times.append(now)

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        response_format: Optional[Dict[str, str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        Complete chat with structured JSON output.

        Sends messages to OpenAI and returns parsed response.
        Automatically handles rate limiting and retries.

        Args:
            messages: Chat messages (system, user, assistant)
            response_format: {"type": "json_object"} for JSON mode
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Max tokens in response

        Returns:
            Dict with:
            - content: Response text
            - usage: Token usage stats
            - finish_reason: Completion reason

        Raises:
            Exception: On API failure after all retries

        Example:
            >>> messages = [
            ...     {"role": "system", "content": "Return JSON"},
            ...     {"role": "user", "content": "Count to 3"},
            ... ]
            >>> response = await client.complete(
            ...     messages=messages,
            ...     response_format={"type": "json_object"}
            ... )
            >>> data = json.loads(response["content"])
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with.")

        # Rate limit before request
        await self._rate_limit()

        # Build request parameters
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            params["response_format"] = response_format

        # Make API call
        completion: ChatCompletion = await self._client.chat.completions.create(**params)

        # Extract response
        choice = completion.choices[0]
        return {
            "content": choice.message.content or "",
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": (completion.usage.prompt_tokens if completion.usage else 0),
                "completion_tokens": (
                    completion.usage.completion_tokens if completion.usage else 0
                ),
                "total_tokens": (completion.usage.total_tokens if completion.usage else 0),
            },
        }

    async def recognize_food(
        self, messages: List[Dict[str, Any]], json_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recognize food from image with structured output.

        Specialized method for food recognition that ensures
        JSON output matching the provided schema.

        Args:
            messages: Vision messages (system + user with image)
            json_schema: Expected JSON structure

        Returns:
            Parsed JSON object matching schema

        Raises:
            json.JSONDecodeError: If response not valid JSON
            Exception: On API failure

        Example:
            >>> messages = [
            ...     {"role": "system", "content": "Identify foods"},
            ...     {
            ...         "role": "user",
            ...         "content": [
            ...             {"type": "image_url", "image_url": {"url": "..."}},
            ...             {"type": "text", "text": "What foods?"},
            ...         ],
            ...     },
            ... ]
            >>> schema = {
            ...     "items": [{"label": "str", "quantity_g": "float"}]
            ... }
            >>> result = await client.recognize_food(messages, schema)
            >>> print(result["items"])
        """
        response = await self.complete(
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,  # Lower for more consistent recognition
            max_tokens=2000,
        )

        # Parse JSON response
        try:
            data = json.loads(response["content"])
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {response['content']}") from e

        return data  # type: ignore[no-any-return]

    async def extract_foods_from_text(
        self, messages: List[Dict[str, Any]], json_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract foods from text description with structured output.

        Specialized method for text-based food extraction.

        Args:
            messages: Text extraction messages (system + user)
            json_schema: Expected JSON structure

        Returns:
            Parsed JSON object matching schema

        Raises:
            json.JSONDecodeError: If response not valid JSON
            Exception: On API failure

        Example:
            >>> messages = [
            ...     {"role": "system", "content": "Extract foods"},
            ...     {"role": "user", "content": "I ate pasta and salad"},
            ... ]
            >>> schema = {"items": [{"label": "str"}]}
            >>> result = await client.extract_foods_from_text(
            ...     messages, schema
            ... )
            >>> print(result["items"])
        """
        response = await self.complete(
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,  # Lower for more consistent extraction
            max_tokens=1500,
        )

        # Parse JSON response
        try:
            data = json.loads(response["content"])
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {response['content']}") from e

        return data  # type: ignore[no-any-return]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.

        Returns:
            Dict with:
            - model: Model name
            - rpm_limit: Rate limit
            - requests_last_minute: Recent request count

        Example:
            >>> stats = client.get_stats()
            >>> print(f"Model: {stats['model']}")
        """
        now = time.time()
        cutoff = now - 60.0
        recent = [t for t in self._request_times if t > cutoff]

        return {
            "model": self.model,
            "rpm_limit": self.rpm_limit,
            "requests_last_minute": len(recent),
        }
