"""Stub provider implementations for testing.

These providers return fake data without calling external APIs.
Used in integration/E2E tests to test workflows without external dependencies.
"""

from infrastructure.meal.providers.stub_vision_provider import StubVisionProvider
from infrastructure.meal.providers.stub_nutrition_provider import StubNutritionProvider
from infrastructure.meal.providers.stub_barcode_provider import StubBarcodeProvider

__all__ = [
    "StubVisionProvider",
    "StubNutritionProvider",
    "StubBarcodeProvider",
]
