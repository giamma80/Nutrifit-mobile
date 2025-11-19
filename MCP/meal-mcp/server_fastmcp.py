#!/usr/bin/env python3
"""
Nutrifit Meal MCP Server (FastMCP)

Meal tracking, nutrition analysis, and food discovery.
Refactored with FastMCP for cleaner tool definitions.

IMPORTANT FOR AI ASSISTANTS:
==========================
15 tools organized in 5 categories:

📤 IMAGE UPLOAD:
1. upload_meal_image(user_id, image_data, filename) - Upload to storage (REQUIRED for images)

📍 ATOMIC OPERATIONS:
2. search_food_by_barcode(barcode) - Product lookup
3. recognize_food(photo_url, text, dish_hint) - AI recognition
4. enrich_nutrients(label, quantity_g) - USDA nutrition data

🍽️ MEAL ANALYSIS (end-to-end):
5. analyze_meal_photo(user_id, photo_url, meal_type) - Photo→meal
6. analyze_meal_text(user_id, text_description, meal_type) - Text→meal
7. analyze_meal_barcode(user_id, barcode, quantity_g, meal_type) - Barcode→meal
8. confirm_meal_analysis(meal_id, user_id, confirmed_entry_ids) - Confirm/reject

📊 MEAL QUERIES:
9. get_meal(meal_id, user_id) - Single meal
10. get_meal_history(user_id, start_date, end_date, meal_type, limit) - History
11. search_meals(user_id, query_text) - Full-text search
12. get_daily_summary(user_id, date) - Day totals
13. get_summary_range(user_id, start_date, end_date, group_by) - Multi-day

✏️ MEAL MANAGEMENT:
14. update_meal(meal_id, user_id, meal_type, timestamp) - Update
15. delete_meal(meal_id, user_id) - Delete

ENUMS:
- meal_type: BREAKFAST, LUNCH, DINNER, SNACK
- group_by: DAY, WEEK, MONTH
"""

import os
from typing import Optional, List

import httpx
from fastmcp import FastMCP
from pydantic import BaseModel, Field


# Configuration
GRAPHQL_ENDPOINT = os.getenv("GRAPHQL_ENDPOINT", "http://localhost:8080/graphql")
REST_API_ENDPOINT = os.getenv("REST_API_ENDPOINT", "http://localhost:8080/api/v1")
DEFAULT_TIMEOUT = 30.0

# Initialize FastMCP
mcp = FastMCP("Nutrifit Meal")


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


# Tool 1: Upload Meal Image
class UploadMealImageInput(BaseModel):
    """Input for upload_meal_image."""
    user_id: str = Field(description="User UUID")
    image_data: str = Field(description="Base64-encoded image data")
    filename: str = Field(description="Original filename (e.g., 'meal.jpg')")


@mcp.tool()
async def upload_meal_image(input: UploadMealImageInput) -> dict:
    """📤 ⚠️ REQUIRED FIRST STEP when user provides image file!
    
    Upload meal image to Supabase Storage and get public URL.
    MUST be called BEFORE analyze_meal_photo if user shares image directly (not URL).
    
    Critical workflow:
    1. User shares image file → upload_meal_image (get URL)
    2. Use returned URL → analyze_meal_photo(photo_url=url)
    3. Confirm analysis → confirm_meal_analysis
    
    DO NOT skip this if user provides image file attachment!
    
    Args:
        input: Upload data
            - user_id: User UUID (required)
            - image_data: Base64-encoded image (required)
                Get from file attachment, NOT manual encoding
            - filename: Original filename (e.g., "meal.jpg", "dinner.png")
    
    Returns:
        Upload result:
        - url: Public URL (e.g., "https://storage.supabase.co/.../meal.jpg")
        Use this URL in analyze_meal_photo's photo_url parameter
    
    Example:
        # Step 1: Upload image
        upload_result = await upload_meal_image(
            user_id="uuid",
            image_data=base64_from_attachment,
            filename="lunch.jpg"
        )
        
        # Step 2: Analyze with returned URL
        meal = await analyze_meal_photo(
            user_id="uuid",
            photo_url=upload_result["url"],
            meal_type="LUNCH"
        )
    """
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(
            f"{REST_API_ENDPOINT}/upload",
            json={
                "userId": input.user_id,
                "imageData": input.image_data,
                "filename": input.filename
            }
        )
        response.raise_for_status()
        return response.json()


# Tool 2: Search Food by Barcode
@mcp.tool()
async def search_food_by_barcode(barcode: str) -> dict:
    """Search product by barcode (EAN-13, UPC, etc.).
    
    Returns product details from OpenFoodFacts database:
    - Name, brand, nutrients
    - Serving size
    - Product image
    
    Args:
        barcode: Product barcode
    
    Returns:
        Product details with nutrition data
    """
    query = """
    query SearchFoodByBarcode($barcode: String!) {
        searchFoodByBarcode(barcode: $barcode) {
            name
            brand
            nutrients {
                calories
                protein
                carbs
                fat
                fiber
            }
            servingSize
            servingUnit
            imageUrl
        }
    }
    """
    data = await graphql_query(query, variables={"barcode": barcode})
    return data["searchFoodByBarcode"]


# Tool 3: Recognize Food
class RecognizeFoodInput(BaseModel):
    """Input for recognize_food."""
    photo_url: Optional[str] = Field(None, description="URL of meal photo")
    text: Optional[str] = Field(None, description="Text description of meal")
    dish_hint: Optional[str] = Field(None, description="Optional dish name hint")


@mcp.tool()
async def recognize_food(input: RecognizeFoodInput) -> dict:
    """AI food recognition from photo or text description.
    
    Uses Vision AI to detect food items with quantities and confidence.
    Provide either photo_url OR text (or both for better accuracy).
    
    Args:
        input: Photo URL and/or text description, optional dish hint
    
    Returns:
        List of detected foods with quantities, confidence, display names
    """
    query = """
    query RecognizeFood($photoUrl: String, $text: String, $dishHint: String) {
        recognizeFood(photoUrl: $photoUrl, text: $text, dishHint: $dishHint) {
            items {
                label
                quantityG
                confidence
                displayName
            }
        }
    }
    """
    graphql_vars = {}
    if input.photo_url:
        graphql_vars["photoUrl"] = input.photo_url
    if input.text:
        graphql_vars["text"] = input.text
    if input.dish_hint:
        graphql_vars["dishHint"] = input.dish_hint
    
    data = await graphql_query(query, variables=graphql_vars)
    return data["recognizeFood"]


# Tool 4: Enrich Nutrients
class EnrichNutrientsInput(BaseModel):
    """Input for enrich_nutrients."""
    label: str = Field(description="Food item label")
    quantity_g: float = Field(description="Quantity in grams")


@mcp.tool()
async def enrich_nutrients(input: EnrichNutrientsInput) -> dict:
    """Get nutrition data from USDA database.
    
    Searches USDA FoodData Central for nutrition info per 100g,
    then scales to requested quantity.
    
    Args:
        input: Food label and quantity in grams
    
    Returns:
        Nutrition data (calories, protein, carbs, fat, fiber)
    """
    query = """
    query EnrichNutrients($label: String!, $quantityG: Float!) {
        enrichNutrients(label: $label, quantityG: $quantityG) {
            calories
            protein
            carbs
            fat
            fiber
        }
    }
    """
    data = await graphql_query(query, variables={
        "label": input.label,
        "quantityG": input.quantity_g
    })
    return data["enrichNutrients"]


# Tool 5: Analyze Meal Photo
class AnalyzeMealPhotoInput(BaseModel):
    """Input for analyze_meal_photo."""
    user_id: str = Field(description="User UUID")
    photo_url: str = Field(description="URL of meal photo (from upload_meal_image)")
    meal_type: str = Field(description="BREAKFAST | LUNCH | DINNER | SNACK")


@mcp.tool()
async def analyze_meal_photo(input: AnalyzeMealPhotoInput) -> dict:
    """🍽️ Complete end-to-end meal analysis from photo.
    
    ⚠️ Photo URL must be from upload_meal_image if user provided file!
    
    AI-powered workflow (automatic):
    1. Vision AI recognizes food items (e.g., "chicken breast 150g")
    2. USDA enriches nutrition data (calories, protein, carbs, fat)
    3. Creates PENDING meal with detected entries
    4. Returns meal for user confirmation
    
    IMPORTANT: Use confirm_meal_analysis to transition PENDING → CONFIRMED.
    
    Args:
        input: Analysis parameters
            - user_id: User UUID (required)
            - photo_url: Public image URL (required)
                From upload_meal_image OR external URL
            - meal_type: Meal category (required)
                → "BREAKFAST" | "LUNCH" | "DINNER" | "SNACK"
    
    Returns:
        Meal with detected entries (status: PENDING):
        - id: Meal UUID (use in confirm_meal_analysis)
        - userId, mealType, timestamp: Metadata
        - totalCalories, totalProtein, totalCarbs, totalFat: Sums
        - status: "PENDING" (awaiting confirmation)
        - photoUrl: Stored image URL
        - entries: Array of detected food items
            * id: Entry UUID (use in confirmed_entry_ids)
            * foodLabel: Detected food name
            * quantityG: Estimated quantity in grams
            * calories, protein, carbs, fat: Nutrition data
    
    Example workflow:
        # 1. Upload image
        upload = await upload_meal_image(...)
        
        # 2. Analyze
        meal = await analyze_meal_photo(
            user_id="uuid",
            photo_url=upload["url"],
            meal_type="LUNCH"
        )
        # Returns: {id: "meal-123", entries: [{id: "entry-1", foodLabel: "chicken", ...}]}
        
        # 3. User reviews → confirm
        confirmed = await confirm_meal_analysis(
            meal_id=meal["id"],
            user_id="uuid",
            confirmed_entry_ids=[meal["entries"][0]["id"]]  # Keep only accurate entries
        )
    """
    query = """
    mutation AnalyzeMealPhoto($input: AnalyzeMealPhotoInput!) {
        analyzeMealPhoto(input: $input) {
            id
            userId
            mealType
            timestamp
            totalCalories
            totalProtein
            totalCarbs
            totalFat
            status
            photoUrl
            entries {
                id
                foodLabel
                quantityG
                calories
                protein
                carbs
                fat
            }
        }
    }
    """
    graphql_input = {
        "userId": input.user_id,
        "photoUrl": input.photo_url,
        "mealType": input.meal_type
    }
    data = await graphql_query(query, variables={"input": graphql_input})
    return data["analyzeMealPhoto"]


# Tool 6: Analyze Meal Text
class AnalyzeMealTextInput(BaseModel):
    """Input for analyze_meal_text."""
    user_id: str = Field(description="User UUID")
    text_description: str = Field(description="Text description of meal")
    meal_type: str = Field(description="BREAKFAST | LUNCH | DINNER | SNACK")


@mcp.tool()
async def analyze_meal_text(input: AnalyzeMealTextInput) -> dict:
    """Analyze meal from text description.
    
    Similar to analyze_meal_photo but uses text input.
    Creates PENDING meal awaiting confirmation.
    
    Args:
        input: User ID, text description, meal type
    
    Returns:
        Meal with detected entries (status: PENDING)
    """
    query = """
    mutation AnalyzeMealText($input: AnalyzeMealTextInput!) {
        analyzeMealText(input: $input) {
            id
            userId
            mealType
            timestamp
            totalCalories
            totalProtein
            totalCarbs
            totalFat
            status
            entries {
                id
                foodLabel
                quantityG
                calories
                protein
                carbs
                fat
            }
        }
    }
    """
    graphql_input = {
        "userId": input.user_id,
        "textDescription": input.text_description,
        "mealType": input.meal_type
    }
    data = await graphql_query(query, variables={"input": graphql_input})
    return data["analyzeMealText"]


# Tool 7: Analyze Meal Barcode
class AnalyzeMealBarcodeInput(BaseModel):
    """Input for analyze_meal_barcode."""
    user_id: str = Field(description="User UUID")
    barcode: str = Field(description="Product barcode")
    quantity_g: float = Field(description="Quantity consumed in grams")
    meal_type: str = Field(description="BREAKFAST | LUNCH | DINNER | SNACK")


@mcp.tool()
async def analyze_meal_barcode(input: AnalyzeMealBarcodeInput) -> dict:
    """Analyze meal from barcode scan.
    
    Looks up product, creates PENDING meal.
    Quick workflow for packaged foods.
    
    Args:
        input: User ID, barcode, quantity, meal type
    
    Returns:
        Meal with product entry (status: PENDING)
    """
    query = """
    mutation AnalyzeMealBarcode($input: AnalyzeMealBarcodeInput!) {
        analyzeMealBarcode(input: $input) {
            id
            userId
            mealType
            timestamp
            totalCalories
            totalProtein
            totalCarbs
            totalFat
            status
            entries {
                id
                foodLabel
                quantityG
                calories
                protein
                carbs
                fat
            }
        }
    }
    """
    graphql_input = {
        "userId": input.user_id,
        "barcode": input.barcode,
        "quantityG": input.quantity_g,
        "mealType": input.meal_type
    }
    data = await graphql_query(query, variables={"input": graphql_input})
    return data["analyzeMealBarcode"]


# Tool 8: Confirm Meal Analysis
class ConfirmMealAnalysisInput(BaseModel):
    """Input for confirm_meal_analysis."""
    meal_id: str = Field(description="Meal UUID")
    user_id: str = Field(description="User UUID")
    confirmed_entry_ids: List[str] = Field(description="List of entry UUIDs to keep")


@mcp.tool()
async def confirm_meal_analysis(input: ConfirmMealAnalysisInput) -> dict:
    """✅ Confirm meal analysis and mark as CONFIRMED.
    
    ⚠️ REQUIRED after analyze_meal_* to finalize meal logging.
    Transitions meal from PENDING → CONFIRMED state.
    
    User review process:
    1. AI detects entries (e.g., chicken 150g, rice 200g, broccoli 100g)
    2. User reviews → keeps accurate entries, rejects errors
    3. Only confirmed_entry_ids are kept, others deleted
    
    Args:
        input: Confirmation data
            - meal_id: Meal UUID from analyze_meal_* (required)
            - user_id: User UUID (required)
            - confirmed_entry_ids: Array of entry UUIDs to keep (required)
                Empty array → rejects ALL entries (meal becomes empty)
                All IDs → confirms entire meal
    
    Returns:
        Updated meal (status: CONFIRMED):
        - id: Meal UUID (unchanged)
        - status: "CONFIRMED"
        - totalCalories, totalProtein, totalCarbs, totalFat: Recalculated
        - entries: Only confirmed entries
    
    Example:
        # Meal has 3 detected entries
        meal = await analyze_meal_photo(...)
        # entries: [
        #   {id: "entry-1", foodLabel: "chicken"},
        #   {id: "entry-2", foodLabel: "rice"},
        #   {id: "entry-3", foodLabel: "mystery_item"}  # Wrong detection
        # ]
        
        # User confirms only chicken + rice
        confirmed = await confirm_meal_analysis(
            meal_id=meal["id"],
            user_id="uuid",
            confirmed_entry_ids=["entry-1", "entry-2"]  # Rejects entry-3
        )
        # Returns: entries with only chicken + rice
    """
    query = """
    mutation ConfirmMealAnalysis($mealId: ID!, $userId: ID!, $confirmedEntryIds: [ID!]!) {
        confirmMealAnalysis(mealId: $mealId, userId: $userId, confirmedEntryIds: $confirmedEntryIds) {
            id
            status
            totalCalories
            totalProtein
            totalCarbs
            totalFat
            entries {
                id
                foodLabel
                quantityG
            }
        }
    }
    """
    data = await graphql_query(query, variables={
        "mealId": input.meal_id,
        "userId": input.user_id,
        "confirmedEntryIds": input.confirmed_entry_ids
    })
    return data["confirmMealAnalysis"]


# Tool 9: Get Meal
@mcp.tool()
async def get_meal(meal_id: str, user_id: str) -> dict:
    """Get single meal details by ID.
    
    Args:
        meal_id: Meal UUID
        user_id: User UUID
    
    Returns:
        Complete meal with all entries
    """
    query = """
    query GetMeal($mealId: ID!, $userId: ID!) {
        meal(mealId: $mealId, userId: $userId) {
            id
            userId
            mealType
            timestamp
            totalCalories
            totalProtein
            totalCarbs
            totalFat
            status
            photoUrl
            entries {
                id
                foodLabel
                quantityG
                calories
                protein
                carbs
                fat
            }
        }
    }
    """
    data = await graphql_query(query, variables={"mealId": meal_id, "userId": user_id})
    return data["meal"]


# Tool 10: Get Meal History
class GetMealHistoryInput(BaseModel):
    """Input for get_meal_history."""
    user_id: str = Field(description="User UUID")
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD")
    meal_type: Optional[str] = Field(None, description="Filter by meal type")
    limit: int = Field(50, description="Max results (default 50)")


@mcp.tool()
async def get_meal_history(input: GetMealHistoryInput) -> dict:
    """Get meal history with pagination and filters.
    
    Args:
        input: User ID, date range, meal type filter, limit
    
    Returns:
        List of meals sorted by timestamp DESC
    """
    query = """
    query GetMealHistory($userId: ID!, $startDate: String, $endDate: String, $mealType: MealType, $limit: Int) {
        mealHistory(userId: $userId, startDate: $startDate, endDate: $endDate, mealType: $mealType, limit: $limit) {
            id
            mealType
            timestamp
            totalCalories
            totalProtein
            totalCarbs
            totalFat
            status
            photoUrl
        }
    }
    """
    graphql_vars = {"userId": input.user_id, "limit": input.limit}
    if input.start_date:
        graphql_vars["startDate"] = input.start_date
    if input.end_date:
        graphql_vars["endDate"] = input.end_date
    if input.meal_type:
        graphql_vars["mealType"] = input.meal_type
    
    data = await graphql_query(query, variables=graphql_vars)
    return data["mealHistory"]


# Tool 11: Search Meals
@mcp.tool()
async def search_meals(user_id: str, query_text: str) -> dict:
    """Full-text search across user's meals.
    
    Searches in food labels and meal metadata.
    
    Args:
        user_id: User UUID
        query_text: Search query
    
    Returns:
        Matching meals with highlighted entries
    """
    query = """
    query SearchMeals($userId: ID!, $query: String!) {
        searchMeals(userId: $userId, query: $query) {
            id
            mealType
            timestamp
            totalCalories
            entries {
                id
                foodLabel
                quantityG
                calories
            }
        }
    }
    """
    data = await graphql_query(query, variables={"userId": user_id, "query": query_text})
    return data["searchMeals"]


# Tool 12: Get Daily Summary
@mcp.tool()
async def get_daily_summary(user_id: str, date: str) -> dict:
    """Get nutrition summary for single day.
    
    Args:
        user_id: User UUID
        date: Date YYYY-MM-DD
    
    Returns:
        Total calories, protein, carbs, fat for the day
    """
    query = """
    query GetDailySummary($userId: ID!, $date: String!) {
        dailySummary(userId: $userId, date: $date) {
            date
            totalCalories
            totalProtein
            totalCarbs
            totalFat
            mealCount
        }
    }
    """
    data = await graphql_query(query, variables={"userId": user_id, "date": date})
    return data["dailySummary"]


# Tool 13: Get Summary Range
class GetSummaryRangeInput(BaseModel):
    """Input for get_summary_range."""
    user_id: str = Field(description="User UUID")
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str = Field(description="End date YYYY-MM-DD")
    group_by: str = Field("DAY", description="DAY | WEEK | MONTH")


@mcp.tool()
async def get_summary_range(input: GetSummaryRangeInput) -> dict:
    """Get aggregated nutrition summary for date range.
    
    Groups data by DAY, WEEK, or MONTH.
    
    Args:
        input: User ID, date range, grouping
    
    Returns:
        List of summaries grouped by time period
    """
    query = """
    query GetSummaryRange($userId: ID!, $startDate: String!, $endDate: String!, $groupBy: GroupBy!) {
        summaryRange(userId: $userId, startDate: $startDate, endDate: $endDate, groupBy: $groupBy) {
            period
            totalCalories
            totalProtein
            totalCarbs
            totalFat
            mealCount
        }
    }
    """
    data = await graphql_query(query, variables={
        "userId": input.user_id,
        "startDate": input.start_date,
        "endDate": input.end_date,
        "groupBy": input.group_by
    })
    return data["summaryRange"]


# Tool 14: Update Meal
class UpdateMealInput(BaseModel):
    """Input for update_meal."""
    meal_id: str = Field(description="Meal UUID")
    user_id: str = Field(description="User UUID")
    meal_type: Optional[str] = Field(None, description="Updated meal type")
    timestamp: Optional[str] = Field(None, description="Updated timestamp ISO 8601")


@mcp.tool()
async def update_meal(input: UpdateMealInput) -> dict:
    """Update meal metadata (type, timestamp).
    
    Args:
        input: Meal ID, user ID, optional updates
    
    Returns:
        Updated meal
    """
    query = """
    mutation UpdateMeal($mealId: ID!, $userId: ID!, $input: UpdateMealInput!) {
        updateMeal(mealId: $mealId, userId: $userId, input: $input) {
            id
            mealType
            timestamp
            totalCalories
        }
    }
    """
    graphql_input = {}
    if input.meal_type:
        graphql_input["mealType"] = input.meal_type
    if input.timestamp:
        graphql_input["timestamp"] = input.timestamp
    
    data = await graphql_query(query, variables={
        "mealId": input.meal_id,
        "userId": input.user_id,
        "input": graphql_input
    })
    return data["updateMeal"]


# Tool 15: Delete Meal
@mcp.tool()
async def delete_meal(meal_id: str, user_id: str) -> dict:
    """Delete meal and all entries.
    
    Args:
        meal_id: Meal UUID
        user_id: User UUID
    
    Returns:
        Success confirmation
    """
    query = """
    mutation DeleteMeal($mealId: ID!, $userId: ID!) {
        deleteMeal(mealId: $mealId, userId: $userId) {
            success
            deletedMealId
        }
    }
    """
    data = await graphql_query(query, variables={"mealId": meal_id, "userId": user_id})
    return data["deleteMeal"]


if __name__ == "__main__":
    mcp.run()
