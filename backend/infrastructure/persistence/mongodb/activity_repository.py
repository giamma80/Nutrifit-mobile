"""MongoDB implementation of IActivityRepository.

Dual-collection architecture:
  - activity_events: minute-level ActivityEvent documents
  - health_snapshots: cumulative HealthSnapshot documents

Design decisions:
  * ActivityEvent: indexed by (user_id, ts), idempotency via unique compound key
  * HealthSnapshot: indexed by (user_id, date, timestamp), idempotency via unique key
  * ActivityDelta: computed on-the-fly from consecutive snapshots (no storage)
  * Batch operations: bulk_write with ordered=False for parallel execution
  * Deduplication: MongoDB unique indexes + error handling
"""

from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from datetime import datetime

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorCollection

from domain.activity.model import (
    ActivityEvent,
    HealthSnapshot,
    ActivityDelta,
    ActivitySource,
)
from domain.activity.repository import IActivityRepository
from infrastructure.persistence.mongodb.base import MongoBaseRepository


logger = logging.getLogger(__name__)


class MongoActivityRepository(
    MongoBaseRepository[ActivityEvent], IActivityRepository
):
    """MongoDB implementation for Activity domain with dual collections."""

    def __init__(
        self, client: Optional[AsyncIOMotorClient[Dict[str, Any]]] = None
    ):
        """Initialize repository with optional MongoDB client.

        Args:
            client: Optional motor client. If None, creates from MONGODB_URI.
        """
        super().__init__(client)
        self._snapshots_collection_name = "health_snapshots"
        logger.info(
            "MongoActivityRepository initialized with collections: "
            f"{self.collection_name}, {self._snapshots_collection_name}"
        )

    @property
    def collection_name(self) -> str:
        """Primary collection for ActivityEvent documents."""
        return "activity_events"

    @property
    def snapshots_collection(
        self,
    ) -> "AsyncIOMotorCollection[Dict[str, Any]]":
        """Access health_snapshots collection."""
        return self._db[self._snapshots_collection_name]

    # ========================================================================
    # Document Mapping - ActivityEvent
    # ========================================================================

    def to_document(self, entity: ActivityEvent) -> Dict[str, Any]:
        """Convert ActivityEvent to MongoDB document.

        Schema:
            {
                "_id": "user123_2024-01-15T10:30:00Z",
                "user_id": "user123",
                "ts": "2024-01-15T10:30:00Z",
                "steps": 120,
                "calories_out": 5.4,
                "hr_avg": 85.0,
                "source": "APPLE_HEALTH"
            }
        """
        # Unique _id = user_id + ts (ensures deduplication)
        doc_id = f"{entity.user_id}_{entity.ts}"

        doc: Dict[str, Any] = {
            "_id": doc_id,
            "user_id": entity.user_id,
            "ts": entity.ts,
            "source": entity.source.value,
        }

        # Optional fields
        if entity.steps is not None:
            doc["steps"] = entity.steps
        if entity.calories_out is not None:
            doc["calories_out"] = entity.calories_out
        if entity.hr_avg is not None:
            doc["hr_avg"] = entity.hr_avg

        return doc

    def from_document(self, doc: Dict[str, Any]) -> ActivityEvent:
        """Convert MongoDB document to ActivityEvent.

        Args:
            doc: MongoDB document with ActivityEvent data

        Returns:
            ActivityEvent domain object
        """
        return ActivityEvent(
            user_id=doc["user_id"],
            ts=doc["ts"],
            steps=doc.get("steps"),
            calories_out=doc.get("calories_out"),
            hr_avg=doc.get("hr_avg"),
            source=ActivitySource(doc.get("source", "MANUAL")),
        )

    # ========================================================================
    # Document Mapping - HealthSnapshot
    # ========================================================================

    def snapshot_to_document(self, snapshot: HealthSnapshot) -> Dict[str, Any]:
        """Convert HealthSnapshot to MongoDB document.

        Schema:
            {
                "_id": "user123_2024-01-15_2024-01-15T23:59:00Z",
                "user_id": "user123",
                "date": "2024-01-15",
                "timestamp": "2024-01-15T23:59:00Z",
                "steps_total": 10000,
                "calories_out_total": 450.0,
                "hr_avg_session": 75.0
            }
        """
        # Unique _id = user_id + date + timestamp
        doc_id = f"{snapshot.user_id}_{snapshot.date}_{snapshot.timestamp}"

        doc: Dict[str, Any] = {
            "_id": doc_id,
            "user_id": snapshot.user_id,
            "date": snapshot.date,
            "timestamp": snapshot.timestamp,
            "steps_total": snapshot.steps_total,
            "calories_out_total": snapshot.calories_out_total,
        }

        if snapshot.hr_avg_session is not None:
            doc["hr_avg_session"] = snapshot.hr_avg_session

        return doc

    def document_to_snapshot(self, doc: Dict[str, Any]) -> HealthSnapshot:
        """Convert MongoDB document to HealthSnapshot.

        Args:
            doc: MongoDB document with HealthSnapshot data

        Returns:
            HealthSnapshot domain object
        """
        return HealthSnapshot(
            user_id=doc["user_id"],
            date=doc["date"],
            timestamp=doc["timestamp"],
            steps_total=doc["steps_total"],
            calories_out_total=doc["calories_out_total"],
            hr_avg_session=doc.get("hr_avg_session"),
        )

    # ========================================================================
    # ActivityEvent Operations
    # ========================================================================

    async def ingest_events(
        self, events: List[ActivityEvent], idempotency_key: Optional[str] = None
    ) -> Tuple[int, int, List[Tuple[int, str]]]:
        """Batch ingest activity events with deduplication.

        Args:
            events: List of ActivityEvent objects to ingest
            idempotency_key: Optional key for request deduplication (currently unused,
                            deduplication handled by unique _id)

        Returns:
            Tuple of (accepted_count, duplicate_count, rejected_list)
            where rejected_list contains (index, reason) tuples

        Implementation:
            Uses MongoDB bulk_write with ordered=False for parallel execution.
            Duplicate key errors (E11000) are caught and counted.
            Other errors are logged and added to rejected list.
        """
        if not events:
            return (0, 0, [])

        # Normalize events to minute precision
        normalized_events = [e.normalized() for e in events]

        # Prepare bulk insert operations
        from pymongo import InsertOne
        from pymongo.errors import BulkWriteError

        operations = [
            InsertOne(self.to_document(event)) for event in normalized_events
        ]

        accepted = 0
        duplicates = 0
        rejected: List[Tuple[int, str]] = []

        try:
            result = await self.collection.bulk_write(
                operations, ordered=False
            )
            accepted = result.inserted_count
            logger.info(f"Ingested {accepted}/{len(events)} activity events")

        except BulkWriteError as bwe:
            # Parse bulk write errors
            accepted = bwe.details.get("nInserted", 0)
            write_errors = bwe.details.get("writeErrors", [])

            for error in write_errors:
                index = error.get("index", -1)
                code = error.get("code", 0)
                msg = error.get("errmsg", "Unknown error")

                if code == 11000:  # Duplicate key error
                    duplicates += 1
                else:
                    rejected.append((index, msg))
                    logger.warning(
                        f"Event {index} rejected: {msg[:100]}"
                    )

            logger.info(
                f"Batch ingest: {accepted} accepted, {duplicates} duplicates, "
                f"{len(rejected)} rejected"
            )

        except Exception as e:
            logger.error(f"Unexpected error during batch ingest: {e}")
            # Mark all as rejected on catastrophic failure
            rejected = [(i, str(e)) for i in range(len(events))]

        return (accepted, duplicates, rejected)

    async def list_events(
        self,
        user_id: str,
        start_ts: Optional[str] = None,
        end_ts: Optional[str] = None,
        limit: int = 1000,
    ) -> List[ActivityEvent]:
        """List activity events with optional timestamp filtering.

        Args:
            user_id: User identifier
            start_ts: Optional start timestamp (ISO8601, inclusive)
            end_ts: Optional end timestamp (ISO8601, exclusive)
            limit: Maximum number of events to return

        Returns:
            List of ActivityEvent objects sorted by timestamp ascending
        """
        query: Dict[str, Any] = {"user_id": user_id}

        # Build timestamp range filter
        if start_ts or end_ts:
            ts_filter: Dict[str, Any] = {}
            if start_ts:
                ts_filter["$gte"] = start_ts
            if end_ts:
                ts_filter["$lt"] = end_ts
            query["ts"] = ts_filter

        docs = await self._find_many(
            query, sort=[("ts", 1)], limit=limit
        )

        events = [self.from_document(doc) for doc in docs]
        logger.debug(
            f"Listed {len(events)} events for user {user_id} "
            f"(range: {start_ts} to {end_ts})"
        )
        return events

    async def get_daily_events_count(
        self, user_id: str, date: str
    ) -> int:
        """Count activity events for a specific date.

        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format

        Returns:
            Number of events for the specified date
        """
        # Build timestamp range for the date
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            start_ts = f"{date}T00:00:00Z"
            end_ts = (
                datetime.combine(
                    date_obj,
                    datetime.min.time()
                ).replace(hour=23, minute=59, second=59)
                .isoformat()
                .replace("+00:00", "Z")
            )

            query = {
                "user_id": user_id,
                "ts": {"$gte": start_ts, "$lte": end_ts},
            }

            count = await self._count(query)
            logger.debug(
                f"Counted {count} events for user {user_id} on {date}"
            )
            return count

        except ValueError as e:
            logger.error(f"Invalid date format {date}: {e}")
            return 0

    # ========================================================================
    # HealthSnapshot Operations
    # ========================================================================

    async def record_snapshot(
        self, snapshot: HealthSnapshot, idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record health snapshot and compute delta from previous snapshot.

        Args:
            snapshot: HealthSnapshot to record
            idempotency_key: Optional key for request deduplication

        Returns:
            Dict with keys:
                - status: "new" | "duplicate"
                - delta: ActivityDelta object (if new)
                - snapshot: HealthSnapshot object (echo back)

        Logic:
            1. Attempt to insert snapshot (duplicate check via unique _id)
            2. If new, fetch previous snapshot for delta calculation
            3. Calculate delta with reset/duplicate detection
            4. Return result dict
        """
        from pymongo.errors import DuplicateKeyError

        doc = self.snapshot_to_document(snapshot)

        try:
            # Attempt insert
            await self.snapshots_collection.insert_one(doc)

            # Fetch previous snapshot for delta calculation
            previous = await self._get_previous_snapshot(
                snapshot.user_id, snapshot.date, snapshot.timestamp
            )

            delta = self._calculate_delta(snapshot, previous)

            logger.info(
                f"Recorded new snapshot for user {snapshot.user_id} "
                f"on {snapshot.date} (delta: {delta.steps_delta} steps)"
            )

            return {
                "status": "new",
                "delta": delta,
                "snapshot": snapshot,
            }

        except DuplicateKeyError:
            logger.info(
                f"Duplicate snapshot for user {snapshot.user_id} "
                f"on {snapshot.date} at {snapshot.timestamp}"
            )
            return {
                "status": "duplicate",
                "snapshot": snapshot,
            }

    async def _get_previous_snapshot(
        self, user_id: str, date_str: str, timestamp: str
    ) -> Optional[HealthSnapshot]:
        """Fetch the most recent snapshot before given timestamp.

        Args:
            user_id: User identifier
            date_str: Date in YYYY-MM-DD format
            timestamp: Current snapshot timestamp (ISO8601)

        Returns:
            Previous HealthSnapshot or None if this is the first
        """
        query = {
            "user_id": user_id,
            "date": date_str,
            "timestamp": {"$lt": timestamp},
        }

        doc = await self.snapshots_collection.find_one(
            query, sort=[("timestamp", -1)]
        )

        if doc:
            return self.document_to_snapshot(doc)
        return None

    def _calculate_delta(
        self,
        current: HealthSnapshot,
        previous: Optional[HealthSnapshot],
    ) -> ActivityDelta:
        """Calculate delta between current and previous snapshots.

        Args:
            current: Current HealthSnapshot
            previous: Previous HealthSnapshot or None

        Returns:
            ActivityDelta with reset/duplicate flags set

        Logic:
            - If no previous: delta = current totals (bootstrap case)
            - If totals decreased: reset=True, delta = current totals
            - If totals unchanged: duplicate=True, delta = 0
            - Otherwise: delta = current - previous
        """
        if previous is None:
            # Bootstrap case: first snapshot of the day
            return ActivityDelta(
                user_id=current.user_id,
                date=current.date,
                timestamp=current.timestamp,
                steps_delta=current.steps_total,
                calories_out_delta=current.calories_out_total,
                steps_total=current.steps_total,
                calories_out_total=current.calories_out_total,
                hr_avg_session=current.hr_avg_session,
                reset=False,
                duplicate=False,
            )

        # Check for reset (totals decreased)
        reset = (
            current.steps_total < previous.steps_total
            or current.calories_out_total < previous.calories_out_total
        )

        if reset:
            # Device reset: treat current as new baseline
            return ActivityDelta(
                user_id=current.user_id,
                date=current.date,
                timestamp=current.timestamp,
                steps_delta=current.steps_total,
                calories_out_delta=current.calories_out_total,
                steps_total=current.steps_total,
                calories_out_total=current.calories_out_total,
                hr_avg_session=current.hr_avg_session,
                reset=True,
                duplicate=False,
            )

        # Calculate deltas
        steps_delta = current.steps_total - previous.steps_total
        calories_delta = (
            current.calories_out_total - previous.calories_out_total
        )

        # Check for duplicate (no change)
        duplicate = steps_delta == 0 and calories_delta == 0.0

        return ActivityDelta(
            user_id=current.user_id,
            date=current.date,
            timestamp=current.timestamp,
            steps_delta=steps_delta,
            calories_out_delta=calories_delta,
            steps_total=current.steps_total,
            calories_out_total=current.calories_out_total,
            hr_avg_session=current.hr_avg_session,
            reset=reset,
            duplicate=duplicate,
        )

    async def list_deltas(
        self,
        user_id: str,
        date: str,
        after_ts: Optional[str] = None,
        limit: int = 100,
    ) -> List[ActivityDelta]:
        """List activity deltas for a specific date.

        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format
            after_ts: Optional timestamp to filter deltas after (exclusive)
            limit: Maximum number of deltas to return

        Returns:
            List of ActivityDelta objects computed from consecutive snapshots

        Implementation:
            Fetches snapshots in chronological order and computes deltas
            by comparing each snapshot with its predecessor.
        """
        query: Dict[str, Any] = {
            "user_id": user_id,
            "date": date,
        }

        if after_ts:
            query["timestamp"] = {"$gt": after_ts}

        # Fetch snapshots sorted by timestamp
        cursor = (
            self.snapshots_collection.find(query)
            .sort("timestamp", 1)
            .limit(limit + 1)
        )
        docs = await cursor.to_list(length=limit + 1)

        if not docs:
            return []

        snapshots = [self.document_to_snapshot(doc) for doc in docs]

        # Compute deltas between consecutive snapshots
        deltas: List[ActivityDelta] = []
        for i, current in enumerate(snapshots):
            previous = snapshots[i - 1] if i > 0 else None
            delta = self._calculate_delta(current, previous)
            deltas.append(delta)

        logger.debug(
            f"Computed {len(deltas)} deltas for user {user_id} on {date}"
        )
        return deltas[:limit]  # Respect limit

    async def get_daily_totals(
        self, user_id: str, date: str
    ) -> Tuple[int, float]:
        """Get daily totals (steps, calories) from latest snapshot.

        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format

        Returns:
            Tuple of (total_steps, total_calories_out)

        Implementation:
            Returns the latest snapshot's cumulative totals for the day.
            If no snapshots exist, returns (0, 0.0).
        """
        query = {
            "user_id": user_id,
            "date": date,
        }

        # Get most recent snapshot
        doc = await self.snapshots_collection.find_one(
            query, sort=[("timestamp", -1)]
        )

        if doc:
            snapshot = self.document_to_snapshot(doc)
            logger.debug(
                f"Daily totals for user {user_id} on {date}: "
                f"{snapshot.steps_total} steps, "
                f"{snapshot.calories_out_total:.1f} cal"
            )
            return (snapshot.steps_total, snapshot.calories_out_total)

        logger.debug(
            f"No snapshots found for user {user_id} on {date}"
        )
        return (0, 0.0)


__all__ = ["MongoActivityRepository"]
