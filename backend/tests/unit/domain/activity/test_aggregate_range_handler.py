"""Unit tests for GetAggregateRangeQuery and handler."""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta

from domain.activity.application.get_aggregate_range import (
    GetAggregateRangeQuery,
    GetAggregateRangeQueryHandler,
    GroupByPeriod,
)
from repository.activities import ActivityEventRecord


@pytest.fixture
def sample_activity_events():
    """Create sample activity events over a week."""
    events = []
    base_date = datetime(2025, 10, 21, 12, 0, 0)

    for day in range(7):  # 7 days
        for hour in range(8, 20):  # 12 hours per day
            timestamp = base_date + timedelta(days=day, hours=hour - 12)
            event = MagicMock(spec=ActivityEventRecord)
            event.user_id = "user123"
            event.ts = timestamp.isoformat() + "Z"
            event.steps = 100 if hour % 2 == 0 else 50  # Vary steps
            event.calories_out = 5.0
            event.hr_avg = 75.0 if hour % 3 == 0 else None
            events.append(event)

    return events


class TestGetAggregateRangeQueryHandler:
    """Test GetAggregateRangeQueryHandler."""

    def test_aggregate_range_by_day(self, sample_activity_events, monkeypatch):
        """Test getting aggregate range grouped by day."""
        # Mock activity_repo
        mock_list_events = MagicMock(return_value=sample_activity_events[:12])
        monkeypatch.setattr(
            "domain.activity.application.get_aggregate_range.activity_repo",
            MagicMock(list_events=mock_list_events),
        )

        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 21, 23, 59, 59)

        query = GetAggregateRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        handler = GetAggregateRangeQueryHandler()
        results = handler.handle(query)

        # Should return 1 period (single day)
        assert len(results) == 1

        day_summary = results[0]
        assert day_summary.period == "2025-10-21"
        # 6 events with 100 steps + 6 with 50 = 900 steps
        assert day_summary.total_steps == 900
        # 12 events * 5 calories = 60
        assert day_summary.total_calories_out == 60.0
        # Events with steps > 0 = 12
        assert day_summary.total_active_minutes == 12
        assert day_summary.event_count == 12

    def test_aggregate_range_by_week(self, sample_activity_events, monkeypatch):
        """Test getting aggregate range grouped by week."""
        # Mock activity_repo
        mock_list_events = MagicMock(return_value=sample_activity_events)
        monkeypatch.setattr(
            "domain.activity.application.get_aggregate_range.activity_repo",
            MagicMock(list_events=mock_list_events),
        )

        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 27, 23, 59, 59)

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
        # 7 days * 12 hours * (100+50)/2 average = 6300 steps
        assert week_summary.total_steps == 6300
        # 7 days * 12 hours * 5 calories = 420
        assert week_summary.total_calories_out == 420.0
        assert week_summary.event_count == 84

    def test_aggregate_range_by_month(self, sample_activity_events, monkeypatch):
        """Test getting aggregate range grouped by month."""
        # Mock activity_repo
        mock_list_events = MagicMock(return_value=sample_activity_events)
        monkeypatch.setattr(
            "domain.activity.application.get_aggregate_range.activity_repo",
            MagicMock(list_events=mock_list_events),
        )

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
        assert month_summary.total_steps == 6300
        assert month_summary.total_calories_out == 420.0

    def test_aggregate_range_empty_result(self, monkeypatch):
        """Test getting aggregate range with no events."""
        # Mock empty result
        mock_list_events = MagicMock(return_value=[])
        monkeypatch.setattr(
            "domain.activity.application.get_aggregate_range.activity_repo",
            MagicMock(list_events=mock_list_events),
        )

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

        # Should return 7 periods with zero values
        assert len(results) == 7
        for result in results:
            assert result.total_steps == 0
            assert result.total_calories_out == 0.0
            assert result.total_active_minutes == 0
            assert result.event_count == 0

    def test_aggregate_range_avg_heart_rate(self, sample_activity_events, monkeypatch):
        """Test heart rate averaging."""
        # Mock activity_repo
        mock_list_events = MagicMock(return_value=sample_activity_events[:12])
        monkeypatch.setattr(
            "domain.activity.application.get_aggregate_range.activity_repo",
            MagicMock(list_events=mock_list_events),
        )

        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 21, 23, 59, 59)

        query = GetAggregateRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        handler = GetAggregateRangeQueryHandler()
        results = handler.handle(query)

        day_summary = results[0]
        # Should have avg HR (some events have 75.0, others None)
        assert day_summary.avg_heart_rate is not None
        assert day_summary.avg_heart_rate == 75.0

    def test_aggregate_range_respects_date_boundaries(self, sample_activity_events, monkeypatch):
        """Test that date boundaries are respected."""
        # Mock activity_repo
        mock_list_events = MagicMock(return_value=sample_activity_events[:36])
        monkeypatch.setattr(
            "domain.activity.application.get_aggregate_range.activity_repo",
            MagicMock(list_events=mock_list_events),
        )

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
