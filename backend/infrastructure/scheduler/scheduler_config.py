"""
APScheduler configuration and management.

Provides centralized scheduler configuration for background jobs
like weekly TDEE recalculation.
"""

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .tdee_recalculation_job import TDEERecalculationJob

logger = logging.getLogger(__name__)


class SchedulerManager:
    """
    Manages APScheduler lifecycle and job registration.

    Singleton-like manager for the application scheduler,
    handling initialization, job registration, and shutdown.
    """

    def __init__(self) -> None:
        """Initialize scheduler manager."""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._tdee_job: Optional[TDEERecalculationJob] = None

    def initialize(
        self,
        tdee_job: TDEERecalculationJob,
        cron_expression: str = "0 2 * * 1",
    ) -> None:
        """
        Initialize and configure scheduler with jobs.

        Args:
            tdee_job: TDEE recalculation job instance
            cron_expression: Cron expression for TDEE job
                (default: 2 AM every Monday)
        """
        if self.scheduler is not None:
            logger.warning("Scheduler already initialized")
            return

        self._tdee_job = tdee_job

        # Create AsyncIO scheduler
        self.scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # Combine missed runs
                "max_instances": 1,  # One instance at a time
                "misfire_grace_time": 3600,  # 1 hour grace period
            },
        )

        # Register TDEE recalculation job
        self._register_tdee_job(cron_expression)

        logger.info("Scheduler initialized successfully")

    def _register_tdee_job(self, cron_expression: str) -> None:
        """
        Register weekly TDEE recalculation job.

        Args:
            cron_expression: Cron expression for scheduling
        """
        if self.scheduler is None or self._tdee_job is None:
            raise RuntimeError("Scheduler not initialized")

        trigger = CronTrigger.from_crontab(cron_expression, timezone="UTC")

        self.scheduler.add_job(
            self._tdee_job.run,
            trigger=trigger,
            id="tdee_recalculation",
            name="Weekly TDEE Recalculation",
            replace_existing=True,
        )

        logger.info(f"TDEE recalculation job registered with cron: " f"{cron_expression}")

    def start(self) -> None:
        """Start scheduler (begin executing jobs)."""
        if self.scheduler is None:
            raise RuntimeError("Scheduler not initialized")

        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return

        self.scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown scheduler gracefully.

        Args:
            wait: If True, wait for running jobs to complete
        """
        if self.scheduler is None:
            logger.warning("Scheduler not initialized")
            return

        if not self.scheduler.running:
            logger.warning("Scheduler not running")
            return

        self.scheduler.shutdown(wait=wait)
        logger.info(f"Scheduler shutdown (wait={wait})")

    def get_jobs(self) -> list[dict[str, str]]:
        """
        Get list of scheduled jobs.

        Returns:
            list[dict[str, str]]: List of job information
        """
        if self.scheduler is None:
            return []

        jobs = self.scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time,
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]

    async def trigger_tdee_job_now(self) -> None:
        """
        Manually trigger TDEE recalculation job immediately.

        Useful for testing or manual execution.
        """
        if self._tdee_job is None:
            raise RuntimeError("TDEE job not initialized")

        logger.info("Manually triggering TDEE recalculation job")
        await self._tdee_job.run()
