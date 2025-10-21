"""
Tests for MealAnalysisOrchestrator.

Tests orchestration logic with mocked dependencies.
Integration tests in tests/integration/.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock
from typing import Any

import pytest

from backend.v2.domain.shared.value_objects import (
    UserId,
    AnalysisId,
    Barcode,
)
from backend.v2.domain.meal.orchestration.analysis_models import (
    MealAnalysis,
    MealAnalysisMetadata,
    AnalysisSource,
    AnalysisStatus,
)
from backend.v2.domain.meal.nutrition.models import (
    NutrientProfile,
    NutrientSource,
)
from backend.v2.domain.meal.barcode.openfoodfacts_models import (
    BarcodeQuality,
)
from backend.v2.application.barcode.enrichment_service import (
    BarcodeEnrichmentResult,
)
from backend.v2.domain.meal.nutrition.usda_models import (
    USDAFoodItem,
    USDANutrient,
    USDASearchResult,
)
from backend.v2.application.meal.orchestration_service import (
    MealAnalysisOrchestrator,
)

# Import interfaces for proper mock spec
from backend.v2.domain.meal.orchestration.ports import (
    IBarcodeEnrichmentService,
    IUSDAClient,
    IFoodRecognitionService,
)
from backend.v2.domain.meal.persistence.analysis_repository import (
    IMealAnalysisRepository,
)


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def user_id() -> UserId:
    """Test user ID."""
    return UserId(value="user123")


@pytest.fixture
def mock_repository() -> Any:
    """Mock repository for testing."""
    repo = AsyncMock(spec=IMealAnalysisRepository)
    repo.exists = AsyncMock(return_value=False)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    repo.get_by_user = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_barcode_service() -> Any:
    """Mock barcode enrichment service (interface-based)."""
    return AsyncMock(spec=IBarcodeEnrichmentService)


@pytest.fixture
def mock_usda_client() -> Any:
    """Mock USDA API client (interface-based)."""
    return AsyncMock(spec=IUSDAClient)


@pytest.fixture
def orchestrator(
    mock_repository: Any,
    mock_barcode_service: Any,
    mock_usda_client: Any,
) -> MealAnalysisOrchestrator:
    """Orchestrator with mocked dependencies."""
    return MealAnalysisOrchestrator(
        repository=mock_repository,
        barcode_service=mock_barcode_service,
        usda_client=mock_usda_client,
    )


@pytest.fixture
def sample_barcode() -> Barcode:
    """Sample barcode."""
    return Barcode(value="3017620422003")


# ═══════════════════════════════════════════════════════════
# BARCODE ANALYSIS TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_analyze_from_barcode_success(
    orchestrator: MealAnalysisOrchestrator,
    mock_barcode_service: Any,
    mock_repository: Any,
    user_id: UserId,
    sample_barcode: Barcode,
) -> None:
    """Test successful barcode analysis."""
    # ARRANGE - Mock enriched product
    enriched = BarcodeEnrichmentResult(
        profile=NutrientProfile(
            calories=539,
            protein=6.3,
            carbs=57.5,
            fat=30.9,
            source="BARCODE_DB",
            confidence=0.95,
            quantity_g=100.0,
        ),
        quality=BarcodeQuality(
            completeness=0.95,
            source_reliability=0.90,
            data_freshness=0.85,
        ),
        product_name="Nutella",
        brand=None,
        barcode_value=sample_barcode.value,
    )
    mock_barcode_service.enrich = AsyncMock(return_value=enriched)

    # ACT
    analysis = await orchestrator.analyze_from_barcode(
        user_id=user_id,
        barcode=sample_barcode,
        quantity_g=150.0,
    )

    # ASSERT
    assert analysis.user_id == user_id
    assert analysis.meal_name == "Nutella"
    assert analysis.quantity_g == 150.0
    assert analysis.nutrient_profile.calories == 539
    assert analysis.nutrient_profile.protein == 6.3
    assert analysis.metadata.source == AnalysisSource.BARCODE_SCAN
    assert analysis.metadata.barcode_value == sample_barcode.value
    assert analysis.status == AnalysisStatus.COMPLETED

    # Verify repository save was called
    mock_repository.save.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_from_barcode_with_custom_id(
    orchestrator: MealAnalysisOrchestrator,
    mock_barcode_service: Any,
    mock_repository: Any,
    user_id: UserId,
    sample_barcode: Barcode,
) -> None:
    """Test barcode analysis with custom analysis_id."""
    # ARRANGE
    custom_id = AnalysisId.generate()
    enriched = BarcodeEnrichmentResult(
        profile=NutrientProfile(
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=3.0,
            source="BARCODE_DB",
            confidence=0.9,
            quantity_g=100.0,
        ),
        quality=BarcodeQuality(
            completeness=0.9,
            source_reliability=0.85,
            data_freshness=0.80,
        ),
        product_name="Product",
        brand=None,
        barcode_value=sample_barcode.value,
    )
    mock_barcode_service.enrich = AsyncMock(return_value=enriched)

    # ACT
    analysis = await orchestrator.analyze_from_barcode(
        user_id=user_id,
        barcode=sample_barcode,
        analysis_id=custom_id,
    )

    # ASSERT
    assert analysis.analysis_id == custom_id


@pytest.mark.asyncio
async def test_analyze_from_barcode_idempotency(
    orchestrator: MealAnalysisOrchestrator,
    mock_repository: Any,
    user_id: UserId,
    sample_barcode: Barcode,
) -> None:
    """Test idempotency - returns cached analysis."""
    # ARRANGE - Cached analysis exists
    cached_analysis = MealAnalysis.create_new(
        user_id=user_id,
        meal_name="Cached Product",
        nutrient_profile=NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=20.0,
            fat=5.0,
            source=NutrientSource.USDA,
            confidence=0.95,
            quantity_g=100.0,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.BARCODE_SCAN,
            confidence=0.95,
            processing_time_ms=100,
        ),
    )

    mock_repository.exists = AsyncMock(return_value=True)
    mock_repository.get_by_id = AsyncMock(return_value=cached_analysis)

    # ACT
    analysis = await orchestrator.analyze_from_barcode(
        user_id=user_id,
        barcode=sample_barcode,
        analysis_id=cached_analysis.analysis_id,
    )

    # ASSERT
    assert analysis == cached_analysis
    assert analysis.meal_name == "Cached Product"

    # Verify repository was checked but not saved again
    mock_repository.exists.assert_called_once()
    mock_repository.get_by_id.assert_called_once()
    mock_repository.save.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_from_barcode_fallback_to_usda(
    orchestrator: MealAnalysisOrchestrator,
    mock_barcode_service: Any,
    mock_usda_client: Any,
    mock_repository: Any,
    user_id: UserId,
    sample_barcode: Barcode,
) -> None:
    """Test fallback to USDA when barcode not found."""
    # ARRANGE - Barcode service fails
    mock_barcode_service.enrich = AsyncMock(side_effect=ValueError("Barcode not found"))

    # USDA returns data
    usda_food = USDAFoodItem(
        fdc_id="123456",
        description="Generic Product",
        data_type="Survey (FNDDS)",
        nutrients=[
            USDANutrient(
                number="1003",
                name="Protein",
                amount=8.0,
                unit="g",
            ),
            USDANutrient(
                number="1005",
                name="Carbohydrate, by difference",
                amount=25.0,
                unit="g",
            ),
            USDANutrient(
                number="1004",
                name="Total lipid (fat)",
                amount=4.0,
                unit="g",
            ),
        ],
    )

    mock_usda_client.search_foods = AsyncMock(
        return_value=USDASearchResult(
            total_hits=1,
            current_page=1,
            total_pages=1,
            foods=[usda_food],
        )
    )
    mock_usda_client.get_food = AsyncMock(return_value=usda_food)

    # ACT
    analysis = await orchestrator.analyze_from_barcode(
        user_id=user_id,
        barcode=sample_barcode,
    )

    # ASSERT
    assert analysis.meal_name == "Generic Product"
    assert analysis.status == AnalysisStatus.PARTIAL
    assert analysis.metadata.fallback_reason is not None
    assert "Barcode not found" in analysis.metadata.fallback_reason
    # Confidence reduced due to fallback
    assert analysis.metadata.confidence < 0.95


# ═══════════════════════════════════════════════════════════
# USDA SEARCH TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_analyze_from_usda_search_success(
    orchestrator: MealAnalysisOrchestrator,
    mock_usda_client: Any,
    mock_repository: Any,
    user_id: UserId,
) -> None:
    """Test successful USDA search analysis."""
    # ARRANGE
    banana_food = USDAFoodItem(
        fdc_id="173944",
        description="Bananas, raw",
        data_type="SR Legacy",
        nutrients=[
            USDANutrient(
                number="1003",
                name="Protein",
                amount=1.09,
                unit="g",
            ),
            USDANutrient(
                number="1005",
                name="Carbohydrate, by difference",
                amount=22.84,
                unit="g",
            ),
            USDANutrient(
                number="1004",
                name="Total lipid (fat)",
                amount=0.33,
                unit="g",
            ),
        ],
    )

    mock_usda_client.search_foods = AsyncMock(
        return_value=USDASearchResult(
            total_hits=1,
            current_page=1,
            total_pages=1,
            foods=[banana_food],
        )
    )
    mock_usda_client.get_food = AsyncMock(return_value=banana_food)

    # ACT
    analysis = await orchestrator.analyze_from_usda_search(
        user_id=user_id,
        search_query="banana",
        quantity_g=118.0,
    )

    # ASSERT
    assert analysis.meal_name == "Bananas, raw"
    assert analysis.quantity_g == 118.0
    assert analysis.nutrient_profile.protein == 1.09
    assert analysis.nutrient_profile.carbs == 22.84
    assert analysis.nutrient_profile.fat == 0.33
    # Calories calculated: (1.09*4) + (22.84*4) + (0.33*9) ≈ 98
    assert 96 <= analysis.nutrient_profile.calories <= 100
    assert analysis.metadata.source == AnalysisSource.USDA_SEARCH
    assert analysis.metadata.confidence == 0.95


@pytest.mark.asyncio
async def test_analyze_from_usda_search_no_results(
    orchestrator: MealAnalysisOrchestrator,
    mock_usda_client: Any,
    user_id: UserId,
) -> None:
    """Test USDA search with no results."""
    # ARRANGE
    mock_usda_client.search_foods = AsyncMock(
        return_value=USDASearchResult(
            total_hits=0,
            current_page=1,
            total_pages=0,
            foods=[],
        )
    )

    # ACT & ASSERT
    with pytest.raises(ValueError, match="No USDA results for"):
        await orchestrator.analyze_from_usda_search(
            user_id=user_id,
            search_query="xyznonexistent",
        )


@pytest.mark.asyncio
async def test_analyze_from_usda_idempotency(
    orchestrator: MealAnalysisOrchestrator,
    mock_repository: Any,
    user_id: UserId,
) -> None:
    """Test USDA search idempotency."""
    # ARRANGE
    cached = MealAnalysis.create_new(
        user_id=user_id,
        meal_name="Cached USDA Food",
        nutrient_profile=NutrientProfile(
            calories=150,
            protein=12.0,
            carbs=18.0,
            fat=4.0,
            source=NutrientSource.USDA,
            confidence=0.95,
            quantity_g=100.0,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.USDA_SEARCH,
            confidence=0.95,
            processing_time_ms=200,
        ),
    )

    mock_repository.exists = AsyncMock(return_value=True)
    mock_repository.get_by_id = AsyncMock(return_value=cached)

    # ACT
    analysis = await orchestrator.analyze_from_usda_search(
        user_id=user_id,
        search_query="chicken",
        analysis_id=cached.analysis_id,
    )

    # ASSERT
    assert analysis == cached
    mock_repository.save.assert_not_called()


# ═══════════════════════════════════════════════════════════
# QUERY TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_analysis(
    orchestrator: MealAnalysisOrchestrator,
    mock_repository: Any,
    user_id: UserId,
) -> None:
    """Test retrieving analysis by ID."""
    # ARRANGE
    analysis = MealAnalysis.create_new(
        user_id=user_id,
        meal_name="Test Meal",
        nutrient_profile=NutrientProfile(
            calories=200,
            protein=15.0,
            carbs=20.0,
            fat=6.0,
            source=NutrientSource.USDA,
            confidence=0.9,
            quantity_g=100.0,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.MANUAL_ENTRY,
            confidence=0.90,
            processing_time_ms=50,
        ),
    )
    mock_repository.get_by_id = AsyncMock(return_value=analysis)

    # ACT
    result = await orchestrator.get_analysis(analysis.analysis_id)

    # ASSERT
    assert result == analysis


@pytest.mark.asyncio
async def test_get_analysis_expired(
    orchestrator: MealAnalysisOrchestrator,
    mock_repository: Any,
    user_id: UserId,
) -> None:
    """Test that expired analyses are filtered out."""
    # ARRANGE - Create expired analysis
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)
    expired = MealAnalysis(
        analysis_id=AnalysisId.generate(),
        user_id=user_id,
        meal_name="Expired",
        nutrient_profile=NutrientProfile(
            calories=100,
            protein=10.0,
            carbs=12.0,
            fat=3.0,
            source=NutrientSource.USDA,
            confidence=0.9,
            quantity_g=100.0,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.MANUAL_ENTRY,
            confidence=0.80,
            processing_time_ms=0,
        ),
        status=AnalysisStatus.COMPLETED,
        created_at=old_time,
        expires_at=old_time + timedelta(hours=24),
    )

    mock_repository.get_by_id = AsyncMock(return_value=expired)

    # ACT
    result = await orchestrator.get_analysis(expired.analysis_id)

    # ASSERT - Should return None for expired
    assert result is None


@pytest.mark.asyncio
async def test_get_recent_analyses(
    orchestrator: MealAnalysisOrchestrator,
    mock_repository: Any,
    user_id: UserId,
) -> None:
    """Test getting recent analyses for user."""
    # ARRANGE
    analyses = [
        MealAnalysis.create_new(
            user_id=user_id,
            meal_name=f"Meal {i}",
            nutrient_profile=NutrientProfile(
                calories=100 + i * 10,
                protein=10.0,
                carbs=15.0,
                fat=3.0,
                source=NutrientSource.USDA,
                confidence=0.9,
                quantity_g=100.0,
            ),
            quantity_g=100.0,
            metadata=MealAnalysisMetadata(
                source=AnalysisSource.MANUAL_ENTRY,
                confidence=0.85,
                processing_time_ms=100,
            ),
        )
        for i in range(3)
    ]

    mock_repository.get_by_user = AsyncMock(return_value=analyses)

    # ACT
    result = await orchestrator.get_recent_analyses(user_id=user_id, limit=5)

    # ASSERT
    assert len(result) == 3
    mock_repository.get_by_user.assert_called_once_with(
        user_id=user_id,
        limit=5,
        include_expired=False,
    )


# ═══════════════════════════════════════════════════════════
# FALLBACK STRATEGY TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_fallback_complete_failure(
    orchestrator: MealAnalysisOrchestrator,
    mock_barcode_service: Any,
    mock_usda_client: Any,
    user_id: UserId,
    sample_barcode: Barcode,
) -> None:
    """Test when both barcode and USDA fail."""
    # ARRANGE - Both sources fail
    mock_barcode_service.enrich = AsyncMock(side_effect=ValueError("Barcode not found"))
    mock_usda_client.search_foods = AsyncMock(side_effect=ValueError("USDA API error"))

    # ACT & ASSERT
    with pytest.raises(ValueError, match="All sources failed"):
        await orchestrator.analyze_from_barcode(
            user_id=user_id,
            barcode=sample_barcode,
        )


@pytest.mark.asyncio
async def test_metadata_tracks_processing_time(
    orchestrator: MealAnalysisOrchestrator,
    mock_barcode_service: Any,
    user_id: UserId,
    sample_barcode: Barcode,
) -> None:
    """Test that processing time is tracked in metadata."""
    # ARRANGE
    enriched = BarcodeEnrichmentResult(
        profile=NutrientProfile(
            calories=100,
            protein=5.0,
            carbs=10.0,
            fat=3.0,
            source="BARCODE_DB",
            confidence=0.9,
            quantity_g=100.0,
        ),
        quality=BarcodeQuality(
            completeness=0.9,
            source_reliability=0.85,
            data_freshness=0.80,
        ),
        product_name="Fast Product",
        brand=None,
        barcode_value=sample_barcode.value,
    )
    mock_barcode_service.enrich = AsyncMock(return_value=enriched)

    # ACT
    analysis = await orchestrator.analyze_from_barcode(
        user_id=user_id,
        barcode=sample_barcode,
    )

    # ASSERT - Processing time should be tracked
    assert analysis.metadata.processing_time_ms >= 0
    assert isinstance(analysis.metadata.processing_time_ms, int)


# ═══════════════════════════════════════════════════════════
# PHOTO ANALYSIS TESTS
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def mock_food_recognition_service() -> Any:
    """Mock food recognition service (interface-based)."""
    return AsyncMock(spec=IFoodRecognitionService)


@pytest.fixture
def orchestrator_with_photo(
    mock_repository: Any,
    mock_barcode_service: Any,
    mock_usda_client: Any,
    mock_food_recognition_service: Any,
) -> MealAnalysisOrchestrator:
    """Orchestrator with photo recognition enabled."""
    return MealAnalysisOrchestrator(
        repository=mock_repository,
        barcode_service=mock_barcode_service,
        usda_client=mock_usda_client,
        food_recognition_service=mock_food_recognition_service,
    )


@pytest.mark.asyncio
async def test_analyze_from_photo_success(
    orchestrator_with_photo: MealAnalysisOrchestrator,
    mock_food_recognition_service: Any,
    mock_usda_client: Any,
    user_id: UserId,
) -> None:
    """Test successful photo analysis with USDA enrichment."""
    # ARRANGE
    from backend.v2.domain.meal.recognition.models import (
        FoodRecognitionResult,
        RecognizedFoodItem,
        RecognitionStatus,
    )

    # Mock AI recognition result
    recognition_result = FoodRecognitionResult(
        items=[
            RecognizedFoodItem(
                label="chicken breast",
                display_name="Grilled Chicken Breast",
                quantity_g=150.0,
                confidence=0.92,
            )
        ],
        dish_name="Pollo alla Griglia",
        image_url="https://example.com/meal.jpg",
        confidence=0.92,
        processing_time_ms=1200,
        status=RecognitionStatus.SUCCESS,
    )
    mock_food_recognition_service.recognize = AsyncMock(return_value=recognition_result)

    # Mock USDA search
    usda_search = USDASearchResult(
        foods=[
            USDAFoodItem(
                fdc_id="12345",
                description="Chicken, breast, grilled",
                data_type="Survey (FNDDS)",
                nutrients=[
                    USDANutrient(number="203", name="Protein", amount=31.0, unit="g"),
                    USDANutrient(
                        number="205", name="Carbohydrate, by difference", amount=0.0, unit="g"
                    ),
                    USDANutrient(number="204", name="Total lipid (fat)", amount=3.6, unit="g"),
                ],
            )
        ],
        total_hits=1,
        current_page=1,
        total_pages=1,
    )
    mock_usda_client.search_foods = AsyncMock(return_value=usda_search)

    # Mock get_food to return the same food item with nutrients
    mock_usda_client.get_food = AsyncMock(return_value=usda_search.foods[0])

    # ACT
    analyses = await orchestrator_with_photo.analyze_from_photo(
        user_id=user_id,
        image_url="https://example.com/meal.jpg",
    )

    # ASSERT
    assert len(analyses) == 1
    analysis = analyses[0]
    assert analysis.meal_name == "Grilled Chicken Breast"
    assert analysis.nutrient_profile.protein == 31.0
    assert analysis.nutrient_profile.carbs == 0.0
    assert analysis.nutrient_profile.fat == 3.6
    assert analysis.metadata.source == AnalysisSource.AI_VISION
    assert analysis.metadata.confidence == 0.92
    assert analysis.metadata.image_url == "https://example.com/meal.jpg"


@pytest.mark.asyncio
async def test_analyze_from_photo_multiple_items(
    orchestrator_with_photo: MealAnalysisOrchestrator,
    mock_food_recognition_service: Any,
    mock_usda_client: Any,
    user_id: UserId,
) -> None:
    """Test photo analysis with multiple recognized items."""
    # ARRANGE
    from backend.v2.domain.meal.recognition.models import (
        FoodRecognitionResult,
        RecognizedFoodItem,
        RecognitionStatus,
    )

    # Mock AI recognition with 2 items
    recognition_result = FoodRecognitionResult(
        items=[
            RecognizedFoodItem(
                label="rice",
                display_name="White Rice",
                quantity_g=200.0,
                confidence=0.88,
            ),
            RecognizedFoodItem(
                label="broccoli",
                display_name="Steamed Broccoli",
                quantity_g=150.0,
                confidence=0.85,
            ),
        ],
        dish_name="Rice and Vegetables",
        confidence=0.865,
        processing_time_ms=1500,
        status=RecognitionStatus.SUCCESS,
    )
    mock_food_recognition_service.recognize = AsyncMock(return_value=recognition_result)

    # Mock USDA for rice
    async def mock_search(query: str, **kwargs: Any) -> USDASearchResult:
        if "rice" in query.lower():
            return USDASearchResult(
                foods=[
                    USDAFoodItem(
                        fdc_id="11111",
                        description="Rice, white, cooked",
                        data_type="Survey (FNDDS)",
                    )
                ],
                total_hits=1,
                current_page=1,
                total_pages=1,
            )
        else:  # broccoli
            return USDASearchResult(
                foods=[
                    USDAFoodItem(
                        fdc_id="22222",
                        description="Broccoli, steamed",
                        data_type="Survey (FNDDS)",
                    )
                ],
                total_hits=1,
                current_page=1,
                total_pages=1,
            )

    mock_usda_client.search_foods = AsyncMock(side_effect=mock_search)

    # Mock USDA details (get_food returns USDAFoodItem with nutrients)
    async def mock_get_food(fdc_id: str) -> USDAFoodItem:
        if fdc_id == "11111":  # Rice
            return USDAFoodItem(
                fdc_id="11111",
                description="Rice, white, cooked",
                data_type="Survey (FNDDS)",
                nutrients=[
                    USDANutrient(number="203", name="Protein", amount=2.7, unit="g"),
                    USDANutrient(
                        number="205", name="Carbohydrate, by difference", amount=28.2, unit="g"
                    ),
                    USDANutrient(number="204", name="Total lipid (fat)", amount=0.3, unit="g"),
                ],
            )
        else:  # Broccoli
            return USDAFoodItem(
                fdc_id="22222",
                description="Broccoli, steamed",
                data_type="Survey (FNDDS)",
                nutrients=[
                    USDANutrient(number="203", name="Protein", amount=2.4, unit="g"),
                    USDANutrient(
                        number="205", name="Carbohydrate, by difference", amount=5.6, unit="g"
                    ),
                    USDANutrient(number="204", name="Total lipid (fat)", amount=0.4, unit="g"),
                ],
            )

    mock_usda_client.get_food = AsyncMock(side_effect=mock_get_food)

    # ACT
    analyses = await orchestrator_with_photo.analyze_from_photo(
        user_id=user_id,
        image_url="https://example.com/meal.jpg",
    )

    # ASSERT
    assert len(analyses) == 2
    assert any(a.meal_name == "White Rice" for a in analyses)
    assert any(a.meal_name == "Steamed Broccoli" for a in analyses)


@pytest.mark.asyncio
async def test_analyze_from_photo_no_recognition_service(
    orchestrator: MealAnalysisOrchestrator,
    user_id: UserId,
) -> None:
    """Test photo analysis fails without recognition service."""
    # ACT & ASSERT
    with pytest.raises(ValueError, match="Food recognition service not configured"):
        await orchestrator.analyze_from_photo(
            user_id=user_id,
            image_url="https://example.com/meal.jpg",
        )


@pytest.mark.asyncio
async def test_analyze_from_photo_recognition_failed(
    orchestrator_with_photo: MealAnalysisOrchestrator,
    mock_food_recognition_service: Any,
    user_id: UserId,
) -> None:
    """Test photo analysis when AI recognition fails."""
    # ARRANGE
    from backend.v2.domain.meal.recognition.models import (
        FoodRecognitionResult,
        RecognitionStatus,
    )

    recognition_result = FoodRecognitionResult(
        items=[],
        status=RecognitionStatus.FAILED,
        raw_response="Error: Unable to process image",
    )
    mock_food_recognition_service.recognize = AsyncMock(return_value=recognition_result)

    # ACT & ASSERT
    with pytest.raises(ValueError, match="Food recognition failed"):
        await orchestrator_with_photo.analyze_from_photo(
            user_id=user_id,
            image_url="https://example.com/meal.jpg",
        )


@pytest.mark.asyncio
async def test_analyze_from_photo_no_usda_matches(
    orchestrator_with_photo: MealAnalysisOrchestrator,
    mock_food_recognition_service: Any,
    mock_usda_client: Any,
    user_id: UserId,
) -> None:
    """Test photo analysis when no USDA matches found."""
    # ARRANGE
    from backend.v2.domain.meal.recognition.models import (
        FoodRecognitionResult,
        RecognizedFoodItem,
        RecognitionStatus,
    )

    recognition_result = FoodRecognitionResult(
        items=[
            RecognizedFoodItem(
                label="unknown food",
                display_name="Mystery Food",
                quantity_g=100.0,
                confidence=0.5,
            )
        ],
        status=RecognitionStatus.SUCCESS,
    )
    mock_food_recognition_service.recognize = AsyncMock(return_value=recognition_result)

    # Mock USDA returns no results
    mock_usda_client.search_foods = AsyncMock(
        return_value=USDASearchResult(
            foods=[],
            total_hits=0,
            current_page=1,
            total_pages=0,
        )
    )

    # ACT & ASSERT
    with pytest.raises(ValueError, match="No USDA matches found"):
        await orchestrator_with_photo.analyze_from_photo(
            user_id=user_id,
            image_url="https://example.com/meal.jpg",
        )


@pytest.mark.asyncio
async def test_analyze_from_photo_idempotency(
    orchestrator_with_photo: MealAnalysisOrchestrator,
    mock_repository: Any,
    user_id: UserId,
) -> None:
    """Test photo analysis returns cached result when available."""
    # ARRANGE
    analysis_id = AnalysisId.generate()
    cached_analysis = MealAnalysis.create_new(
        user_id=user_id,
        meal_name="Cached Meal",
        nutrient_profile=NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=20.0,
            fat=5.0,
            source="USDA",
            confidence=0.9,
            quantity_g=100.0,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.AI_VISION,
            confidence=0.9,
            processing_time_ms=1000,
        ),
        analysis_id=analysis_id,
    )

    mock_repository.exists = AsyncMock(return_value=True)
    mock_repository.get_by_id = AsyncMock(return_value=cached_analysis)

    # ACT
    analyses = await orchestrator_with_photo.analyze_from_photo(
        user_id=user_id,
        image_url="https://example.com/meal.jpg",
        analysis_id=analysis_id,
    )

    # ASSERT
    assert len(analyses) == 1
    assert analyses[0].meal_name == "Cached Meal"


@pytest.mark.asyncio
async def test_analyze_from_usda_with_fiber_and_sugar(
    orchestrator: MealAnalysisOrchestrator,
    mock_usda_client: Any,
    user_id: UserId,
) -> None:
    """Test USDA analysis with fiber and sugar nutrients."""
    # ARRANGE
    usda_search = USDASearchResult(
        foods=[
            USDAFoodItem(
                fdc_id="12345",
                description="Banana, raw",
                data_type="Survey (FNDDS)",
                nutrients=[
                    USDANutrient(number="203", name="Protein", amount=1.1, unit="g"),
                    USDANutrient(
                        number="205",
                        name="Carbohydrate, by difference",
                        amount=22.8,
                        unit="g",
                    ),
                    USDANutrient(
                        number="204",
                        name="Total lipid (fat)",
                        amount=0.3,
                        unit="g",
                    ),
                    USDANutrient(
                        number="291",
                        name="Fiber, total dietary",
                        amount=2.6,
                        unit="g",
                    ),
                    USDANutrient(
                        number="269",
                        name="Sugars, total",
                        amount=12.2,
                        unit="g",
                    ),
                ],
            )
        ],
        total_hits=1,
        current_page=1,
        total_pages=1,
    )

    mock_usda_client.search_foods = AsyncMock(return_value=usda_search)
    mock_usda_client.get_food = AsyncMock(return_value=usda_search.foods[0])

    # ACT
    analysis = await orchestrator.analyze_from_usda_search(
        user_id=user_id,
        search_query="banana",
        quantity_g=118.0,
    )

    # ASSERT
    assert analysis.nutrient_profile.fiber == 2.6
    assert analysis.nutrient_profile.sugar == 12.2
    assert analysis.nutrient_profile.protein == 1.1
    assert analysis.nutrient_profile.carbs == 22.8
    assert analysis.nutrient_profile.fat == 0.3


@pytest.mark.asyncio
async def test_analyze_from_photo_partial_usda_failures(
    orchestrator_with_photo: MealAnalysisOrchestrator,
    mock_food_recognition_service: Any,
    mock_usda_client: Any,
    user_id: UserId,
) -> None:
    """Test photo analysis with some USDA lookup failures."""
    from backend.v2.domain.meal.recognition.models import (
        FoodRecognitionResult,
        RecognizedFoodItem,
        RecognitionStatus,
    )

    # ARRANGE: Recognize 2 items, but only 1 has USDA match
    recognition_result = FoodRecognitionResult(
        items=[
            RecognizedFoodItem(
                label="banana",
                display_name="Banana",
                category="fruit",
                confidence=0.95,
                quantity_g=118.0,
                quantity_unit="g",
            ),
            RecognizedFoodItem(
                label="unknown_exotic_fruit",
                display_name="Unknown Fruit",
                category="fruit",
                confidence=0.60,
                quantity_g=50.0,
                quantity_unit="g",
            ),
        ],
        status=RecognitionStatus.SUCCESS,
        confidence=0.85,
        processing_time_ms=1500,
    )

    mock_food_recognition_service.recognize = AsyncMock(return_value=recognition_result)

    # First item succeeds
    usda_search_banana = USDASearchResult(
        foods=[
            USDAFoodItem(
                fdc_id="12345",
                description="Banana",
                data_type="Survey (FNDDS)",
                nutrients=[
                    USDANutrient(number="203", name="Protein", amount=1.1, unit="g"),
                    USDANutrient(
                        number="205",
                        name="Carbohydrate, by difference",
                        amount=22.8,
                        unit="g",
                    ),
                    USDANutrient(
                        number="204",
                        name="Total lipid (fat)",
                        amount=0.3,
                        unit="g",
                    ),
                ],
            )
        ],
        total_hits=1,
        current_page=1,
        total_pages=1,
    )

    # Second item fails
    def usda_side_effect(query: str, page_size: int = 1):
        if "banana" in query.lower():
            return usda_search_banana
        # Simulate USDA failure for unknown fruit
        raise ValueError(f"USDA lookup failed for: {query}")

    mock_usda_client.search_foods = AsyncMock(side_effect=usda_side_effect)
    mock_usda_client.get_food = AsyncMock(return_value=usda_search_banana.foods[0])

    # ACT
    analyses = await orchestrator_with_photo.analyze_from_photo(
        user_id=user_id,
        image_url="https://example.com/meal.jpg",
    )

    # ASSERT: Only 1 analysis (banana), unknown_exotic_fruit skipped
    assert len(analyses) == 1
    assert "Banana" in analyses[0].meal_name
