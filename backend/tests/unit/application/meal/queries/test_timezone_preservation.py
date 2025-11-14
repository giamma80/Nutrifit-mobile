"""Unit tests for timezone preservation in GetSummaryRangeQuery.

This test suite verifies that timezone information is correctly preserved
when splitting date ranges, which is critical for MongoDB compatibility
(MongoDB requires timezone-aware datetime objects).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from application.meal.queries.get_summary_range import (
    GetSummaryRangeQuery,
    GetSummaryRangeQueryHandler,
)
from domain.shared.types import GroupByPeriod


@pytest.fixture
def mock_repository():
    """Create mock meal repository."""
    repository = AsyncMock()
    repository.get_by_user_and_date_range = AsyncMock(return_value=[])
    return repository


@pytest.fixture
def handler(mock_repository):
    """Create query handler with mock repository."""
    return GetSummaryRangeQueryHandler(repository=mock_repository)


class TestTimezonePreservation:
    """Test timezone preservation in date range splitting."""

    @pytest.mark.asyncio
    async def test_day_grouping_preserves_timezone(self, handler, mock_repository):
        """Test that DAY grouping preserves timezone in split periods."""
        # Create timezone-aware datetimes (UTC)
        start = datetime(2025, 11, 13, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 15, 23, 59, 59, tzinfo=timezone.utc)

        query = GetSummaryRangeQuery(
            user_id="test-user",
            start_date=start,
            end_date=end,
            group_by=GroupByPeriod.DAY,
        )

        # Execute query
        await handler.handle(query)

        # Verify repository was called for each day with timezone-aware dates
        assert mock_repository.get_by_user_and_date_range.call_count == 3

        # Check each call has timezone-aware datetimes
        for call in mock_repository.get_by_user_and_date_range.call_args_list:
            _, kwargs = call
            period_start = kwargs["start_date"]
            period_end = kwargs["end_date"]

            # Critical: Both must be timezone-aware (MongoDB requirement)
            assert period_start.tzinfo is not None, f"period_start lost timezone: {period_start}"
            assert period_end.tzinfo is not None, f"period_end lost timezone: {period_end}"
            assert period_start.tzinfo == timezone.utc
            assert period_end.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_week_grouping_preserves_timezone(self, handler, mock_repository):
        """Test that WEEK grouping preserves timezone in split periods."""
        # Create timezone-aware datetimes (UTC)
        start = datetime(2025, 11, 10, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 23, 23, 59, 59, tzinfo=timezone.utc)

        query = GetSummaryRangeQuery(
            user_id="test-user",
            start_date=start,
            end_date=end,
            group_by=GroupByPeriod.WEEK,
        )

        # Execute query
        await handler.handle(query)

        # Verify all calls have timezone-aware datetimes
        for call in mock_repository.get_by_user_and_date_range.call_args_list:
            _, kwargs = call
            period_start = kwargs["start_date"]
            period_end = kwargs["end_date"]

            # Critical: Must preserve timezone
            assert period_start.tzinfo is not None, f"period_start lost timezone: {period_start}"
            assert period_end.tzinfo is not None, f"period_end lost timezone: {period_end}"
            assert period_start.tzinfo == timezone.utc
            assert period_end.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_month_grouping_preserves_timezone(self, handler, mock_repository):
        """Test that MONTH grouping preserves timezone in split periods."""
        # Create timezone-aware datetimes (UTC)
        start = datetime(2025, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        query = GetSummaryRangeQuery(
            user_id="test-user",
            start_date=start,
            end_date=end,
            group_by=GroupByPeriod.MONTH,
        )

        # Execute query
        await handler.handle(query)

        # Verify all calls have timezone-aware datetimes
        for call in mock_repository.get_by_user_and_date_range.call_args_list:
            _, kwargs = call
            period_start = kwargs["start_date"]
            period_end = kwargs["end_date"]

            # Critical: Must preserve timezone
            assert period_start.tzinfo is not None, f"period_start lost timezone: {period_start}"
            assert period_end.tzinfo is not None, f"period_end lost timezone: {period_end}"
            assert period_start.tzinfo == timezone.utc
            assert period_end.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_mongodb_compatibility_regression(self, handler, mock_repository):
        """
        Regression test for MongoDB compatibility issue.

        Before fix: .replace() without tzinfo parameter stripped timezone,
        causing MongoDB to reject datetime objects as naive.

        After fix: Timezone is explicitly preserved, ensuring MongoDB
        compatibility.
        """
        # Simulate MongoDB requirement: timezone-aware datetime
        start = datetime(2025, 11, 13, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 13, 23, 59, 59, tzinfo=timezone.utc)

        query = GetSummaryRangeQuery(
            user_id="test-user",
            start_date=start,
            end_date=end,
            group_by=GroupByPeriod.DAY,
        )

        # Execute query (should not raise ValueError from MongoDB)
        await handler.handle(query)

        # Verify repository was called with timezone-aware datetimes
        call_args = mock_repository.get_by_user_and_date_range.call_args
        _, kwargs = call_args

        # MongoDB datetime_to_iso() would raise ValueError if tzinfo is None
        # This verifies the fix prevents that error
        assert kwargs["start_date"].tzinfo is not None
        assert kwargs["end_date"].tzinfo is not None

    def test_split_periods_returns_aware_datetimes(self, handler):
        """Test _split_range_into_periods returns timezone-aware tuples."""
        start = datetime(2025, 11, 13, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 15, 23, 59, 59, tzinfo=timezone.utc)

        periods = handler._split_range_into_periods(
            start_date=start, end_date=end, group_by=GroupByPeriod.DAY
        )

        # Verify all returned datetimes are timezone-aware
        for period_start, period_end in periods:
            assert (
                period_start.tzinfo is not None
            ), f"Split period start lost timezone: {period_start}"
            assert period_end.tzinfo is not None, f"Split period end lost timezone: {period_end}"
            assert period_start.tzinfo == timezone.utc
            assert period_end.tzinfo == timezone.utc
