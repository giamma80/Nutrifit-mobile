"""
Tests for BarcodeEnrichmentService.

Tests enrichment service with dependency injection and mocking.
"""

from typing import Any

import pytest

from backend.v2.domain.shared.value_objects import Barcode
from backend.v2.domain.shared.errors import BarcodeNotFoundError
from backend.v2.application.barcode.enrichment_service import (
    BarcodeEnrichmentService,
    BarcodeEnrichmentResult,
)


# ═══════════════════════════════════════════════════════════
# HAPPY PATH TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_enrich_with_both_sources(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_usda_search_result: Any,
    sample_off_search_result: Any,
) -> None:
    """Test enrichment with both USDA and OpenFoodFacts data.

    BEST PRACTICE: AAA Pattern
    - Arrange: Setup mocks
    - Act: Call service
    - Assert: Verify results
    """
    # ARRANGE - Configure mocks to return data
    mock_usda_client.search_by_barcode.return_value = sample_usda_search_result
    mock_off_client.get_product.return_value = sample_off_search_result

    # ACT - Execute enrichment
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - Verify result
    assert isinstance(result, BarcodeEnrichmentResult)
    assert result.profile is not None
    assert result.profile.calories == 520.0  # USDA value preferred
    assert result.quality.overall_score() > 0.9  # High quality (both sources)

    # Verify metadata from OpenFoodFacts
    assert result.product_name == "Nutella"
    assert result.brand == "Ferrero"
    assert result.image_url is not None
    assert result.barcode_value == "3017620422003"

    # Verify both APIs were called
    mock_off_client.get_product.assert_awaited_once_with(sample_barcode)
    mock_usda_client.search_by_barcode.assert_awaited_once_with(sample_barcode)


@pytest.mark.asyncio
async def test_enrich_with_off_only(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_off_search_result: Any,
) -> None:
    """Test enrichment with OpenFoodFacts only (USDA not found)."""
    # ARRANGE - OFF found, USDA not found
    mock_off_client.get_product.return_value = sample_off_search_result
    mock_usda_client.search_by_barcode.return_value = None

    # ACT
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT
    assert result.profile is not None
    assert result.profile.calories == 539.0  # OFF value
    assert result.quality.source_reliability == 0.80  # OFF reliability
    assert result.product_name == "Nutella"
    assert result.image_url is not None


@pytest.mark.asyncio
async def test_enrich_with_usda_only(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_usda_search_result: Any,
) -> None:
    """Test enrichment with USDA only (OpenFoodFacts not found)."""
    # ARRANGE - USDA found, OFF not found
    mock_usda_client.search_by_barcode.return_value = sample_usda_search_result
    mock_off_client.get_product.return_value = None

    # ACT
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT
    assert result.profile is not None
    assert result.profile.calories == 520.0  # USDA value
    assert result.quality.source_reliability == 0.95  # USDA reliability

    # USDA doesn't have metadata
    assert result.product_name is None
    assert result.brand is None
    assert result.image_url is None


# ═══════════════════════════════════════════════════════════
# ERROR PATH TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_enrich_not_found_in_any_db(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
) -> None:
    """Test enrichment when barcode not found in any database.

    BEST PRACTICE: Test error paths
    - Verify correct exception raised
    - Verify both APIs were called
    """
    # ARRANGE - Both return None
    mock_off_client.get_product.return_value = None
    mock_usda_client.search_by_barcode.return_value = None

    # ACT & ASSERT - Should raise exception
    with pytest.raises(BarcodeNotFoundError) as exc_info:
        await barcode_enrichment_service.enrich(sample_barcode)

    assert "not found in any database" in str(exc_info.value)

    # Verify both APIs were attempted
    mock_off_client.get_product.assert_awaited_once()
    mock_usda_client.search_by_barcode.assert_awaited_once()


@pytest.mark.asyncio
async def test_enrich_off_api_error(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_usda_search_result: Any,
) -> None:
    """Test enrichment when OpenFoodFacts API fails.

    Service should gracefully handle errors and use USDA only.
    """
    # ARRANGE - OFF throws exception, USDA succeeds
    mock_off_client.get_product.side_effect = Exception("API error")
    mock_usda_client.search_by_barcode.return_value = sample_usda_search_result

    # ACT - Should not raise (graceful degradation)
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - Falls back to USDA
    assert result.profile is not None
    assert result.profile.calories == 520.0


@pytest.mark.asyncio
async def test_enrich_usda_api_error(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_off_search_result: Any,
) -> None:
    """Test enrichment when USDA API fails.

    Service should gracefully handle errors and use OpenFoodFacts only.
    """
    # ARRANGE - USDA throws exception, OFF succeeds
    mock_usda_client.search_by_barcode.side_effect = Exception("USDA timeout")
    mock_off_client.get_product.return_value = sample_off_search_result

    # ACT - Should not raise (graceful degradation)
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - Falls back to OFF
    assert result.profile is not None
    assert result.profile.calories == 539.0


# ═══════════════════════════════════════════════════════════
# DATA MERGE TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_merge_prefers_usda_for_macros(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_usda_search_result: Any,
    sample_off_search_result: Any,
) -> None:
    """Test that merged data prefers USDA for macros (higher quality)."""
    # ARRANGE
    mock_usda_client.search_by_barcode.return_value = sample_usda_search_result
    mock_off_client.get_product.return_value = sample_off_search_result

    # ACT
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - Should use USDA values (520 vs 539 for calories)
    assert result.profile.calories == 520.0  # USDA
    assert result.profile.protein == 6.3  # Same in both
    assert result.profile.carbs == 58.0  # USDA


@pytest.mark.asyncio
async def test_merge_fills_gaps_from_off(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
) -> None:
    """Test that merged data fills missing values from OpenFoodFacts."""
    # ARRANGE - USDA has incomplete data
    from backend.v2.domain.meal.nutrition.usda_models import (
        USDAFoodItem,
        USDANutrient,
        USDASearchResult,
        USDADataType,
    )

    incomplete_usda = USDASearchResult(
        total_hits=1,
        current_page=1,
        total_pages=1,
        foods=[
            USDAFoodItem(
                fdc_id="123",
                description="Test",
                data_type=USDADataType.BRANDED,
                nutrients=[
                    USDANutrient(
                        number="208",
                        name="Energy",
                        amount=520.0,
                        unit="kcal",
                    ),
                    # Missing fiber, sugar, sodium
                ],
            )
        ],
    )

    from backend.v2.domain.meal.barcode.openfoodfacts_models import (
        OFFProduct,
        OFFNutriments,
        OFFSearchResult,
    )

    complete_off = OFFSearchResult(
        status=1,
        status_verbose="found",
        code="123",
        product=OFFProduct(
            code="123",
            product_name="Test",
            nutriments=OFFNutriments(
                energy_kcal=539.0,
                fiber=5.0,  # Has fiber
                sugars=10.0,  # Has sugar
                sodium=200.0,  # Has sodium (in mg)
            ),
        ),
    )

    mock_usda_client.search_by_barcode.return_value = incomplete_usda
    mock_off_client.get_product.return_value = complete_off

    # ACT
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - Uses USDA for calories, fills gaps from OFF
    assert result.profile.calories == 520.0  # USDA
    assert result.profile.fiber == 5.0  # From OFF (USDA missing)
    assert result.profile.sugar == 10.0  # From OFF (USDA missing)
    assert result.profile.sodium == 200.0  # From OFF (USDA missing)


# ═══════════════════════════════════════════════════════════
# QUALITY SCORING TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_quality_score_both_sources(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_usda_search_result: Any,
    sample_off_search_result: Any,
) -> None:
    """Test quality score with both sources (highest quality)."""
    # ARRANGE
    mock_usda_client.search_by_barcode.return_value = sample_usda_search_result
    mock_off_client.get_product.return_value = sample_off_search_result

    # ACT
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - Highest reliability (both sources)
    assert result.quality.source_reliability == 0.95
    assert result.quality.overall_score() > 0.9


@pytest.mark.asyncio
async def test_quality_score_off_only(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_off_search_result: Any,
) -> None:
    """Test quality score with OpenFoodFacts only (medium quality)."""
    # ARRANGE
    mock_off_client.get_product.return_value = sample_off_search_result
    mock_usda_client.search_by_barcode.return_value = None

    # ACT
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - Lower reliability (OFF only)
    assert result.quality.source_reliability == 0.80
    assert 0.8 <= result.quality.overall_score() < 0.9


@pytest.mark.asyncio
async def test_quality_score_usda_only(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_usda_search_result: Any,
) -> None:
    """Test quality score with USDA only."""
    # ARRANGE
    mock_usda_client.search_by_barcode.return_value = sample_usda_search_result
    mock_off_client.get_product.return_value = None

    # ACT
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - High reliability but may have gaps
    assert result.quality.source_reliability == 0.95


# ═══════════════════════════════════════════════════════════
# METADATA TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_metadata_from_openfoodfacts(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_off_search_result: Any,
) -> None:
    """Test that metadata (name, brand, image) comes from OpenFoodFacts."""
    # ARRANGE
    mock_off_client.get_product.return_value = sample_off_search_result
    mock_usda_client.search_by_barcode.return_value = None

    # ACT
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - Metadata from OFF
    assert result.product_name == "Nutella"
    assert result.brand == "Ferrero"
    assert result.image_url is not None
    assert "openfoodfacts.org" in result.image_url
    assert result.barcode_value == "3017620422003"


@pytest.mark.asyncio
async def test_no_metadata_with_usda_only(
    barcode_enrichment_service: BarcodeEnrichmentService,
    mock_usda_client: Any,
    mock_off_client: Any,
    sample_barcode: Barcode,
    sample_usda_search_result: Any,
) -> None:
    """Test that USDA-only results have no metadata."""
    # ARRANGE
    mock_usda_client.search_by_barcode.return_value = sample_usda_search_result
    mock_off_client.get_product.return_value = None

    # ACT
    result = await barcode_enrichment_service.enrich(sample_barcode)

    # ASSERT - No metadata from USDA
    assert result.product_name is None
    assert result.brand is None
    assert result.image_url is None
    assert result.barcode_value == "3017620422003"  # Still has barcode
