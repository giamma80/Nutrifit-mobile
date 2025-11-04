"""Provider Factory for AI Services.

Environment-based provider selection with graceful fallback to stubs.
Strategy:
- .env (runtime): VISION_PROVIDER=openai, NUTRITION_PROVIDER=usda, etc.
- .env.test (pytest): VISION_PROVIDER=stub, NUTRITION_PROVIDER=stub, etc.
- Default: stub (safe fallback if env vars not set)

Usage:
    from infrastructure.meal.providers.factory import (
        create_vision_provider,
        create_nutrition_provider,
        create_barcode_provider,
    )

    vision = create_vision_provider()  # Returns stub or real based on env
    nutrition = create_nutrition_provider()
    barcode = create_barcode_provider()
"""

import os
from typing import Optional

# Protocol interfaces (Dependency Inversion)
from domain.meal.recognition.ports.vision_provider import IVisionProvider
from domain.meal.nutrition.ports.nutrition_provider import INutritionProvider
from domain.meal.barcode.ports.barcode_provider import IBarcodeProvider

# Stub providers (fast, deterministic)
from infrastructure.meal.providers.stub_vision_provider import StubVisionProvider
from infrastructure.meal.providers.stub_nutrition_provider import StubNutritionProvider
from infrastructure.meal.providers.stub_barcode_provider import StubBarcodeProvider

# Real providers (require API keys)
from infrastructure.ai.openai.client import OpenAIVisionClient
from infrastructure.external_apis.usda.client import USDAClient
from infrastructure.external_apis.openfoodfacts.client import OpenFoodFactsClient


def create_vision_provider() -> IVisionProvider:
    """Create vision provider based on VISION_PROVIDER env var.

    Environment variable: VISION_PROVIDER
    Values:
        - "openai": OpenAI Vision API (requires OPENAI_API_KEY)
        - "stub": Stub provider (default)

    Returns:
        IVisionProvider: Vision provider instance

    Example:
        # In .env (production):
        VISION_PROVIDER=openai
        OPENAI_API_KEY=sk-...

        # In .env.test (testing):
        VISION_PROVIDER=stub
    """
    mode = os.getenv("VISION_PROVIDER", "stub").lower()

    if mode == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "VISION_PROVIDER=openai but OPENAI_API_KEY not set. "
                "Set OPENAI_API_KEY in .env or use VISION_PROVIDER=stub"
            )
        return OpenAIVisionClient(api_key=api_key)

    # Default: stub (safe fallback)
    return StubVisionProvider()


def create_nutrition_provider() -> INutritionProvider:
    """Create nutrition provider based on NUTRITION_PROVIDER env var.

    Environment variable: NUTRITION_PROVIDER
    Values:
        - "usda": USDA FoodData Central API (requires USDA_API_KEY)
        - "stub": Stub provider (default)

    Returns:
        INutritionProvider: Nutrition provider instance

    Example:
        # In .env (production):
        NUTRITION_PROVIDER=usda
        USDA_API_KEY=abc123...

        # In .env.test (testing):
        NUTRITION_PROVIDER=stub
    """
    mode = os.getenv("NUTRITION_PROVIDER", "stub").lower()

    if mode == "usda":
        api_key = os.getenv("AI_USDA_API_KEY")
        if not api_key:
            raise ValueError(
                "NUTRITION_PROVIDER=usda but AI_USDA_API_KEY not set. "
                "Set AI_USDA_API_KEY in .env or use NUTRITION_PROVIDER=stub"
            )
        return USDAClient(api_key=api_key)

    # Default: stub (safe fallback)
    return StubNutritionProvider()


def create_barcode_provider() -> IBarcodeProvider:
    """Create barcode provider based on BARCODE_PROVIDER env var.

    Environment variable: BARCODE_PROVIDER
    Values:
        - "openfoodfacts": OpenFoodFacts API (public, no key required)
        - "stub": Stub provider (default)

    Returns:
        IBarcodeProvider: Barcode provider instance

    Example:
        # In .env (production):
        BARCODE_PROVIDER=openfoodfacts

        # In .env.test (testing):
        BARCODE_PROVIDER=stub
    """
    mode = os.getenv("BARCODE_PROVIDER", "stub").lower()

    if mode == "openfoodfacts":
        return OpenFoodFactsClient()

    # Default: stub (safe fallback)
    return StubBarcodeProvider()


# Singleton instances (lazy initialization)
_vision_provider: Optional[IVisionProvider] = None
_nutrition_provider: Optional[INutritionProvider] = None
_barcode_provider: Optional[IBarcodeProvider] = None


def get_vision_provider() -> IVisionProvider:
    """Get singleton vision provider instance.

    Returns:
        IVisionProvider: Cached vision provider instance
    """
    global _vision_provider
    if _vision_provider is None:
        _vision_provider = create_vision_provider()
    return _vision_provider


def get_nutrition_provider() -> INutritionProvider:
    """Get singleton nutrition provider instance.

    Returns:
        INutritionProvider: Cached nutrition provider instance
    """
    global _nutrition_provider
    if _nutrition_provider is None:
        _nutrition_provider = create_nutrition_provider()
    return _nutrition_provider


def get_barcode_provider() -> IBarcodeProvider:
    """Get singleton barcode provider instance.

    Returns:
        IBarcodeProvider: Cached barcode provider instance
    """
    global _barcode_provider
    if _barcode_provider is None:
        _barcode_provider = create_barcode_provider()
    return _barcode_provider


def reset_providers() -> None:
    """Reset all singleton provider instances.

    Useful for testing to force re-creation with different env vars.
    """
    global _vision_provider, _nutrition_provider, _barcode_provider
    _vision_provider = None
    _nutrition_provider = None
    _barcode_provider = None
