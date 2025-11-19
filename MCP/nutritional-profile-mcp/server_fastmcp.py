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
    query GetNutritionalProfile($userId: ID!) {
        nutritionalProfile(userId: $userId) {
            id
            userId
            currentWeight
            targetWeight
            height
            age
            gender
            activityLevel
            goalType
            bmr
            tdee
            targetCalories
            targetProteinRatio
            targetCarbsRatio
            targetFatRatio
            createdAt
            updatedAt
        }
    }
    """
    data = await graphql_query(query, variables={"userId": user_id})
    return data["nutritionalProfile"]


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
    """Create new nutritional profile with automatic BMR/TDEE calculation.
    
    Creates profile and automatically calculates:
    - BMR using Mifflin-St Jeor equation
    - TDEE based on activity level
    - Target calories based on goal type
    - Recommended macro ratios
    
    Args:
        input: Profile data (weight, height, age, gender, activity, goal)
    
    Returns:
        Created NutritionalProfile with calculated metrics
    """
    query = """
    mutation CreateNutritionalProfile($input: CreateNutritionalProfileInput!) {
        createNutritionalProfile(input: $input) {
            id
            userId
            currentWeight
            targetWeight
            height
            age
            gender
            activityLevel
            goalType
            bmr
            tdee
            targetCalories
            targetProteinRatio
            targetCarbsRatio
            targetFatRatio
            createdAt
        }
    }
    """
    graphql_input = {
        "userId": input.user_id,
        "currentWeight": input.current_weight,
        "targetWeight": input.target_weight,
        "height": input.height,
        "age": input.age,
        "gender": input.gender,
        "activityLevel": input.activity_level,
        "goalType": input.goal_type
    }
    data = await graphql_query(query, variables={"input": graphql_input})
    return data["createNutritionalProfile"]


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
    
    Returns:
        Updated NutritionalProfile with recalculated metrics
    """
    query = """
    mutation UpdateNutritionalProfile($profileId: ID!, $input: UpdateNutritionalProfileInput!) {
        updateNutritionalProfile(profileId: $profileId, input: $input) {
            id
            currentWeight
            targetWeight
            activityLevel
            goalType
            bmr
            tdee
            targetCalories
            updatedAt
        }
    }
    """
    graphql_input = {}
    if input.current_weight:
        graphql_input["currentWeight"] = input.current_weight
    if input.target_weight:
        graphql_input["targetWeight"] = input.target_weight
    if input.activity_level:
        graphql_input["activityLevel"] = input.activity_level
    if input.goal_type:
        graphql_input["goalType"] = input.goal_type
    
    data = await graphql_query(query, variables={
        "profileId": input.profile_id,
        "input": graphql_input
    })
    return data["updateNutritionalProfile"]


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
        recordProgress(input: $input) {
            id
            userId
            date
            weight
            caloriesConsumed
            consumedProtein
            consumedCarbs
            consumedFat
            caloriesBurnedBMR
            caloriesBurnedActive
            createdAt
        }
    }
    """
    graphql_input = {
        "userId": input.user_id,
        "date": input.date
    }
    if input.weight:
        graphql_input["weight"] = input.weight
    if input.calories_consumed:
        graphql_input["caloriesConsumed"] = input.calories_consumed
    if input.consumed_protein:
        graphql_input["consumedProtein"] = input.consumed_protein
    if input.consumed_carbs:
        graphql_input["consumedCarbs"] = input.consumed_carbs
    if input.consumed_fat:
        graphql_input["consumedFat"] = input.consumed_fat
    if input.calories_burned_bmr:
        graphql_input["caloriesBurnedBMR"] = input.calories_burned_bmr
    if input.calories_burned_active:
        graphql_input["caloriesBurnedActive"] = input.calories_burned_active
    
    data = await graphql_query(query, variables={"input": graphql_input})
    return data["recordProgress"]


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
    query GetProgressScore($userId: ID!, $startDate: String!, $endDate: String!) {
        progressScore(userId: $userId, startDate: $startDate, endDate: $endDate) {
            weightChange
            weightChangePercentage
            adherenceRate
            averageCalorieDeficit
            macroBalanceScore
            trendDirection
            totalDays
            loggedDays
        }
    }
    """
    data = await graphql_query(query, variables={
        "userId": input.user_id,
        "startDate": input.start_date,
        "endDate": input.end_date
    })
    return data["progressScore"]


# Tool 6: Forecast Weight
class ForecastWeightInput(BaseModel):
    """Input for forecast_weight."""
    profile_id: str = Field(description="Profile UUID")
    days_ahead: int = Field(7, description="Days to forecast (default 7)")
    confidence_level: float = Field(0.95, description="Confidence level 0-1 (default 0.95)")


@mcp.tool()
async def forecast_weight(input: ForecastWeightInput) -> dict:
    """ML-powered weight forecast using ARIMA model.
    
    Predicts future weight trajectory based on:
    - Historical weight measurements
    - Calorie deficit/surplus patterns
    - Activity level trends
    
    Uses ARIMA time series model with confidence intervals.
    
    Args:
        input: Profile ID, forecast horizon, confidence level
    
    Returns:
        WeightForecast with predictions and confidence intervals
    """
    query = """
    query ForecastWeight($profileId: ID!, $daysAhead: Int!, $confidenceLevel: Float!) {
        forecastWeight(profileId: $profileId, daysAhead: $daysAhead, confidenceLevel: $confidenceLevel) {
            predictions {
                date
                predictedWeight
                lowerBound
                upperBound
            }
            confidence
            model
        }
    }
    """
    data = await graphql_query(query, variables={
        "profileId": input.profile_id,
        "daysAhead": input.days_ahead,
        "confidenceLevel": input.confidence_level
    })
    return data["forecastWeight"]


if __name__ == "__main__":
    mcp.run()
