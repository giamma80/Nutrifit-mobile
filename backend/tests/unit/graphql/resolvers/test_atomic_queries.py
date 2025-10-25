"""Unit tests for atomic query resolvers.

Tests the 3 atomic utility queries that test capabilities in isolation:
- recognizeFood: Tests IVisionProvider (OpenAI)
- enrichNutrients: Tests INutritionProvider (USDA)
- searchFoodByBarcode: Tests IBarcodeProvider (OpenFoodFacts)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any

from graphql.resolvers.meal.atomic_queries import AtomicQueries
from domain.meal.recognition.entities.recognized_food import (
    RecognizedFood as DomainRecognizedFood,
    FoodRecognitionResult as DomainFoodRecognitionResult,
)
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile as DomainNutrientProfile
from domain.meal.barcode.entities.barcode_product import BarcodeProduct as DomainBarcodeProduct


@pytest.fixture
def mock_context() -> Any:
    """Create mock Strawberry context with all dependencies."""
    # Create persistent mocks (not recreated on each .get() call)
    mocks = {
        "recognition_service": AsyncMock(),
        "enrichment_service": AsyncMock(),
        "barcode_service": AsyncMock(),
    }

    context = MagicMock()
    context.get = MagicMock(side_effect=lambda key: mocks.get(key))
    return context


@pytest.fixture
def mock_info(mock_context: Any) -> Any:
    """Create mock Strawberry Info object."""
    info = MagicMock()
    info.context = mock_context
    return info


@pytest.fixture
def atomic_queries() -> AtomicQueries:
    """Create AtomicQueries resolver instance."""
    return AtomicQueries()


# ============================================
# recognizeFood Tests
# ============================================


@pytest.mark.asyncio
async def test_recognize_food_from_photo_success(
    atomic_queries: AtomicQueries, mock_info: Any
) -> None:
    """Test recognizeFood with photo URL."""
    # Arrange
    photo_url = "https://example.com/pasta.jpg"

    # Mock recognition service response
    domain_items = [
        DomainRecognizedFood(
            label="roasted_chicken",
            display_name="Roasted Chicken",
            quantity_g=150.0,
            confidence=0.85,
        ),
        DomainRecognizedFood(
            label="steamed_broccoli",
            display_name="Steamed Broccoli",
            quantity_g=100.0,
            confidence=0.92,
        ),
    ]
    domain_result = DomainFoodRecognitionResult(items=domain_items)

    recognition_service = mock_info.context.get("recognition_service")
    recognition_service.recognize_from_photo.return_value = domain_result

    # Act
    result = await atomic_queries.recognize_food(  # type: ignore[misc,call-arg]
        info=mock_info,
        photo_url=photo_url,
        text=None,
        dish_hint="chicken and vegetables",
    )

    # Assert
    assert result.items is not None
    assert len(result.items) == 2
    assert result.items[0].label == "roasted_chicken"
    assert result.items[0].display_name == "Roasted Chicken"
    assert result.items[0].quantity_g == 150.0
    assert result.items[0].confidence == 0.85
    assert result.items[1].label == "steamed_broccoli"
    assert result.average_confidence == 0.885  # (0.85 + 0.92) / 2

    # Verify service was called correctly
    recognition_service.recognize_from_photo.assert_called_once_with(
        photo_url=photo_url,
        dish_hint="chicken and vegetables",
    )


@pytest.mark.asyncio
async def test_recognize_food_from_text_success(
    atomic_queries: AtomicQueries, mock_info: Any
) -> None:
    """Test recognizeFood with text description."""
    # Arrange
    text_description = "pasta with tomato sauce and basil"

    domain_items = [
        DomainRecognizedFood(
            label="pasta",
            display_name="Pasta",
            quantity_g=200.0,
            confidence=0.90,
        ),
    ]
    domain_result = DomainFoodRecognitionResult(items=domain_items)

    recognition_service = mock_info.context.get("recognition_service")
    recognition_service.recognize_from_text.return_value = domain_result

    # Act
    result = await atomic_queries.recognize_food(  # type: ignore[misc,call-arg]
        info=mock_info,
        photo_url=None,
        text=text_description,
        dish_hint=None,
    )

    # Assert
    assert result.items is not None
    assert len(result.items) == 1
    assert result.items[0].label == "pasta"
    assert result.average_confidence == 0.90

    recognition_service.recognize_from_text.assert_called_once_with(
        description=text_description,
    )


@pytest.mark.asyncio
async def test_recognize_food_service_not_available(atomic_queries: AtomicQueries) -> None:
    """Test recognizeFood when recognition service not available in context."""
    # Arrange
    mock_info = MagicMock()
    mock_info.context.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="RecognitionService not available in context"):
        await atomic_queries.recognize_food(  # type: ignore[misc,call-arg]
            info=mock_info,
            photo_url="https://example.com/food.jpg",
        )


# ============================================
# enrichNutrients Tests
# ============================================


@pytest.mark.asyncio
async def test_enrich_nutrients_success(atomic_queries: AtomicQueries, mock_info: Any) -> None:
    """Test enrichNutrients with valid food label."""
    # Arrange
    label = "banana"
    quantity_g = 120.0

    # Mock enrichment service response
    domain_profile = DomainNutrientProfile(
        calories=105,
        protein=1.3,
        carbs=27.0,
        fat=0.4,
        fiber=3.1,
        sugar=14.4,
        sodium=1.0,
        quantity_g=120.0,
    )

    enrichment_service = mock_info.context.get("enrichment_service")
    enrichment_service.enrich.return_value = domain_profile

    # Act
    result = await atomic_queries.enrich_nutrients(  # type: ignore[misc,call-arg]
        info=mock_info,
        label=label,
        quantity_g=quantity_g,
    )

    # Assert
    assert result is not None
    assert result.calories == 105
    assert result.protein == 1.3
    assert result.carbs == 27.0
    assert result.fat == 0.4
    assert result.fiber == 3.1
    assert result.sugar == 14.4
    assert result.sodium == 1.0
    assert result.quantity_g == 120.0

    enrichment_service.enrich.assert_called_once_with(
        label=label,
        quantity_g=quantity_g,
    )


@pytest.mark.asyncio
async def test_enrich_nutrients_not_found(atomic_queries: AtomicQueries, mock_info: Any) -> None:
    """Test enrichNutrients when food label not found."""
    # Arrange
    enrichment_service = mock_info.context.get("enrichment_service")
    enrichment_service.enrich.return_value = None

    # Act
    result = await atomic_queries.enrich_nutrients(  # type: ignore[misc,call-arg]
        info=mock_info,
        label="unknown_food_xyz",
        quantity_g=100.0,
    )

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_enrich_nutrients_service_not_available(atomic_queries: AtomicQueries) -> None:
    """Test enrichNutrients when enrichment service not available."""
    # Arrange
    mock_info = MagicMock()
    mock_info.context.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="EnrichmentService not available in context"):
        await atomic_queries.enrich_nutrients(  # type: ignore[misc,call-arg]
            info=mock_info,
            label="banana",
            quantity_g=100.0,
        )


# ============================================
# searchFoodByBarcode Tests
# ============================================


@pytest.mark.asyncio
async def test_search_food_by_barcode_success(
    atomic_queries: AtomicQueries, mock_info: Any
) -> None:
    """Test searchFoodByBarcode with valid barcode."""
    # Arrange
    barcode = "8001505005707"

    # Mock barcode service response
    domain_nutrients = DomainNutrientProfile(
        calories=250,
        protein=8.0,
        carbs=40.0,
        fat=7.0,
        fiber=2.0,
        sugar=5.0,
        sodium=300.0,
        quantity_g=100.0,
    )

    domain_product = DomainBarcodeProduct(
        barcode=barcode,
        name="Pasta Barilla",
        brand="Barilla",
        nutrients=domain_nutrients,
        serving_size_g=100.0,
        image_url="https://example.com/barilla.jpg",
    )

    barcode_service = mock_info.context.get("barcode_service")
    barcode_service.lookup.return_value = domain_product

    # Act
    result = await atomic_queries.search_food_by_barcode(  # type: ignore[misc,call-arg]
        info=mock_info,
        barcode=barcode,
    )

    # Assert
    assert result is not None
    assert result.barcode == barcode
    assert result.name == "Pasta Barilla"
    assert result.brand == "Barilla"
    assert result.serving_size_g == 100.0
    assert result.image_url == "https://example.com/barilla.jpg"

    # Check nutrients
    assert result.nutrients is not None
    assert result.nutrients.calories == 250
    assert result.nutrients.protein == 8.0
    assert result.nutrients.carbs == 40.0
    assert result.nutrients.fat == 7.0

    barcode_service.lookup.assert_called_once_with(barcode)


@pytest.mark.asyncio
async def test_search_food_by_barcode_not_found(
    atomic_queries: AtomicQueries, mock_info: Any
) -> None:
    """Test searchFoodByBarcode when barcode not found."""
    # Arrange
    barcode_service = mock_info.context.get("barcode_service")
    barcode_service.lookup.side_effect = ValueError("Barcode not found")

    # Act
    result = await atomic_queries.search_food_by_barcode(  # type: ignore[misc,call-arg]
        info=mock_info,
        barcode="0000000000000",
    )

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_search_food_by_barcode_without_nutrients(
    atomic_queries: AtomicQueries, mock_info: Any
) -> None:
    """Test searchFoodByBarcode when product has no nutrient data."""
    # Arrange
    domain_product = DomainBarcodeProduct(
        barcode="8001505005707",
        name="Generic Product",
        brand="Generic",
        nutrients=None,  # type: ignore[arg-type]
        serving_size_g=None,
        image_url=None,
    )

    barcode_service = mock_info.context.get("barcode_service")
    barcode_service.lookup.return_value = domain_product

    # Act
    result = await atomic_queries.search_food_by_barcode(  # type: ignore[misc,call-arg]
        info=mock_info,
        barcode="8001505005707",
    )

    # Assert
    assert result is not None
    assert result.barcode == "8001505005707"
    assert result.name == "Generic Product"
    assert result.nutrients is None
    assert result.serving_size_g is None
    assert result.image_url is None


@pytest.mark.asyncio
async def test_search_food_by_barcode_service_not_available(atomic_queries: AtomicQueries) -> None:
    """Test searchFoodByBarcode when barcode service not available."""
    # Arrange
    mock_info = MagicMock()
    mock_info.context.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="BarcodeService not available in context"):
        await atomic_queries.search_food_by_barcode(  # type: ignore[misc,call-arg]
            info=mock_info,
            barcode="8001505005707",
        )
