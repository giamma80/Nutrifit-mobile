"""Base MongoDB repository with reusable patterns.

Provides common functionality for all MongoDB repositories:
- Connection management
- Document mapping (domain ↔ MongoDB)
- Error handling
- Retry logic
- Logging

All concrete MongoDB repositories should inherit from MongoBaseRepository.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Dict, Any, List, Tuple
from uuid import UUID
from datetime import datetime
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from infrastructure.config import get_mongodb_uri, get_mongodb_database


# Type variables for generics
TEntity = TypeVar("TEntity")  # Domain entity type
TDocument = TypeVar("TDocument", bound=Dict[str, Any])  # MongoDB document type

logger = logging.getLogger(__name__)


class MongoBaseRepository(ABC, Generic[TEntity]):
    """
    Abstract base class for MongoDB repositories.

    Provides common functionality:
    - Connection pooling (motor handles this automatically)
    - Document ↔ Entity mapping
    - Error handling with proper logging
    - UUID ↔ string conversion
    - Datetime handling (timezone-aware)

    Subclasses must implement:
    - collection_name: Name of MongoDB collection
    - to_document(): Convert domain entity to MongoDB document
    - from_document(): Convert MongoDB document to domain entity

    Example:
        class MongoMealRepository(MongoBaseRepository[Meal]):
            @property
            def collection_name(self) -> str:
                return "meals"

            def to_document(self, meal: Meal) -> Dict[str, Any]:
                # Convert Meal to MongoDB document
                ...

            def from_document(self, doc: Dict[str, Any]) -> Meal:
                # Convert MongoDB document to Meal
                ...
    """

    def __init__(self, client: Optional[AsyncIOMotorClient[Dict[str, Any]]] = None):
        """
        Initialize repository with optional client.

        Args:
            client: Motor client (if None, creates new one from config)
        """
        if client is None:
            uri = get_mongodb_uri()
            if not uri:
                raise ValueError(
                    "MONGODB_URI not configured. "
                    "Set MONGODB_URI, MONGODB_USER, "
                    "and MONGODB_PASSWORD environment variables."
                )
            self._client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(uri)
        else:
            self._client = client

        database_name = get_mongodb_database()
        self._db = self._client[database_name]
        self._collection = self._db[self.collection_name]

        logger.info(
            f"Initialized {self.__class__.__name__} " f"for collection '{self.collection_name}'"
        )

    # ============================================================
    # Abstract Properties/Methods (must be implemented)
    # ============================================================

    @property
    @abstractmethod
    def collection_name(self) -> str:
        """MongoDB collection name."""
        pass

    @abstractmethod
    def to_document(self, entity: TEntity) -> Dict[str, Any]:
        """
        Convert domain entity to MongoDB document.

        Args:
            entity: Domain entity

        Returns:
            MongoDB document (dict)
        """
        pass

    @abstractmethod
    def from_document(self, doc: Dict[str, Any]) -> TEntity:
        """
        Convert MongoDB document to domain entity.

        Args:
            doc: MongoDB document

        Returns:
            Domain entity

        Raises:
            ValueError: If document is invalid or missing required fields
        """
        pass

    # ============================================================
    # Protected Utility Methods (for subclasses)
    # ============================================================

    @property
    def collection(self) -> AsyncIOMotorCollection[Dict[str, Any]]:
        """Get MongoDB collection handle."""
        return self._collection

    @staticmethod
    def uuid_to_str(uuid_value: UUID) -> str:
        """Convert UUID to string for MongoDB storage."""
        return str(uuid_value)

    @staticmethod
    def str_to_uuid(str_value: str) -> UUID:
        """Convert string to UUID from MongoDB document."""
        return UUID(str_value)

    @staticmethod
    def datetime_to_iso(dt: datetime) -> str:
        """
        Convert datetime to ISO string for MongoDB storage.

        Args:
            dt: Timezone-aware datetime

        Returns:
            ISO 8601 string in UTC
        """
        if dt.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return dt.isoformat()

    @staticmethod
    def iso_to_datetime(iso_str: str) -> datetime:
        """
        Convert ISO string to timezone-aware datetime.

        Args:
            iso_str: ISO 8601 string

        Returns:
            Timezone-aware datetime
        """
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            # If no timezone, assume UTC
            from datetime import timezone

            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    async def _find_one(
        self,
        filter_dict: Dict[str, Any],
        projection: Optional[Dict[str, int]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find single document with error handling.

        Args:
            filter_dict: MongoDB filter
            projection: Optional projection

        Returns:
            Document dict or None if not found

        Raises:
            Exception: If MongoDB operation fails (logged and re-raised)
        """
        try:
            doc = await self._collection.find_one(filter_dict, projection)
            return doc
        except Exception as e:
            logger.error(
                f"Error in find_one: collection={self.collection_name}, "
                f"filter={filter_dict}, error={e}"
            )
            raise

    async def _find_many(
        self,
        filter_dict: Dict[str, Any],
        sort: Optional[List[Tuple[str, int]]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        projection: Optional[Dict[str, int]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents with error handling.

        Args:
            filter_dict: MongoDB filter
            sort: Sort specification [(field, direction), ...]
            limit: Max documents to return
            skip: Documents to skip
            projection: Optional projection

        Returns:
            List of document dicts

        Raises:
            Exception: If MongoDB operation fails (logged and re-raised)
        """
        try:
            cursor = self._collection.find(filter_dict, projection)

            if sort:
                cursor = cursor.sort(sort)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)

            documents = await cursor.to_list(length=limit)
            return documents
        except Exception as e:
            logger.error(
                f"Error in find_many: collection={self.collection_name}, "
                f"filter={filter_dict}, error={e}"
            )
            raise

    async def _insert_one(self, document: Dict[str, Any]) -> None:
        """
        Insert single document with error handling.

        Args:
            document: MongoDB document to insert

        Raises:
            Exception: If MongoDB operation fails (logged and re-raised)
        """
        try:
            await self._collection.insert_one(document)
        except Exception as e:
            logger.error(f"Error in insert_one: collection={self.collection_name}, " f"error={e}")
            raise

    async def _update_one(
        self,
        filter_dict: Dict[str, Any],
        update_dict: Dict[str, Any],
        upsert: bool = False,
    ) -> int:
        """
        Update single document with error handling.

        Args:
            filter_dict: MongoDB filter
            update_dict: Update operations (e.g., {"$set": {...}})
            upsert: Create document if not found

        Returns:
            Number of documents modified (0 or 1)

        Raises:
            Exception: If MongoDB operation fails (logged and re-raised)
        """
        try:
            result = await self._collection.update_one(filter_dict, update_dict, upsert=upsert)
            return result.modified_count
        except Exception as e:
            logger.error(
                f"Error in update_one: collection={self.collection_name}, "
                f"filter={filter_dict}, error={e}"
            )
            raise

    async def _delete_one(self, filter_dict: Dict[str, Any]) -> int:
        """
        Delete single document with error handling.

        Args:
            filter_dict: MongoDB filter

        Returns:
            Number of documents deleted (0 or 1)

        Raises:
            Exception: If MongoDB operation fails (logged and re-raised)
        """
        try:
            result = await self._collection.delete_one(filter_dict)
            return result.deleted_count
        except Exception as e:
            logger.error(
                f"Error in delete_one: collection={self.collection_name}, "
                f"filter={filter_dict}, error={e}"
            )
            raise

    async def _count(self, filter_dict: Dict[str, Any]) -> int:
        """
        Count documents with error handling.

        Args:
            filter_dict: MongoDB filter

        Returns:
            Number of matching documents

        Raises:
            Exception: If MongoDB operation fails (logged and re-raised)
        """
        try:
            count = await self._collection.count_documents(filter_dict)
            return count
        except Exception as e:
            logger.error(
                f"Error in count: collection={self.collection_name}, "
                f"filter={filter_dict}, error={e}"
            )
            raise

    async def close(self) -> None:
        """Close MongoDB connection."""
        self._client.close()
        logger.info(f"Closed connection for {self.__class__.__name__}")
