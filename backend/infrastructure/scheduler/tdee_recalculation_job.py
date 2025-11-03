"""
Weekly TDEE recalculation background job.

This job runs weekly to update adaptive TDEE estimates for all active profiles
using recent progress data (weight, calories) with Kalman filtering.
"""

import logging
from datetime import datetime, timedelta
from typing import List

from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.entities.progress_record import (
    ProgressRecord,
)
from domain.nutritional_profile.core.ports.ml_services import (
    IAdaptiveTDEEService,
)
from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)

logger = logging.getLogger(__name__)


class TDEERecalculationJob:
    """
    Background job for weekly TDEE recalculation.

    Fetches all profiles with recent progress data (last 7-14 days)
    and updates their adaptive TDEE estimates using Kalman filtering.
    """

    def __init__(
        self,
        profile_repository: IProfileRepository,
        adaptive_tdee_service: IAdaptiveTDEEService,
        lookback_days: int = 14,
        min_records: int = 3,
    ):
        """
        Initialize TDEE recalculation job.

        Args:
            profile_repository: Repository for profile persistence
            adaptive_tdee_service: Kalman TDEE service for updates
            lookback_days: Number of days to look back for progress records
            min_records: Minimum progress records required for update
        """
        self.profile_repository = profile_repository
        self.adaptive_tdee_service = adaptive_tdee_service
        self.lookback_days = lookback_days
        self.min_records = min_records

    async def run(self) -> None:
        """
        Execute weekly TDEE recalculation job.

        Main entry point called by scheduler. Processes all active profiles
        with recent progress data.
        """
        logger.info("Starting weekly TDEE recalculation job")
        start_time = datetime.now()

        try:
            # Get all profiles with recent progress
            # (requires new repo method)
            profiles = await self._get_profiles_with_recent_progress()

            success_count = 0
            error_count = 0

            for profile in profiles:
                try:
                    await self._update_profile_tdee(profile)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(
                        f"Failed to update TDEE for profile " f"{profile.profile_id.value}: {e}",
                        exc_info=True,
                    )

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"TDEE recalculation completed: "
                f"{success_count} success, {error_count} errors, "
                f"duration: {elapsed:.2f}s"
            )

        except Exception as e:
            logger.error(f"TDEE recalculation job failed: {e}", exc_info=True)
            raise

    async def _get_profiles_with_recent_progress(
        self,
    ) -> List[NutritionalProfile]:
        """
        Get all profiles with progress records in lookback window.

        Note: This requires adding a new method to IProfileRepository:
        `find_with_recent_progress(days: int, min_records: int)`

        For now, this is a placeholder that would need to be implemented
        in the repository layer.

        Returns:
            List[NutritionalProfile]: Profiles with recent progress
        """
        # TODO: Add repository method for efficient querying
        # For now, return empty list (would be implemented in production)
        logger.warning(
            "Profile querying not yet implemented - "
            "requires repository method: find_with_recent_progress()"
        )
        return []

    async def _update_profile_tdee(self, profile: NutritionalProfile) -> None:
        """
        Update TDEE estimate for a single profile.

        Args:
            profile: Profile to update

        Raises:
            ValueError: If insufficient progress data
        """
        # Get recent progress records
        recent_records = self._get_recent_progress_records(profile)

        if len(recent_records) < self.min_records:
            logger.debug(
                f"Skipping profile {profile.profile_id.value}: "
                f"only {len(recent_records)} records "
                f"(minimum: {self.min_records})"
            )
            return

        # Extract data for Kalman update
        dates = [r.date for r in recent_records]
        weights = [r.weight for r in recent_records]
        calories = [
            r.consumed_calories if r.consumed_calories is not None else 0.0 for r in recent_records
        ]

        # Update TDEE using batch method
        # Note: update_batch in KalmanTDEEAdapter expects ProgressRecord list
        # But the service expects separate lists. We use the service directly:
        for i in range(len(dates)):
            if i > 0:
                prev_weight = weights[i - 1]
                self.adaptive_tdee_service.update(weights[i], prev_weight, calories[i])

        # Get updated estimate
        tdee_estimate = self.adaptive_tdee_service.get_current_estimate()

        if tdee_estimate is None:
            logger.warning(f"No TDEE estimate for profile " f"{profile.profile_id.value}")
            return

        # Update profile's calculated TDEE (if we want to store it)
        # This would require adding a field to store Kalman TDEE
        # For now, just log the update
        logger.info(
            f"Updated TDEE for profile {profile.profile_id.value}: "
            f"{tdee_estimate:.0f} kcal/day "
            f"(used {len(recent_records)} records)"
        )

        # TODO: Persist updated TDEE to profile if needed
        # profile.update_adaptive_tdee(tdee_estimate)
        # await self.profile_repository.save(profile)

    def _get_recent_progress_records(self, profile: NutritionalProfile) -> List[ProgressRecord]:
        """
        Get progress records within lookback window.

        Args:
            profile: Profile to get records from

        Returns:
            List[ProgressRecord]: Recent progress records, sorted by date
        """
        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)

        cutoff_datetime = datetime.combine(cutoff_date.date(), datetime.min.time())
        recent = [
            record
            for record in profile.progress_history
            if datetime.combine(record.date, datetime.min.time()) >= cutoff_datetime
        ]

        # Sort by date ascending
        recent.sort(key=lambda r: r.date)

        return recent

    async def health_check(self) -> bool:
        """
        Check if job dependencies are healthy.

        Returns:
            bool: True if all dependencies are available
        """
        try:
            # Verify repository is accessible
            # This is a simple check - could be expanded
            return self.profile_repository is not None
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
