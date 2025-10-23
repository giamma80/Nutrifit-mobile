"""Unit tests for BarcodeService.

Tests service orchestration with mocked barcode provider.
"""

import pytest
from typing import Optional

from domain.meal.barcode.entities import BarcodeProduct
from domain.meal.barcode.services import BarcodeService
from domain.meal.nutrition.entities import NutrientProfile


# Mock provider implementation for testing
class MockBarcodeProvider:
    """Mock barcode provider for testing."""

    def __init__(
        self,
        result: Optional[BarcodeProduct] = None,
        should_raise: bool = False,
    ):
        self.result = result
        self.should_raise = should_raise
        self.lookup_calls: list[str] = []

    async def lookup_barcode(self, barcode: str) -> Optional[BarcodeProduct]:
        self.lookup_calls.append(barcode)
        if self.should_raise:
            raise Exception("Barcode API error")
        return self.result


class TestLookup:
    """Test suite for lookup method."""

    @pytest.mark.asyncio
    async def test_lookup_returns_product_when_found(self) -> None:
        """Test successful barcode lookup."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            source="BARCODE_DB",
            confidence=0.95,
        )

        mock_product = BarcodeProduct(
            barcode="8001505005707",
            name="Galletti Biscuits",
            brand="Mulino Bianco",
            nutrients=nutrients,
        )

        provider = MockBarcodeProvider(result=mock_product)
        service = BarcodeService(provider)

        result = await service.lookup("8001505005707")

        assert result is not None
        assert result.barcode == "8001505005707"
        assert result.name == "Galletti Biscuits"
        assert result.brand == "Mulino Bianco"

    @pytest.mark.asyncio
    async def test_lookup_returns_none_when_not_found(self) -> None:
        """Test barcode lookup when product not found."""
        provider = MockBarcodeProvider(result=None)
        service = BarcodeService(provider)

        result = await service.lookup("9999999999999")

        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_passes_barcode_to_provider(self) -> None:
        """Test that barcode is passed to provider."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        mock_product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        provider = MockBarcodeProvider(result=mock_product)
        service = BarcodeService(provider)

        await service.lookup("8001505005707")

        assert len(provider.lookup_calls) == 1
        assert provider.lookup_calls[0] == "8001505005707"

    @pytest.mark.asyncio
    async def test_lookup_cleans_barcode_before_lookup(self) -> None:
        """Test that barcode is cleaned (spaces/dashes removed)."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
        )

        mock_product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        provider = MockBarcodeProvider(result=mock_product)
        service = BarcodeService(provider)

        # Barcode with spaces and dashes
        await service.lookup("800-1505-005707")

        # Should be cleaned before passing to provider
        assert provider.lookup_calls[0] == "8001505005707"

        provider.lookup_calls.clear()

        await service.lookup("800 1505 005707")
        assert provider.lookup_calls[0] == "8001505005707"

    @pytest.mark.asyncio
    async def test_lookup_raises_if_barcode_empty(self) -> None:
        """Test that empty barcode raises ValueError."""
        provider = MockBarcodeProvider()
        service = BarcodeService(provider)

        with pytest.raises(ValueError, match="Barcode cannot be empty"):
            await service.lookup("")

        with pytest.raises(ValueError, match="Barcode cannot be empty"):
            await service.lookup("   ")

    @pytest.mark.asyncio
    async def test_lookup_raises_if_barcode_not_alphanumeric(self) -> None:
        """Test that non-alphanumeric barcode raises ValueError."""
        provider = MockBarcodeProvider()
        service = BarcodeService(provider)

        with pytest.raises(ValueError, match="must be alphanumeric"):
            await service.lookup("800@150#500")

    @pytest.mark.asyncio
    async def test_lookup_raises_exception_on_provider_failure(self) -> None:
        """Test that provider exceptions are propagated."""
        provider = MockBarcodeProvider(should_raise=True)
        service = BarcodeService(provider)

        with pytest.raises(Exception, match="Barcode API error"):
            await service.lookup("8001505005707")


class TestValidateProduct:
    """Test suite for validate_product method."""

    @pytest.mark.asyncio
    async def test_validates_high_confidence_product(self) -> None:
        """Test validation passes for high confidence."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            source="BARCODE_DB",
            confidence=0.95,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        provider = MockBarcodeProvider()
        service = BarcodeService(provider)

        is_valid = await service.validate_product(product)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validates_low_confidence_product(self) -> None:
        """Test validation fails for low confidence."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            source="AI_ESTIMATE",
            confidence=0.5,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        provider = MockBarcodeProvider()
        service = BarcodeService(provider)

        is_valid = await service.validate_product(product)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validates_with_custom_threshold(self) -> None:
        """Test validation with custom min_confidence."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            source="BARCODE_DB",
            confidence=0.75,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        provider = MockBarcodeProvider()
        service = BarcodeService(provider)

        # Should pass with default threshold (0.7)
        is_valid_default = await service.validate_product(product)
        assert is_valid_default is True

        # Should fail with higher threshold (0.8)
        is_valid_high = await service.validate_product(product, min_confidence=0.8)
        assert is_valid_high is False

    @pytest.mark.asyncio
    async def test_validates_boundary_at_threshold(self) -> None:
        """Test validation boundary at exact threshold."""
        nutrients = NutrientProfile(
            calories=450,
            protein=6.5,
            carbs=68.0,
            fat=16.0,
            source="BARCODE_DB",
            confidence=0.7,
        )

        product = BarcodeProduct(
            barcode="8001505005707",
            name="Product",
            brand="Brand",
            nutrients=nutrients,
        )

        provider = MockBarcodeProvider()
        service = BarcodeService(provider)

        # Should pass when confidence equals threshold (>=)
        is_valid = await service.validate_product(product, min_confidence=0.7)
        assert is_valid is True
