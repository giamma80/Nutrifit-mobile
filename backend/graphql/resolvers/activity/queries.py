"""Activity query resolvers.

Groups activity-related queries:
- entries: List activity events
- syncEntries: List health totals sync deltas
"""

import dataclasses
from typing import List, Optional, Any
import strawberry
from strawberry.types import Info

from graphql.types_activity_health import ActivityEvent, HealthTotalsDelta
from repository.activities import activity_repo
from repository.health_totals import health_totals_repo

DEFAULT_USER_ID = "default"


@strawberry.type
class ActivityQueries:
    """Activity data queries."""

    @strawberry.field(description="Lista eventi attività con paginazione")
    def entries(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        limit: int = 100,
        after: Optional[str] = None,
        before: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[ActivityEvent]:
        """List activity events with pagination.

        Args:
            limit: Max results (default 100, max 500)
            after: Start timestamp (optional)
            before: End timestamp (optional)
            user_id: User ID (defaults to "default")

        Returns:
            List of activity events

        Example:
            query {
              activity {
                entries(userId: "user123", limit: 10) {
                  id, timestamp, source, steps
                }
              }
            }
        """
        if limit <= 0:
            limit = 100
        if limit > 500:
            limit = 500
        uid = user_id or DEFAULT_USER_ID
        events = activity_repo.list(
            uid,
            start_ts=after,
            end_ts=before,
            limit=limit,
        )
        return [ActivityEvent(**dataclasses.asdict(e)) for e in events]

    @strawberry.field(description="Lista delta sync health totals per giorno")
    def sync_entries(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        date: str,
        user_id: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 200,
    ) -> List[HealthTotalsDelta]:
        """List health totals sync deltas for a date.

        Args:
            date: Date in YYYY-MM-DD format
            user_id: User ID (defaults to "default")
            after: After timestamp (optional)
            limit: Max results (default 200, max 500)

        Returns:
            List of sync deltas

        Example:
            query {
              activity {
                syncEntries(date: "2025-10-25", userId: "user123") {
                  timestamp, steps, caloriesOut
                }
              }
            }
        """
        if limit <= 0:
            limit = 50
        if limit > 500:
            limit = 500
        uid = user_id or DEFAULT_USER_ID
        records = health_totals_repo.list_deltas(
            user_id=uid, date=date, after_ts=after, limit=limit
        )
        return [HealthTotalsDelta(**dataclasses.asdict(r)) for r in records]
