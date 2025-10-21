"""
Unit tests for MongoDB meal analysis repository.

Uses AsyncMock for Motor (MongoDB async driver) to avoid real DB dependencies.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from backend.v2.infrastructure.database.analysis_repository_mongo import (
    MealAnalysisRepositoryMongo,
)
from backend.v2.domain.meal.orchestration.analysis_models import (
    MealAnalysis,
    MealAnalysisMetadata,
    AnalysisSource,
    AnalysisStatus,
)
from backend.v2.domain.meal.nutrition.models import NutrientProfile
from backend.v2.domain.shared.value_objects import (
    UserId,
    AnalysisId,
    MealId,
)


@pytest.fixture
def mock_db() -> MagicMock:
    """Mock Motor AsyncIOMotorDatabase."""
    db = MagicMock()
    collection = AsyncMock()
    db.__getitem__ = MagicMock(return_value=collection)
    return db


@pytest.fixture
def mock_collection(mock_db: MagicMock) -> AsyncMock:
    """Get mock collection from mock database."""
    collection: AsyncMock = mock_db["meal_analyses"]
    return collection


@pytest.fixture
def repository(mock_db: MagicMock) -> MealAnalysisRepositoryMongo:
    """Repository instance with mocked database."""
    return MealAnalysisRepositoryMongo(mock_db)


@pytest.fixture
def sample_analysis() -> MealAnalysis:
    """Sample meal analysis for testing."""
    nutrient_profile = NutrientProfile(
        calories=250,
        protein=12.5,
        carbs=35.0,
        fat=8.0,
        fiber=3.5,
        sugar=5.0,
        sodium=200.0,
        source="AI_ESTIMATE",
        confidence=0.92,
        quantity_g=150.0,
    )

    metadata = MealAnalysisMetadata(
        source=AnalysisSource.AI_VISION,
        confidence=0.92,
        processing_time_ms=1250,
        ai_model_version="gpt-4-vision-1.0",
        image_url="https://storage.example.com/img123.jpg",
        barcode_value=None,
        fallback_reason=None,
    )

    return MealAnalysis(
        analysis_id=AnalysisId(value="analysis_abc123def456"),
        user_id=UserId(value="user_456"),
        meal_name="Grilled Chicken Salad",
        nutrient_profile=nutrient_profile,
        quantity_g=150.0,
        metadata=metadata,
        status=AnalysisStatus.COMPLETED,
        created_at=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
        expires_at=datetime(2025, 1, 15, 18, 0, tzinfo=timezone.utc),
        converted_to_meal_at=None,
    )


class TestMealAnalysisRepositoryMongo:
    """Test suite for MongoDB meal analysis repository."""

    @pytest.mark.asyncio
    async def test_init_creates_collection_reference(self, mock_db: MagicMock) -> None:
        """Test repository initialization creates collection reference."""
        repo = MealAnalysisRepositoryMongo(mock_db)

        assert repo.db is mock_db
        assert repo.collection is not None
        assert repo._indexes_created is False

    @pytest.mark.asyncio
    async def test_ensure_indexes_creates_all_indexes(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
    ) -> None:
        """Test index creation on first access."""
        mock_collection.create_index = AsyncMock()

        await repository._ensure_indexes()

        # Should create 4 indexes
        assert mock_collection.create_index.call_count == 4

        # Verify TTL index
        calls = mock_collection.create_index.call_args_list
        assert any(call_args[0][0] == "expires_at" for call_args in calls), "TTL index not created"

        # Verify unique analysis_id index
        assert any(
            call_args[0][0] == "analysis_id" for call_args in calls
        ), "Unique analysis_id index not created"

        # Mark indexes as created
        assert repository._indexes_created is True

    @pytest.mark.asyncio
    async def test_ensure_indexes_called_once_only(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
    ) -> None:
        """Test indexes are created only once."""
        mock_collection.create_index = AsyncMock()

        await repository._ensure_indexes()
        await repository._ensure_indexes()
        await repository._ensure_indexes()

        # Should only be called 4 times (not 12)
        assert mock_collection.create_index.call_count == 4

    @pytest.mark.asyncio
    async def test_to_document_converts_analysis_correctly(
        self,
        repository: MealAnalysisRepositoryMongo,
        sample_analysis: MealAnalysis,
    ) -> None:
        """Test analysis is correctly converted to MongoDB document."""
        doc = repository._to_document(sample_analysis)

        assert doc["analysis_id"] == "analysis_abc123def456"
        assert doc["user_id"] == "user_456"
        assert doc["meal_name"] == "Grilled Chicken Salad"
        assert doc["quantity_g"] == 150.0
        assert doc["status"] == "COMPLETED"

        # Verify nested nutrient profile
        assert doc["nutrient_profile"]["calories"] == 250
        assert doc["nutrient_profile"]["protein"] == 12.5
        assert doc["nutrient_profile"]["source"] == "AI_ESTIMATE"

        # Verify nested metadata
        assert doc["metadata"]["source"] == "AI_VISION"
        assert doc["metadata"]["confidence"] == 0.92
        assert doc["metadata"]["ai_model_version"] == "gpt-4-vision-1.0"

        # Verify timestamps
        assert doc["created_at"] == datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        assert doc["expires_at"] == datetime(2025, 1, 15, 18, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_from_document_reconstructs_analysis(
        self,
        repository: MealAnalysisRepositoryMongo,
        sample_analysis: MealAnalysis,
    ) -> None:
        """Test MongoDB document is correctly converted back to analysis."""
        # Convert to document and back
        doc = repository._to_document(sample_analysis)
        reconstructed = repository._from_document(doc)

        assert reconstructed.analysis_id.value == "analysis_abc123def456"
        assert reconstructed.user_id.value == "user_456"
        assert reconstructed.meal_name == "Grilled Chicken Salad"
        assert reconstructed.quantity_g == 150.0
        assert reconstructed.status == AnalysisStatus.COMPLETED

        # Verify nutrient profile
        assert reconstructed.nutrient_profile.calories == 250
        assert reconstructed.nutrient_profile.protein == 12.5
        assert reconstructed.nutrient_profile.fiber == 3.5

        # Verify metadata
        assert reconstructed.metadata.source == AnalysisSource.AI_VISION
        assert reconstructed.metadata.confidence == 0.92
        assert reconstructed.metadata.ai_model_version == "gpt-4-vision-1.0"

    @pytest.mark.asyncio
    async def test_save_upserts_analysis(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
        sample_analysis: MealAnalysis,
    ) -> None:
        """Test save performs upsert operation."""
        mock_collection.update_one = AsyncMock()

        await repository.save(sample_analysis)

        # Verify update_one called with upsert=True
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args

        assert call_args[0][0] == {"analysis_id": "analysis_abc123def456"}
        assert call_args[1]["upsert"] is True

        # Verify document contains all fields
        set_data = call_args[0][1]["$set"]
        assert set_data["user_id"] == "user_456"
        assert set_data["meal_name"] == "Grilled Chicken Salad"

    @pytest.mark.asyncio
    async def test_get_by_id_returns_analysis(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
        sample_analysis: MealAnalysis,
    ) -> None:
        """Test get_by_id retrieves analysis successfully."""
        doc = repository._to_document(sample_analysis)
        mock_collection.find_one = AsyncMock(return_value=doc)

        result = await repository.get_by_id(AnalysisId(value="analysis_abc123def456"))

        assert result is not None
        assert result.analysis_id.value == "analysis_abc123def456"
        assert result.meal_name == "Grilled Chicken Salad"

        # Verify query
        mock_collection.find_one.assert_called_once_with({"analysis_id": "analysis_abc123def456"})

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
    ) -> None:
        """Test get_by_id returns None when analysis doesn't exist."""
        mock_collection.find_one = AsyncMock(return_value=None)

        result = await repository.get_by_id(AnalysisId(value="analysis_000000000000"))

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_user_excludes_expired_by_default(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
        sample_analysis: MealAnalysis,
    ) -> None:
        """Test get_by_user excludes expired analyses by default."""
        doc = repository._to_document(sample_analysis)

        # Mock cursor
        mock_cursor = AsyncMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[doc])

        mock_collection.find = MagicMock(return_value=mock_cursor)

        user_id = UserId(value="user_456")
        results = await repository.get_by_user(user_id, limit=10)

        # Verify query excludes expired
        call_args = mock_collection.find.call_args[0][0]
        assert call_args["user_id"] == "user_456"
        assert "$gt" in call_args["expires_at"]

        # Verify sorting and limiting
        mock_cursor.sort.assert_called_once_with("created_at", -1)
        mock_cursor.limit.assert_called_once_with(10)

        # Verify results
        assert len(results) == 1
        assert results[0].analysis_id.value == "analysis_abc123def456"

    @pytest.mark.asyncio
    async def test_get_by_user_includes_expired_when_requested(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
    ) -> None:
        """Test get_by_user includes expired when requested."""
        mock_cursor = AsyncMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[])

        mock_collection.find = MagicMock(return_value=mock_cursor)

        user_id = UserId(value="user_456")
        await repository.get_by_user(user_id, limit=5, include_expired=True)

        # Verify query does NOT filter by expires_at
        call_args = mock_collection.find.call_args[0][0]
        assert call_args == {"user_id": "user_456"}
        assert "expires_at" not in call_args

    @pytest.mark.asyncio
    async def test_mark_converted_updates_timestamp(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
    ) -> None:
        """Test mark_converted sets converted_to_meal_at timestamp."""
        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one = AsyncMock(return_value=mock_result)

        analysis_id = AnalysisId(value="analysis_abc123def456")
        meal_id = MealId(value="meal_789")

        await repository.mark_converted(analysis_id, meal_id)

        # Verify update call
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args

        assert call_args[0][0] == {"analysis_id": "analysis_abc123def456"}
        assert "converted_to_meal_at" in call_args[0][1]["$set"]

        # Verify timestamp is recent (within last 2 seconds)
        timestamp = call_args[0][1]["$set"]["converted_to_meal_at"]
        now = datetime.now(timezone.utc)
        assert (now - timestamp).total_seconds() < 2

    @pytest.mark.asyncio
    async def test_mark_converted_raises_error_when_not_found(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
    ) -> None:
        """Test mark_converted raises error for nonexistent analysis."""
        mock_result = MagicMock()
        mock_result.matched_count = 0
        mock_collection.update_one = AsyncMock(return_value=mock_result)

        analysis_id = AnalysisId(value="analysis_000000000000")
        meal_id = MealId(value="meal_789")

        with pytest.raises(ValueError, match="Analysis not found"):
            await repository.mark_converted(analysis_id, meal_id)

    @pytest.mark.asyncio
    async def test_delete_expired_removes_old_analyses(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
    ) -> None:
        """Test delete_expired removes analyses past expiration."""
        mock_result = MagicMock()
        mock_result.deleted_count = 5
        mock_collection.delete_many = AsyncMock(return_value=mock_result)

        count = await repository.delete_expired()

        assert count == 5

        # Verify delete query
        mock_collection.delete_many.assert_called_once()
        call_args = mock_collection.delete_many.call_args[0][0]

        assert "expires_at" in call_args
        assert "$lt" in call_args["expires_at"]

        # Verify timestamp is recent
        timestamp = call_args["expires_at"]["$lt"]
        now = datetime.now(timezone.utc)
        assert (now - timestamp).total_seconds() < 2

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_analysis_exists(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
    ) -> None:
        """Test exists returns True when analysis is found."""
        mock_collection.count_documents = AsyncMock(return_value=1)

        result = await repository.exists(AnalysisId(value="analysis_abc123def456"))

        assert result is True

        # Verify query
        mock_collection.count_documents.assert_called_once()
        call_args = mock_collection.count_documents.call_args
        assert call_args[0][0] == {"analysis_id": "analysis_abc123def456"}
        assert call_args[1]["limit"] == 1

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_not_found(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
    ) -> None:
        """Test exists returns False when analysis doesn't exist."""
        mock_collection.count_documents = AsyncMock(return_value=0)

        result = await repository.exists(AnalysisId(value="analysis_000000000000"))

        assert result is False

    @pytest.mark.asyncio
    async def test_roundtrip_preserves_all_data(
        self,
        repository: MealAnalysisRepositoryMongo,
        sample_analysis: MealAnalysis,
    ) -> None:
        """Test converting to document and back preserves all data."""
        doc = repository._to_document(sample_analysis)
        reconstructed = repository._from_document(doc)

        # All scalar fields
        assert reconstructed.analysis_id == sample_analysis.analysis_id
        assert reconstructed.user_id == sample_analysis.user_id
        assert reconstructed.meal_name == sample_analysis.meal_name
        assert reconstructed.quantity_g == sample_analysis.quantity_g
        assert reconstructed.status == sample_analysis.status
        assert reconstructed.created_at == sample_analysis.created_at
        assert reconstructed.expires_at == sample_analysis.expires_at
        assert reconstructed.converted_to_meal_at == sample_analysis.converted_to_meal_at

        # Nutrient profile
        assert reconstructed.nutrient_profile.calories == sample_analysis.nutrient_profile.calories
        assert reconstructed.nutrient_profile.protein == sample_analysis.nutrient_profile.protein

        # Metadata
        assert reconstructed.metadata.source == sample_analysis.metadata.source
        assert reconstructed.metadata.confidence == sample_analysis.metadata.confidence

    @pytest.mark.asyncio
    async def test_save_and_retrieve_integration(
        self,
        repository: MealAnalysisRepositoryMongo,
        mock_collection: AsyncMock,
        sample_analysis: MealAnalysis,
    ) -> None:
        """Test integration: save then retrieve returns same data."""
        # Mock save
        mock_collection.update_one = AsyncMock()

        await repository.save(sample_analysis)

        # Mock retrieve with same data
        saved_doc = repository._to_document(sample_analysis)
        mock_collection.find_one = AsyncMock(return_value=saved_doc)

        retrieved = await repository.get_by_id(sample_analysis.analysis_id)

        assert retrieved is not None
        assert retrieved.analysis_id == sample_analysis.analysis_id
        assert retrieved.meal_name == sample_analysis.meal_name
        assert retrieved.nutrient_profile.calories == sample_analysis.nutrient_profile.calories
