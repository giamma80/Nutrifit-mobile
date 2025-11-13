"""Unit tests for Activity Repository implementations."""

import pytest

from domain.activity.model import (
    ActivityEvent,
    ActivitySource,
    HealthSnapshot,
)
from infrastructure.persistence.inmemory.activity_repository import (
    InMemoryActivityRepository,
)
from infrastructure.persistence.activity_repository_factory import (
    create_activity_repository,
    reset_activity_repository,
)


@pytest.fixture(autouse=True)
def reset_repos():
    """Reset all repositories before each test."""
    # Reset factory singletons
    reset_activity_repository()

    # Import and reset legacy repositories
    from repository import activities, health_totals

    # Recreate fresh instances (if they have clear methods, use them)
    activities.activity_repo = activities.InMemoryActivityRepository()
    health_totals.health_totals_repo = health_totals.HealthTotalsRepository()

    yield

    # Cleanup after test
    reset_activity_repository()


@pytest.fixture
def activity_repo():
    """Create fresh activity repository for each test."""
    return InMemoryActivityRepository()


@pytest.mark.asyncio
class TestInMemoryActivityRepository:
    """Test InMemoryActivityRepository implementation."""

    async def test_ingest_events_success(self, activity_repo):
        """Test successful event ingestion."""
        events = [
            ActivityEvent(
                user_id="user_123",
                ts="2025-11-05T10:00:00Z",
                steps=100,
                calories_out=5.0,
                hr_avg=75,
                source=ActivitySource.APPLE_HEALTH,
            ),
            ActivityEvent(
                user_id="user_123",
                ts="2025-11-05T10:01:00Z",
                steps=50,
                calories_out=2.5,
                hr_avg=70,
                source=ActivitySource.GOOGLE_FIT,
            ),
        ]

        accepted, duplicates, rejected = await activity_repo.ingest_events(events)

        assert accepted == 2
        assert duplicates == 0
        assert len(rejected) == 0

    async def test_ingest_events_duplicates(self, activity_repo):
        """Test duplicate detection in event ingestion."""
        event = ActivityEvent(
            user_id="user_123",
            ts="2025-11-05T10:00:00Z",
            steps=100,
            calories_out=5.0,
            hr_avg=75,
            source=ActivitySource.APPLE_HEALTH,
        )

        # First ingest
        result1 = await activity_repo.ingest_events([event])
        accepted1, duplicates1, rejected1 = result1
        assert accepted1 == 1
        assert duplicates1 == 0

        # Second ingest (duplicate)
        result2 = await activity_repo.ingest_events([event])
        accepted2, duplicates2, rejected2 = result2
        assert accepted2 == 0
        assert duplicates2 == 1

    async def test_list_events(self, activity_repo):
        """Test listing events."""
        events = [
            ActivityEvent(
                user_id="user_123",
                ts="2025-11-05T10:00:00Z",
                steps=100,
                calories_out=5.0,
                hr_avg=75,
                source=ActivitySource.APPLE_HEALTH,
            ),
            ActivityEvent(
                user_id="user_123",
                ts="2025-11-05T11:00:00Z",
                steps=150,
                calories_out=7.5,
                hr_avg=80,
                source=ActivitySource.APPLE_HEALTH,
            ),
        ]

        await activity_repo.ingest_events(events)

        # List all events
        result = await activity_repo.list_events("user_123")
        assert len(result) == 2
        assert result[0].steps == 100
        assert result[1].steps == 150

    async def test_list_events_with_date_range(self, activity_repo):
        """Test listing events with date range filter."""
        events = [
            ActivityEvent(
                user_id="user_123",
                ts="2025-11-05T10:00:00Z",
                steps=100,
                calories_out=5.0,
                hr_avg=75,
                source=ActivitySource.APPLE_HEALTH,
            ),
            ActivityEvent(
                user_id="user_123",
                ts="2025-11-06T10:00:00Z",
                steps=150,
                calories_out=7.5,
                hr_avg=80,
                source=ActivitySource.APPLE_HEALTH,
            ),
        ]

        await activity_repo.ingest_events(events)

        # List only Nov 5
        result = await activity_repo.list_events(
            "user_123",
            start_ts="2025-11-05T00:00:00Z",
            end_ts="2025-11-05T23:59:59Z",
        )
        assert len(result) == 1
        assert result[0].steps == 100

    async def test_get_daily_events_count(self, activity_repo):
        """Test counting daily events."""
        events = [
            ActivityEvent(
                user_id="user_123",
                ts="2025-11-05T10:00:00Z",
                steps=100,
                calories_out=5.0,
                hr_avg=75,
                source=ActivitySource.APPLE_HEALTH,
            ),
            ActivityEvent(
                user_id="user_123",
                ts="2025-11-05T11:00:00Z",
                steps=150,
                calories_out=7.5,
                hr_avg=80,
                source=ActivitySource.APPLE_HEALTH,
            ),
        ]

        await activity_repo.ingest_events(events)

        count = await activity_repo.get_daily_events_count("user_123", "2025-11-05")
        assert count == 2

    async def test_record_snapshot_success(self, activity_repo):
        """Test recording health snapshot."""
        snapshot = HealthSnapshot(
            user_id="user_123",
            date="2025-11-05",
            timestamp="2025-11-05T12:00:00Z",
            steps_total=1000,
            calories_out_total=50.0,
            hr_avg_session=75,
        )

        result = await activity_repo.record_snapshot(snapshot)

        assert result["accepted"] is True
        assert result["duplicate"] is False
        assert result["delta"] is not None
        assert result["delta"].steps_delta == 1000

    async def test_record_snapshot_duplicate(self, activity_repo):
        """Test duplicate snapshot detection."""
        snapshot = HealthSnapshot(
            user_id="user_123",
            date="2025-11-05",
            timestamp="2025-11-05T12:00:00Z",
            steps_total=1000,
            calories_out_total=50.0,
            hr_avg_session=75,
        )

        # First record
        result1 = await activity_repo.record_snapshot(snapshot)
        assert result1["accepted"] is True

        # Duplicate
        result2 = await activity_repo.record_snapshot(snapshot)
        assert result2["duplicate"] is True

    async def test_list_deltas(self, activity_repo):
        """Test listing activity deltas."""
        snapshot1 = HealthSnapshot(
            user_id="user_123",
            date="2025-11-05",
            timestamp="2025-11-05T12:00:00Z",
            steps_total=1000,
            calories_out_total=50.0,
            hr_avg_session=75,
        )

        snapshot2 = HealthSnapshot(
            user_id="user_123",
            date="2025-11-05",
            timestamp="2025-11-05T13:00:00Z",
            steps_total=1500,
            calories_out_total=75.0,
            hr_avg_session=80,
        )

        await activity_repo.record_snapshot(snapshot1)
        await activity_repo.record_snapshot(snapshot2)

        deltas = await activity_repo.list_deltas("user_123", "2025-11-05")

        assert len(deltas) == 2
        assert deltas[0].steps_delta == 1000
        assert deltas[1].steps_delta == 500

    async def test_get_daily_totals(self, activity_repo):
        """Test getting daily totals."""
        snapshot = HealthSnapshot(
            user_id="user_123",
            date="2025-11-05",
            timestamp="2025-11-05T12:00:00Z",
            steps_total=1000,
            calories_out_total=50.0,
            hr_avg_session=75,
        )

        await activity_repo.record_snapshot(snapshot)

        steps, calories = await activity_repo.get_daily_totals("user_123", "2025-11-05")

        assert steps == 1000
        assert calories == 50.0


class TestActivityRepositoryFactory:
    """Test activity repository factory."""

    def test_create_activity_repository_inmemory(self, monkeypatch):
        """Test factory creates inmemory repository."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "inmemory")
        reset_activity_repository()

        repo = create_activity_repository()

        assert isinstance(repo, InMemoryActivityRepository)

    def test_create_activity_repository_singleton(self, monkeypatch):
        """Test factory returns singleton instance."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "inmemory")
        reset_activity_repository()

        repo1 = create_activity_repository()
        repo2 = create_activity_repository()

        assert repo1 is repo2

    def test_create_activity_repository_mongodb_requires_uri(self, monkeypatch):
        """Test factory requires MONGODB_URI for MongoDB backend."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "mongodb")
        monkeypatch.delenv("MONGODB_URI", raising=False)
        reset_activity_repository()

        with pytest.raises(ValueError, match="MONGODB_URI not configured"):
            create_activity_repository()

    def test_create_activity_repository_invalid_backend(self, monkeypatch):
        """Test factory raises error for invalid backend."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "invalid")
        reset_activity_repository()

        with pytest.raises(ValueError, match="Unknown REPOSITORY_BACKEND"):
            create_activity_repository()

    def test_reset_activity_repository(self, monkeypatch):
        """Test repository reset for testing."""
        monkeypatch.setenv("REPOSITORY_BACKEND", "inmemory")
        reset_activity_repository()

        repo1 = create_activity_repository()
        reset_activity_repository()
        repo2 = create_activity_repository()

        # After reset, should be different instances
        assert repo1 is not repo2
