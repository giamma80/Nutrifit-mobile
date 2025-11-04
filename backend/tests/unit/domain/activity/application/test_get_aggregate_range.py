"""Unit tests for GetAggregateRangeQuery and handler."""

import pytest
from datetime import datetime, timezone, timedelta

from domain.activity.application.get_aggregate_range import (
    GetAggregateRangeQuery,
    GetAggregateRangeQueryHandler,
    GroupByPeriod,
)
from repository.activities import ActivityEventRecord, ActivitySource


@pytest.fixture
def sample_activity_events():
    """Create sample activity events over a week."""
    events = []
    base_date = datetime(2025, 10, 21, 12, 0, 0, tzinfo=timezone.utc)

    for day in range(7):  # 7 days
        timestamp = base_date + timedelta(days=day)

        # Morning activity
        morning = ActivityEventRecord(
            user_id="user123",
            ts=timestamp.replace(hour=9).isoformat().replace("+00:00", "Z"),
            steps=1000,
            calories_out=50.0,
            hr_avg=120.0,
            source=ActivitySource.APPLE_HEALTH,
        )
        events.append(morning)

        # Afternoon activity
        afternoon = ActivityEventRecord(
            user_id="user123",
            ts=timestamp.replace(hour=15).isoformat().replace("+00:00", "Z"),
            steps=1500,
            calories_out=75.0,
            hr_avg=135.0,
            source=ActivitySource.APPLE_HEALTH,
        )
        events.append(afternoon)

    return events


@pytest.fixture
def mock_activity_repo(monkeypatch, sample_activity_events):
    """Mock activity_repo with proper filtering."""

    def list_events(user_id, start_ts=None, end_ts=None, limit=10000):
        # Filtra eventi per date range
        if not start_ts or not end_ts:
            return sample_activity_events

        # Parse timestamps - handle both naive and aware
        start_dt = datetime.fromisoformat(start_ts)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)

        end_dt = datetime.fromisoformat(end_ts)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)

        filtered = []
        for event in sample_activity_events:
            event_dt = datetime.fromisoformat(event.ts.replace("Z", "+00:00"))
            if start_dt <= event_dt <= end_dt:
                filtered.append(event)
        return filtered

    # Mock il metodo list_events di activity_repo
    import repository.activities

    monkeypatch.setattr(repository.activities.activity_repo, "list_events", list_events)

    return repository.activities.activity_repo


class TestGetAggregateRangeQueryHandler:
    """Test GetAggregateRangeQueryHandler."""

    def test_aggregate_range_by_day(self, mock_activity_repo):
        """Test getting aggregate range grouped by day."""
        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 27, 23, 59, 59)

        query = GetAggregateRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        handler = GetAggregateRangeQueryHandler()
        results = handler.handle(query)

        # Should return 7 periods (one per day)
        assert len(results) == 7

        # Check first day
        first_day = results[0]
        assert first_day.period == "2025-10-21"
        assert first_day.total_steps == 2500  # 1000 + 1500
        assert first_day.total_calories_out == 125.0  # 50 + 75
        assert first_day.event_count == 2
        assert first_day.avg_heart_rate == 127.5  # (120 + 135) / 2

    def test_aggregate_range_by_week(self, mock_activity_repo):
        """Test getting aggregate range grouped by week."""
        # Week starting Monday 20 Oct through Sunday 26 Oct
        start_date = datetime(2025, 10, 20, 0, 0, 0)
        end_date = datetime(2025, 10, 26, 23, 59, 59)

        query = GetAggregateRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.WEEK,
        )

        handler = GetAggregateRangeQueryHandler()
        results = handler.handle(query)

        # Should return 1 period (entire week)
        assert len(results) == 1

        week_summary = results[0]
        assert week_summary.period == "2025-W43"
        # 6 days (21-26) * 2 events * (1000 + 1500) steps = 30000 steps
        # But we have 7 days of data (21-27), so data only covers 6 of them
        assert week_summary.total_steps == 15000  # Actually 6 days worth
        assert week_summary.event_count == 12

    def test_aggregate_range_by_month(self, mock_activity_repo):
        """Test getting aggregate range grouped by month."""
        start_date = datetime(2025, 10, 1, 0, 0, 0)
        end_date = datetime(2025, 10, 31, 23, 59, 59)

        query = GetAggregateRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.MONTH,
        )

        handler = GetAggregateRangeQueryHandler()
        results = handler.handle(query)

        # Should return 1 period (entire month)
        assert len(results) == 1

        month_summary = results[0]
        assert month_summary.period == "2025-10"
        # 7 days * 2 events * (1000 + 1500) steps
        assert month_summary.total_steps == 17500
        assert month_summary.total_calories_out == 875.0
        assert month_summary.event_count == 14

    def test_aggregate_range_empty_result(self, mock_activity_repo, monkeypatch):
        """Test getting aggregate range with no activity."""
        start_date = datetime(2025, 11, 1, 0, 0, 0)
        end_date = datetime(2025, 11, 7, 23, 59, 59)

        # Mock per restituire lista vuota
        import repository.activities

        monkeypatch.setattr(
            repository.activities.activity_repo, "list_events", lambda *args, **kwargs: []
        )

        query = GetAggregateRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        handler = GetAggregateRangeQueryHandler()
        results = handler.handle(query)

        # Should return 7 periods with zero values
        assert len(results) == 7
        for result in results:
            assert result.total_steps == 0
            assert result.total_calories_out == 0.0
            assert result.event_count == 0
            assert result.avg_heart_rate is None

    def test_aggregate_range_respects_date_boundaries(self, mock_activity_repo):
        """Test that date boundaries are respected."""
        # Query only 3 days
        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 23, 23, 59, 59)

        query = GetAggregateRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        handler = GetAggregateRangeQueryHandler()
        results = handler.handle(query)

        # Should return only 3 periods
        assert len(results) == 3
        assert results[0].period == "2025-10-21"
        assert results[1].period == "2025-10-22"
        assert results[2].period == "2025-10-23"

    def test_aggregate_range_handles_partial_data(self, mock_activity_repo, monkeypatch):
        """Test getting aggregate range with partial data."""
        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 27, 23, 59, 59)

        # Solo 1 evento sul primo giorno
        single_event = ActivityEventRecord(
            user_id="user123",
            ts="2025-10-21T10:00:00Z",
            steps=5000,
            calories_out=250.0,
            hr_avg=150.0,
            source=ActivitySource.MANUAL,
        )

        def list_events(user_id, start_ts=None, end_ts=None, limit=10000):
            if not start_ts or not end_ts:
                return [single_event]

            # Parse timestamps - handle both naive and aware
            start_dt = datetime.fromisoformat(start_ts)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)

            end_dt = datetime.fromisoformat(end_ts)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)

            event_dt = datetime.fromisoformat(single_event.ts.replace("Z", "+00:00"))

            if start_dt <= event_dt <= end_dt:
                return [single_event]
            return []

        import repository.activities

        monkeypatch.setattr(repository.activities.activity_repo, "list_events", list_events)

        query = GetAggregateRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        handler = GetAggregateRangeQueryHandler()
        results = handler.handle(query)

        # Should return 7 periods
        assert len(results) == 7

        # First day has data
        assert results[0].total_steps == 5000
        assert results[0].event_count == 1

        # Other days are empty
        for i in range(1, 7):
            assert results[i].total_steps == 0
            assert results[i].event_count == 0
