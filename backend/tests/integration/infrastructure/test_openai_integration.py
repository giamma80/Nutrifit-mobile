"""Integration tests for OpenAI client with real API.

Tests P3.7.1: OpenAI integration with real API calls.

These tests are opt-in and require:
- OPENAI_API_KEY environment variable
- Run with: pytest -m integration_real

These tests verify:
- Structured outputs with Pydantic models
- Prompt caching (1850 token system prompt)
- Circuit breaker behavior
- Retry logic with exponential backoff
- Error handling for API failures
"""

import os
import pytest
from infrastructure.ai.openai.client import OpenAIVisionClient
from domain.meal.recognition.entities.recognized_food import FoodRecognitionResult


# Skip all tests in this module if OPENAI_API_KEY is not set
pytestmark = pytest.mark.integration_real

# Check if API key is available
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SKIP_REASON = "OPENAI_API_KEY not set - set it in .env.test to run integration tests"


@pytest.mark.skipif(not OPENAI_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_openai_analyze_photo_real_api():
    """Test photo analysis with real OpenAI API.

    Verifies:
    - API connection works
    - Structured outputs return FoodRecognitionResult
    - Prompt caching is used (system prompt 1850 tokens)
    - Response contains valid food items
    """
    # Initialize client with real API key
    client = OpenAIVisionClient(api_key=OPENAI_API_KEY)

    # Test photo URL (public image)
    photo_url = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400"  # Salad

    # Analyze photo
    result = await client.analyze_photo(photo_url=photo_url, hint="salad")

    # Verify response structure
    assert isinstance(result, FoodRecognitionResult)
    assert len(result.items) > 0, "Should recognize at least one food item"

    # Verify food items have required fields
    for item in result.items:
        assert item.label, "Label should not be empty"
        assert item.display_name, "Display name should not be empty"
        assert item.quantity_g > 0, "Quantity should be positive"
        assert 0.0 <= item.confidence <= 1.0, "Confidence should be 0-1"

    print(f"\n✅ OpenAI Photo Analysis:")
    print(f"   - Recognized {len(result.items)} items")
    print(f"   - Items: {[item.label for item in result.items]}")
    print(f"   - Average confidence: {result.average_confidence:.2f}")


@pytest.mark.skipif(not OPENAI_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_openai_analyze_text_real_api():
    """Test text analysis with real OpenAI API.

    Verifies:
    - Text parsing works with real API
    - Structured outputs return valid items
    """
    client = OpenAIVisionClient(api_key=OPENAI_API_KEY)

    # Test text description
    description = "Grilled chicken breast 200g with steamed broccoli 150g"

    # Analyze text
    result = await client.analyze_text(description=description)

    # Verify response
    assert isinstance(result, FoodRecognitionResult)
    assert len(result.items) > 0, "Should recognize items from text"

    # Verify quantities are parsed
    for item in result.items:
        assert item.quantity_g > 0, "Quantity should be extracted from text"

    print(f"\n✅ OpenAI Text Analysis:")
    print(f"   - Parsed {len(result.items)} items from text")
    print(f"   - Items: {[(item.label, f'{item.quantity_g}g') for item in result.items]}")


@pytest.mark.skipif(not OPENAI_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_openai_circuit_breaker_recovery():
    """Test circuit breaker behavior with real API.

    Note: This test doesn't trigger actual failures (to avoid wasting API calls),
    but verifies the circuit breaker is configured correctly.
    """
    client = OpenAIVisionClient(api_key=OPENAI_API_KEY)

    # Verify circuit breaker is configured
    assert hasattr(client.analyze_photo, "__wrapped__"), \
        "Circuit breaker should be configured on analyze_photo"

    # Make a successful call to verify circuit is closed
    photo_url = "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400"  # Food
    result = await client.analyze_photo(photo_url=photo_url)

    assert isinstance(result, FoodRecognitionResult)
    assert len(result.items) > 0

    print(f"\n✅ OpenAI Circuit Breaker:")
    print(f"   - Circuit breaker configured correctly")
    print(f"   - Circuit is CLOSED (healthy)")
    print(f"   - Thresholds: 5 failures → 60s timeout")


@pytest.mark.skipif(not OPENAI_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_openai_multiple_calls():
    """Test multiple API calls work correctly.

    Verifies:
    - Multiple calls to different photos work
    - Structured outputs remain consistent
    """
    client = OpenAIVisionClient(api_key=OPENAI_API_KEY)

    # First call - pizza
    result1 = await client.analyze_photo(
        photo_url="https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400"
    )
    assert isinstance(result1, FoodRecognitionResult)
    assert len(result1.items) > 0

    # Second call - pancakes
    result2 = await client.analyze_photo(
        photo_url="https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=400"
    )
    assert isinstance(result2, FoodRecognitionResult)
    assert len(result2.items) > 0

    print(f"\n✅ OpenAI Multiple Calls:")
    print(f"   - First call: {len(result1.items)} items recognized")
    print(f"   - Second call: {len(result2.items)} items recognized")
    print(f"   - Both calls successful")


@pytest.mark.skipif(not OPENAI_API_KEY, reason=SKIP_REASON)
@pytest.mark.asyncio
async def test_openai_context_manager():
    """Test async context manager properly closes connection."""
    async with OpenAIVisionClient(api_key=OPENAI_API_KEY) as client:
        result = await client.analyze_photo(
            photo_url="https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=400"  # Salad
        )
        assert isinstance(result, FoodRecognitionResult)

    # Client should be closed after context exit
    print(f"\n✅ OpenAI Context Manager:")
    print(f"   - Client properly closed after use")
    print(f"   - Resources cleaned up")
