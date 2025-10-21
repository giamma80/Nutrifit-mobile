"""
MongoDB implementation of meal analysis repository.

Uses TTL index for automatic expiration cleanup.
"""

from datetime import datetime, timezone
from typing import Optional, Any

from motor.motor_asyncio import AsyncIOMotorDatabase

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
from backend.v2.domain.meal.nutrition.models import NutrientProfile


class MealAnalysisRepositoryMongo:
    """
    MongoDB implementation of meal analysis repository.

    Storage design:
    - Collection: meal_analyses
    - TTL index on expires_at (auto-cleanup)
    - Unique index on analysis_id (idempotency)
    - Index on user_id (user queries)
    - Index on created_at DESC (recent queries)

    Example:
        >>> from motor.motor_asyncio import AsyncIOMotorClient
        >>> client = AsyncIOMotorClient("mongodb://localhost:27017")
        >>> db = client.nutrifit
        >>> repository = MealAnalysisRepositoryMongo(db)
        >>> await repository.save(analysis)
    """

    COLLECTION_NAME = "meal_analyses"

    def __init__(self, db: AsyncIOMotorDatabase[Any]):
        """
        Initialize repository with MongoDB database.

        Creates indexes on first use.

        Args:
            db: Motor AsyncIOMotorDatabase instance
        """
        self.db = db
        self.collection = db[self.COLLECTION_NAME]
        self._indexes_created = False

    async def _ensure_indexes(self) -> None:
        """
        Create indexes if not already created.

        Indexes:
        - TTL index on expires_at (expireAfterSeconds=0)
        - Unique index on analysis_id
        - Index on user_id
        - Index on created_at DESC
        """
        if self._indexes_created:
            return

        # TTL index for automatic cleanup
        await self.collection.create_index(
            "expires_at",
            expireAfterSeconds=0,
            name="ttl_expires_at",
        )

        # Unique index for idempotency
        await self.collection.create_index(
            "analysis_id",
            unique=True,
            name="unique_analysis_id",
        )

        # Index for user queries
        await self.collection.create_index(
            "user_id",
            name="idx_user_id",
        )

        # Index for recent queries (DESC for newest first)
        await self.collection.create_index(
            [("user_id", 1), ("created_at", -1)],
            name="idx_user_recent",
        )

        self._indexes_created = True

    def _to_document(self, analysis: MealAnalysis) -> dict[str, Any]:
        """
        Convert MealAnalysis to MongoDB document.

        Args:
            analysis: MealAnalysis domain model

        Returns:
            MongoDB document dictionary
        """
        return {
            "analysis_id": analysis.analysis_id.value,
            "user_id": analysis.user_id.value,
            "meal_name": analysis.meal_name,
            "nutrient_profile": analysis.nutrient_profile.to_dict(),
            "quantity_g": analysis.quantity_g,
            "metadata": {
                "source": analysis.metadata.source,
                "confidence": analysis.metadata.confidence,
                "processing_time_ms": analysis.metadata.processing_time_ms,
                "ai_model_version": analysis.metadata.ai_model_version,
                "image_url": analysis.metadata.image_url,
                "barcode_value": analysis.metadata.barcode_value,
                "fallback_reason": analysis.metadata.fallback_reason,
            },
            "status": analysis.status,
            "created_at": analysis.created_at,
            "expires_at": analysis.expires_at,
            "converted_to_meal_at": analysis.converted_to_meal_at,
        }

    def _from_document(self, doc: dict[str, Any]) -> MealAnalysis:
        """
        Convert MongoDB document to MealAnalysis.

        Args:
            doc: MongoDB document

        Returns:
            MealAnalysis domain model
        """
        # Reconstruct nutrient profile
        profile_data = doc["nutrient_profile"]
        nutrient_profile = NutrientProfile(
            calories=profile_data["calories"],
            protein=profile_data["protein"],
            carbs=profile_data["carbs"],
            fat=profile_data["fat"],
            fiber=profile_data.get("fiber"),
            sugar=profile_data.get("sugar"),
            sodium=profile_data.get("sodium"),
            source=profile_data["source"],
            confidence=profile_data["confidence"],
            quantity_g=profile_data.get("quantity_g", 100.0),
        )

        # Reconstruct metadata
        meta_data = doc["metadata"]
        metadata = MealAnalysisMetadata(
            source=AnalysisSource(meta_data["source"]),
            confidence=meta_data["confidence"],
            processing_time_ms=meta_data["processing_time_ms"],
            ai_model_version=meta_data.get("ai_model_version"),
            image_url=meta_data.get("image_url"),
            barcode_value=meta_data.get("barcode_value"),
            fallback_reason=meta_data.get("fallback_reason"),
        )

        return MealAnalysis(
            analysis_id=AnalysisId(value=doc["analysis_id"]),
            user_id=UserId(value=doc["user_id"]),
            meal_name=doc["meal_name"],
            nutrient_profile=nutrient_profile,
            quantity_g=doc["quantity_g"],
            metadata=metadata,
            status=AnalysisStatus(doc["status"]),
            created_at=doc["created_at"],
            expires_at=doc["expires_at"],
            converted_to_meal_at=doc.get("converted_to_meal_at"),
        )

    async def save(self, analysis: MealAnalysis) -> None:
        """Save or update meal analysis (upsert)."""
        await self._ensure_indexes()

        doc = self._to_document(analysis)
        await self.collection.update_one(
            {"analysis_id": doc["analysis_id"]},
            {"$set": doc},
            upsert=True,
        )

    async def get_by_id(self, analysis_id: AnalysisId) -> Optional[MealAnalysis]:
        """Retrieve analysis by ID."""
        await self._ensure_indexes()

        doc = await self.collection.find_one({"analysis_id": analysis_id.value})
        if doc is None:
            return None

        return self._from_document(doc)

    async def get_by_user(
        self,
        user_id: UserId,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[MealAnalysis]:
        """Get recent analyses for user."""
        await self._ensure_indexes()

        query: dict[str, Any] = {"user_id": user_id.value}

        # Exclude expired unless requested
        if not include_expired:
            now = datetime.now(timezone.utc)
            query["expires_at"] = {"$gt": now}

        # Newest first
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)

        docs = await cursor.to_list(length=limit)
        return [self._from_document(doc) for doc in docs]

    async def mark_converted(
        self,
        analysis_id: AnalysisId,
        meal_id: MealId,
    ) -> None:
        """Mark analysis as converted to meal."""
        await self._ensure_indexes()

        now = datetime.now(timezone.utc)
        result = await self.collection.update_one(
            {"analysis_id": analysis_id.value},
            {"$set": {"converted_to_meal_at": now}},
        )

        if result.matched_count == 0:
            raise ValueError(f"Analysis not found: {analysis_id.value}")

    async def delete_expired(self) -> int:
        """Manually delete expired analyses."""
        await self._ensure_indexes()

        now = datetime.now(timezone.utc)
        result = await self.collection.delete_many({"expires_at": {"$lt": now}})

        return result.deleted_count

    async def exists(self, analysis_id: AnalysisId) -> bool:
        """Check if analysis exists."""
        await self._ensure_indexes()

        count = await self.collection.count_documents(
            {"analysis_id": analysis_id.value},
            limit=1,
        )

        return count > 0
