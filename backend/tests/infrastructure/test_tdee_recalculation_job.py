"""
Tests for TDEE recalculation background job.
"""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.entities.progress_record import (
    ProgressRecord,
)
from domain.nutritional_profile.core.value_objects.bmr import BMR
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.macro_split import (
    MacroSplit,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId
from domain.nutritional_profile.core.value_objects.activity_level import (
    ActivityLevel,
)
from domain.nutritional_profile.core.value_objects.tdee import TDEE
from domain.nutritional_profile.core.value_objects.user_data import UserData
from infrastructure.scheduler.tdee_recalculation_job import (
    TDEERecalculationJob,
)


@pytest.fixture
def mock_repository():
    """Mock profile repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_tdee_service():
    """Mock adaptive TDEE service."""
    service = MagicMock()
    service.get_current_estimate.return_value = 2000.0
    return service


@pytest.fixture
def tdee_job(mock_repository, mock_tdee_service):
    """Create TDEE recalculation job instance."""
    return TDEERecalculationJob(
        profile_repository=mock_repository,
        adaptive_tdee_service=mock_tdee_service,
        lookback_days=14,
        min_records=3,
    )


@pytest.fixture
def sample_profile():
    """Create sample nutritional profile with progress history."""
    profile_id = ProfileId.generate()
    user_data = UserData(
        weight=80.0,
        height=180.0,
        age=30,
        sex="M",
        activity_level=ActivityLevel.MODERATE,
    )

    profile = NutritionalProfile(
        profile_id=profile_id,
        user_id="user123",
        user_data=user_data,
        goal=Goal.MAINTAIN,
        bmr=BMR(1800.0),
        tdee=TDEE(2400.0),
        calories_target=2400.0,
        macro_split=MacroSplit(protein_g=180, carbs_g=240, fat_g=80),
        progress_history=[],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Add progress records for last 10 days
    for i in range(10):
        record_date = date.today() - timedelta(days=i)
        record = ProgressRecord(
            record_id=uuid4(),
            profile_id=profile_id,
            date=record_date,
            weight=80.0 - i * 0.1,
            consumed_calories=2000.0,
        )
        profile.progress_history.append(record)

    return profile


class TestTDEERecalculationJobInitialization:
    """Test TDEE job initialization."""

    def test_init_with_defaults(self, mock_repository, mock_tdee_service):
        """Test initialization with default parameters."""
        job = TDEERecalculationJob(
            profile_repository=mock_repository,
            adaptive_tdee_service=mock_tdee_service,
        )

        assert job.profile_repository is mock_repository
        assert job.adaptive_tdee_service is mock_tdee_service
        assert job.lookback_days == 14
        assert job.min_records == 3

    def test_init_with_custom_params(
        self, mock_repository, mock_tdee_service
    ):
        """Test initialization with custom parameters."""
        job = TDEERecalculationJob(
            profile_repository=mock_repository,
            adaptive_tdee_service=mock_tdee_service,
            lookback_days=7,
            min_records=5,
        )

        assert job.lookback_days == 7
        assert job.min_records == 5


class TestTDEERecalculationJobExecution:
    """Test TDEE job execution."""

    @pytest.mark.asyncio
    async def test_run_with_no_profiles(self, tdee_job):
        """Test job execution when no profiles found."""
        # Job returns empty list (placeholder implementation)
        await tdee_job.run()

        # Should complete without error
        # (actual implementation would query repository)

    @pytest.mark.asyncio
    async def test_update_profile_tdee_success(
        self, tdee_job, sample_profile, mock_tdee_service
    ):
        """Test successful TDEE update for single profile."""
        await tdee_job._update_profile_tdee(sample_profile)

        # Should call TDEE service update for each record pair
        # (9 updates for 10 records)
        assert mock_tdee_service.update.call_count == 9

        # Should get final estimate
        mock_tdee_service.get_current_estimate.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_skips_insufficient_records(
        self, tdee_job, sample_profile, mock_tdee_service
    ):
        """Test profile skipped if insufficient progress records."""
        # Keep only 2 records (below min_records=3)
        sample_profile.progress_history = sample_profile.progress_history[:2]

        await tdee_job._update_profile_tdee(sample_profile)

        # Should not call service
        mock_tdee_service.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_profile_handles_none_calories(
        self, tdee_job, sample_profile, mock_tdee_service
    ):
        """Test handling of None consumed_calories."""
        # Set some records to None calories
        for record in sample_profile.progress_history[:3]:
            record.consumed_calories = None

        await tdee_job._update_profile_tdee(sample_profile)

        # Should still process with 0.0 for None values
        assert mock_tdee_service.update.call_count == 9

    @pytest.mark.asyncio
    async def test_update_profile_handles_none_estimate(
        self, tdee_job, sample_profile, mock_tdee_service
    ):
        """Test handling when TDEE service returns None."""
        mock_tdee_service.get_current_estimate.return_value = None

        await tdee_job._update_profile_tdee(sample_profile)

        # Should complete without error
        # (logs warning but doesn't raise)


class TestTDEERecalculationJobHelpers:
    """Test helper methods."""

    def test_get_recent_progress_records(self, tdee_job, sample_profile):
        """Test filtering recent progress records."""
        # Job has lookback_days=14
        recent = tdee_job._get_recent_progress_records(sample_profile)

        # All 10 records should be within 14 days
        assert len(recent) == 10

        # Should be sorted by date ascending
        dates = [r.date for r in recent]
        assert dates == sorted(dates)

    def test_get_recent_progress_filters_old_records(
        self, tdee_job, sample_profile
    ):
        """Test old records are filtered out."""
        # Add old record (30 days ago)
        old_record = ProgressRecord(
            record_id=uuid4(),
            profile_id=sample_profile.profile_id,
            date=date.today() - timedelta(days=30),
            weight=85.0,
            consumed_calories=2000.0,
        )
        sample_profile.progress_history.append(old_record)

        recent = tdee_job._get_recent_progress_records(sample_profile)

        # Should exclude old record (only 10 recent ones)
        assert len(recent) == 10
        assert all(
            (datetime.now() - datetime.combine(r.date, datetime.min.time()))
            <= timedelta(days=14)
            for r in recent
        )

    @pytest.mark.asyncio
    async def test_health_check_success(self, tdee_job, mock_repository):
        """Test health check with available repository."""
        result = await tdee_job.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_tdee_service):
        """Test health check with None repository."""
        job = TDEERecalculationJob(
            profile_repository=None,  # type: ignore
            adaptive_tdee_service=mock_tdee_service,
        )

        result = await job.health_check()

        assert result is False


class TestTDEERecalculationJobEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_update_profile_with_single_record(
        self, tdee_job, sample_profile, mock_tdee_service
    ):
        """Test profile with only 1 record (below minimum)."""
        sample_profile.progress_history = sample_profile.progress_history[:1]

        await tdee_job._update_profile_tdee(sample_profile)

        # Should skip (needs min 3 records)
        mock_tdee_service.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_profile_with_exactly_min_records(
        self, tdee_job, sample_profile, mock_tdee_service
    ):
        """Test profile with exactly min_records (3)."""
        sample_profile.progress_history = sample_profile.progress_history[:3]

        await tdee_job._update_profile_tdee(sample_profile)

        # Should process (2 updates for 3 records)
        assert mock_tdee_service.update.call_count == 2

    def test_get_recent_progress_empty_history(self, tdee_job, sample_profile):
        """Test profile with no progress history."""
        sample_profile.progress_history = []

        recent = tdee_job._get_recent_progress_records(sample_profile)

        assert len(recent) == 0
