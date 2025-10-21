"""
Tests for meal analysis repository (in-memory implementation).

Tests repository interface with in-memory mock for unit testing.
Integration tests with real MongoDB are in tests/integration/.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

import pytest

from backend.v2.domain.shared.value_objects import (
    UserId,
    AnalysisId,
    MealId,
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


# ═══════════════════════════════════════════════════════════
# IN-MEMORY REPOSITORY (FOR TESTING)
# ═══════════════════════════════════════════════════════════


class InMemoryMealAnalysisRepository:
    """
    In-memory implementation for testing.

    Simulates repository behavior without database.
    """

    def __init__(self) -> None:
        self._storage: dict[str, MealAnalysis] = {}

    async def save(self, analysis: MealAnalysis) -> None:
        """Save analysis to memory."""
        self._storage[analysis.analysis_id.value] = analysis

    async def get_by_id(self, analysis_id: AnalysisId) -> Optional[MealAnalysis]:
        """Get analysis from memory."""
        return self._storage.get(analysis_id.value)

    async def get_by_user(
        self,
        user_id: UserId,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[MealAnalysis]:
        """Get user analyses from memory."""
        results = []
        for analysis in self._storage.values():
            if analysis.user_id.value != user_id.value:
                continue

            if not include_expired and analysis.is_expired():
                continue

            results.append(analysis)

        # Sort by created_at DESC
        results.sort(key=lambda a: a.created_at, reverse=True)
        return results[:limit]

    async def mark_converted(
        self,
        analysis_id: AnalysisId,
        meal_id: MealId,
    ) -> None:
        """Mark analysis as converted."""
        analysis = self._storage.get(analysis_id.value)
        if analysis is None:
            raise ValueError(f"Analysis not found: {analysis_id.value}")

        # Create new instance with updated timestamp
        updated = MealAnalysis(
            analysis_id=analysis.analysis_id,
            user_id=analysis.user_id,
            meal_name=analysis.meal_name,
            nutrient_profile=analysis.nutrient_profile,
            quantity_g=analysis.quantity_g,
            metadata=analysis.metadata,
            status=analysis.status,
            created_at=analysis.created_at,
            expires_at=analysis.expires_at,
            converted_to_meal_at=datetime.now(timezone.utc),
        )
        self._storage[analysis_id.value] = updated

    async def delete_expired(self) -> int:
        """Delete expired analyses."""
        to_delete = [aid for aid, analysis in self._storage.items() if analysis.is_expired()]

        for aid in to_delete:
            del self._storage[aid]

        return len(to_delete)

    async def exists(self, analysis_id: AnalysisId) -> bool:
        """Check if analysis exists."""
        return analysis_id.value in self._storage


# ═══════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════


@pytest.fixture
def repository() -> InMemoryMealAnalysisRepository:
    """In-memory repository for testing."""
    return InMemoryMealAnalysisRepository()


@pytest.fixture
def sample_analysis() -> MealAnalysis:
    """Sample meal analysis for testing."""
    return MealAnalysis.create_new(
        user_id=UserId(value="user123"),
        meal_name="Test Meal",
        nutrient_profile=NutrientProfile(
            calories=200,
            protein=20.0,
            carbs=30.0,
            fat=8.0,
            source=NutrientSource.USDA,
            confidence=0.95,
        ),
        quantity_g=150.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.BARCODE_SCAN,
            confidence=0.95,
            processing_time_ms=250,
            barcode_value="123456",
        ),
    )


# ═══════════════════════════════════════════════════════════
# REPOSITORY TESTS
# ═══════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_save_and_retrieve(
    repository: InMemoryMealAnalysisRepository,
    sample_analysis: MealAnalysis,
) -> None:
    """Test saving and retrieving analysis."""
    # ACT
    await repository.save(sample_analysis)
    retrieved = await repository.get_by_id(sample_analysis.analysis_id)

    # ASSERT
    assert retrieved is not None
    assert retrieved.analysis_id == sample_analysis.analysis_id
    assert retrieved.meal_name == sample_analysis.meal_name
    assert retrieved.quantity_g == sample_analysis.quantity_g


@pytest.mark.asyncio
async def test_save_upsert_behavior(
    repository: InMemoryMealAnalysisRepository,
    sample_analysis: MealAnalysis,
) -> None:
    """Test that save performs upsert (update if exists)."""
    # ARRANGE - Save original
    await repository.save(sample_analysis)

    # ACT - Save updated version with same ID
    updated = MealAnalysis(
        analysis_id=sample_analysis.analysis_id,
        user_id=sample_analysis.user_id,
        meal_name="Updated Meal",  # Changed
        nutrient_profile=sample_analysis.nutrient_profile,
        quantity_g=200.0,  # Changed
        metadata=sample_analysis.metadata,
        status=sample_analysis.status,
        created_at=sample_analysis.created_at,
        expires_at=sample_analysis.expires_at,
    )
    await repository.save(updated)

    # ASSERT - Should have updated version
    retrieved = await repository.get_by_id(sample_analysis.analysis_id)
    assert retrieved is not None
    assert retrieved.meal_name == "Updated Meal"
    assert retrieved.quantity_g == 200.0


@pytest.mark.asyncio
async def test_get_by_id_not_found(
    repository: InMemoryMealAnalysisRepository,
) -> None:
    """Test retrieving non-existent analysis returns None."""
    # ACT
    result = await repository.get_by_id(AnalysisId(value="analysis_000000000000"))

    # ASSERT
    assert result is None


@pytest.mark.asyncio
async def test_get_by_user(
    repository: InMemoryMealAnalysisRepository,
) -> None:
    """Test retrieving user's analyses."""
    # ARRANGE - Create analyses for different users
    user1_id = UserId(value="user1")
    user2_id = UserId(value="user2")

    analysis1 = MealAnalysis.create_new(
        user_id=user1_id,
        meal_name="User1 Meal 1",
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
            processing_time_ms=200,
        ),
    )

    analysis2 = MealAnalysis.create_new(
        user_id=user1_id,
        meal_name="User1 Meal 2",
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
            processing_time_ms=250,
        ),
    )

    analysis3 = MealAnalysis.create_new(
        user_id=user2_id,
        meal_name="User2 Meal",
        nutrient_profile=NutrientProfile(
            calories=200,
            protein=20.0,
            carbs=25.0,
            fat=7.0,
            source=NutrientSource.USDA,
            confidence=0.9,
        ),
        quantity_g=140.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.AI_VISION,
            confidence=0.85,
            processing_time_ms=1500,
        ),
    )

    await repository.save(analysis1)
    await repository.save(analysis2)
    await repository.save(analysis3)

    # ACT
    user1_analyses = await repository.get_by_user(user1_id)

    # ASSERT
    assert len(user1_analyses) == 2
    assert all(a.user_id == user1_id for a in user1_analyses)
    # Should be sorted by created_at DESC (newest first)
    assert user1_analyses[0].created_at >= user1_analyses[1].created_at


@pytest.mark.asyncio
async def test_get_by_user_with_limit(
    repository: InMemoryMealAnalysisRepository,
) -> None:
    """Test get_by_user respects limit parameter."""
    # ARRANGE - Create 5 analyses for same user
    user_id = UserId(value="user123")

    for i in range(5):
        analysis = MealAnalysis.create_new(
            user_id=user_id,
            meal_name=f"Meal {i}",
            nutrient_profile=NutrientProfile(
                calories=100 + i * 10,
                protein=10.0,
                carbs=15.0,
                fat=3.0,
                source=NutrientSource.USDA,
                confidence=0.9,
            ),
            quantity_g=100.0,
            metadata=MealAnalysisMetadata(
                source=AnalysisSource.MANUAL_ENTRY,
                confidence=0.80,
                processing_time_ms=50,
            ),
        )
        await repository.save(analysis)

    # ACT
    results = await repository.get_by_user(user_id, limit=3)

    # ASSERT
    assert len(results) == 3


@pytest.mark.asyncio
async def test_get_by_user_excludes_expired(
    repository: InMemoryMealAnalysisRepository,
) -> None:
    """Test get_by_user excludes expired analyses by default."""
    # ARRANGE - Create expired analysis
    user_id = UserId(value="user123")
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)

    expired_analysis = MealAnalysis(
        analysis_id=AnalysisId.generate(),
        user_id=user_id,
        meal_name="Expired Meal",
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
            confidence=0.80,
            processing_time_ms=0,
        ),
        status=AnalysisStatus.COMPLETED,
        created_at=old_time,
        expires_at=old_time + timedelta(hours=24),
    )

    fresh_analysis = MealAnalysis.create_new(
        user_id=user_id,
        meal_name="Fresh Meal",
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
            source=AnalysisSource.USDA_SEARCH,
            confidence=0.90,
            processing_time_ms=300,
        ),
    )

    await repository.save(expired_analysis)
    await repository.save(fresh_analysis)

    # ACT
    results = await repository.get_by_user(user_id)

    # ASSERT - Should only return fresh analysis
    assert len(results) == 1
    assert results[0].meal_name == "Fresh Meal"


@pytest.mark.asyncio
async def test_get_by_user_include_expired(
    repository: InMemoryMealAnalysisRepository,
) -> None:
    """Test get_by_user includes expired when requested."""
    # ARRANGE
    user_id = UserId(value="user123")
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)

    expired_analysis = MealAnalysis(
        analysis_id=AnalysisId.generate(),
        user_id=user_id,
        meal_name="Expired Meal",
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
            confidence=0.80,
            processing_time_ms=0,
        ),
        status=AnalysisStatus.COMPLETED,
        created_at=old_time,
        expires_at=old_time + timedelta(hours=24),
    )

    await repository.save(expired_analysis)

    # ACT
    results = await repository.get_by_user(user_id, include_expired=True)

    # ASSERT - Should include expired
    assert len(results) == 1
    assert results[0].meal_name == "Expired Meal"


@pytest.mark.asyncio
async def test_mark_converted(
    repository: InMemoryMealAnalysisRepository,
    sample_analysis: MealAnalysis,
) -> None:
    """Test marking analysis as converted."""
    # ARRANGE
    await repository.save(sample_analysis)
    meal_id = MealId(value="507f1f77bcf86cd799439011")

    # ACT
    await repository.mark_converted(sample_analysis.analysis_id, meal_id)

    # ASSERT
    updated = await repository.get_by_id(sample_analysis.analysis_id)
    assert updated is not None
    assert updated.converted_to_meal_at is not None
    assert not updated.is_convertible()  # No longer convertible


@pytest.mark.asyncio
async def test_mark_converted_not_found(
    repository: InMemoryMealAnalysisRepository,
) -> None:
    """Test marking non-existent analysis raises error."""
    # ACT & ASSERT
    with pytest.raises(ValueError, match="Analysis not found"):
        await repository.mark_converted(
            AnalysisId(value="analysis_000000000000"),
            MealId(value="507f1f77bcf86cd799439011"),
        )


@pytest.mark.asyncio
async def test_delete_expired(
    repository: InMemoryMealAnalysisRepository,
) -> None:
    """Test deleting expired analyses."""
    # ARRANGE - Create mix of fresh and expired
    user_id = UserId(value="user123")
    old_time = datetime.now(timezone.utc) - timedelta(hours=25)

    expired1 = MealAnalysis(
        analysis_id=AnalysisId.generate(),
        user_id=user_id,
        meal_name="Expired 1",
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
            confidence=0.80,
            processing_time_ms=0,
        ),
        status=AnalysisStatus.COMPLETED,
        created_at=old_time,
        expires_at=old_time + timedelta(hours=24),
    )

    expired2 = MealAnalysis(
        analysis_id=AnalysisId.generate(),
        user_id=user_id,
        meal_name="Expired 2",
        nutrient_profile=NutrientProfile(
            calories=120,
            protein=12.0,
            carbs=18.0,
            fat=4.0,
            source=NutrientSource.USDA,
            confidence=0.9,
        ),
        quantity_g=110.0,
        metadata=MealAnalysisMetadata(
            source=AnalysisSource.MANUAL_ENTRY,
            confidence=0.80,
            processing_time_ms=0,
        ),
        status=AnalysisStatus.COMPLETED,
        created_at=old_time,
        expires_at=old_time + timedelta(hours=24),
    )

    fresh = MealAnalysis.create_new(
        user_id=user_id,
        meal_name="Fresh",
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
            source=AnalysisSource.USDA_SEARCH,
            confidence=0.90,
            processing_time_ms=300,
        ),
    )

    await repository.save(expired1)
    await repository.save(expired2)
    await repository.save(fresh)

    # ACT
    deleted_count = await repository.delete_expired()

    # ASSERT
    assert deleted_count == 2
    remaining = await repository.get_by_user(user_id, include_expired=True)
    assert len(remaining) == 1
    assert remaining[0].meal_name == "Fresh"


@pytest.mark.asyncio
async def test_exists(
    repository: InMemoryMealAnalysisRepository,
    sample_analysis: MealAnalysis,
) -> None:
    """Test checking if analysis exists."""
    # ARRANGE
    await repository.save(sample_analysis)

    # ACT & ASSERT
    assert await repository.exists(sample_analysis.analysis_id)
    assert not await repository.exists(AnalysisId(value="analysis_000000000000"))
