"""OpenAI Client v2.5.0+ - Implements IVisionProvider port.

Key Features:
- Structured outputs (native Pydantic support)
- Prompt caching (>1024 token system prompt → 50% cost reduction)
- Circuit breaker (5 failures → 60s timeout)
- Retry logic (exponential backoff)
- Cache metrics tracking
"""

# mypy: warn-unused-ignores=False

import logging
from typing import Optional, Dict, Any
import time

from openai import AsyncOpenAI, APIError
from circuitbreaker import circuit
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from domain.meal.recognition.entities.recognized_food import (
    FoodRecognitionResult,
    RecognizedFood,
)
from infrastructure.ai.openai.models import FoodRecognitionResponse
from infrastructure.ai.prompts.food_recognition import (
    FOOD_RECOGNITION_SYSTEM_PROMPT,
    TEXT_ANALYSIS_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class OpenAIVisionClient:
    """
    OpenAI GPT-4 Vision client implementing IVisionProvider port.

    This adapter uses OpenAI v2.5.0+ structured outputs to implement
    the vision provider port defined by the domain layer.

    Follows Dependency Inversion Principle:
    - Domain defines IVisionProvider interface (port)
    - Infrastructure provides OpenAIVisionClient implementation (adapter)

    Example:
        >>> from infrastructure.ai.openai.client import OpenAIVisionClient
        >>> client = OpenAIVisionClient(api_key="sk-...")
        >>> result = await client.analyze_photo("https://example.com/food.jpg")
        >>> print(f"Recognized {len(result.items)} items")
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-2024-08-06",
        temperature: float = 0.1,
    ):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o-2024-08-06 with structured outputs)
            temperature: Sampling temperature (0.1 for consistency)
        """
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._cache_stats = {"hits": 0, "misses": 0}

    @circuit(failure_threshold=5, recovery_timeout=60, name="openai_vision")  # type: ignore[misc]
    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, APIError)),
    )
    async def analyze_photo(
        self,
        photo_url: str,
        hint: Optional[str] = None,
    ) -> FoodRecognitionResult:
        """
        Analyze photo and recognize food items.

        Implements IVisionProvider.analyze_photo() port.

        Args:
            photo_url: URL of the food photo
            hint: Optional hint about the dish (e.g., "pizza", "salad")

        Returns:
            FoodRecognitionResult with recognized items

        Raises:
            APIError: On OpenAI API failures
            ValidationError: On schema validation failures
            Exception: On network or parsing errors

        Example:
            >>> result = await client.analyze_photo(
            ...     "https://example.com/pasta.jpg",
            ...     hint="pasta dish"
            ... )
            >>> for item in result.items:
            ...     print(f"{item.display_name}: {item.quantity_g}g")
        """
        start_time = time.time()

        logger.info(
            "Analyzing photo",
            extra={
                "photo_url": photo_url,
                "hint": hint,
                "model": self._model,
            },
        )

        # Build user message with vision
        user_message: Dict[str, Any] = {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": photo_url},
                }
            ],
        }

        # Add hint if provided
        if hint:
            user_message["content"].append(
                {
                    "type": "text",
                    "text": f"Dish hint: {hint}",
                }
            )

        # Call OpenAI with structured outputs
        response = await self._structured_completion(
            messages=[user_message],
            response_model=FoodRecognitionResponse,
            system_prompt=FOOD_RECOGNITION_SYSTEM_PROMPT,
        )

        # Convert to domain entity
        domain_result = self._to_domain_result(response)

        # Track processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Photo analysis complete",
            extra={
                "item_count": len(domain_result.items),
                "confidence": domain_result.confidence,
                "processing_time_ms": processing_time_ms,
                "dish_name": response.dish_title,
            },
        )

        # Inject processing time
        return FoodRecognitionResult(
            items=domain_result.items,
            dish_name=response.dish_title or None,
            confidence=domain_result.confidence,
            processing_time_ms=processing_time_ms,
        )

    @circuit(failure_threshold=5, recovery_timeout=60, name="openai_text")  # type: ignore[misc]
    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, APIError)),
    )
    async def analyze_text(
        self,
        description: str,
    ) -> FoodRecognitionResult:
        """
        Extract food items from text description.

        Implements IVisionProvider.analyze_text() port.

        Args:
            description: Text description of the meal

        Returns:
            FoodRecognitionResult with extracted items

        Raises:
            APIError: On OpenAI API failures
            ValidationError: On schema validation failures
            Exception: On network or parsing errors

        Example:
            >>> result = await client.analyze_text(
            ...     "I ate 150g of grilled chicken and 200g of rice"
            ... )
            >>> result.item_count()
            2
        """
        start_time = time.time()

        logger.info(
            "Analyzing text",
            extra={
                "text_length": len(description),
                "model": self._model,
            },
        )

        # Build user message
        user_message = {
            "role": "user",
            "content": description,
        }

        # Call OpenAI with structured outputs
        response = await self._structured_completion(
            messages=[user_message],
            response_model=FoodRecognitionResponse,
            system_prompt=TEXT_ANALYSIS_SYSTEM_PROMPT,
        )

        # Convert to domain entity
        domain_result = self._to_domain_result(response)

        # Track processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "Text analysis complete",
            extra={
                "item_count": len(domain_result.items),
                "confidence": domain_result.confidence,
                "processing_time_ms": processing_time_ms,
            },
        )

        # Inject processing time
        return FoodRecognitionResult(
            items=domain_result.items,
            dish_name=response.dish_title or None,
            confidence=domain_result.confidence,
            processing_time_ms=processing_time_ms,
        )

    async def _structured_completion(
        self,
        messages: list[Dict[str, Any]],
        response_model: type[FoodRecognitionResponse],
        system_prompt: str,
    ) -> FoodRecognitionResponse:
        """
        Execute OpenAI completion with structured output.

        Uses beta.chat.completions.parse() for native Pydantic support.

        Args:
            messages: User messages (with images if Vision)
            response_model: Pydantic model for response schema
            system_prompt: System prompt (>1024 tokens for caching)

        Returns:
            Parsed Pydantic model instance

        Raises:
            APIError: On API failures
            ValidationError: On schema validation failures
        """
        # Prepend system message
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]

        logger.debug(
            "Calling OpenAI structured completion",
            extra={
                "model": self._model,
                "response_model": response_model.__name__,
                "message_count": len(full_messages),
            },
        )

        # Call OpenAI with structured outputs (v2.5.0+)
        response = await self._client.beta.chat.completions.parse(
            model=self._model,
            messages=full_messages,  # type: ignore[arg-type]
            response_format=response_model,  # Native Pydantic!
            temperature=self._temperature,
        )

        # Track cache metrics
        usage = response.usage
        if not usage:
            raise ValueError("OpenAI response missing usage information")
        if hasattr(usage, "prompt_tokens_details"):
            details = getattr(usage, "prompt_tokens_details", None)
            if details:
                cached = getattr(details, "cached_tokens", 0)
                # Handle both real int and mock objects
                try:
                    if cached > 0:
                        self._cache_stats["hits"] += 1
                        logger.info(
                            "OpenAI cache hit",
                            extra={"cached_tokens": cached},
                        )
                    else:
                        self._cache_stats["misses"] += 1
                except (TypeError, AttributeError):
                    # Mock object comparison, skip tracking
                    pass

        # Log token usage
        logger.info(
            "OpenAI response received",
            extra={
                "model": self._model,
                "total_tokens": usage.total_tokens,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
            },
        )

        # Return parsed Pydantic model
        parsed = response.choices[0].message.parsed
        if not parsed:
            raise ValueError("OpenAI returned empty parsed response")

        return parsed

    def _to_domain_result(
        self,
        response: FoodRecognitionResponse,
    ) -> FoodRecognitionResult:
        """
        Convert Pydantic response to domain entity.

        Maps infrastructure model (FoodRecognitionResponse) to
        domain entity (FoodRecognitionResult).

        Args:
            response: Pydantic model from OpenAI

        Returns:
            Domain entity FoodRecognitionResult
        """
        # Convert items
        domain_items = [
            RecognizedFood(
                label=item.label,
                display_name=item.display_name,
                quantity_g=item.quantity_g,
                confidence=item.confidence,
            )
            for item in response.items
        ]

        # Handle empty response
        if not domain_items:
            # Return single low-confidence placeholder to satisfy domain invariant
            domain_items = [
                RecognizedFood(
                    label="unknown",
                    display_name="Non riconosciuto",
                    quantity_g=100.0,
                    confidence=0.1,
                )
            ]

        # Create domain result (confidence auto-calculated)
        return FoodRecognitionResult(
            items=domain_items,
            dish_name=response.dish_title or None,
        )

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache hits, misses, and hit rate

        Example:
            >>> stats = client.get_cache_stats()
            >>> print(f"Cache hit rate: {stats['hit_rate_percent']}%")
        """
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total * 100) if total > 0 else 0

        return {
            **self._cache_stats,
            "hit_rate_percent": round(hit_rate, 2),
        }
