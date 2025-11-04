"""Unit tests for provider factory (P7.0.4).

Tests environment-based provider selection with graceful fallback.
"""

import pytest

from infrastructure.meal.providers.factory import (
    create_vision_provider,
    create_nutrition_provider,
    create_barcode_provider,
    get_vision_provider,
    get_nutrition_provider,
    get_barcode_provider,
    reset_providers,
)
from infrastructure.meal.providers.stub_vision_provider import StubVisionProvider
from infrastructure.meal.providers.stub_nutrition_provider import StubNutritionProvider
from infrastructure.meal.providers.stub_barcode_provider import StubBarcodeProvider
from infrastructure.ai.openai.client import OpenAIVisionClient
from infrastructure.external_apis.usda.client import USDAClient
from infrastructure.external_apis.openfoodfacts.client import OpenFoodFactsClient


class TestVisionProviderFactory:
    """Test create_vision_provider() factory function."""

    def test_default_to_stub_when_env_not_set(self, monkeypatch):
        """Should return stub provider when VISION_PROVIDER not set."""
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        provider = create_vision_provider()
        assert isinstance(provider, StubVisionProvider)

    def test_explicit_stub_selection(self, monkeypatch):
        """Should return stub provider when VISION_PROVIDER=stub."""
        monkeypatch.setenv("VISION_PROVIDER", "stub")
        provider = create_vision_provider()
        assert isinstance(provider, StubVisionProvider)

    def test_openai_provider_with_api_key(self, monkeypatch):
        """Should return OpenAI provider when VISION_PROVIDER=openai and API key set."""
        monkeypatch.setenv("VISION_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        provider = create_vision_provider()
        assert isinstance(provider, OpenAIVisionClient)

    def test_openai_provider_without_api_key_raises_error(self, monkeypatch):
        """Should raise ValueError when VISION_PROVIDER=openai but no API key."""
        monkeypatch.setenv("VISION_PROVIDER", "openai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with pytest.raises(ValueError, match="OPENAI_API_KEY not set"):
            create_vision_provider()

    def test_case_insensitive_provider_selection(self, monkeypatch):
        """Should handle case-insensitive provider names."""
        monkeypatch.setenv("VISION_PROVIDER", "STUB")
        provider = create_vision_provider()
        assert isinstance(provider, StubVisionProvider)

        monkeypatch.setenv("VISION_PROVIDER", "OpenAI")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        provider = create_vision_provider()
        assert isinstance(provider, OpenAIVisionClient)


class TestNutritionProviderFactory:
    """Test create_nutrition_provider() factory function."""

    def test_default_to_stub_when_env_not_set(self, monkeypatch):
        """Should return stub provider when NUTRITION_PROVIDER not set."""
        monkeypatch.delenv("NUTRITION_PROVIDER", raising=False)
        provider = create_nutrition_provider()
        assert isinstance(provider, StubNutritionProvider)

    def test_explicit_stub_selection(self, monkeypatch):
        """Should return stub provider when NUTRITION_PROVIDER=stub."""
        monkeypatch.setenv("NUTRITION_PROVIDER", "stub")
        provider = create_nutrition_provider()
        assert isinstance(provider, StubNutritionProvider)

    def test_usda_provider_with_api_key(self, monkeypatch):
        """Should return USDA provider when NUTRITION_PROVIDER=usda and API key set."""
        monkeypatch.setenv("NUTRITION_PROVIDER", "usda")
        monkeypatch.setenv("AI_USDA_API_KEY", "test-usda-key")
        provider = create_nutrition_provider()
        assert isinstance(provider, USDAClient)

    def test_usda_provider_without_api_key_raises_error(self, monkeypatch):
        """Should raise ValueError when NUTRITION_PROVIDER=usda but no API key."""
        monkeypatch.setenv("NUTRITION_PROVIDER", "usda")
        monkeypatch.delenv("AI_USDA_API_KEY", raising=False)

        with pytest.raises(ValueError, match="AI_USDA_API_KEY not set"):
            create_nutrition_provider()

    def test_case_insensitive_provider_selection(self, monkeypatch):
        """Should handle case-insensitive provider names."""
        monkeypatch.setenv("NUTRITION_PROVIDER", "USDA")
        monkeypatch.setenv("AI_USDA_API_KEY", "test-key")
        provider = create_nutrition_provider()
        assert isinstance(provider, USDAClient)


class TestBarcodeProviderFactory:
    """Test create_barcode_provider() factory function."""

    def test_default_to_stub_when_env_not_set(self, monkeypatch):
        """Should return stub provider when BARCODE_PROVIDER not set."""
        monkeypatch.delenv("BARCODE_PROVIDER", raising=False)
        provider = create_barcode_provider()
        assert isinstance(provider, StubBarcodeProvider)

    def test_explicit_stub_selection(self, monkeypatch):
        """Should return stub provider when BARCODE_PROVIDER=stub."""
        monkeypatch.setenv("BARCODE_PROVIDER", "stub")
        provider = create_barcode_provider()
        assert isinstance(provider, StubBarcodeProvider)

    def test_openfoodfacts_provider_selection(self, monkeypatch):
        """Should return OpenFoodFacts provider when BARCODE_PROVIDER=openfoodfacts."""
        monkeypatch.setenv("BARCODE_PROVIDER", "openfoodfacts")
        provider = create_barcode_provider()
        assert isinstance(provider, OpenFoodFactsClient)

    def test_openfoodfacts_no_api_key_required(self, monkeypatch):
        """OpenFoodFacts provider should work without API key (public API)."""
        monkeypatch.setenv("BARCODE_PROVIDER", "openfoodfacts")
        monkeypatch.delenv("OPENFOODFACTS_API_KEY", raising=False)

        # Should not raise
        provider = create_barcode_provider()
        assert isinstance(provider, OpenFoodFactsClient)

    def test_case_insensitive_provider_selection(self, monkeypatch):
        """Should handle case-insensitive provider names."""
        monkeypatch.setenv("BARCODE_PROVIDER", "OpenFoodFacts")
        provider = create_barcode_provider()
        assert isinstance(provider, OpenFoodFactsClient)


class TestSingletonGetters:
    """Test singleton get_*_provider() functions."""

    def setup_method(self):
        """Reset singletons before each test."""
        reset_providers()

    def test_get_vision_provider_singleton(self, monkeypatch):
        """get_vision_provider() should return same instance on multiple calls."""
        monkeypatch.setenv("VISION_PROVIDER", "stub")

        provider1 = get_vision_provider()
        provider2 = get_vision_provider()

        assert provider1 is provider2  # Same instance

    def test_get_nutrition_provider_singleton(self, monkeypatch):
        """get_nutrition_provider() should return same instance on multiple calls."""
        monkeypatch.setenv("NUTRITION_PROVIDER", "stub")

        provider1 = get_nutrition_provider()
        provider2 = get_nutrition_provider()

        assert provider1 is provider2  # Same instance

    def test_get_barcode_provider_singleton(self, monkeypatch):
        """get_barcode_provider() should return same instance on multiple calls."""
        monkeypatch.setenv("BARCODE_PROVIDER", "stub")

        provider1 = get_barcode_provider()
        provider2 = get_barcode_provider()

        assert provider1 is provider2  # Same instance

    def test_reset_providers_clears_singletons(self, monkeypatch):
        """reset_providers() should clear cached instances."""
        monkeypatch.setenv("VISION_PROVIDER", "stub")

        provider1 = get_vision_provider()
        reset_providers()
        provider2 = get_vision_provider()

        assert provider1 is not provider2  # Different instances after reset

    def test_singleton_respects_env_changes_after_reset(self, monkeypatch):
        """After reset, should use new environment configuration."""
        # First call with stub
        monkeypatch.setenv("VISION_PROVIDER", "stub")
        provider1 = get_vision_provider()
        assert isinstance(provider1, StubVisionProvider)

        # Reset and change env
        reset_providers()
        monkeypatch.setenv("VISION_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        provider2 = get_vision_provider()
        assert isinstance(provider2, OpenAIVisionClient)

        # Different instances, different types
        assert provider1 is not provider2  # type: ignore[comparison-overlap]
        assert type(provider1) is not type(provider2)  # type: ignore[comparison-overlap]


class TestFactoryIntegration:
    """Integration tests for factory behavior."""

    def test_all_factories_work_with_stub_default(self, monkeypatch):
        """All factories should default to stub when no env vars set."""
        monkeypatch.delenv("VISION_PROVIDER", raising=False)
        monkeypatch.delenv("NUTRITION_PROVIDER", raising=False)
        monkeypatch.delenv("BARCODE_PROVIDER", raising=False)

        vision = create_vision_provider()
        nutrition = create_nutrition_provider()
        barcode = create_barcode_provider()

        assert isinstance(vision, StubVisionProvider)
        assert isinstance(nutrition, StubNutritionProvider)
        assert isinstance(barcode, StubBarcodeProvider)

    def test_mixed_real_and_stub_providers(self, monkeypatch):
        """Should support mixing real and stub providers."""
        # Vision: real
        monkeypatch.setenv("VISION_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Nutrition: stub
        monkeypatch.setenv("NUTRITION_PROVIDER", "stub")

        # Barcode: real
        monkeypatch.setenv("BARCODE_PROVIDER", "openfoodfacts")

        vision = create_vision_provider()
        nutrition = create_nutrition_provider()
        barcode = create_barcode_provider()

        assert isinstance(vision, OpenAIVisionClient)
        assert isinstance(nutrition, StubNutritionProvider)
        assert isinstance(barcode, OpenFoodFactsClient)

    def test_env_test_configuration(self, monkeypatch):
        """Test configuration from .env.test (all stubs)."""
        monkeypatch.setenv("VISION_PROVIDER", "stub")
        monkeypatch.setenv("NUTRITION_PROVIDER", "stub")
        monkeypatch.setenv("BARCODE_PROVIDER", "stub")

        vision = create_vision_provider()
        nutrition = create_nutrition_provider()
        barcode = create_barcode_provider()

        assert isinstance(vision, StubVisionProvider)
        assert isinstance(nutrition, StubNutritionProvider)
        assert isinstance(barcode, StubBarcodeProvider)

    def test_production_configuration(self, monkeypatch):
        """Test configuration from .env (all real)."""
        monkeypatch.setenv("VISION_PROVIDER", "openai")
        monkeypatch.setenv("OPENAI_API_KEY", "prod-key")
        monkeypatch.setenv("NUTRITION_PROVIDER", "usda")
        monkeypatch.setenv("AI_USDA_API_KEY", "prod-usda-key")
        monkeypatch.setenv("BARCODE_PROVIDER", "openfoodfacts")

        vision = create_vision_provider()
        nutrition = create_nutrition_provider()
        barcode = create_barcode_provider()

        assert isinstance(vision, OpenAIVisionClient)
        assert isinstance(nutrition, USDAClient)
        assert isinstance(barcode, OpenFoodFactsClient)
