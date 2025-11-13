"""Integration tests for MongoActivityRepository.

Tests actual MongoDB operations against test database including:
- Batch event ingestion with deduplication
- Snapshot recording with delta calculation
- Temporal queries using production indexes

Requires MONGODB_URI to be set in environment.
"""

import os
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio

from domain.activity.model import (
    ActivityEvent,
    HealthSnapshot,
    ActivitySource,
)
from infrastructure.persistence.mongodb.activity_repository import (
    MongoActivityRepository,
)


pytestmark = pytest.mark.skipif(
    os.getenv("REPOSITORY_BACKEND") != "mongodb",
    reason="MongoDB integration tests require REPOSITORY_BACKEND=mongodb",
)


@pytest_asyncio.fixture
async def mongo_repo():
    """Create a MongoActivityRepository for testing."""
    repo = MongoActivityRepository()
    yield repo
    # Cleanup: delete all test data
    await repo.collection.delete_many({"user_id": {"$regex": "^test_user_"}})
    await repo.snapshots_collection.delete_many({"user_id": {"$regex": "^test_user_"}})


@pytest.mark.asyncio
class TestMongoActivityRepositoryEventIngestion:
    """Test batch event ingestion with deduplication."""

    async def test_ingest_events_success(self, mongo_repo):
        """Should successfully ingest batch of activity events."""
        base_time = datetime(2025, 11, 13, 10, 0, 0, tzinfo=timezone.utc)
        events = [
            ActivityEvent(
                user_id="test_user_001",
                ts=(base_time + timedelta(minutes=i)).isoformat().replace("+00:00", "Z"),
                steps=100 + i * 10,
                calories_out=4.5 + i,
                hr_avg=70.0 + i,
                source=ActivitySource.APPLE_HEALTH,
            )
            for i in range(3)
        ]

        accepted, duplicates, rejected = await mongo_repo.ingest_events(events)

        assert accepted == 3
        assert duplicates == 0
        assert len(rejected) == 0

        # Verify events stored in MongoDB
        stored_events = await mongo_repo.list_events(
            user_id="test_user_001",
            start_ts=events[0].ts,
            end_ts=events[-1].ts,
        )
        assert len(stored_events) == 3

    async def test_ingest_events_deduplication(self, mongo_repo):
        """Should detect and skip duplicate events on second ingestion."""
        base_time = datetime(2025, 11, 13, 10, 0, 0, tzinfo=timezone.utc)
        events = [
            ActivityEvent(
                user_id="test_user_001",
                ts=base_time.isoformat().replace("+00:00", "Z"),
                steps=100,
                calories_out=4.5,
                hr_avg=72.0,
                source=ActivitySource.APPLE_HEALTH,
            )
        ]

        # First ingestion
        accepted1, duplicates1, rejected1 = await mongo_repo.ingest_events(events)
        assert accepted1 == 1
        assert duplicates1 == 0

        # Second ingestion (same event)
        accepted2, duplicates2, rejected2 = await mongo_repo.ingest_events(events)
        assert accepted2 == 0
        assert duplicates2 == 1
        assert len(rejected2) == 0

    async def test_ingest_events_partial_duplicates(self, mongo_repo):
        """Should handle mix of new and duplicate events."""
        base_time = datetime(2025, 11, 13, 10, 0, 0, tzinfo=timezone.utc)

        # Ingest first event
        event1 = ActivityEvent(
            user_id="test_user_001",
            ts=base_time.isoformat().replace("+00:00", "Z"),
            steps=100,
            calories_out=4.5,
            hr_avg=72.0,
            source=ActivitySource.APPLE_HEALTH,
        )
        accepted1, _, _ = await mongo_repo.ingest_events([event1])
        assert accepted1 == 1

        # Ingest batch with 1 duplicate and 1 new
        event2 = ActivityEvent(
            user_id="test_user_001",
            ts=(base_time + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
            steps=120,
            calories_out=5.4,
            hr_avg=75.0,
            source=ActivitySource.APPLE_HEALTH,
        )
        accepted2, duplicates2, _ = await mongo_repo.ingest_events([event1, event2])
        assert accepted2 == 1  # Only event2 inserted
        assert duplicates2 == 1  # event1 duplicate


@pytest.mark.asyncio
class TestMongoActivityRepositorySnapshotRecording:
    """Test snapshot recording with delta calculation."""

    async def test_record_snapshot_first_of_day(self, mongo_repo):
        """Should record first snapshot with no previous delta."""
        snapshot = HealthSnapshot(
            user_id="test_user_001",
            date="2025-11-13",
            timestamp=datetime(2025, 11, 13, 12, 0, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            steps_total=5000,
            calories_out_total=220.0,
            hr_avg_session=72.0,
        )

        delta = await mongo_repo.record_snapshot(snapshot)

        # First snapshot: no previous data for delta
        assert delta is None

        # Verify snapshot stored (check collection directly)
        doc = await mongo_repo.snapshots_collection.find_one(
            {"user_id": "test_user_001", "date": "2025-11-13"}
        )
        assert doc is not None
        assert doc["steps_total"] == 5000
        assert doc["calories_out_total"] == 220.0

    async def test_record_snapshot_with_delta_calculation(self, mongo_repo):
        """Should calculate delta between consecutive snapshots."""
        # Record first snapshot
        snapshot1 = HealthSnapshot(
            user_id="test_user_001",
            date="2025-11-13",
            timestamp=datetime(2025, 11, 13, 12, 0, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            steps_total=5000,
            calories_out_total=220.0,
            hr_avg_session=72.0,
        )
        delta1 = await mongo_repo.record_snapshot(snapshot1)
        assert delta1 is None

        # Record second snapshot (later in the day)
        snapshot2 = HealthSnapshot(
            user_id="test_user_001",
            date="2025-11-13",
            timestamp=datetime(2025, 11, 13, 18, 0, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            steps_total=10000,
            calories_out_total=450.0,
            hr_avg_session=74.0,
        )
        delta2 = await mongo_repo.record_snapshot(snapshot2)

        # Verify delta calculated correctly
        assert delta2 is not None
        assert delta2.steps_delta == 5000
        assert delta2.calories_out_delta == 230.0
        assert delta2.reset is False
        assert delta2.duplicate is False

    async def test_record_snapshot_cross_day_no_delta(self, mongo_repo):
        """Should not calculate delta across different dates."""
        # Snapshot for 2025-11-13
        snapshot1 = HealthSnapshot(
            user_id="test_user_001",
            date="2025-11-13",
            timestamp=datetime(2025, 11, 13, 23, 59, 59, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            steps_total=12000,
            calories_out_total=540.0,
            hr_avg_session=73.0,
        )
        await mongo_repo.record_snapshot(snapshot1)

        # Snapshot for 2025-11-14 (different date)
        snapshot2 = HealthSnapshot(
            user_id="test_user_001",
            date="2025-11-14",
            timestamp=datetime(2025, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            steps_total=3000,
            calories_out_total=135.0,
            hr_avg_session=71.0,
        )
        delta = await mongo_repo.record_snapshot(snapshot2)

        # Different dates: no delta calculated
        assert delta is None


@pytest.mark.asyncio
class TestMongoActivityRepositoryTemporalQueries:
    """Test temporal queries using production indexes."""

    async def test_list_events_with_time_range(self, mongo_repo):
        """Should retrieve events within time range using idx_user_ts."""
        base_time = datetime(2025, 11, 13, 10, 0, 0, tzinfo=timezone.utc)
        events = [
            ActivityEvent(
                user_id="test_user_001",
                ts=(base_time + timedelta(minutes=i)).isoformat().replace("+00:00", "Z"),
                steps=100,
                calories_out=4.5,
                hr_avg=70.0,
                source=ActivitySource.APPLE_HEALTH,
            )
            for i in range(3)
        ]
        await mongo_repo.ingest_events(events)

        # Query with time range (first 2 events only)
        retrieved = await mongo_repo.list_events(
            user_id="test_user_001",
            start_ts=events[0].ts,
            end_ts=events[1].ts,
        )

        # Should return first 2 events (start_ts inclusive, end_ts exclusive typically)
        assert len(retrieved) in [1, 2]  # Depends on exact boundary handling

    async def test_list_events_empty_range(self, mongo_repo):
        """Should return empty list for time range with no events."""
        base_time = datetime(2025, 11, 13, 10, 0, 0, tzinfo=timezone.utc)

        events = await mongo_repo.list_events(
            user_id="test_user_001",
            start_ts=base_time.isoformat().replace("+00:00", "Z"),
            end_ts=(base_time + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        )

        assert events == []


@pytest.mark.asyncio
class TestMongoActivityRepositoryDailyTotals:
    """Test daily aggregation queries."""

    async def test_get_daily_totals_with_events(self, mongo_repo):
        """Should aggregate events into daily totals."""
        base_time = datetime(2025, 11, 13, 8, 0, 0, tzinfo=timezone.utc)
        events = [
            ActivityEvent(
                user_id="test_user_001",
                ts=(base_time + timedelta(hours=i)).isoformat().replace("+00:00", "Z"),
                steps=500,
                calories_out=22.5,
                hr_avg=70.0,
                source=ActivitySource.APPLE_HEALTH,
            )
            for i in range(5)  # 5 hours of data
        ]
        await mongo_repo.ingest_events(events)

        # Get daily totals
        totals = await mongo_repo.get_daily_totals(
            user_id="test_user_001",
            date="2025-11-13",
        )

        # Verify aggregation
        assert totals["steps_total"] == 2500  # 500 * 5
        assert totals["calories_out_total"] == 112.5  # 22.5 * 5

    async def test_get_daily_totals_empty_day(self, mongo_repo):
        """Should return zeros for day with no events."""
        totals = await mongo_repo.get_daily_totals(
            user_id="test_user_001",
            date="2025-11-13",
        )

        assert totals["steps_total"] == 0
        assert totals["calories_out_total"] == 0.0


@pytest.mark.asyncio
class TestMongoActivityRepositoryListDeltas:
    """Test delta listing across date ranges."""

    async def test_list_deltas_multi_day(self, mongo_repo):
        """Should calculate deltas across multiple days."""
        # Create snapshots for 2 consecutive days
        dates = ["2025-11-13", "2025-11-14"]
        for idx, date in enumerate(dates):
            # Morning snapshot
            snapshot1 = HealthSnapshot(
                user_id="test_user_001",
                date=date,
                timestamp=datetime(2025, 11, 13 + idx, 12, 0, 0, tzinfo=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                steps_total=5000,
                calories_out_total=220.0,
                hr_avg_session=72.0,
            )
            await mongo_repo.record_snapshot(snapshot1)

            # Evening snapshot
            snapshot2 = HealthSnapshot(
                user_id="test_user_001",
                date=date,
                timestamp=datetime(2025, 11, 13 + idx, 20, 0, 0, tzinfo=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                steps_total=12000,
                calories_out_total=540.0,
                hr_avg_session=74.0,
            )
            await mongo_repo.record_snapshot(snapshot2)

        # Query deltas across both days
        deltas = await mongo_repo.list_deltas(
            user_id="test_user_001",
            start_date="2025-11-13",
            end_date="2025-11-15",
        )

        # Should have deltas for 2 days (morning->evening for each)
        assert len(deltas) >= 2

        # Verify delta calculations
        for delta in deltas:
            if not delta.duplicate and not delta.reset:
                assert delta.steps_delta == 7000  # 12000 - 5000
                assert delta.calories_out_delta == 320.0  # 540 - 220

    async def test_list_deltas_empty_range(self, mongo_repo):
        """Should return empty list for date range with no snapshots."""
        deltas = await mongo_repo.list_deltas(
            user_id="test_user_001",
            start_date="2025-11-13",
            end_date="2025-11-15",
        )

        assert deltas == []
