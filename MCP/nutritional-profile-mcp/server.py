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
                    "user_id": {
                        "type": "string",
                        "description": "User ID"
                    },
                },
                "required": ["user_id"],
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
                    "user_id": {
                        "type": "string",
                        "description": "User ID"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD format, e.g., '2025-10-01')"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD format, e.g., '2025-10-31')"
                    },
                },
                "required": ["user_id", "start_date", "end_date"],
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
                    "user_id": {
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
                    "current_weight": {
                        "type": "number",
                        "description": "Current weight in kg"
                    },
                    "goal_weight": {
                        "type": "number",
                        "description": "Goal weight in kg (optional for MAINTAIN)"
                    },
                    "activity_level": {
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
                    "goal_type": {
                        "type": "string",
                        "enum": ["CUT", "MAINTAIN", "BULK"],
                    },
                },
                "required": [
                    "user_id",
                    "age",
                    "gender",
                    "height",
                    "current_weight",
                    "activity_level",
                    "goal_type",
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
                    "profile_id": {
                        "type": "string",
                        "description": "Profile ID"
                    },
                    "current_weight": {
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
                    "activity_level": {
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
                    "goal_type": {
                        "type": "string",
                        "enum": ["CUT", "MAINTAIN", "BULK"],
                        "description": "Nutrition goal"
                    },
                },
                "required": ["profile_id"],
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
                    "profile_id": {
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
                    "calories_consumed": {
                        "type": "number",
                        "description": "Total calories from meals"
                    },
                    "consumed_protein": {
                        "type": "number",
                        "description": "Protein consumed in grams"
                    },
                    "consumed_carbs": {
                        "type": "number",
                        "description": "Carbs consumed in grams"
                    },
                    "consumed_fat": {
                        "type": "number",
                        "description": "Fat consumed in grams"
                    },
                    "calories_burned_bmr": {
                        "type": "number",
                        "description": "BMR calories burned"
                    },
                    "calories_burned_active": {
                        "type": "number",
                        "description": "Active calories burned"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes"
                    },
                },
                "required": ["profile_id", "date", "weight"],
            },
        ),
        Tool(
            name="forecast_weight",
            description="""
🤖 ML-POWERED: Generate future weight predictions using time series models.

Advanced forecasting with 4 adaptive models:
- SimpleTrend (<7 data points): Linear extrapolation
- LinearRegression (7-13 points): OLS with prediction intervals
- ExponentialSmoothing (14-29 points): Holt's method
- ARIMA(1,1,1) (30+ points): Full time series modeling

Returns:
- Model used (automatic selection based on data)
- Confidence level (68%, 95%, or 99%)
- Data points used (number of progress records)
- Trend analysis:
  * Direction: "decreasing", "increasing", or "stable"
  * Magnitude: Change in kg (first to last prediction)
  * Stable threshold: ±0.5 kg
- Daily predictions with confidence intervals:
  * Predicted weight
  * Lower bound (confidence interval)
  * Upper bound (confidence interval)

Trend insights:
- "decreasing": Weight loss trend (CUT goal on track)
- "stable": Plateau detected (consider calorie adjustment)
- "increasing": Weight gain trend (BULK goal or review deficit)

Use cases:
- Goal prediction: "When will I reach target weight?"
- Progress validation: "Am I on the right track?"
- Plateau detection: "Why isn't my weight changing?"
- Motivation: Visualize future progress

Requirements:
- Minimum 2 progress records in profile
- Records must have chronological dates
- All weights must be positive

Performance: 30-170ms response time
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {
                        "type": "string",
                        "description": "Profile ID"
                    },
                    "days_ahead": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 90,
                        "default": 30,
                        "description": "Number of days to forecast (1-90, default: 30)"
                    },
                    "confidence_level": {
                        "type": "number",
                        "enum": [0.68, 0.95, 0.99],
                        "default": 0.95,
                        "description": "Confidence level for intervals (0.68=1σ, 0.95=2σ, 0.99=3σ)"
                    },
                },
                "required": ["profile_id"],
            },
        ),
    ]


# Tool call handlers
@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""

    if name == "get_nutritional_profile":
        user_id = arguments["user_id"]

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
        user_id = arguments["user_id"]
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")

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
        user_id = arguments["user_id"]
        age = arguments["age"]
        sex = arguments["gender"]  # Map to 'sex' for schema
        height = arguments["height"]
        weight = arguments["current_weight"]
        activity_level = arguments["activity_level"]
        goal = arguments["goal_type"]

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
        profile_id = arguments["profile_id"]
        
        # Build input based on provided fields
        input_data = {"profileId": profile_id}
        
        # Handle userData updates
        if any(k in arguments for k in ["current_weight", "height", "age", 
                                         "gender", "activity_level"]):
            user_data = {}
            if "current_weight" in arguments:
                user_data["weight"] = arguments["current_weight"]
            if "height" in arguments:
                user_data["height"] = arguments["height"]
            if "age" in arguments:
                user_data["age"] = arguments["age"]
            if "gender" in arguments:
                user_data["sex"] = arguments["gender"]
            if "activity_level" in arguments:
                user_data["activityLevel"] = arguments["activity_level"]
            
            # If partial userData, need to get current profile first
            # For now, require all userData fields
            if len(user_data) == 5:
                input_data["userData"] = user_data
        
        if "goal_type" in arguments:
            input_data["goal"] = arguments["goal_type"]

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
        profile_id = arguments["profile_id"]
        date = arguments["date"]
        weight = arguments["weight"]
        consumed_calories = arguments.get("calories_consumed")
        consumed_protein = arguments.get("consumed_protein")
        consumed_carbs = arguments.get("consumed_carbs")
        consumed_fat = arguments.get("consumed_fat")
        calories_burned_bmr = arguments.get("calories_burned_bmr")
        calories_burned_active = arguments.get("calories_burned_active")
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

    elif name == "forecast_weight":
        profile_id = arguments.get("profile_id")
        days_ahead = arguments.get("days_ahead", 30)
        confidence_level = arguments.get("confidence_level", 0.95)

        query = """
        query ForecastWeight($profileId: ID!, $daysAhead: Int!, $confidenceLevel: Float!) {
            nutritionalProfile(id: $profileId) {
                id
                forecastWeight(daysAhead: $daysAhead, confidenceLevel: $confidenceLevel) {
                    modelUsed
                    confidenceLevel
                    dataPointsUsed
                    trendDirection
                    trendMagnitude
                    predictions {
                        date
                        predictedWeight
                        lowerBound
                        upperBound
                    }
                }
            }
        }
        """

        variables = {
            "profileId": profile_id,
            "daysAhead": days_ahead,
            "confidenceLevel": confidence_level,
        }

        result = await gql_client.execute(query, variables)

        profile = result.get("nutritionalProfile")

        if not profile:
            raise ValueError(f"Profile not found: {profile_id}")

        forecast = profile.get("forecastWeight")

        if not forecast:
            raise ValueError("No forecast data available (insufficient progress records)")

        # Trend interpretation
        trend_emoji = {
            "decreasing": "📉",
            "stable": "➡️",
            "increasing": "📈"
        }

        trend_desc = {
            "decreasing": "Weight loss trend - on track for CUT goal",
            "stable": "Plateau detected - consider adjusting calorie intake",
            "increasing": "Weight gain trend - check if intentional (BULK)"
        }

        direction = forecast["trendDirection"]
        magnitude = forecast["trendMagnitude"]

        # Format predictions table
        predictions_text = "\n".join([
            f"  Day {i+1:2d} ({p['date']}): "
            f"{p['predictedWeight']:.2f} kg "
            f"[{p['lowerBound']:.2f} - {p['upperBound']:.2f}]"
            for i, p in enumerate(forecast["predictions"][:7])  # Show first week
        ])

        if len(forecast["predictions"]) > 7:
            predictions_text += f"\n  ... ({len(forecast['predictions']) - 7} more days)"

        # Format the response
        response = f"""
🤖 ML Weight Forecast

📊 Model Analysis:
- Algorithm: {forecast['modelUsed']}
- Data points: {forecast['dataPointsUsed']} progress records
- Confidence: {int(forecast['confidenceLevel']*100)}%

{trend_emoji[direction]} Trend Analysis:
- Direction: {direction.upper()}
- Magnitude: {magnitude:+.2f} kg over {days_ahead} days
- Insight: {trend_desc[direction]}

📅 Predictions (first week):
{predictions_text}

💡 Interpretation:
- Predicted Weight: Most likely weight for each day
- Confidence Interval: Range where actual weight will likely fall
- Model Selection: Automatic based on data availability

{"⚠️ Note: Plateau detected. Consider:" if direction == "stable" else ""}
{"  - Review calorie intake vs TDEE" if direction == "stable" else ""}
{"  - Adjust macro distribution" if direction == "stable" else ""}
{"  - Check activity levels" if direction == "stable" else ""}

Use this forecast to:
- Set realistic expectations
- Validate goal timeline
- Detect plateaus early
- Adjust strategy proactively
"""

        return [
            TextContent(
                type="text",
                text=response,
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
