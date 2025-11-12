"""MongoDB implementation of meal repository.

Provides persistent storage for Meal aggregates using MongoDB Atlas.
Uses MongoBaseRepository for common patterns.
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
from uuid import UUID

from infrastructure.persistence.mongodb.base import MongoBaseRepository
from domain.meal.core.entities.meal import Meal
from domain.meal.core.entities.meal_entry import MealEntry


class MongoMealRepository(MongoBaseRepository[Meal]):
    """
    MongoDB implementation of meal repository.

    Storage Strategy:
    - Each Meal is a single MongoDB document
    - MealEntry objects are embedded as array of subdocuments
    - UUID fields stored as strings
    - Datetime fields stored as ISO 8601 strings (timezone-aware)

    Document Schema:
    {
        "_id": "uuid-string",           # Meal ID
        "user_id": "string",
        "timestamp": "2025-11-12T10:00:00Z",
        "meal_type": "LUNCH",
        "dish_name": "Pasta",
        "image_url": "https://...",
        "source": "gpt4v_v2",
        "confidence": 0.95,
        "entries": [
            {
                "id": "uuid-string",
                "meal_id": "uuid-string",
                "food_item": "Pasta al pomodoro",
                "quantity_g": 150.0,
                "calories": 200,
                "protein": 8.0,
                ...
            }
        ],
        "total_calories": 200,
        "total_protein": 8.0,
        ...
        "analysis_id": "optional-string",
        "notes": "optional-string",
        "created_at": "2025-11-12T10:00:00Z",
        "updated_at": "2025-11-12T10:00:00Z"
    }

    Indexes:
    - (user_id, timestamp): For user meal list queries
    - _id: Unique index (automatic)
    """

    @property
    def collection_name(self) -> str:
        """MongoDB collection name."""
        return "meals"

    # ============================================================
    # Document Mapping (Domain ↔ MongoDB)
    # ============================================================

    def to_document(self, entity: Meal) -> Dict[str, Any]:
        """
        Convert Meal entity to MongoDB document.

        Args:
            entity: Meal domain entity

        Returns:
            MongoDB document dict
        """
        meal = entity
        return {
            "_id": self.uuid_to_str(meal.id),
            "user_id": meal.user_id,
            "timestamp": self.datetime_to_iso(meal.timestamp),
            "meal_type": meal.meal_type,
            "dish_name": meal.dish_name,
            "image_url": meal.image_url,
            "source": meal.source,
            "confidence": meal.confidence,
            "entries": [self._entry_to_dict(entry) for entry in meal.entries],
            "total_calories": meal.total_calories,
            "total_protein": meal.total_protein,
            "total_carbs": meal.total_carbs,
            "total_fat": meal.total_fat,
            "total_fiber": meal.total_fiber,
            "total_sugar": meal.total_sugar,
            "total_sodium": meal.total_sodium,
            "analysis_id": meal.analysis_id,
            "notes": meal.notes,
            "created_at": self.datetime_to_iso(meal.created_at),
            "updated_at": self.datetime_to_iso(meal.updated_at),
        }

    def from_document(self, doc: Dict[str, Any]) -> Meal:
        """
        Convert MongoDB document to Meal entity.

        Args:
            doc: MongoDB document

        Returns:
            Meal domain entity

        Raises:
            ValueError: If document is invalid or missing required fields
        """
        try:
            entries = [
                self._dict_to_entry(entry_dict)
                for entry_dict in doc.get("entries", [])
            ]

            meal = Meal(
                id=self.str_to_uuid(doc["_id"]),
                user_id=doc["user_id"],
                timestamp=self.iso_to_datetime(doc["timestamp"]),
                meal_type=doc["meal_type"],
                dish_name=doc.get("dish_name", "Meal"),
                image_url=doc.get("image_url"),
                source=doc.get("source", "manual"),
                confidence=doc.get("confidence", 1.0),
                entries=entries,
                total_calories=doc.get("total_calories", 0),
                total_protein=doc.get("total_protein", 0.0),
                total_carbs=doc.get("total_carbs", 0.0),
                total_fat=doc.get("total_fat", 0.0),
                total_fiber=doc.get("total_fiber", 0.0),
                total_sugar=doc.get("total_sugar", 0.0),
                total_sodium=doc.get("total_sodium", 0.0),
                analysis_id=doc.get("analysis_id"),
                notes=doc.get("notes"),
                created_at=self.iso_to_datetime(doc["created_at"]),
                updated_at=self.iso_to_datetime(doc["updated_at"]),
            )

            return meal

        except KeyError as e:
            msg = f"Missing required field in MongoDB document: {e}"
            raise ValueError(msg)
        except Exception as e:
            raise ValueError(f"Error converting MongoDB document to Meal: {e}")

    def _entry_to_dict(self, entry: MealEntry) -> Dict[str, Any]:
        """Convert MealEntry to dict for MongoDB storage."""
        return {
            "id": self.uuid_to_str(entry.id),
            "meal_id": self.uuid_to_str(entry.meal_id),
            "name": entry.name,
            "display_name": entry.display_name,
            "quantity_g": entry.quantity_g,
            "calories": entry.calories,
            "protein": entry.protein,
            "carbs": entry.carbs,
            "fat": entry.fat,
            "fiber": entry.fiber,
            "sugar": entry.sugar,
            "sodium": entry.sodium,
            "source": entry.source,
            "confidence": entry.confidence,
            "category": entry.category,
            "barcode": entry.barcode,
            "image_url": entry.image_url,
            "created_at": self.datetime_to_iso(entry.created_at),
        }

    def _dict_to_entry(self, entry_dict: Dict[str, Any]) -> MealEntry:
        """Convert dict to MealEntry entity."""
        return MealEntry(
            id=self.str_to_uuid(entry_dict["id"]),
            meal_id=self.str_to_uuid(entry_dict["meal_id"]),
            name=entry_dict["name"],
            display_name=entry_dict["display_name"],
            quantity_g=entry_dict["quantity_g"],
            calories=entry_dict["calories"],
            protein=entry_dict["protein"],
            carbs=entry_dict["carbs"],
            fat=entry_dict["fat"],
            fiber=entry_dict.get("fiber"),
            sugar=entry_dict.get("sugar"),
            sodium=entry_dict.get("sodium"),
            source=entry_dict.get("source", "MANUAL"),
            confidence=entry_dict.get("confidence", 1.0),
            category=entry_dict.get("category"),
            barcode=entry_dict.get("barcode"),
            image_url=entry_dict.get("image_url"),
            created_at=self.iso_to_datetime(entry_dict["created_at"]),
        )

    # ============================================================
    # Repository Operations (IMealRepository interface)
    # ============================================================

    async def save(self, meal: Meal) -> None:
        """
        Save or update a meal in MongoDB.

        Args:
            meal: Meal entity to save

        Note:
            - Uses upsert to handle both insert and update
            - Updates meal.updated_at to current UTC time
        """
        from datetime import timezone

        meal.updated_at = datetime.now(timezone.utc)

        document = self.to_document(meal)
        filter_dict = {"_id": document["_id"]}
        update_dict = {"$set": document}

        await self._update_one(filter_dict, update_dict, upsert=True)

    async def get_by_id(self, meal_id: UUID, user_id: str) -> Optional[Meal]:
        """
        Retrieve meal by ID for a specific user.

        Args:
            meal_id: Unique meal identifier
            user_id: User identifier (for authorization)

        Returns:
            Meal if found and belongs to user, None otherwise
        """
        filter_dict = {"_id": self.uuid_to_str(meal_id), "user_id": user_id}

        doc = await self._find_one(filter_dict)
        if doc is None:
            return None

        return self.from_document(doc)

    async def get_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Meal]:
        """
        Get meals for a user with pagination.

        Args:
            user_id: User identifier
            limit: Maximum number of meals to return
            offset: Number of meals to skip

        Returns:
            List of meals ordered by timestamp descending (newest first)
        """
        filter_dict = {"user_id": user_id}
        sort = [("timestamp", -1)]  # Descending (newest first)

        docs = await self._find_many(
            filter_dict, sort=sort, limit=limit, skip=offset
        )

        return [self.from_document(doc) for doc in docs]

    async def get_by_user_and_date_range(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Meal]:
        """
        Get meals for a user within a date range.

        Args:
            user_id: User identifier
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of meals ordered by timestamp ascending (oldest first)
        """
        # Convert to ISO strings for MongoDB comparison
        start_iso = self.datetime_to_iso(start_date)
        end_iso = self.datetime_to_iso(end_date)

        filter_dict = {
            "user_id": user_id,
            "timestamp": {"$gte": start_iso, "$lte": end_iso},
        }
        sort = [("timestamp", 1)]  # Ascending (oldest first)

        docs = await self._find_many(filter_dict, sort=sort)

        return [self.from_document(doc) for doc in docs]

    async def delete(self, meal_id: UUID, user_id: str) -> bool:
        """
        Delete a meal from MongoDB.

        Args:
            meal_id: Unique meal identifier
            user_id: User identifier (for authorization)

        Returns:
            True if meal was deleted, False if not found or unauthorized
        """
        filter_dict = {"_id": self.uuid_to_str(meal_id), "user_id": user_id}

        deleted_count = await self._delete_one(filter_dict)
        return deleted_count > 0

    async def exists(self, meal_id: UUID, user_id: str) -> bool:
        """
        Check if a meal exists for a user.

        Args:
            meal_id: Unique meal identifier
            user_id: User identifier (for authorization)

        Returns:
            True if meal exists and belongs to user, False otherwise
        """
        filter_dict = {"_id": self.uuid_to_str(meal_id), "user_id": user_id}

        doc = await self._find_one(filter_dict, projection={"_id": 1})
        return doc is not None

    async def count_by_user(self, user_id: str) -> int:
        """
        Count total meals for a user.

        Args:
            user_id: User identifier

        Returns:
            Total number of meals for user
        """
        filter_dict = {"user_id": user_id}
        return await self._count(filter_dict)
