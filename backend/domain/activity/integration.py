"""Activity domain integration service.

Layer di integrazione tra il dominio Activity e il GraphQL layer esistente.
Gestisce feature flag ACTIVITY_DOMAIN_V2 per rollout graduale con fallback
alla logica legacy in caso di errori.

Responsabilità:
- Feature flag check e inizializzazione domain services
- Enhanced daily summary con aggregazioni domain-driven
- Bridge per mutations ingestActivityEvents e syncHealthTotals
- Graceful degradation alla logica esistente
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Tuple

from domain.activity.model import (
    ActivityEvent,
    HealthSnapshot,
    ActivityDelta,
    ActivitySource as DomainActivitySource,
)
from infrastructure.persistence.activity_repository_factory import (
    create_activity_repository,
)
from domain.activity.application import (
    ActivitySyncService,
    ActivityAggregationService,
    create_activity_sync_service,
    create_activity_aggregation_service,
)

logger = logging.getLogger("domain.activity.integration")


class ActivityIntegrationService:
    """Integration layer tra activity domain e GraphQL esistente."""

    def __init__(self) -> None:
        self._sync_service: Optional[ActivitySyncService] = None
        self._aggregation_service: Optional[ActivityAggregationService] = None
        # V2 è sempre attivo

        try:
            self._initialize_services()
            logger.info("Activity domain V2 enabled and initialized")
        except Exception as e:
            logger.error(f"Failed to initialize activity V2: {e}")
            raise RuntimeError(f"Critical: Activity service failed to initialize: {e}")

    def _initialize_services(self) -> None:
        """Inizializza servizi domain con repository dependency injection."""
        activity_repo = create_activity_repository()

        self._sync_service = create_activity_sync_service(activity_repo)
        self._aggregation_service = create_activity_aggregation_service(activity_repo)

    async def enhanced_daily_summary(
        self,
        user_id: str,
        date: str,
        fallback_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enhanced daily summary con activity domain calculations.

        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format
            fallback_summary: Existing summary from app.py logic

        Returns:
            Enhanced summary dict with activity domain insights
        """
        if not self._aggregation_service:
            return fallback_summary

        try:
            # Calculate enhanced summary using activity domain
            domain_summary = await self._aggregation_service.calculate_daily_summary(
                user_id=user_id, date=date
            )

            # Merge with existing summary, keeping backward compatibility
            enhanced = fallback_summary.copy()

            # Add new fields from activity domain
            enhanced.update(
                {
                    "activity_v2_enabled": True,
                    "domain_total_steps": domain_summary.total_steps,
                    "domain_total_calories_out": domain_summary.calories_out_rounded(),  # noqa: E501
                    "domain_events_count": domain_summary.events_count,
                    "calculation_source": "activity_domain_v2",
                }
            )

            logger.debug(
                f"Enhanced daily summary for {user_id}/{date} "
                f"(steps: {domain_summary.total_steps}, "
                f"calories: {domain_summary.total_calories_out})"
            )
            return enhanced

        except Exception as e:
            logger.error(f"Error in enhanced daily summary: {e}")
            # Graceful fallback to existing logic
            return fallback_summary

    async def ingest_activity_events_v2(
        self,
        events_data: List[Dict[str, Any]],
        user_id: str,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[int, int, List[Tuple[int, str]], bool]:
        """Enhanced activity events ingest con domain validation.

        Returns:
            (accepted, duplicates, rejected, used_domain_v2)
        """
        if not self._sync_service:
            return 0, 0, [], False

        try:
            # Convert GraphQL input → domain events
            domain_events = []
            for event_data in events_data:
                # Map GraphQL ActivitySource → domain ActivitySource
                source_value = event_data.get("source", "MANUAL")
                if hasattr(source_value, "name"):
                    source_value = source_value.name

                domain_source = DomainActivitySource(source_value)

                domain_event = ActivityEvent(
                    user_id=user_id,
                    ts=event_data["ts"],
                    steps=event_data.get("steps"),
                    calories_out=event_data.get("calories_out"),
                    hr_avg=event_data.get("hr_avg"),
                    source=domain_source,
                )
                domain_events.append(domain_event)

            # Ingest usando domain service
            result = await self._sync_service.ingest_activity_events(domain_events, idempotency_key)
            accepted, duplicates, rejected = result

            logger.debug(
                f"Activity events ingest V2: accepted={accepted}, "
                f"duplicates={duplicates}, rejected={len(rejected)}"
            )

            return accepted, duplicates, rejected, True

        except Exception as e:
            logger.error(f"Error in activity events ingest V2: {e}")
            return 0, 0, [], False

    async def sync_health_snapshot_v2(
        self,
        snapshot_data: Dict[str, Any],
        user_id: str,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], bool]:
        """Enhanced health snapshot sync con domain validation.

        Returns:
            (sync_result, used_domain_v2)
        """
        if not self._sync_service:
            return {}, False

        try:
            # Convert GraphQL input → domain snapshot
            domain_snapshot = HealthSnapshot(
                user_id=user_id,
                date=snapshot_data["date"],
                timestamp=snapshot_data["timestamp"],
                steps_total=snapshot_data["steps"],
                calories_out_total=snapshot_data["calories_out"],
                hr_avg_session=snapshot_data.get("hr_avg_session"),
            )

            # Sync usando domain service
            result = await self._sync_service.sync_health_snapshot(domain_snapshot, idempotency_key)

            logger.debug(
                f"Health snapshot sync V2: accepted={result['accepted']}, "
                f"duplicate={result['duplicate']}, reset={result['reset']}"
            )

            return result, True

        except Exception as e:
            logger.error(f"Error in health snapshot sync V2: {e}")
            return {}, False

    async def list_activity_deltas_v2(
        self,
        user_id: str,
        date: str,
        after_ts: Optional[str] = None,
        limit: int = 200,
    ) -> Tuple[List[ActivityDelta], bool]:
        """Lista delta activity con domain service.

        Returns:
            (deltas_list, used_domain_v2)
        """
        if not self._aggregation_service:
            return [], False

        try:
            deltas = await self._aggregation_service.list_activity_deltas(
                user_id, date, after_ts, limit
            )
            return deltas, True

        except Exception as e:
            logger.error(f"Error listing deltas V2: {e}")
            return [], False


# Global singleton for easy access
_integration_service: Optional[ActivityIntegrationService] = None


def get_activity_integration_service() -> ActivityIntegrationService:
    """Get or create activity integration service singleton."""
    global _integration_service
    if _integration_service is None:
        _integration_service = ActivityIntegrationService()
    return _integration_service


__all__ = [
    "ActivityIntegrationService",
    "get_activity_integration_service",
]
