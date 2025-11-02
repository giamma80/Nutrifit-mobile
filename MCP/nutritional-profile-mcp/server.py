#!/usr/bin/env python3
"""
Nutrifit Nutritional Profile MCP Server

Exposes nutritional profile management and progress tracking
through the Model Context Protocol.

IMPORTANT FOR AI ASSISTANTS:
==========================
This server provides 5 tools for nutritional profile management:

1. get_nutritional_profile(userId) - Get complete profile with BMR/TDEE
2. get_progress_score(userId, startDate, endDate) - Analyze progress
3. create_nutritional_profile(...) - Initial setup with auto-calculations
4. update_nutritional_profile(profileId, ...) - Update existing profile
5. record_progress(profileId, date, weight, ...) - Log daily progress

CRITICAL ENUM VALUES (from GraphQL schema):
- sex: "M" or "F" (NOT "MALE"/"FEMALE")
- activityLevel: "SEDENTARY", "LIGHT", "MODERATE", "ACTIVE", "VERY_ACTIVE"
  (NOT "LIGHTLY_ACTIVE", "MODERATELY_ACTIVE", "EXTRA_ACTIVE")
- goal: "CUT", "MAINTAIN", "BULK" (uppercase)

WORKFLOW BEST PRACTICES:
1. Start: create_nutritional_profile with user data
2. Daily: record_progress with weight + calories
3. Weekly: get_progress_score for adherence analysis
4. As needed: update_nutritional_profile when goals change

PARAMETER REQUIREMENTS:
- Dates: YYYY-MM-DD format (e.g., "2025-11-01")
- All dates in progress_score are REQUIRED (startDate, endDate)
- update requires profileId (NOT userId)
- record_progress requires profileId (NOT userId)
"""

import asyncio
import json
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.types import TextContent, Tool

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
app = Server("nutrifit-nutritional-profile")
gql_client = GraphQLClient(GRAPHQL_ENDPOINT)


# Define tools
@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available nutritional profile tools"""
    return [
        Tool(
            name="get_nutritional_profile",
            description="""
Get complete nutritional profile for a user.

Returns:
- Basic info: age, sex (M/F), height, current weight, goal weight
- Activity level: SEDENTARY/LIGHT/MODERATE/ACTIVE/VERY_ACTIVE
- Goal type: CUT (weight loss) | MAINTAIN | BULK (muscle gain)
- Calculated metrics:
  * BMR (Basal Metabolic Rate) - Mifflin-St Jeor formula
  * TDEE (Total Daily Energy Expenditure) - BMR * activity multiplier
  * Daily calorie target (TDEE ± goal adjustment)
- Macro split: Protein, carbs, fat in grams
- Micronutrient goals: Vitamins, minerals
- Current progress: Weight change, adherence rate

Use for:
- Initial profile setup review
- Checking current targets
- Verifying calculations
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "string",
                        "description": "User ID"
                    },
                },
                "required": ["userId"],
            },
        ),
        Tool(
            name="get_progress_score",
            description="""
Analyze progress toward nutritional goals over a date range.

Returns detailed statistics:
- Weight change (delta in kg)
- Average daily calories consumed
- Average calories burned (from activity)
- Average calorie deficit/surplus
- Adherence metrics:
  * Days on track (within tolerance)
  * Adherence rate percentage
  * Total days analyzed
- Macro adherence: Protein, carbs, fat targets vs actual

Useful for:
- Weekly/monthly progress reports
- Goal achievement analysis
- Identifying adherence patterns
- Adjusting targets based on results

Date range defaults to last 30 days if not specified.
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
                        "description": "Start date (YYYY-MM-DD format, e.g., '2025-10-01')"
                    },
                    "endDate": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD format, e.g., '2025-10-31')"
                    },
                },
                "required": ["userId", "startDate", "endDate"],
            },
        ),
        Tool(
            name="create_nutritional_profile",
            description="""
Create initial nutritional profile for a user.

⚠️ CRITICAL: Use EXACT enum values from schema:
- gender: "M" or "F" (NOT "MALE", "FEMALE", "OTHER")
- activityLevel: "SEDENTARY", "LIGHT", "MODERATE", "ACTIVE", "VERY_ACTIVE"
  ❌ WRONG: "LIGHTLY_ACTIVE", "MODERATELY_ACTIVE", "EXTRA_ACTIVE"
- goalType: "CUT", "MAINTAIN", "BULK" (uppercase)

Required inputs:
- age, gender (M/F), height, currentWeight
- activityLevel: SEDENTARY | LIGHT | MODERATE | ACTIVE | VERY_ACTIVE
- goalType: CUT | MAINTAIN | BULK
- goalWeight (optional for MAINTAIN)

Calculations performed automatically:
1. BMR using Mifflin-St Jeor equation:
   - Men: 10*weight + 6.25*height - 5*age + 5
   - Women: 10*weight + 6.25*height - 5*age - 161

2. TDEE = BMR * activity multiplier:
   - SEDENTARY: 1.2
   - LIGHT: 1.375
   - MODERATE: 1.55
   - ACTIVE: 1.725
   - VERY_ACTIVE: 1.9

3. Daily calorie target:
   - CUT: TDEE - 500 (safe deficit)
   - MAINTAIN: TDEE
   - BULK: TDEE + 300 (lean bulk)

4. Macro split (default balanced):
   - Protein: 30%
   - Carbs: 40%
   - Fat: 30%

Returns created profile with all calculated values.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "userId": {
                        "type": "string",
                        "description": "User ID"
                    },
                    "age": {"type": "integer", "minimum": 10, "maximum": 120},
                    "gender": {
                        "type": "string",
                        "enum": ["M", "F"],
                        "description": "Sex (M or F)"
                    },
                    "height": {
                        "type": "number",
                        "description": "Height in cm"
                    },
                    "currentWeight": {
                        "type": "number",
                        "description": "Current weight in kg"
                    },
                    "goalWeight": {
                        "type": "number",
                        "description": "Goal weight in kg (optional for MAINTAIN)"
                    },
                    "activityLevel": {
                        "type": "string",
                        "enum": [
                            "SEDENTARY",
                            "LIGHT",
                            "MODERATE",
                            "ACTIVE",
                            "VERY_ACTIVE",
                        ],
                        "description": "Activity level"
                    },
                    "goalType": {
                        "type": "string",
                        "enum": ["CUT", "MAINTAIN", "BULK"],
                    },
                },
                "required": [
                    "userId",
                    "age",
                    "gender",
                    "height",
                    "currentWeight",
                    "activityLevel",
                    "goalType",
                ],
            },
        ),
        Tool(
            name="update_nutritional_profile",
            description="""
Update existing nutritional profile.

Updatable fields:
- currentWeight: Triggers recalculation of BMR/TDEE/targets
- height, age, gender: Update user data
- activityLevel: Update activity multiplier
- goalType: Change CUT/MAINTAIN/BULK strategy

Calculations are automatically updated when relevant fields change.

Use cases:
- Weight check-in: Update currentWeight
- Activity change: e.g., started gym (SEDENTARY → MODERATE)
- Goal adjustment: Switch from CUT to MAINTAIN

Returns updated profile with recalculated values.

Note: To update userData, provide all 5 fields (weight, height, age, sex, activityLevel)
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "profileId": {
                        "type": "string",
                        "description": "Profile ID"
                    },
                    "currentWeight": {
                        "type": "number",
                        "description": "Current weight in kg"
                    },
                    "height": {
                        "type": "number",
                        "description": "Height in cm"
                    },
                    "age": {
                        "type": "integer",
                        "description": "Age in years"
                    },
                    "gender": {
                        "type": "string",
                        "enum": ["M", "F"],
                        "description": "Sex (M or F)"
                    },
                    "activityLevel": {
                        "type": "string",
                        "enum": [
                            "SEDENTARY",
                            "LIGHT",
                            "MODERATE",
                            "ACTIVE",
                            "VERY_ACTIVE",
                        ],
                        "description": "Activity level"
                    },
                    "goalType": {
                        "type": "string",
                        "enum": ["CUT", "MAINTAIN", "BULK"],
                        "description": "Nutrition goal"
                    },
                },
                "required": ["profileId"],
            },
        ),
        Tool(
            name="record_progress",
            description="""
Record daily progress snapshot.

Input:
- profileId: Profile ID
- date: Progress date (YYYY-MM-DD)
- weight: Current weight in kg
- consumedCalories: Total calories from meals (optional)
- consumedProtein/Carbs/Fat: Macros in grams (optional)
- caloriesBurnedBmr: BMR calories (optional)
- caloriesBurnedActive: Activity calories (optional)
- notes: Optional notes

This creates a progress record used for:
- Weight trend analysis
- Calorie deficit tracking
- Macro adherence monitoring
- Progress score calculations

Typical workflow:
1. User logs meals throughout the day
2. User syncs activity data
3. At EOD, call recordProgress with totals
4. System stores progress snapshot

Integration with other domains:
- Meal domain provides consumed calories/macros
- Activity domain provides calories burned
- This mutation ties them together for progress tracking
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "profileId": {
                        "type": "string",
                        "description": "Profile ID"
                    },
                    "date": {
                        "type": "string",
                        "description": "Progress date (YYYY-MM-DD)"
                    },
                    "weight": {
                        "type": "number",
                        "description": "Weight in kg"
                    },
                    "caloriesConsumed": {
                        "type": "number",
                        "description": "Total calories from meals"
                    },
                    "consumedProtein": {
                        "type": "number",
                        "description": "Protein consumed in grams"
                    },
                    "consumedCarbs": {
                        "type": "number",
                        "description": "Carbs consumed in grams"
                    },
                    "consumedFat": {
                        "type": "number",
                        "description": "Fat consumed in grams"
                    },
                    "caloriesBurnedBmr": {
                        "type": "number",
                        "description": "BMR calories burned"
                    },
                    "caloriesBurnedActive": {
                        "type": "number",
                        "description": "Active calories burned"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes"
                    },
                },
                "required": ["profileId", "date", "weight"],
            },
        ),
    ]


# Tool call handlers
@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""

    if name == "get_nutritional_profile":
        user_id = arguments["userId"]

        query = """
        query GetNutritionalProfile($userId: String!) {
            nutritionalProfile {
                nutritionalProfile(userId: $userId) {
                    profileId
                    userId
                    userData {
                        weight
                        height
                        age
                        sex
                        activityLevel
                    }
                    goal
                    bmr {
                        value
                    }
                    tdee {
                        value
                        activityLevel
                    }
                    caloriesTarget
                    macroSplit {
                        proteinG
                        carbsG
                        fatG
                    }
                    createdAt
                    updatedAt
                }
            }
        }
        """

        result = await gql_client.execute(query, {"userId": user_id})
        profile = result.get("nutritionalProfile", {}).get(
            "nutritionalProfile"
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(profile, indent=2),
            )
        ]

    elif name == "get_progress_score":
        user_id = arguments["userId"]
        start_date = arguments.get("startDate")
        end_date = arguments.get("endDate")

        query = """
        query GetProgressScore(
            $userId: String!
            $startDate: Date!
            $endDate: Date!
        ) {
            nutritionalProfile {
                progressScore(
                    userId: $userId
                    startDate: $startDate
                    endDate: $endDate
                ) {
                    startDate
                    endDate
                    weightDelta
                    avgDailyCalories
                    avgCaloriesBurned
                    avgDeficit
                    daysDeficitOnTrack
                    daysMacrosOnTrack
                    totalDays
                    adherenceRate
                }
            }
        }
        """

        variables = {"userId": user_id}
        if start_date:
            variables["startDate"] = start_date
        if end_date:
            variables["endDate"] = end_date

        result = await gql_client.execute(query, variables)
        score = result.get("nutritionalProfile", {}).get("progressScore")

        return [
            TextContent(
                type="text",
                text=json.dumps(score, indent=2),
            )
        ]

    elif name == "create_nutritional_profile":
        user_id = arguments["userId"]
        age = arguments["age"]
        sex = arguments["gender"]  # Map to 'sex' for schema
        height = arguments["height"]
        weight = arguments["currentWeight"]
        activity_level = arguments["activityLevel"]
        goal = arguments["goalType"]

        mutation = """
        mutation CreateNutritionalProfile($input: CreateProfileInput!) {
            nutritionalProfile {
                createNutritionalProfile(input: $input) {
                    profileId
                    userId
                    userData {
                        weight
                        height
                        age
                        sex
                        activityLevel
                    }
                    goal
                    bmr {
                        value
                    }
                    tdee {
                        value
                        activityLevel
                    }
                    caloriesTarget
                    macroSplit {
                        proteinG
                        carbsG
                        fatG
                    }
                    createdAt
                }
            }
        }
        """

        input_data = {
            "userId": user_id,
            "userData": {
                "weight": weight,
                "height": height,
                "age": age,
                "sex": sex,
                "activityLevel": activity_level,
            },
            "goal": goal,
            "initialWeight": weight,
        }

        result = await gql_client.execute(
            mutation, {"input": input_data}
        )
        profile = result.get("nutritionalProfile", {}).get(
            "createNutritionalProfile"
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(profile, indent=2),
            )
        ]

    elif name == "update_nutritional_profile":
        profile_id = arguments["profileId"]
        
        # Build input based on provided fields
        input_data = {"profileId": profile_id}
        
        # Handle userData updates
        if any(k in arguments for k in ["currentWeight", "height", "age", 
                                         "gender", "activityLevel"]):
            user_data = {}
            if "currentWeight" in arguments:
                user_data["weight"] = arguments["currentWeight"]
            if "height" in arguments:
                user_data["height"] = arguments["height"]
            if "age" in arguments:
                user_data["age"] = arguments["age"]
            if "gender" in arguments:
                user_data["sex"] = arguments["gender"]
            if "activityLevel" in arguments:
                user_data["activityLevel"] = arguments["activityLevel"]
            
            # If partial userData, need to get current profile first
            # For now, require all userData fields
            if len(user_data) == 5:
                input_data["userData"] = user_data
        
        if "goalType" in arguments:
            input_data["goal"] = arguments["goalType"]

        mutation = """
        mutation UpdateNutritionalProfile($input: UpdateProfileInput!) {
            nutritionalProfile {
                updateNutritionalProfile(input: $input) {
                    profileId
                    userId
                    userData {
                        weight
                        height
                        age
                        sex
                        activityLevel
                    }
                    goal
                    bmr {
                        value
                    }
                    tdee {
                        value
                        activityLevel
                    }
                    caloriesTarget
                    macroSplit {
                        proteinG
                        carbsG
                        fatG
                    }
                    updatedAt
                }
            }
        }
        """

        result = await gql_client.execute(mutation, {"input": input_data})
        profile = result.get("nutritionalProfile", {}).get(
            "updateNutritionalProfile"
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(profile, indent=2),
            )
        ]

    elif name == "record_progress":
        profile_id = arguments["profileId"]
        date = arguments["date"]
        weight = arguments["weight"]
        consumed_calories = arguments.get("caloriesConsumed")
        consumed_protein = arguments.get("consumedProtein")
        consumed_carbs = arguments.get("consumedCarbs")
        consumed_fat = arguments.get("consumedFat")
        calories_burned_bmr = arguments.get("caloriesBurnedBmr")
        calories_burned_active = arguments.get("caloriesBurnedActive")
        notes = arguments.get("notes")

        mutation = """
        mutation RecordProgress($input: RecordProgressInput!) {
            nutritionalProfile {
                recordProgress(input: $input) {
                    date
                    weight
                    consumedCalories
                    consumedProteinG
                    consumedCarbsG
                    consumedFatG
                    caloriesBurnedBmr
                    caloriesBurnedActive
                    notes
                }
            }
        }
        """

        input_data = {
            "profileId": profile_id,
            "date": date,
            "weight": weight,
        }
        if consumed_calories is not None:
            input_data["consumedCalories"] = consumed_calories
        if consumed_protein is not None:
            input_data["consumedProteinG"] = consumed_protein
        if consumed_carbs is not None:
            input_data["consumedCarbsG"] = consumed_carbs
        if consumed_fat is not None:
            input_data["consumedFatG"] = consumed_fat
        if calories_burned_bmr is not None:
            input_data["caloriesBurnedBmr"] = calories_burned_bmr
        if calories_burned_active is not None:
            input_data["caloriesBurnedActive"] = calories_burned_active
        if notes is not None:
            input_data["notes"] = notes

        result = await gql_client.execute(mutation, {"input": input_data})
        progress = result.get("nutritionalProfile", {}).get("recordProgress")

        return [
            TextContent(
                type="text",
                text=json.dumps(progress, indent=2),
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
