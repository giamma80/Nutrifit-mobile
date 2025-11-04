"""Activity mutation resolvers.

Groups activity-related mutations:
- syncActivityEvents: Sync batch activity events (was ingestActivityEvents)
"""

from typing import List, Optional, Any
import json as _json
import hashlib as _hashlib
import strawberry
from strawberry.types import Info
from graphql import GraphQLError

from graphql.types_activity_health import (
    ActivityMinuteInput,
    IngestActivityResult,
    RejectedActivityEvent,
    ActivitySource as GraphQLActivitySource,
)
from repository.activities import (
    activity_repo,
    ActivitySource as RepoActivitySource,
    ActivityEventRecord,
)

DEFAULT_USER_ID = "default"


def _normalize_activity_event(e: ActivityMinuteInput, user_id: str) -> ActivityEventRecord:
    """Convert GraphQL input to repository format."""
    return ActivityEventRecord(
        user_id=user_id,
        ts=e.ts,
        steps=e.steps or 0,
        calories_out=e.calories_out,
        hr_avg=e.hr_avg,
        source=_map_source_to_repo(e.source),
    )


def _map_source_to_repo(source: GraphQLActivitySource) -> RepoActivitySource:
    """Map GraphQL ActivitySource to repository ActivitySource."""
    mapping = {
        GraphQLActivitySource.APPLE_HEALTH: RepoActivitySource.APPLE_HEALTH,
        GraphQLActivitySource.GOOGLE_FIT: RepoActivitySource.GOOGLE_FIT,
        GraphQLActivitySource.MANUAL: RepoActivitySource.MANUAL,
    }
    return mapping[source]


@strawberry.type
class ActivityMutations:
    """Activity domain mutations."""

    @strawberry.mutation(  # type: ignore[misc]
        description="Sync batch minute activity events (idempotent)"
    )
    def sync_activity_events(
        self,
        info: Info[Any, Any],  # noqa: ARG002
        input: List[ActivityMinuteInput],
        idempotency_key: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> IngestActivityResult:
        """Sync batch activity events with idempotency support.

        This mutation ingests minute-level activity data (steps, calories, HR)
        with automatic deduplication based on (user_id, timestamp).

        Args:
            input: List of activity minute records
            idempotency_key: Optional client-provided deduplication key
            user_id: User ID (defaults to "default")

        Returns:
            IngestActivityResult with accepted/duplicate/rejected counts

        Example:
            mutation {
              activity {
                syncActivityEvents(
                  input: [
                    {ts: "2025-10-28T10:00:00Z", steps: 50, caloriesOut: 5.2}
                    {ts: "2025-10-28T10:01:00Z", steps: 48}
                  ]
                  userId: "user123"
                ) {
                  accepted
                  duplicates
                  rejected { index reason }
                }
              }
            }
        """
        uid = user_id or DEFAULT_USER_ID
        sig: Optional[str] = None

        # Auto-generate idempotency key if not provided
        if not idempotency_key:
            # Generate deterministic key based on payload (excluding timestamps)
            sig_payload = {
                "userId": uid,
                "input": [
                    {
                        "steps": e.steps,
                        "caloriesOut": e.calories_out,
                        "hrAvg": e.hr_avg,
                        "source": e.source.value,
                    }
                    for e in input
                ],
            }
            canonical = _json.dumps(sig_payload, sort_keys=True)
            sig = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
            idempotency_key = f"auto-{sig}"

        # Idempotency check
        if idempotency_key:
            # Calculate signature of input payload (exclude timestamp)
            if sig is None:
                sig_payload = {
                    "userId": uid,
                    "input": [
                        {
                            "steps": e.steps,
                            "caloriesOut": e.calories_out,
                            "hrAvg": e.hr_avg,
                            "source": e.source.value,
                        }
                        for e in input
                    ],
                }
                canonical = _json.dumps(sig_payload, sort_keys=True)
                sig = _hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

            # Check if we have cached result for this key
            cached_sig = activity_repo.get_idempotency(idempotency_key)
            if cached_sig is not None:
                # Key exists - check if payload matches
                if cached_sig != sig:
                    raise GraphQLError(
                        f"IdempotencyConflict: key '{idempotency_key}' "
                        f"used with different payload"
                    )
                # Same key, same payload → return cached result
                # For simplicity, we return the same result structure
                # In production, you'd cache the actual result
                return IngestActivityResult(
                    accepted=len(input),
                    duplicates=0,
                    rejected=[],
                    idempotency_key_used=idempotency_key,
                )

        # Normalize events
        norm_events = [_normalize_activity_event(e, uid) for e in input]

        # Ingest batch
        (
            accepted,
            duplicates,
            rejected,
        ) = activity_repo.ingest_batch(norm_events)

        # Cache success result if idempotency_key provided
        if idempotency_key and sig is not None and not rejected:
            activity_repo.store_idempotency(idempotency_key, sig, ttl_seconds=3600 * 24)

        return IngestActivityResult(
            accepted=accepted,
            duplicates=duplicates,
            rejected=[RejectedActivityEvent(index=i, reason=r) for i, r in rejected],
            idempotency_key_used=idempotency_key,
        )


__all__ = ["ActivityMutations"]
