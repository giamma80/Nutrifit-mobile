"""
Tests for meal analysis domain models.

Tests MealAnalysis, AnalysisMetadata, and related value objects.
"""

from datetime import datetime, timezone, timedelta

import pytest

from backend.v2.domain.meal.orchestration.analysis_models import (
    AnalysisSource,
    AnalysisStatus,
    MealAnalysisMetadata,
    MealAnalysis,
)
from backend.v2.domain.shared.value_objects import UserId, AnalysisId
from backend.v2.domain.meal.nutrition.models import (
    NutrientProfile,
    NutrientSource,
)


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def sample_user_id() -> UserId:
    """Sample user ID for tests."""
    return UserId(value="user123")


@pytest.fixture
def sample_analysis_id() -> AnalysisId:
    """Sample analysis ID for tests."""
    return AnalysisId(value="analysis_abc123def456")


@pytest.fixture
def sample_nutrient_profile() -> NutrientProfile:
    """Sample nutrient profile for tests."""
    return NutrientProfile(
        calories=89,
        protein=1.09,
        carbs=22.84,
        fat=0.33,
        fiber=2.6,
        sugar=12.23,
        sodium=1.0,
        source=NutrientSource.USDA,
        confidence=0.95,
        quantity_g=100.0,
    )


@pytest.fixture
def sample_metadata() -> MealAnalysisMetadata:
    """Sample metadata for tests."""
    return MealAnalysisMetadata(
        source=AnalysisSource.BARCODE_SCAN,
        confidence=0.95,
        processing_time_ms=250,
        barcode_value="3017620422003",
    )


@pytest.fixture
def sample_analysis(
    sample_analysis_id: AnalysisId,
    sample_user_id: UserId,
    sample_nutrient_profile: NutrientProfile,
    sample_metadata: MealAnalysisMetadata,
) -> MealAnalysis:
    """Sample meal analysis for tests."""
    now = datetime.now(timezone.utc)
    return MealAnalysis(
        analysis_id=sample_analysis_id,
        user_id=sample_user_id,
        meal_name="Banana",
        nutrient_profile=sample_nutrient_profile,
        quantity_g=118.0,
        metadata=sample_metadata,
        status=AnalysisStatus.COMPLETED,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )


# ═══════════════════════════════════════════════════════════
# METADATA TESTS
# ═══════════════════════════════════════════════════════════


def test_metadata_creation(sample_metadata: MealAnalysisMetadata) -> None:
    """Test metadata creation with all fields."""
    assert sample_metadata.source == AnalysisSource.BARCODE_SCAN
    assert sample_metadata.confidence == 0.95
    assert sample_metadata.processing_time_ms == 250
    assert sample_metadata.barcode_value == "3017620422003"


def test_metadata_confidence_rounded() -> None:
    """Test confidence is rounded to 2 decimals."""
    metadata = MealAnalysisMetadata(
        source=AnalysisSource.AI_VISION,
        confidence=0.123456,
        processing_time_ms=1500,
    )
    assert metadata.confidence == 0.12


def test_metadata_with_ai_fields() -> None:
    """Test metadata with AI-specific fields."""
    metadata = MealAnalysisMetadata(
        source=AnalysisSource.AI_VISION,
        confidence=0.88,
        processing_time_ms=1800,
        ai_model_version="gpt-4-vision-preview",
        image_url="https://example.com/meal.jpg",
    )
    assert metadata.ai_model_version == "gpt-4-vision-preview"
    assert metadata.image_url == "https://example.com/meal.jpg"


def test_metadata_with_fallback() -> None:
    """Test metadata with fallback information."""
    metadata = MealAnalysisMetadata(
        source=AnalysisSource.CATEGORY_PROFILE,
        confidence=0.60,
        processing_time_ms=100,
        fallback_reason="Barcode not found in database",
    )
    assert metadata.fallback_reason == "Barcode not found in database"


def test_metadata_immutable() -> None:
    """Test metadata is immutable."""
    metadata = MealAnalysisMetadata(
        source=AnalysisSource.USDA_SEARCH,
        confidence=0.90,
        processing_time_ms=500,
    )
    with pytest.raises(Exception):  # Pydantic frozen error
        metadata.confidence = 0.80


# ═══════════════════════════════════════════════════════════
# MEAL ANALYSIS TESTS
# ═══════════════════════════════════════════════════════════


def test_analysis_creation(sample_analysis: MealAnalysis) -> None:
    """Test meal analysis creation with all required fields."""
    assert sample_analysis.meal_name == "Banana"
    assert sample_analysis.quantity_g == 118.0
    assert sample_analysis.status == AnalysisStatus.COMPLETED
    assert sample_analysis.converted_to_meal_at is None


def test_analysis_is_not_expired_when_fresh(
    sample_analysis: MealAnalysis,
) -> None:
    """Test fresh analysis is not expired."""
    assert not sample_analysis.is_expired()


def test_analysis_is_expired_when_old() -> None:
    """Test analysis is expired when created >24h ago."""
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(hours=25)

    analysis = MealAnalysis(
        analysis_id=AnalysisId(value="analysis_0123456789ab"),
        user_id=UserId(value="user123"),
        meal_name="Old meal",
        nutrient_profile=NutrientProfile(
            calories=100,
            protein=10.0,
            carbs=20.0,
            fat=5.0,
            source=NutrientSource.MANUAL,
            confidence=0.8,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.MANUAL_ENTRY,
            confidence=0.80,
            processing_time_ms=0,
        ),
        created_at=old_time,
        expires_at=old_time + timedelta(hours=24),
    )

    assert analysis.is_expired()


def test_analysis_is_convertible_when_completed(
    sample_analysis: MealAnalysis,
) -> None:
    """Test completed analysis is convertible."""
    assert sample_analysis.is_convertible()


def test_analysis_not_convertible_when_partial() -> None:
    """Test partial analysis is not convertible."""
    now = datetime.now(timezone.utc)
    analysis = MealAnalysis(
        analysis_id=AnalysisId(value="analysis_0a1234567890"),
        user_id=UserId(value="user123"),
        meal_name="Partial meal",
        nutrient_profile=NutrientProfile(
            calories=100,
            protein=10.0,
            carbs=20.0,
            fat=5.0,
            source=NutrientSource.CATEGORY_PROFILE,
            confidence=0.6,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.CATEGORY_PROFILE,
            confidence=0.60,
            processing_time_ms=50,
            fallback_reason="Primary source failed",
        ),
        status=AnalysisStatus.PARTIAL,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )

    assert not analysis.is_convertible()


def test_analysis_not_convertible_when_already_converted(
    sample_analysis: MealAnalysis,
) -> None:
    """Test analysis not convertible if already converted."""
    # Create new analysis with converted timestamp
    now = datetime.now(timezone.utc)
    converted_analysis = MealAnalysis(
        analysis_id=sample_analysis.analysis_id,
        user_id=sample_analysis.user_id,
        meal_name=sample_analysis.meal_name,
        nutrient_profile=sample_analysis.nutrient_profile,
        quantity_g=sample_analysis.quantity_g,
        metadata=sample_analysis.metadata,
        status=sample_analysis.status,
        created_at=sample_analysis.created_at,
        expires_at=sample_analysis.expires_at,
        converted_to_meal_at=now,
    )

    assert not converted_analysis.is_convertible()


def test_analysis_time_until_expiration() -> None:
    """Test time until expiration calculation."""
    now = datetime.now(timezone.utc)
    analysis = MealAnalysis(
        analysis_id=AnalysisId(value="analysis_01234567890a"),
        user_id=UserId(value="user123"),
        meal_name="Test meal",
        nutrient_profile=NutrientProfile(
            calories=100,
            protein=10.0,
            carbs=20.0,
            fat=5.0,
            source=NutrientSource.USDA,
            confidence=0.9,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.USDA_SEARCH,
            confidence=0.90,
            processing_time_ms=300,
        ),
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )

    time_left = analysis.time_until_expiration()
    # Should be approximately 24 hours (with small tolerance for test execution time)
    assert timedelta(hours=23, minutes=59) < time_left < timedelta(hours=24)


def test_analysis_factory_method_creates_valid_instance() -> None:
    """Test factory method creates valid analysis."""
    user_id = UserId(value="factory123")
    profile = NutrientProfile(
        calories=200,
        protein=20.0,
        carbs=30.0,
        fat=8.0,
        source=NutrientSource.USDA,
        confidence=0.95,
    )
    metadata = MealAnalysisMetadata(
        source=AnalysisSource.BARCODE_SCAN,
        confidence=0.95,
        processing_time_ms=200,
    )

    analysis = MealAnalysis.create_new(
        user_id=user_id,
        meal_name="Factory meal",
        nutrient_profile=profile,
        quantity_g=150.0,
        metadata=metadata,
    )

    assert analysis.user_id == user_id
    assert analysis.meal_name == "Factory meal"
    assert analysis.quantity_g == 150.0
    assert analysis.status == AnalysisStatus.COMPLETED
    assert not analysis.is_expired()
    assert analysis.is_convertible()


def test_analysis_factory_method_with_custom_id() -> None:
    """Test factory method respects custom analysis_id."""
    custom_id = AnalysisId(value="analysis_0cdef1234567")
    analysis = MealAnalysis.create_new(
        user_id=UserId(value="user123"),
        meal_name="Custom ID meal",
        nutrient_profile=NutrientProfile(
            calories=100,
            protein=10.0,
            carbs=15.0,
            fat=3.0,
            source=NutrientSource.USDA,
            confidence=0.9,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.USDA_SEARCH,
            confidence=0.90,
            processing_time_ms=250,
        ),
        analysis_id=custom_id,
    )

    assert analysis.analysis_id == custom_id


def test_analysis_factory_method_custom_ttl() -> None:
    """Test factory method respects custom TTL."""
    analysis = MealAnalysis.create_new(
        user_id=UserId(value="user123"),
        meal_name="Custom TTL meal",
        nutrient_profile=NutrientProfile(
            calories=100,
            protein=10.0,
            carbs=15.0,
            fat=3.0,
            source=NutrientSource.USDA,
            confidence=0.9,
        ),
        quantity_g=100.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.USDA_SEARCH,
            confidence=0.90,
            processing_time_ms=250,
        ),
        ttl_hours=12,
    )

    time_left = analysis.time_until_expiration()
    # Should be approximately 12 hours
    assert timedelta(hours=11, minutes=59) < time_left < timedelta(hours=12)


def test_analysis_to_dict_serialization() -> None:
    """Test analysis can be serialized to dict."""
    analysis = MealAnalysis.create_new(
        user_id=UserId(value="user123"),
        meal_name="Serializable meal",
        nutrient_profile=NutrientProfile(
            calories=150,
            protein=15.0,
            carbs=20.0,
            fat=5.0,
            source=NutrientSource.USDA,
            confidence=0.9,
        ),
        quantity_g=120.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.BARCODE_SCAN,
            confidence=0.95,
            processing_time_ms=300,
            barcode_value="123456",
        ),
    )

    data = analysis.to_dict()

    assert isinstance(data, dict)
    assert data["meal_name"] == "Serializable meal"
    assert data["quantity_g"] == 120.0
    assert data["status"] == "COMPLETED"  # Enum converted to value


# ═══════════════════════════════════════════════════════════
# VALIDATION TESTS
# ═══════════════════════════════════════════════════════════


def test_analysis_validation_expires_after_created() -> None:
    """Test validation: expires_at must be after created_at."""
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="expires_at must be after created_at"):
        MealAnalysis(
            analysis_id=AnalysisId(value="analysis_00001234567a"),
            user_id=UserId(value="user123"),
            meal_name="Invalid",
            nutrient_profile=NutrientProfile(
                calories=100,
                protein=10.0,
                carbs=15.0,
                fat=3.0,
                source=NutrientSource.USDA,
                confidence=0.9,
            ),
            quantity_g=100.0,
            metadata=MealAnalysisMetadata(
                source=AnalysisSource.MANUAL_ENTRY,
                confidence=0.8,
                processing_time_ms=0,
            ),
            created_at=now,
            expires_at=now - timedelta(hours=1),  # Before created_at!
        )


def test_analysis_validation_converted_after_created() -> None:
    """Test validation: converted_to_meal_at must be after created_at."""
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="converted_to_meal_at must be after created_at"):
        MealAnalysis(
            analysis_id=AnalysisId(value="analysis_0000456789ab"),
            user_id=UserId(value="user123"),
            meal_name="Invalid conversion",
            nutrient_profile=NutrientProfile(
                calories=100,
                protein=10.0,
                carbs=15.0,
                fat=3.0,
                source=NutrientSource.USDA,
                confidence=0.9,
            ),
            quantity_g=100.0,
            metadata=MealAnalysisMetadata(
                source=AnalysisSource.MANUAL_ENTRY,
                confidence=0.8,
                processing_time_ms=0,
            ),
            created_at=now,
            expires_at=now + timedelta(hours=24),
            converted_to_meal_at=now - timedelta(hours=1),  # Before created_at!
        )


def test_analysis_validation_empty_meal_name() -> None:
    """Test validation: meal_name cannot be empty."""
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        MealAnalysis(
            analysis_id=AnalysisId(value="analysis_0e0012345678"),
            user_id=UserId(value="user123"),
            meal_name="",  # Empty!
            nutrient_profile=NutrientProfile(
                calories=100,
                protein=10.0,
                carbs=15.0,
                fat=3.0,
                source=NutrientSource.USDA,
                confidence=0.9,
            ),
            quantity_g=100.0,
            metadata=MealAnalysisMetadata(
                source=AnalysisSource.MANUAL_ENTRY,
                confidence=0.8,
                processing_time_ms=0,
            ),
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )


def test_analysis_validation_negative_quantity() -> None:
    """Test validation: quantity_g must be positive."""
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError):
        MealAnalysis(
            analysis_id=AnalysisId(value="analysis_0e0e12345678"),
            user_id=UserId(value="user123"),
            meal_name="Negative quantity",
            nutrient_profile=NutrientProfile(
                calories=100,
                protein=10.0,
                carbs=15.0,
                fat=3.0,
                source=NutrientSource.USDA,
                confidence=0.9,
            ),
            quantity_g=-50.0,  # Negative!
            metadata=MealAnalysisMetadata(
                source=AnalysisSource.MANUAL_ENTRY,
                confidence=0.8,
                processing_time_ms=0,
            ),
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
