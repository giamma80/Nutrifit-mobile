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
    """Query minute-level activity events with filtering.
    
    Returns individual data points (steps, calories, heart rate) within date range.
    Supports pagination via limit parameter.
    
    Args:
        input: Query filters (user_id required, others optional)
    
    Returns:
        List of activity events with optional fields (steps, caloriesOut, hrAvg)
    """
    query = """
    query GetActivityEntries($userId: ID!, $startDate: String, $endDate: String, $source: ActivitySource, $limit: Int) {
        activityEntries(userId: $userId, startDate: $startDate, endDate: $endDate, source: $source, first: $limit) {
            edges {
                node {
                    id
                    userId
                    timestamp
                    source
                    steps
                    caloriesOut
                    hrAvg
                }
            }
            pageInfo {
                hasNextPage
                hasPreviousPage
            }
        }
    }
    """
    data = await graphql_query(query, variables={
        "userId": input.user_id,
        "startDate": input.start_date,
        "endDate": input.end_date,
        "source": input.source,
        "limit": input.limit
    })
    return data["activityEntries"]


# Tool 2: Get Activity Sync Entries
@mcp.tool()
async def get_activity_sync_entries(user_id: str, date: str) -> dict:
    """Get daily delta sync for activity data.
    
    Returns changes (deltas) for specific date. Used for incremental sync.
    
    Args:
        user_id: User UUID
        date: Date in YYYY-MM-DD format
    
    Returns:
        HealthTotalsDelta with stepsDelta, caloriesOutDelta, and totals
    """
    query = """
    query GetActivitySyncEntries($userId: ID!, $date: String!) {
        activitySyncEntries(userId: $userId, date: $date) {
            date
            stepsDelta
            stepsTotal
            caloriesOutDelta
            caloriesOutTotal
            syncedAt
        }
    }
    """
    data = await graphql_query(query, variables={
        "userId": user_id,
        "date": date
    })
    return data["activitySyncEntries"]


# Tool 3: Aggregate Activity Range
class AggregateActivityRangeInput(BaseModel):
    """Input for aggregate_activity_range."""
    user_id: str = Field(description="User UUID")
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str = Field(description="End date YYYY-MM-DD")
    group_by: str = Field("DAY", description="Grouping: DAY | WEEK | MONTH")


@mcp.tool()
async def aggregate_activity_range(input: AggregateActivityRangeInput) -> dict:
    """Get aggregated activity summaries for date range.
    
    Returns summary statistics grouped by DAY, WEEK, or MONTH.
    Optimized for charts and reports.
    
    Args:
        input: Date range and grouping parameters
    
    Returns:
        List of ActivityPeriodSummary with totalSteps, totalCalories per period
    """
    query = """
    query AggregateActivityRange($userId: ID!, $startDate: String!, $endDate: String!, $groupBy: ActivityGroupBy!) {
        aggregateActivityRange(userId: $userId, startDate: $startDate, endDate: $endDate, groupBy: $groupBy) {
            period
            startDate
            endDate
            totalSteps
            totalCalories
            avgHeartRate
        }
    }
    """
    data = await graphql_query(query, variables={
        "userId": input.user_id,
        "startDate": input.start_date,
        "endDate": input.end_date,
        "groupBy": input.group_by
    })
    return data["aggregateActivityRange"]


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
    """Batch sync minute-level activity data from devices.
    
    IDEMPOTENT: Provide idempotency_key for safe retries.
    Use for syncing step count, calories, heart rate from HealthKit/GoogleFit.
    
    Args:
        input: User ID, events array, source, optional idempotency key
    
    Returns:
        Sync confirmation with count of inserted/updated events
    """
    query = """
    mutation SyncActivityEvents($userId: ID!, $events: [ActivityEventInput!]!, $source: ActivitySource!, $idempotencyKey: String) {
        syncActivityEvents(userId: $userId, events: $events, source: $source, idempotencyKey: $idempotencyKey) {
            success
            insertedCount
            updatedCount
        }
    }
    """
    # Convert snake_case to camelCase for GraphQL
    events_graphql = [
        {
            "timestamp": e.timestamp,
            "steps": e.steps,
            "caloriesOut": e.calories_out,
            "hrAvg": e.hr_avg
        }
        for e in input.events
    ]
    
    data = await graphql_query(query, variables={
        "userId": input.user_id,
        "events": events_graphql,
        "source": input.source,
        "idempotencyKey": input.idempotency_key
    })
    return data["syncActivityEvents"]


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
    mutation SyncHealthTotals($input: HealthTotalsDeltaInput!) {
        syncHealthTotals(input: $input) {
            date
            stepsDelta
            stepsTotal
            caloriesOutDelta
            caloriesOutTotal
            syncedAt
        }
    }
    """
    # Build GraphQL input with camelCase
    graphql_input = {
        "userId": input.user_id,
        "date": input.date,
        "stepsDelta": input.steps_delta,
        "stepsTotal": input.steps_total,
        "caloriesOutDelta": input.calories_delta,
        "caloriesOutTotal": input.calories_total,
        "source": input.source
    }
    if input.idempotency_key:
        graphql_input["idempotencyKey"] = input.idempotency_key
    
    data = await graphql_query(query, variables={"input": graphql_input})
    return data["syncHealthTotals"]


if __name__ == "__main__":
    mcp.run()
