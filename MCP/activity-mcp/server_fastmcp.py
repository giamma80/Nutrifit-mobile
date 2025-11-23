#!/usr/bin/env python3
"""
Nutrifit Activity MCP Server (FastMCP)

Activity tracking and health data synchronization via Model Context Protocol.
Refactored with FastMCP for type-safe, concise tool definitions.

IMPORTANT FOR AI ASSISTANTS:
==========================
5 tools for activity and health data:

📊 QUERIES:
1. get_activity_entries(user_id, start_date, end_date, source) - Minute-level data
2. get_activity_sync_entries(user_id, date) - Daily delta sync
3. aggregate_activity_range(user_id, start_date, end_date, group_by) - Summary stats

🔄 MUTATIONS (IDEMPOTENT):
4. sync_activity_events(user_id, events, idempotency_key) - Batch sync minutes
5. sync_health_totals(user_id, date, steps_delta, calories_delta, idempotency_key) - Daily snapshot

ENUM VALUES:
- source: "APPLE_HEALTH", "GOOGLE_FIT", "MANUAL"
- group_by: "DAY", "WEEK", "MONTH"
"""

import os
from typing import Optional, List
from datetime import date

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field


# Configuration
GRAPHQL_ENDPOINT = os.getenv("GRAPHQL_ENDPOINT", "http://localhost:8080/graphql")
DEFAULT_TIMEOUT = 30.0

# Initialize FastMCP
mcp = FastMCP("Nutrifit Activity Tracking")


async def graphql_query(query: str, variables: Optional[dict] = None) -> dict:
    """Execute GraphQL query."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(GRAPHQL_ENDPOINT, json=payload)
        response.raise_for_status()
        result = response.json()

    if "errors" in result:
        errors = [err.get("message", str(err)) for err in result["errors"]]
        raise Exception(f"GraphQL errors: {'; '.join(errors)}")

    return result["data"]


# Tool 1: Get Activity Entries
class GetActivityEntriesInput(BaseModel):
    """Input for get_activity_entries."""
    user_id: str = Field(description="User UUID")
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD")
    source: Optional[str] = Field(None, description="APPLE_HEALTH | GOOGLE_FIT | MANUAL")
    limit: int = Field(100, description="Max entries per page")


@mcp.tool()
async def get_activity_entries(input: GetActivityEntriesInput) -> dict:
    """📊 Query minute-level activity events with filtering.
    
    Returns granular data points (steps, calories, heart rate) for detailed analysis.
    Use this for charts, detailed views, or exporting raw data.
    
    Args:
        input: Query filters
            - user_id: User UUID (required)
            - start_date: Start date YYYY-MM-DD (optional)
            - end_date: End date YYYY-MM-DD (optional)
            - source: Filter by source → APPLE_HEALTH | GOOGLE_FIT | MANUAL (optional)
            - limit: Max results (default 100, max 1000)
    
    Returns:
        Paginated activity events:
        - edges: Array of activity nodes
            * id, userId, timestamp, source
            * steps, caloriesOut, hrAvg (optional fields)
        - pageInfo: {hasNextPage, hasPreviousPage}
    
    Example:
        # Last week of HealthKit data
        entries = await get_activity_entries(
            user_id="uuid",
            start_date="2025-11-10",
            end_date="2025-11-17",
            source="APPLE_HEALTH",
            limit=500
        )
    """
    query = """
    query GetActivityEntries($userId: String, $limit: Int, $after: String, $before: String) {
        activity {
            entries(userId: $userId, limit: $limit, after: $after, before: $before) {
                userId
                ts
                steps
                caloriesOut
                hrAvg
                source
            }
        }
    }
    """
    variables = {"userId": input.user_id, "limit": input.limit}
    if input.start_date:
        variables["after"] = input.start_date
    if input.end_date:
        variables["before"] = input.end_date
    
    data = await graphql_query(query, variables=variables)
    return data["activity"]["entries"]


# Tool 2: Get Activity Sync Entries
@mcp.tool()
async def get_activity_sync_entries(user_id: str, date: str) -> dict:
    """🔄 Get daily delta sync for activity data (incremental sync).
    
    Returns CHANGES (deltas) for specific date since last sync.
    Use this for efficient real-time updates without re-fetching all data.
    
    Workflow:
    1. App syncs at 10:00 AM → stepsDelta: +3,500, stepsTotal: 3,500
    2. User walks more, syncs at 2:00 PM → stepsDelta: +1,200, stepsTotal: 4,700
    3. Each sync returns ONLY new data (delta) + current total
    
    Args:
        user_id: User UUID
        date: Date in YYYY-MM-DD format (typically today)
    
    Returns:
        HealthTotalsDelta for specified date:
        - date: Date queried
        - stepsDelta: Steps added since last sync
        - stepsTotal: Cumulative steps for the day
        - caloriesOutDelta: New calories burned
        - caloriesOutTotal: Total calories for the day
        - syncedAt: Last sync timestamp
    """
    query = """
    query GetActivitySyncEntries($date: String!, $userId: String, $after: String, $limit: Int) {
        activity {
            syncEntries(date: $date, userId: $userId, after: $after, limit: $limit) {
                id
                userId
                date
                timestamp
                stepsDelta
                caloriesOutDelta
                stepsTotal
                caloriesOutTotal
                hrAvgSession
            }
        }
    }
    """
    data = await graphql_query(query, variables={
        "userId": user_id,
        "date": date
    })
    return data["activity"]["syncEntries"]


# Tool 3: Aggregate Activity Range
class AggregateActivityRangeInput(BaseModel):
    """Input for aggregate_activity_range."""
    user_id: str = Field(description="User UUID")
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str = Field(description="End date YYYY-MM-DD")
    group_by: str = Field("DAY", description="Grouping: DAY | WEEK | MONTH")


@mcp.tool()
async def aggregate_activity_range(input: AggregateActivityRangeInput) -> dict:
    """📈 Get aggregated activity summaries for date range.
    
    Returns summary statistics grouped by DAY, WEEK, or MONTH.
    Optimized for charts, reports, and trend analysis.
    
    Use cases:
    - Daily view: Last 7 days with group_by=DAY
    - Weekly report: Last 3 months with group_by=WEEK
    - Monthly trends: Last year with group_by=MONTH
    
    Args:
        input: Date range and grouping
            - user_id: User UUID (required)
            - start_date: Start date YYYY-MM-DD (required)
            - end_date: End date YYYY-MM-DD (required)
            - group_by: Grouping → "DAY" | "WEEK" | "MONTH" (default: "DAY")
    
    Returns:
        Array of ActivityPeriodSummary:
        - period: Period label (e.g., "2025-W46" for week)
        - startDate, endDate: Period boundaries
        - totalSteps, totalCalories: Sums for period
        - avgHeartRate: Average HR (if available)
    
    Performance: Pre-aggregated data → fast queries even for large ranges.
    """
    query = """
    query AggregateActivityRange($userId: String!, $startDate: String!, $endDate: String!, $groupBy: GroupByPeriod!) {
        activity {
            aggregateRange(userId: $userId, startDate: $startDate, endDate: $endDate, groupBy: $groupBy) {
                periods {
                    period
                    startDate
                    endDate
                    totalSteps
                    totalCaloriesOut
                    totalActiveMinutes
                    avgHeartRate
                    eventCount
                    hasActivity
                    avgDailySteps
                }
                total {
                    period
                    startDate
                    endDate
                    totalSteps
                    totalCaloriesOut
                    totalActiveMinutes
                    avgHeartRate
                }
            }
        }
    }
    """
    data = await graphql_query(query, variables={
        "userId": input.user_id,
        "startDate": input.start_date,
        "endDate": input.end_date,
        "groupBy": input.group_by
    })
    return data["activity"]["aggregateRange"]


# Tool 4: Sync Activity Events
class ActivityEventInput(BaseModel):
    """Single activity event for sync."""
    timestamp: str = Field(description="ISO 8601 timestamp")
    steps: Optional[int] = Field(None, description="Step count")
    calories_out: Optional[float] = Field(None, description="Calories burned")
    hr_avg: Optional[int] = Field(None, description="Average heart rate")


class SyncActivityEventsInput(BaseModel):
    """Input for sync_activity_events."""
    user_id: str = Field(description="User UUID")
    events: List[ActivityEventInput] = Field(description="Activity events to sync")
    source: str = Field("MANUAL", description="APPLE_HEALTH | GOOGLE_FIT | MANUAL")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key for safe retries")


@mcp.tool()
async def sync_activity_events(input: SyncActivityEventsInput) -> dict:
    """⬆️ Batch sync minute-level activity events (IDEMPOTENT).
    
    ⚠️ USE THIS for syncing data from HealthKit/GoogleFit.
    Upload multiple activity data points at once with automatic deduplication.
    
    Idempotency guarantee:
    - Same idempotency_key → skips duplicate events
    - Safe to retry on network failure
    - Events matched by timestamp + user_id + source
    
    Workflow:
    1. Collect activity events from device
    2. Build events array with timestamps
    3. Generate unique idempotency_key (e.g., "healthkit-sync-20251117-143000")
    4. Call sync_activity_events
    5. If fails → retry with SAME idempotency_key
    
    Args:
        input: User ID, events array, source, optional idempotency key
    
    Returns:
        Sync confirmation with count of inserted/updated events
    """
    query = """
    mutation SyncActivityEvents($input: [ActivityMinuteInput!]!, $idempotencyKey: String, $userId: String) {
        activity {
            syncActivityEvents(input: $input, idempotencyKey: $idempotencyKey, userId: $userId) {
                accepted
                duplicates
                rejected {
                    index
                    reason
                }
                idempotencyKeyUsed
            }
        }
    }
    """
    # Convert snake_case to camelCase for GraphQL
    events_graphql = [
        {
            "ts": e.timestamp,
            "steps": e.steps or 0,
            "caloriesOut": e.calories_out,
            "hrAvg": e.hr_avg,
            "source": input.source
        }
        for e in input.events
    ]
    
    data = await graphql_query(query, variables={
        "userId": input.user_id,
        "input": events_graphql,
        "idempotencyKey": input.idempotency_key
    })
    return data["activity"]["syncActivityEvents"]


# Tool 5: Sync Health Totals
class SyncHealthTotalsInput(BaseModel):
    """Input for sync_health_totals."""
    user_id: str = Field(description="User UUID")
    date: str = Field(description="Date YYYY-MM-DD")
    steps_delta: int = Field(description="Step count change for this day")
    steps_total: int = Field(description="Total accumulated steps")
    calories_delta: float = Field(description="Calories burned change")
    calories_total: float = Field(description="Total accumulated calories")
    source: str = Field("MANUAL", description="APPLE_HEALTH | GOOGLE_FIT | MANUAL")
    idempotency_key: Optional[str] = Field(None, description="Idempotency key")


@mcp.tool()
async def sync_health_totals(input: SyncHealthTotalsInput) -> dict:
    """Sync daily health snapshot (end-of-day totals).
    
    IDEMPOTENT: Use idempotency_key for safe retries.
    Captures daily totals and deltas for dashboard summary.
    
    Args:
        input: Daily health data with deltas and totals
    
    Returns:
        HealthTotalsDelta confirmation
    """
    query = """
    mutation SyncHealthTotals($input: HealthTotalsInput!, $idempotencyKey: String, $userId: String) {
        syncHealthTotals(input: $input, idempotencyKey: $idempotencyKey, userId: $userId) {
            accepted
            duplicate
            reset
            idempotencyKeyUsed
            idempotencyConflict
            delta {
                id
                userId
                date
                timestamp
                stepsDelta
                caloriesOutDelta
                stepsTotal
                caloriesOutTotal
                hrAvgSession
            }
        }
    }
    """
    # Build GraphQL input with camelCase - HealthTotalsInput
    import datetime
    graphql_input = {
        "timestamp": datetime.datetime.now().isoformat(),
        "date": input.date,
        "steps": input.steps_total,
        "caloriesOut": input.calories_total,
        "hrAvgSession": None
    }
    
    data = await graphql_query(query, variables={
        "input": graphql_input,
        "idempotencyKey": input.idempotency_key,
        "userId": input.user_id
    })
    return data["syncHealthTotals"]


if __name__ == "__main__":
    mcp.run()
