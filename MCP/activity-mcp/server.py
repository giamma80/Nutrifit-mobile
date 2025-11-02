#!/usr/bin/env python3
"""
Nutrifit Activity MCP Server

Exposes activity tracking and health data synchronization capabilities
through the Model Context Protocol.

IMPORTANT FOR AI ASSISTANTS:
==========================
This server provides 5 tools for activity and health data:

1. get_activity_entries(...) - Query minute-by-minute activity data
2. get_activity_sync_entries(date, ...) - Daily delta sync
3. aggregate_activity_range(...) - Aggregated summaries (DAY/WEEK/MONTH)
4. sync_activity_events(events) - Batch sync minute data (IDEMPOTENT)
5. sync_health_totals(input) - Daily snapshot sync (IDEMPOTENT)

CRITICAL ENUM VALUES (from GraphQL schema):
- source: "APPLE_HEALTH", "GOOGLE_FIT", "MANUAL"
  ❌ WRONG: "HEALTHKIT", "GOOGLEFIT"
- groupBy: "DAY", "WEEK", "MONTH"
  (ActivityPeriodSummary grouping)

DATA MODELS:
- ActivityMinute: timestamp, steps, calories (minute-level)
- HealthTotalsDelta: date, stepsDelta, stepsTotal, caloriesOutDelta, caloriesOutTotal
- ActivityPeriodSummary: period, startDate, endDate, totalSteps, totalCalories

IDEMPOTENCY:
Both sync mutations support idempotencyKey for safe retries.
Always provide idempotencyKey when syncing from devices.

TYPICAL WORKFLOWS:
1. Device sync: sync_activity_events with minute data
2. Daily summary: sync_health_totals at end of day
3. Reporting: aggregate_activity_range for charts
4. Delta sync: get_activity_sync_entries for incremental updates

PARAMETER NOTES:
- Dates: "YYYY-MM-DD" format
- Timestamps: ISO 8601 format (e.g., "2025-11-01T10:30:00Z")
- Events array: each requires 'ts' field minimum
"""

import asyncio
import json
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.types import (
    TextContent,
    Tool,
)

# GraphQL endpoint
GRAPHQL_ENDPOINT = os.getenv(
    "GRAPHQL_ENDPOINT", "http://localhost:8080/graphql"
)


class GraphQLClient:
    """Async GraphQL client for Nutrifit backend"""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient(timeout=30.0)

    async def execute(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute GraphQL query/mutation"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = await self.client.post(self.endpoint, json=payload)
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                error_msg = "; ".join(
                    [e.get("message", str(e)) for e in result["errors"]]
                )
                raise Exception(f"GraphQL errors: {error_msg}")

            return result.get("data", {})
        except httpx.HTTPError as e:
            raise Exception(f"HTTP error: {str(e)}")

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Initialize server and GraphQL client
app = Server("nutrifit-activity")
gql_client = GraphQLClient(GRAPHQL_ENDPOINT)


# Define tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available activity tools"""
    return [
        Tool(
            name="get_activity_entries",
            description="""
Query granular activity and health events with flexible filtering.
Returns individual data points (steps, calories, heart rate, etc.)
within a date/time range.

Use cases:
- Hourly activity breakdown
- Step count tracking
- Calorie burn monitoring
- Heart rate analysis
- Health metric trends

Filters:
- userId: Required - user identifier
- startDate: YYYY-MM-DD (optional)
- endDate: YYYY-MM-DD (optional)
- source: APPLE_HEALTH | GOOGLE_FIT | MANUAL (optional)

Note: ActivityEvent contains optional fields (steps, caloriesOut, hrAvg)
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max entries (default 100)",
                        "default": 100
                    },
                    "after": {
                        "type": "string",
                        "description": "Cursor for pagination"
                    },
                    "before": {
                        "type": "string",
                        "description": "Cursor for pagination"
                    },
                    "userId": {
                        "type": "string",
                        "description": "Filter by user ID"
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_activity_sync_entries",
            description="""
Query daily health totals delta for a specific date.
Returns HealthTotalsDelta entries showing daily snapshots.

Use for:
- Getting daily activity summary
- Sync daily totals from device
- Minimizing data transfer (date-based queries)

Returns list of HealthTotalsDelta with:
- date, userId
- stepsDelta, stepsTotal
- caloriesDelta, caloriesTotal
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date (YYYY-MM-DD)"
                    },
                    "userId": {
                        "type": "string",
                        "description": "Filter by user ID"
                    },
                    "after": {
                        "type": "string",
                        "description": "Cursor for pagination"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max entries (default 200)",
                        "default": 200
                    },
                },
                "required": ["date"],
            },
        ),
        Tool(
            name="aggregate_activity_range",
            description="""
Get aggregated activity data with flexible grouping.
Perfect for dashboards, reports, and trend analysis.

Grouping options:
- DAY: Daily totals (steps/day, calories/day)
- WEEK: Weekly aggregates
- MONTH: Monthly summaries

Returns for each period:
- Total steps
- Total calories burned
- Total distance
- Active minutes
- Average heart rate
- Sleep duration

Use cases:
- "Show my steps this week"
- "Monthly calorie burn report"
- "Daily activity for the past 7 days"
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "string",
                        "description": "User ID"
                    },
                    "startDate": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "endDate": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                    },
                    "groupBy": {
                        "type": "string",
                        "enum": ["DAY", "WEEK", "MONTH"],
                        "description": "Aggregation period"
                    },
                },
                "required": ["userId", "startDate", "endDate", "groupBy"],
            },
        ),
        Tool(
            name="sync_activity_events",
            description="""
Batch sync minute-by-minute activity events (idempotent).

Input format:
- Array of ActivityMinuteInput objects
- Each event: ts (timestamp), steps, caloriesOut, hrAvg, source
- Idempotency supported via idempotencyKey

Returns:
- accepted: Number of events processed
- duplicates: Number of duplicate events
- rejected: Array of rejected events with reasons
- idempotencyKeyUsed: Key used for idempotency

Use for:
- Device data synchronization (Apple Health, Google Fit)
- Batch import from fitness apps
- Manual data entry
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "string",
                        "description": "User ID (optional)"
                    },
                    "idempotencyKey": {
                        "type": "string",
                        "description": "Idempotency key (optional)"
                    },
                    "events": {
                        "type": "array",
                        "description": "Activity minute events",
                        "items": {
                            "type": "object",
                            "properties": {
                                "ts": {
                                    "type": "string",
                                    "description": "ISO timestamp"
                                },
                                "steps": {
                                    "type": "integer",
                                    "description": "Steps count",
                                    "default": 0
                                },
                                "caloriesOut": {
                                    "type": "number",
                                    "description": "Calories burned"
                                },
                                "hrAvg": {
                                    "type": "number",
                                    "description": "Average heart rate"
                                },
                                "source": {
                                    "type": "string",
                                    "enum": [
                                        "APPLE_HEALTH",
                                        "GOOGLE_FIT",
                                        "MANUAL"
                                    ],
                                    "default": "MANUAL"
                                },
                            },
                            "required": ["ts"],
                        },
                    },
                },
                "required": ["events"],
            },
        ),
        Tool(
            name="sync_health_totals",
            description="""
Sync daily health totals snapshot (idempotent).

Input: HealthTotalsInput
- timestamp: ISO timestamp
- date: Date (YYYY-MM-DD)
- steps: Total steps for the day
- caloriesOut: Total calories burned
- hrAvgSession: Average HR (optional)
- userId: User ID (optional)

Returns:
- accepted: Boolean (snapshot accepted)
- duplicate: Boolean (already exists)
- reset: Boolean (replaced existing)
- idempotencyKeyUsed: Key used
- idempotencyConflict: Conflict detected
- delta: HealthTotalsDelta with cumulative totals

Typical workflow:
1. Device provides end-of-day totals
2. Call this mutation to store snapshot (idempotent)
3. Query with aggregateRange for reporting

Difference from syncActivityEvents:
- syncActivityEvents: Minute-by-minute data
- syncHealthTotals: Daily cumulative snapshot
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "object",
                        "description": "Health totals input",
                        "properties": {
                            "timestamp": {
                                "type": "string",
                                "description": "ISO timestamp"
                            },
                            "date": {
                                "type": "string",
                                "description": "Date (YYYY-MM-DD)"
                            },
                            "steps": {
                                "type": "integer",
                                "description": "Total steps"
                            },
                            "caloriesOut": {
                                "type": "number",
                                "description": "Total calories burned"
                            },
                            "hrAvgSession": {
                                "type": "number",
                                "description": "Average heart rate"
                            },
                            "userId": {
                                "type": "string",
                                "description": "User ID"
                            },
                        },
                        "required": ["timestamp", "date", "steps", "caloriesOut"],
                    },
                    "idempotencyKey": {
                        "type": "string",
                        "description": "Idempotency key (optional)"
                    },
                    "userId": {
                        "type": "string",
                        "description": "User ID override (optional)"
                    },
                },
                "required": ["input"],
            },
        ),
    ]


# Tool call handlers
@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""

    if name == "get_activity_entries":
        limit = arguments.get("limit", 100)
        after = arguments.get("after")
        before = arguments.get("before")
        user_id = arguments.get("userId")

        query = """
        query GetActivityEntries(
            $limit: Int!
            $after: String
            $before: String
            $userId: String
        ) {
            activity {
                entries(
                    limit: $limit
                    after: $after
                    before: $before
                    userId: $userId
                ) {
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

        variables = {"limit": limit}
        if after:
            variables["after"] = after
        if before:
            variables["before"] = before
        if user_id:
            variables["userId"] = user_id

        result = await gql_client.execute(query, variables)
        entries = result.get("activity", {}).get("entries", [])

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "entries": entries,
                        "count": len(entries),
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "get_activity_sync_entries":
        date = arguments["date"]
        user_id = arguments.get("userId")
        after = arguments.get("after")
        limit = arguments.get("limit", 200)

        query = """
        query SyncActivityEntries(
            $date: String!
            $userId: String
            $after: String
            $limit: Int!
        ) {
            activity {
                syncEntries(
                    date: $date
                    userId: $userId
                    after: $after
                    limit: $limit
                ) {
                    date
                    userId
                    stepsDelta
                    stepsTotal
                    caloriesOutDelta
                    caloriesOutTotal
                }
            }
        }
        """

        variables = {"date": date, "limit": limit}
        if user_id:
            variables["userId"] = user_id
        if after:
            variables["after"] = after

        result = await gql_client.execute(query, variables)
        sync_result = result.get("activity", {}).get("syncEntries", [])

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "entries": sync_result,
                        "count": len(sync_result),
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "aggregate_activity_range":
        user_id = arguments["userId"]
        start_date = arguments["startDate"]
        end_date = arguments["endDate"]
        group_by = arguments["groupBy"]

        query = """
        query AggregateActivityRange(
            $userId: String!
            $startDate: String!
            $endDate: String!
            $groupBy: GroupByPeriod!
        ) {
            activity {
                aggregateRange(
                    userId: $userId
                    startDate: $startDate
                    endDate: $endDate
                    groupBy: $groupBy
                ) {
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
                    }
                    total {
                        period
                        startDate
                        endDate
                        totalSteps
                        totalCaloriesOut
                        totalActiveMinutes
                        avgHeartRate
                        eventCount
                        hasActivity
                    }
                }
            }
        }
        """

        result = await gql_client.execute(
            query,
            {
                "userId": user_id,
                "startDate": start_date,
                "endDate": end_date,
                "groupBy": group_by,
            },
        )
        range_result = result.get("activity", {}).get(
            "aggregateRange", {}
        )
        aggregates = range_result.get("periods", [])

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "periods": aggregates,
                        "total": range_result.get("total", {}),
                        "periodCount": len(aggregates),
                    },
                    indent=2,
                ),
            )
        ]

    elif name == "sync_activity_events":
        user_id = arguments.get("userId")
        events = arguments["events"]
        idempotency_key = arguments.get("idempotencyKey")

        # Convert events to ActivityMinuteInput format
        activity_minutes = []
        for event in events:
            activity_minutes.append({
                "ts": event.get("startTime") or event.get("ts"),
                "steps": event.get("steps", 0),
                "caloriesOut": event.get("caloriesOut"),
                "hrAvg": event.get("hrAvg"),
                "source": event.get("source", "MANUAL"),
            })

        mutation = """
        mutation SyncActivityEvents(
            $input: [ActivityMinuteInput!]!
            $idempotencyKey: String
            $userId: String
        ) {
            activity {
                syncActivityEvents(
                    input: $input
                    idempotencyKey: $idempotencyKey
                    userId: $userId
                ) {
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

        variables = {"input": activity_minutes}
        if idempotency_key:
            variables["idempotencyKey"] = idempotency_key
        if user_id:
            variables["userId"] = user_id

        result = await gql_client.execute(mutation, variables)
        sync_result = result.get("activity", {}).get(
            "syncActivityEvents", {}
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(sync_result, indent=2),
            )
        ]

    elif name == "sync_health_totals":
        input_data = arguments["input"]
        idempotency_key = arguments.get("idempotencyKey")
        user_id = arguments.get("userId")

        mutation = """
        mutation SyncHealthTotals(
            $input: HealthTotalsInput!
            $idempotencyKey: String
            $userId: String
        ) {
            syncHealthTotals(
                input: $input
                idempotencyKey: $idempotencyKey
                userId: $userId
            ) {
                accepted
                duplicate
                reset
                idempotencyKeyUsed
                idempotencyConflict
                delta {
                    date
                    userId
                    stepsDelta
                    stepsTotal
                    caloriesOutDelta
                    caloriesOutTotal
                }
            }
        }
        """

        variables = {"input": input_data}
        if idempotency_key:
            variables["idempotencyKey"] = idempotency_key
        if user_id:
            variables["userId"] = user_id

        result = await gql_client.execute(mutation, variables)
        sync_result = result.get("syncHealthTotals", {})

        return [
            TextContent(
                type="text",
                text=json.dumps(sync_result, indent=2),
            )
        ]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
