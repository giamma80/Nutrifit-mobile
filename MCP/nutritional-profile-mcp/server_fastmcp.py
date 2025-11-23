#!/usr/bin/env python3
"""
Nutrifit Nutritional Profile MCP Server (FastMCP)

Profile management, progress tracking, and ML-powered weight forecasting.
Refactored with FastMCP for cleaner tool definitions.

IMPORTANT FOR AI ASSISTANTS:
==========================
6 tools for nutritional profile and progress:

👤 PROFILE MANAGEMENT:
1. get_nutritional_profile(user_id) - Get profile with BMR/TDEE calculations
2. create_nutritional_profile(user_id, current_weight, activity_level, goal_type) - Create profile
3. update_nutritional_profile(profile_id, current_weight, activity_level, goal_type) - Update profile

📊 PROGRESS TRACKING:
4. record_progress(user_id, date, weight, calories, macros, activity) - Daily log
5. get_progress_score(user_id, start_date, end_date) - Adherence analysis

🔮 ML FORECAST:
6. forecast_weight(profile_id, days_ahead, confidence_level) - AI weight prediction

ENUM VALUES:
- activity_level: "SEDENTARY", "LIGHTLY_ACTIVE", "MODERATELY_ACTIVE", "VERY_ACTIVE", "EXTRA_ACTIVE"
- goal_type: "LOSE_WEIGHT", "MAINTAIN_WEIGHT", "GAIN_WEIGHT"
"""

import os
from typing import Optional

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field


# Configuration
GRAPHQL_ENDPOINT = os.getenv("GRAPHQL_ENDPOINT", "http://localhost:8080/graphql")
DEFAULT_TIMEOUT = 30.0

# Initialize FastMCP
mcp = FastMCP("Nutrifit Nutritional Profile")


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


# Tool 1: Get Nutritional Profile
@mcp.tool()
async def get_nutritional_profile(user_id: str) -> dict:
    """Get user's nutritional profile with calculated BMR/TDEE.
    
    Returns complete profile including:
    - Current weight, height, age, gender
    - Activity level and goal type
    - Calculated BMR (Basal Metabolic Rate)
    - Calculated TDEE (Total Daily Energy Expenditure)
    - Target calories and macro ratios
    
    Args:
        user_id: User UUID
    
    Returns:
        NutritionalProfile with all metrics
    """
    query = """
    query GetNutritionalProfile($userId: String) {
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
                progressHistory {
                    date
                    weight
                    consumedCalories
                }
                createdAt
                updatedAt
            }
        }
    }
    """
    data = await graphql_query(query, variables={"userId": user_id})
    return data["nutritionalProfile"]["nutritionalProfile"]


# Tool 2: Create Nutritional Profile
class CreateNutritionalProfileInput(BaseModel):
    """Input for create_nutritional_profile."""
    user_id: str = Field(description="User UUID")
    current_weight: float = Field(description="Current weight in kg")
    target_weight: Optional[float] = Field(None, description="Target weight in kg")
    height: float = Field(description="Height in cm")
    age: int = Field(description="Age in years")
    gender: str = Field(description="MALE or FEMALE")
    activity_level: str = Field(description="SEDENTARY | LIGHTLY_ACTIVE | MODERATELY_ACTIVE | VERY_ACTIVE | EXTRA_ACTIVE")
    goal_type: str = Field(description="LOSE_WEIGHT | MAINTAIN_WEIGHT | GAIN_WEIGHT")


@mcp.tool()
async def create_nutritional_profile(input: CreateNutritionalProfileInput) -> dict:
    """👤 Create new nutritional profile with automatic BMR/TDEE calculation.
    
    ⚠️ REQUIRED before tracking meals and progress.
    Creates profile and automatically calculates personalized nutrition targets.
    
    Automatic calculations (Mifflin-St Jeor + Harris-Benedict):
    1. BMR (Basal Metabolic Rate) → calories at rest
    2. TDEE (Total Daily Energy Expenditure) → BMR × activity_level multiplier
    3. Target calories → TDEE ± deficit/surplus based on goal_type
    4. Macro ratios → protein/carbs/fat percentages
    
    Args:
        input: Profile data
            - user_id: User UUID (required)
            - current_weight: Weight in kg (required, e.g., 85.0)
            - target_weight: Goal weight in kg (optional, e.g., 75.0)
            - height: Height in cm (required, e.g., 175)
            - age: Age in years (required, e.g., 30)
            - gender: Biological gender (required)
                → "MALE" | "FEMALE"
            - activity_level: Physical activity level (required)
                → "SEDENTARY" (desk job, no exercise)
                → "LIGHT" (light exercise 1-3 days/week)
                → "MODERATE" (moderate exercise 3-5 days/week)
                → "ACTIVE" (hard exercise 6-7 days/week)
                → "VERY_ACTIVE" (very hard exercise, athlete)
            - goal_type: Weight goal (required)
                → "CUT" (calorie deficit for weight loss)
                → "MAINTAIN" (maintenance calories)
                → "BULK" (calorie surplus for muscle gain)
    
    Returns:
        Created profile with calculated metrics:
        - id: Profile UUID
        - userId, currentWeight, targetWeight, height, age, gender
        - activityLevel, goalType: Input values
        - bmr: Calculated resting metabolic rate
        - tdee: Calculated total daily energy
        - targetCalories: Daily calorie target
        - targetProteinRatio, targetCarbsRatio, targetFatRatio: Macro %
        - createdAt: Timestamp
    
    Example:
        profile = await create_nutritional_profile(
            user_id="uuid",
            current_weight=85.0,
            target_weight=75.0,
            height=175,
            age=30,
            gender="MALE",
            activity_level="MODERATE",
            goal_type="CUT"
        )
        # Returns: bmr=1800, tdee=2700, targetCalories=2200 (-500 deficit)
    """
    query = """
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
    graphql_input = {
        "userId": input.user_id,
        "userData": {
            "weight": input.current_weight,
            "height": input.height,
            "age": input.age,
            "sex": "M" if input.gender == "MALE" else "F",
            "activityLevel": input.activity_level
        },
        "goal": input.goal_type,  # No transformation - agent sends correct value
        "initialWeight": input.current_weight
    }
    data = await graphql_query(query, variables={"input": graphql_input})
    return data["nutritionalProfile"]["createNutritionalProfile"]


# Tool 3: Update Nutritional Profile
class UpdateNutritionalProfileInput(BaseModel):
    """Input for update_nutritional_profile."""
    profile_id: str = Field(description="Profile UUID")
    current_weight: Optional[float] = Field(None, description="Updated weight in kg")
    target_weight: Optional[float] = Field(None, description="Updated target weight")
    activity_level: Optional[str] = Field(None, description="Updated activity level")
    goal_type: Optional[str] = Field(None, description="Updated goal type")


@mcp.tool()
async def update_nutritional_profile(input: UpdateNutritionalProfileInput) -> dict:
    """Update nutritional profile and recalculate BMR/TDEE.
    
    Updates profile fields and automatically recalculates:
    - TDEE if activity level changes
    - Target calories if goal type changes
    
    All fields are optional - only provided fields are updated.
    
    Args:
        input: Profile updates (all optional)
            - profile_id: Profile UUID (required)
            - current_weight: New weight in kg (optional)
            - target_weight: New goal weight in kg (optional)
            - activity_level: New activity level (optional)
                → "SEDENTARY" | "LIGHT" | "MODERATE" | "ACTIVE" | "VERY_ACTIVE"
            - goal_type: New goal (optional)
                → "CUT" | "MAINTAIN" | "BULK"
    
    Returns:
        Updated NutritionalProfile with recalculated metrics
    """
    query = """
    mutation UpdateNutritionalProfile($input: UpdateProfileInput!) {
        nutritionalProfile {
            updateNutritionalProfile(input: $input) {
                profileId
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
                }
                caloriesTarget
                updatedAt
            }
        }
    }
    """
    graphql_input = {"profileId": input.profile_id}
    
    if input.current_weight or input.activity_level:
        user_data = {}
        if input.current_weight:
            user_data["weight"] = input.current_weight
        if input.activity_level:
            user_data["activityLevel"] = input.activity_level
        graphql_input["userData"] = user_data
    
    if input.goal_type:
        graphql_input["goal"] = input.goal_type  # No transformation - agent sends correct value
    
    data = await graphql_query(query, variables={"input": graphql_input})
    return data["nutritionalProfile"]["updateNutritionalProfile"]


# Tool 4: Record Progress
class RecordProgressInput(BaseModel):
    """Input for record_progress."""
    user_id: str = Field(description="User UUID")
    date: str = Field(description="Date YYYY-MM-DD")
    weight: Optional[float] = Field(None, description="Weight in kg")
    calories_consumed: Optional[float] = Field(None, description="Calories eaten")
    consumed_protein: Optional[float] = Field(None, description="Protein in grams")
    consumed_carbs: Optional[float] = Field(None, description="Carbs in grams")
    consumed_fat: Optional[float] = Field(None, description="Fat in grams")
    calories_burned_bmr: Optional[float] = Field(None, description="BMR calories")
    calories_burned_active: Optional[float] = Field(None, description="Activity calories")


@mcp.tool()
async def record_progress(input: RecordProgressInput) -> dict:
    """Record daily progress entry (weight, calories, macros, activity).
    
    Creates or updates progress log for specific date.
    Used for tracking adherence to nutritional goals.
    
    Args:
        input: Daily progress data (all fields optional except user_id and date)
    
    Returns:
        ProgressEntry confirmation
    """
    query = """
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
    
    # Need profileId - get it first from user
    profile_query = """
    query GetProfileId($userId: String) {
        nutritionalProfile {
            nutritionalProfile(userId: $userId) {
                profileId
            }
        }
    }
    """
    profile_data = await graphql_query(profile_query, variables={"userId": input.user_id})
    profile_id = profile_data["nutritionalProfile"]["nutritionalProfile"]["profileId"]
    
    graphql_input = {
        "profileId": profile_id,
        "date": input.date,
        "weight": input.weight or 0.0
    }
    if input.calories_consumed:
        graphql_input["consumedCalories"] = input.calories_consumed
    if input.consumed_protein:
        graphql_input["consumedProteinG"] = input.consumed_protein
    if input.consumed_carbs:
        graphql_input["consumedCarbsG"] = input.consumed_carbs
    if input.consumed_fat:
        graphql_input["consumedFatG"] = input.consumed_fat
    if input.calories_burned_bmr:
        graphql_input["caloriesBurnedBmr"] = input.calories_burned_bmr
    if input.calories_burned_active:
        graphql_input["caloriesBurnedActive"] = input.calories_burned_active
    
    data = await graphql_query(query, variables={"input": graphql_input})
    return data["nutritionalProfile"]["recordProgress"]


# Tool 5: Get Progress Score
class GetProgressScoreInput(BaseModel):
    """Input for get_progress_score."""
    user_id: str = Field(description="User UUID")
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str = Field(description="End date YYYY-MM-DD")


@mcp.tool()
async def get_progress_score(input: GetProgressScoreInput) -> dict:
    """Analyze progress and calculate adherence score for date range.
    
    Calculates:
    - Weight change (kg and %)
    - Adherence rate (% of days logged)
    - Average calorie deficit/surplus
    - Macro balance score
    - Trend direction
    
    Args:
        input: User ID and date range
    
    Returns:
        ProgressScore with analytics
    """
    query = """
    query GetProgressScore($userId: String!, $startDate: Date!, $endDate: Date!) {
        nutritionalProfile {
            progressScore(userId: $userId, startDate: $startDate, endDate: $endDate) {
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
    data = await graphql_query(query, variables={
        "userId": input.user_id,
        "startDate": input.start_date,
        "endDate": input.end_date
    })
    return data["nutritionalProfile"]["progressScore"]


# Tool 6: Forecast Weight
class ForecastWeightInput(BaseModel):
    """Input for forecast_weight."""
    profile_id: str = Field(description="Profile UUID")
    days_ahead: int = Field(7, description="Days to forecast (default 7)")
    confidence_level: float = Field(0.95, description="Confidence level 0-1 (default 0.95)")


@mcp.tool()
async def forecast_weight(input: ForecastWeightInput) -> dict:
    """🔮 ML-powered weight forecast using ARIMA time series model.
    
    Predicts future weight trajectory based on historical data.
    Requires at least 14 days of progress records for accurate predictions.
    
    ML model analyzes:
    - Historical weight measurements (daily records)
    - Calorie deficit/surplus patterns
    - Activity level trends
    - Time-of-week effects (weekdays vs weekends)
    
    Uses ARIMA (AutoRegressive Integrated Moving Average) with confidence intervals.
    
    Args:
        input: Forecast parameters
            - profile_id: Profile UUID (required)
            - days_ahead: Forecast horizon (default 7, max 90)
                Recommended: 7 for week, 30 for month
            - confidence_level: Prediction confidence (default 0.95)
                Range: 0.80-0.99 (0.95 = 95% confidence interval)
    
    Returns:
        WeightForecast with predictions:
        - predictions: Array of daily forecasts
            * date: Prediction date (YYYY-MM-DD)
            * predictedWeight: Most likely weight (kg)
            * lowerBound: Lower CI (95% sure weight >= this)
            * upperBound: Upper CI (95% sure weight <= this)
        - confidence: Confidence level used (e.g., 0.95)
        - model: Model name ("ARIMA")
    
    Raises:
        Exception: If insufficient historical data (<14 days)
    
    Example:
        # Forecast next 30 days
        forecast = await forecast_weight(
            profile_id="profile-uuid",
            days_ahead=30,
            confidence_level=0.95
        )
        # Returns: [
        #   {date: "2025-11-18", predictedWeight: 84.2, lowerBound: 83.8, upperBound: 84.6},
        #   {date: "2025-11-19", predictedWeight: 84.0, lowerBound: 83.5, upperBound: 84.5},
        #   ...
        # ]
    
    Interpretation:
        - predictedWeight: Expected weight (centerline on chart)
        - [lowerBound, upperBound]: 95% confidence zone (shaded area)
        - Wider bounds = more uncertainty (normal for longer forecasts)
    """
    query = """
    query ForecastWeight($profileId: String!, $daysAhead: Int!, $confidenceLevel: Float!) {
        nutritionalProfile {
            forecastWeight(profileId: $profileId, daysAhead: $daysAhead, confidenceLevel: $confidenceLevel) {
                profileId
                generatedAt
                predictions {
                    date
                    predictedWeight
                    lowerBound
                    upperBound
                }
                modelUsed
                confidenceLevel
                dataPointsUsed
                trendDirection
                trendMagnitude
            }
        }
    }
    """
    data = await graphql_query(query, variables={
        "profileId": input.profile_id,
        "daysAhead": input.days_ahead,
        "confidenceLevel": input.confidence_level
    })
    return data["nutritionalProfile"]["forecastWeight"]


if __name__ == "__main__":
    mcp.run()
