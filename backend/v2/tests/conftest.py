"""
Shared fixtures for V2 tests.

This file provides reusable test fixtures following best practices
from V2_SERVICE_EXAMPLES_AND_BEST_PRACTICES.md
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock
from datetime import datetime, timezone

import pytest

# Domain models
from backend.v2.domain.meal.nutrition.models import (
    NutrientProfile,
    NutrientSource,
)
from backend.v2.domain.meal.barcode.openfoodfacts_models import (
    OFFProduct,
    OFFNutriments,
    OFFSearchResult,
    BarcodeQuality,
)
from backend.v2.domain.meal.nutrition.usda_models import (
    USDAFoodItem,
    USDANutrient,
    USDASearchResult,
)
from backend.v2.domain.shared.value_objects import Barcode

# Infrastructure clients (for mocking)
from backend.v2.infrastructure.usda.api_client import USDAApiClient
from backend.v2.infrastructure.openfoodfacts.api_client import (
    OpenFoodFactsClient,
)

# Application services
from backend.v2.application.barcode.enrichment_service import (
    BarcodeEnrichmentService,
)


# ═══════════════════════════════════════════════════════════
# DOMAIN MODEL FIXTURES
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def sample_barcode() -> Barcode:
    """Sample barcode for Nutella."""
    return Barcode(value="3017620422003")


@pytest.fixture
def sample_nutrient_profile() -> NutrientProfile:
    """Sample complete nutrient profile."""
    return NutrientProfile(
        calories=539.0,
        protein=6.3,
        carbs=57.5,
        fat=30.9,
        fiber=2.0,
        sugar=56.3,
        sodium=0.107,
        source=NutrientSource.USDA,
    )


@pytest.fixture
def sample_off_nutriments() -> OFFNutriments:
    """Sample OpenFoodFacts nutriments."""
    return OFFNutriments(
        energy_kcal=539.0,
        proteins=6.3,
        carbohydrates=57.5,
        fat=30.9,
        fiber=2.0,
        sugars=56.3,
        salt=0.107,
    )


@pytest.fixture
def sample_off_product(sample_off_nutriments: OFFNutriments) -> OFFProduct:
    """Sample OpenFoodFacts product (Nutella)."""
    image_url = "https://images.openfoodfacts.org/images/products/" "301/762/042/2003/front_en.jpg"
    timestamp = int(datetime(2024, 1, 15, tzinfo=timezone.utc).timestamp())
    return OFFProduct(
        code="3017620422003",
        product_name="Nutella",
        brands="Ferrero",
        quantity="750g",
        categories="Spreads, Chocolate spreads",
        nutriments=sample_off_nutriments,
        nutriscore_grade="e",
        nova_group="4",
        image_url=image_url,
        completeness=0.89,
        last_modified_t=timestamp,
    )


@pytest.fixture
def sample_off_search_result(
    sample_off_product: OFFProduct,
) -> OFFSearchResult:
    """Sample OpenFoodFacts search result."""
    return OFFSearchResult(
        status=1,
        status_verbose="product found",
        code="3017620422003",
        product=sample_off_product,
    )


@pytest.fixture
def sample_usda_nutrients() -> list[USDANutrient]:
    """Sample USDA nutrients list."""
    return [
        USDANutrient(
            number="208",
            name="Energy",
            amount=520.0,
            unit="kcal",
        ),
        USDANutrient(
            number="203",
            name="Protein",
            amount=6.3,
            unit="g",
        ),
        USDANutrient(
            number="205",
            name="Carbohydrate, by difference",
            amount=58.0,
            unit="g",
        ),
        USDANutrient(
            number="204",
            name="Total lipid (fat)",
            amount=31.0,
            unit="g",
        ),
        USDANutrient(
            number="291",
            name="Fiber, total dietary",
            amount=2.1,
            unit="g",
        ),
        USDANutrient(
            number="269",
            name="Sugars, total including NLEA",
            amount=56.0,
            unit="g",
        ),
        USDANutrient(
            number="307",
            name="Sodium, Na",
            amount=107.0,
            unit="mg",
        ),
    ]


@pytest.fixture
def sample_usda_food_item(
    sample_usda_nutrients: list[USDANutrient],
) -> USDAFoodItem:
    """Sample USDA food item."""
    from backend.v2.domain.meal.nutrition.usda_models import USDADataType

    return USDAFoodItem(
        fdc_id="123456",
        description="Chocolate hazelnut spread",
        data_type=USDADataType.BRANDED,
        brand_owner="Ferrero",
        gtin_upc="3017620422003",
        nutrients=sample_usda_nutrients,
    )


@pytest.fixture
def sample_usda_search_result(
    sample_usda_food_item: USDAFoodItem,
) -> USDASearchResult:
    """Sample USDA search result."""
    return USDASearchResult(
        total_hits=1,
        current_page=1,
        total_pages=1,
        foods=[sample_usda_food_item],
    )


@pytest.fixture
def sample_barcode_quality() -> BarcodeQuality:
    """Sample barcode quality metrics."""
    return BarcodeQuality(
        completeness=0.89,
        source_reliability=0.95,
        data_freshness=0.90,
    )


# ═══════════════════════════════════════════════════════════
# MOCK CLIENT FIXTURES
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def mock_usda_client() -> AsyncMock:
    """Mock USDA API client.

    Default behavior: Returns None (not found)
    Override in tests with specific return values.
    """
    client = AsyncMock(spec=USDAApiClient)
    client.search_by_barcode.return_value = None
    return client


@pytest.fixture
def mock_off_client() -> AsyncMock:
    """Mock OpenFoodFacts API client.

    Default behavior: Returns None (not found)
    Override in tests with specific return values.
    """
    client = AsyncMock(spec=OpenFoodFactsClient)
    client.get_product.return_value = None
    return client


# ═══════════════════════════════════════════════════════════
# SERVICE FIXTURES WITH DEPENDENCY INJECTION
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def barcode_enrichment_service(
    mock_usda_client: AsyncMock,
    mock_off_client: AsyncMock,
) -> BarcodeEnrichmentService:
    """Barcode enrichment service with mocked dependencies.

    BEST PRACTICE: Dependency Injection
    - Service receives mock clients
    - Easy to test different scenarios
    - No global state
    - Clear dependencies

    Example usage in tests:
        async def test_something(
            barcode_enrichment_service,
            mock_usda_client,
            sample_usda_search_result,
        ):
            # Configure mock
            mock_usda_client.search_by_barcode.return_value = (
                sample_usda_search_result
            )

            # Test
            result = await barcode_enrichment_service.enrich(barcode)

            # Assert
            assert result.profile.calories == 520.0
    """
    return BarcodeEnrichmentService(
        usda_client=mock_usda_client,
        off_client=mock_off_client,
    )


# ═══════════════════════════════════════════════════════════
# ASYNC TEST CONFIGURATION
# ═══════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def event_loop_policy() -> asyncio.AbstractEventLoopPolicy:
    """Use default event loop policy for async tests."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


# ═══════════════════════════════════════════════════════════
# PARAMETRIZE HELPERS
# ═══════════════════════════════════════════════════════════


@pytest.fixture(params=["", None, "   "])
def invalid_barcode_value(request: pytest.FixtureRequest) -> Any:
    """Parametrized fixture for invalid barcode values.

    Example usage:
        def test_invalid_barcode(invalid_barcode_value):
            with pytest.raises(ValueError):
                Barcode(value=invalid_barcode_value)
    """
    return request.param


@pytest.fixture(
    params=[
        ("3017620422003", True),  # Valid EAN-13
        ("012345678905", True),  # Valid UPC-A
        ("invalid", False),  # Invalid
        ("", False),  # Empty
    ]
)
def barcode_validation_case(
    request: pytest.FixtureRequest,
) -> Any:
    """Parametrized fixture for barcode validation test cases.

    Returns: Tuple of (barcode_value, is_valid)
    """
    return request.param
