#!/usr/bin/env python3
"""
Nutrifit Meal MCP Server

Model Context Protocol server for the Nutrifit Meal domain. Provides tools
for AI assistants to help users track nutrition and analyze meals.

IMPORTANT FOR AI ASSISTANTS:
==========================
This server provides 15 tools organized in 5 categories:

📤 IMAGE UPLOAD (REQUIRED when user shares image file):
1. upload_meal_image(user_id, image_data, filename) - Upload to storage
   ⚠️ MUST use this FIRST if user provides image (not URL)
   Returns URL for use in analyze_meal_photo

📍 ATOMIC OPERATIONS (building blocks):
2. search_food_by_barcode(barcode) - Product lookup
3. recognize_food(photo_url|text, dish_hint) - AI food recognition
4. enrich_nutrients(label, quantity_g) - USDA nutrition data

🍽️ MEAL ANALYSIS (end-to-end workflows):
5. analyze_meal_photo(user_id, photo_url, meal_type) - Complete photo→meal
6. analyze_meal_text(user_id, text_description, meal_type) - Text description→meal
7. analyze_meal_barcode(user_id, barcode, quantity_g, meal_type) - Barcode→meal
8. confirm_meal_analysis(meal_id, user_id, confirmed_entry_ids) - Confirm/reject

📊 MEAL QUERIES:
9. get_meal(meal_id, user_id) - Single meal details
10. get_meal_history(user_id, start_date, end_date, ...) - History
11. search_meals(user_id, query_text) - Full-text search
12. get_daily_summary(user_id, date) - Single day totals
13. get_summary_range(user_id, start_date, end_date, group_by) - Multi-day

✏️ MEAL MANAGEMENT:
14. update_meal(meal_id, user_id, meal_type?, timestamp?) - Update
15. delete_meal(meal_id, user_id) - Delete meal

CRITICAL ENUM VALUES (from GraphQL schema):
- meal_type: "BREAKFAST", "LUNCH", "DINNER", "SNACK" (uppercase)
- group_by: "DAY", "WEEK", "MONTH" (for summaryRange)

PARAMETER NAMING (snake_case in MCP → camelCase in GraphQL):
⚠️ Tool inputs use snake_case but are converted to camelCase for GraphQL:
- user_id → userId
- photo_url → photoUrl
- meal_type → mealType
- quantity_g → quantityG
- start_date → startDate
- dish_hint → dishHint

WORKFLOW BEST PRACTICES:
1. Photo meal: upload_meal_image → analyze_meal_photo → confirm
2. Text meal: analyze_meal_text → confirm_meal_analysis
3. Barcode meal: analyze_meal_barcode → confirm_meal_analysis
4. Manual entry: recognize_food + enrich_nutrients (separate steps)
5. Daily check: get_daily_summary
6. Weekly report: get_summary_range with groupBy=DAY

MEAL ANALYSIS STATES:
- PENDING: Awaiting confirmation (after analyze_*)
- CONFIRMED: User confirmed entries
- Use confirm_meal_analysis to transition PENDING→CONFIRMED

DATE/TIME FORMATS:
- Dates: "YYYY-MM-DD"
- Timestamps: ISO 8601 (e.g., "2025-11-01T12:30:00Z")
"""

import asyncio
import datetime
import json
import os
from typing import Any, Optional

import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field


# API endpoint configuration
GRAPHQL_ENDPOINT = "http://localhost:8080/graphql"
REST_API_ENDPOINT = "http://localhost:8080/api/v1"
DEFAULT_TIMEOUT = 30.0


class GraphQLClient:
    """Client for executing GraphQL queries against Nutrifit backend."""

    def __init__(self, endpoint: str = GRAPHQL_ENDPOINT):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)

    async def execute(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query and return the response."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await self.client.post(self.endpoint, json=payload)
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            error_messages = [e.get("message", str(e)) for e in data["errors"]]
            raise Exception(f"GraphQL errors: {', '.join(error_messages)}")

        return data.get("data", {})

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Initialize MCP server and GraphQL client
app = Server("nutrifit-meal-mcp")
gql_client = GraphQLClient()


# ============================================
# ATOMIC QUERIES - Food Discovery
# ============================================


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools in the Meal MCP."""
    return [
        Tool(
            name="upload_meal_image",
            description=(
                "⚠️ REQUIRED FIRST STEP when user provides an image file!\n\n"
                "Upload a meal image to secure storage and get a public URL.\n"
                "This tool MUST be called BEFORE analyze_meal_photo if the user "
                "shares an image directly (not a URL).\n\n"
                "What it does:\n"
                "1. Takes base64-encoded image data from user's file\n"
                "2. Uploads to Supabase Storage (auto-converts to JPEG)\n"
                "3. Returns a public URL\n"
                "4. Use that URL in analyze_meal_photo's photo_url parameter\n\n"
                "DO NOT try to encode images yourself - use this tool instead!"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID for organizing images",
                    },
                    "image_data": {
                        "type": "string",
                        "description": (
                            "Base64-encoded image data. "
                            "Get this from the user's image file attachment."
                        ),
                    },
                    "filename": {
                        "type": "string",
                        "description": (
                            "Original filename with extension "
                            "(e.g., 'meal.jpg', 'dinner.png')"
                        ),
                    },
                },
                "required": ["user_id", "image_data", "filename"],
            },
        ),
        Tool(
            name="search_food_by_barcode",
            description=(
                "Search for a food product by barcode. "
                "Returns product details including name, brand, nutrients, serving size, and image. "
                "Useful for quick product lookup when user scans a barcode."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "barcode": {
                        "type": "string",
                        "description": "Product barcode (EAN-13, UPC, etc.)",
                    }
                },
                "required": ["barcode"],
            },
        ),
        Tool(
            name="recognize_food",
            description=(
                "Recognize food items from a photo or text description using AI vision. "
                "Returns list of detected food items with quantities, confidence scores, and display names. "
                "Use when user uploads a meal photo or describes what they ate."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "photo_url": {
                        "type": "string",
                        "description": "URL of the meal photo (optional if text provided)",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text description of the meal (optional if photo_url provided)",
                    },
                    "dish_hint": {
                        "type": "string",
                        "description": "Optional hint about the dish name (e.g., 'pasta carbonara')",
                    },
                },
            },
        ),
        Tool(
            name="enrich_nutrients",
            description=(
                "Enrich food label with complete nutritional data from USDA. "
                "Use when you have a food name and need complete nutrition facts.\n\n"
                "⚠️ PARAMETER CONVERSION:\n"
                "- Input: quantity_g (snake_case)\n"
                "- GraphQL: quantityG (camelCase)\n"
                "The server automatically converts this parameter."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "Food name (e.g., 'chicken breast', 'brown rice')",
                    },
                    "quantity_g": {
                        "type": "number",
                        "description": "Quantity in grams",
                    },
                },
                "required": ["label", "quantity_g"],
            },
        ),
        # Meal Management
        Tool(
            name="analyze_meal_photo",
            description=(
                "Analyze a meal photo: AI recognizes foods + enriches with "
                "USDA nutrients + creates meal entry.\n\n"
                "📌 IMPORTANT: This tool requires a photo_url parameter.\n"
                "If user provides an image file (not a URL), you MUST:\n"
                "1. First call upload_meal_image to upload the image\n"
                "2. Then use the returned URL here in photo_url\n\n"
                "Returns complete meal with entries in PENDING state "
                "(requires confirmation via confirm_meal_analysis).\n\n"
                "⚠️ meal_type: 'BREAKFAST', 'LUNCH', 'DINNER', or 'SNACK'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "photo_url": {
                        "type": "string",
                        "description": (
                            "Public URL of the meal photo. "
                            "If you don't have a URL yet, use upload_meal_image "
                            "first to get one."
                        ),
                    },
                    "dish_hint": {
                        "type": "string",
                        "description": "Optional hint about the dish",
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "ISO 8601 timestamp (default: now)",
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["BREAKFAST", "LUNCH", "DINNER", "SNACK"],
                        "description": "Type of meal",
                    },
                },
                "required": ["user_id", "photo_url", "meal_type"],
            },
        ),
        Tool(
            name="analyze_meal_text",
            description=(
                "Analyze a meal from text description: recognize foods from description + enrich nutrients + create meal entry. "
                "Returns complete meal with entries in PENDING state (requires confirmation). "
                "Use this when user describes their meal in text (e.g., '150g pasta with tomato sauce').\n\n"
                "⚠️ meal_type must be: 'BREAKFAST', 'LUNCH', 'DINNER', or 'SNACK' (uppercase)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "text_description": {
                        "type": "string",
                        "description": "Text description of the meal",
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "ISO 8601 timestamp (default: now)",
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["BREAKFAST", "LUNCH", "DINNER", "SNACK"],
                        "description": "Type of meal",
                    },
                },
                "required": ["user_id", "text_description", "meal_type"],
            },
        ),
        Tool(
            name="analyze_meal_barcode",
            description=(
                "Analyze a meal from barcode: lookup product + create meal entry. "
                "Returns meal with product entry in PENDING state. "
                "Use when user scans a packaged food product."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "barcode": {"type": "string", "description": "Product barcode"},
                    "quantity_g": {
                        "type": "number",
                        "description": "Quantity consumed in grams",
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "ISO 8601 timestamp (default: now)",
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["BREAKFAST", "LUNCH", "DINNER", "SNACK"],
                        "description": "Type of meal",
                    },
                },
                "required": ["user_id", "barcode", "quantity_g", "meal_type"],
            },
        ),
        Tool(
            name="confirm_meal_analysis",
            description=(
                "Confirm a meal analysis created by photo/barcode analysis. "
                "Allows user to review and select which entries to keep. "
                "Meal becomes permanent after confirmation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "meal_id": {"type": "string", "description": "Meal ID to confirm"},
                    "user_id": {"type": "string", "description": "User ID"},
                    "confirmed_entry_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of entry IDs to keep (others will be rejected)",
                    },
                },
                "required": ["meal_id", "user_id", "confirmed_entry_ids"],
            },
        ),
        # Queries
        Tool(
            name="get_meal",
            description=(
                "Get a single meal by ID. Returns complete meal details including entries and nutrition totals."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "meal_id": {"type": "string", "description": "Meal ID"},
                    "user_id": {"type": "string", "description": "User ID"},
                },
                "required": ["meal_id", "user_id"],
            },
        ),
        Tool(
            name="get_meal_history",
            description=(
                "Get meal history with filters and pagination. "
                "Supports filtering by date range and meal type. "
                "Returns list of meals with pagination info."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "start_date": {
                        "type": "string",
                        "description": "Start date (ISO 8601, optional)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (ISO 8601, optional)",
                    },
                    "meal_type": {
                        "type": "string",
                        "enum": ["BREAKFAST", "LUNCH", "DINNER", "SNACK"],
                        "description": "Filter by meal type (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Results per page (default: 20)",
                        "default": 20,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Pagination offset (default: 0)",
                        "default": 0,
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="search_meals",
            description=(
                "Full-text search in meals. Searches dish names, entry names, and notes. "
                "Use when user asks 'find meals with chicken' or 'show me pasta dishes'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "query_text": {
                        "type": "string",
                        "description": "Search query text",
                    },
                    "limit": {"type": "integer", "default": 20},
                    "offset": {"type": "integer", "default": 0},
                },
                "required": ["user_id", "query_text"],
            },
        ),
        Tool(
            name="get_daily_summary",
            description=(
                "Get nutrition summary for a single day. "
                "Returns total calories, protein, carbs, fat, fiber, sugar, sodium, and meal count. "
                "Includes breakdown by meal type (breakfast, lunch, dinner, snack)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "date": {
                        "type": "string",
                        "description": "Date in ISO 8601 format (e.g., '2025-10-28T00:00:00Z')",
                    },
                },
                "required": ["user_id", "date"],
            },
        ),
        Tool(
            name="get_summary_range",
            description=(
                "Get nutrition summaries for a date range with flexible grouping (DAY/WEEK/MONTH). "
                "Returns breakdown per period + total aggregate. "
                "Optimized for weekly/monthly dashboards - one query instead of N loops. "
                "Use this for 'show me this week' or 'monthly report' queries.\n\n"
                "⚠️ group_by must be: 'DAY', 'WEEK', or 'MONTH' (uppercase)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID"},
                    "start_date": {
                        "type": "string",
                        "description": "Start date (ISO 8601)",
                    },
                    "end_date": {"type": "string", "description": "End date (ISO 8601)"},
                    "group_by": {
                        "type": "string",
                        "enum": ["DAY", "WEEK", "MONTH"],
                        "description": "Group results by period (default: DAY)",
                        "default": "DAY",
                    },
                },
                "required": ["user_id", "start_date", "end_date"],
            },
        ),
        # Updates
        Tool(
            name="update_meal",
            description=(
                "Update a meal's type, timestamp, or notes. "
                "Cannot modify entries - delete and recreate meal to change entries."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "meal_id": {"type": "string", "description": "Meal ID"},
                    "user_id": {"type": "string", "description": "User ID"},
                    "meal_type": {
                        "type": "string",
                        "enum": ["BREAKFAST", "LUNCH", "DINNER", "SNACK"],
                        "description": "New meal type (optional)",
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "New timestamp ISO 8601 (optional)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "New notes (optional)",
                    },
                },
                "required": ["meal_id", "user_id"],
            },
        ),
        Tool(
            name="delete_meal",
            description="Delete a meal permanently. Cannot be undone.",
            inputSchema={
                "type": "object",
                "properties": {
                    "meal_id": {"type": "string", "description": "Meal ID"},
                    "user_id": {"type": "string", "description": "User ID"},
                },
                "required": ["meal_id", "user_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Execute a tool and return the result."""

    try:
        if name == "upload_meal_image":
            import base64
            
            # Decode base64 image data
            image_data = base64.b64decode(arguments["image_data"])
            
            # Prepare multipart form data
            files = {
                "file": (arguments["filename"], image_data, "image/jpeg")
            }
            
            # Upload to REST API
            user_id = arguments['user_id']
            upload_url = f"{REST_API_ENDPOINT}/upload-image/{user_id}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(upload_url, files=files)
                response.raise_for_status()
                upload_result = response.json()
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps(upload_result, indent=2),
                )
            ]

        elif name == "search_food_by_barcode":
            query = """
            query SearchBarcode($barcode: String!) {
              atomic {
                searchFoodByBarcode(barcode: $barcode) {
                  barcode
                  name
                  brand
                  nutrients {
                    calories
                    protein
                    carbs
                    fat
                    fiber
                    sugar
                    sodium
                    quantityG
                  }
                  servingSizeG
                  imageUrl
                }
              }
            }
            """
            result = await gql_client.execute(query, {"barcode": arguments["barcode"]})
            product = result.get("atomic", {}).get("searchFoodByBarcode")

            if product is None:
                return [
                    TextContent(
                        type="text",
                        text=f"No product found for barcode: {arguments['barcode']}",
                    )
                ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps(product, indent=2),
                )
            ]

        elif name == "recognize_food":
            query = """
            query RecognizeFood($photoUrl: String, $text: String, $dishHint: String) {
              atomic {
                recognizeFood(photoUrl: $photoUrl, text: $text, dishHint: $dishHint) {
                  items {
                    label
                    displayName
                    quantityG
                    confidence
                  }
                  averageConfidence
                }
              }
            }
            """
            variables = {
                "photoUrl": arguments.get("photo_url"),
                "text": arguments.get("text"),
                "dishHint": arguments.get("dish_hint"),
            }
            result = await gql_client.execute(query, variables)
            recognition = result.get("atomic", {}).get("recognizeFood")

            return [
                TextContent(
                    type="text",
                    text=json.dumps(recognition, indent=2),
                )
            ]

        elif name == "enrich_nutrients":
            label = arguments["label"]
            quantity_g = arguments["quantity_g"]
            
            query = """
            query EnrichNutrients($label: String!, $quantityG: Float!) {
              atomic {
                enrichNutrients(label: $label, quantityG: $quantityG) {
                  calories
                  protein
                  carbs
                  fat
                  fiber
                  sugar
                  sodium
                  quantityG
                }
              }
            }
            """
            result = await gql_client.execute(
                query, {"label": label, "quantityG": quantity_g}
            )
            nutrients = result.get("atomic", {}).get("enrichNutrients")

            if nutrients is None:
                return [
                    TextContent(
                        type="text",
                        text=f"No nutritional data found for: {label}",
                    )
                ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps(nutrients, indent=2),
                )
            ]

        elif name == "analyze_meal_photo":
            query = """
            mutation AnalyzePhoto($input: AnalyzeMealPhotoInput!) {
              meals {
                analyzeMealPhoto(input: $input) {
                  ... on MealAnalysisSuccess {
                    analysisId
                    meal {
                      id
                      dishName
                      confidence
                      entries {
                        id
                        name
                        displayName
                        quantityG
                        calories
                        protein
                        carbs
                        fat
                      }
                      totalCalories
                      totalProtein
                    }
                  }
                  ... on MealAnalysisError {
                    code
                    message
                  }
                }
              }
            }
            """
            input_data = {
                "userId": arguments["user_id"],
                "photoUrl": arguments["photo_url"],
                "mealType": arguments["meal_type"],
            }
            if "dish_hint" in arguments:
                input_data["dishHint"] = arguments["dish_hint"]
            if "timestamp" in arguments:
                input_data["timestamp"] = arguments["timestamp"]

            result = await gql_client.execute(query, {"input": input_data})
            analysis_result = result.get("meals", {}).get("analyzeMealPhoto", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(analysis_result, indent=2),
                )
            ]

        elif name == "analyze_meal_text":
            query = """
            mutation AnalyzeText($input: AnalyzeMealTextInput!) {
              meals {
                analyzeMealText(input: $input) {
                  ... on MealAnalysisSuccess {
                    analysisId
                    meal {
                      id
                      dishName
                      confidence
                      entries {
                        id
                        name
                        displayName
                        quantityG
                        calories
                        protein
                        carbs
                        fat
                      }
                      totalCalories
                      totalProtein
                    }
                  }
                  ... on MealAnalysisError {
                    code
                    message
                  }
                }
              }
            }
            """
            input_data = {
                "userId": arguments["user_id"],
                "textDescription": arguments["text_description"],
                "mealType": arguments["meal_type"],
            }
            if "timestamp" in arguments:
                input_data["timestamp"] = arguments["timestamp"]

            result = await gql_client.execute(query, {"input": input_data})
            analysis_result = result.get("meals", {}).get("analyzeMealText", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(analysis_result, indent=2),
                )
            ]

        elif name == "analyze_meal_barcode":
            query = """
            mutation AnalyzeBarcode($input: AnalyzeMealBarcodeInput!) {
              meals {
                analyzeMealBarcode(input: $input) {
                  ... on MealAnalysisSuccess {
                    analysisId
                    meal {
                      id
                      dishName
                      entries {
                        id
                        name
                        barcode
                        quantityG
                        calories
                        protein
                      }
                      totalCalories
                    }
                  }
                  ... on MealAnalysisError {
                    code
                    message
                  }
                }
              }
            }
            """
            input_data = {
                "userId": arguments["user_id"],
                "barcode": arguments["barcode"],
                "quantityG": arguments["quantity_g"],
                "mealType": arguments["meal_type"],
            }
            if "timestamp" in arguments:
                input_data["timestamp"] = arguments["timestamp"]

            result = await gql_client.execute(query, {"input": input_data})
            analysis_result = result.get("meals", {}).get("analyzeMealBarcode", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(analysis_result, indent=2),
                )
            ]

        elif name == "confirm_meal_analysis":
            query = """
            mutation ConfirmAnalysis($input: ConfirmAnalysisInput!) {
              meals {
                confirmMealAnalysis(input: $input) {
                  ... on ConfirmAnalysisSuccess {
                    meal {
                      id
                      dishName
                      entries { id name calories }
                      totalCalories
                    }
                    confirmedCount
                    rejectedCount
                  }
                  ... on ConfirmAnalysisError {
                    code
                    message
                  }
                }
              }
            }
            """
            # Convert snake_case to camelCase for input
            input_data = {
                "mealId": arguments["meal_id"],
                "userId": arguments["user_id"],
                "confirmedEntryIds": arguments["confirmed_entry_ids"]
            }
            result = await gql_client.execute(query, {"input": input_data})
            confirm_result = result.get("meals", {}).get("confirmMealAnalysis", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(confirm_result, indent=2),
                )
            ]

        elif name == "get_meal":
            query = """
            query GetMeal($mealId: String!, $userId: String!) {
              meals {
                meal(mealId: $mealId, userId: $userId) {
                  id
                  userId
                  timestamp
                  mealType
                  dishName
                  entries {
                    id
                    name
                    displayName
                    quantityG
                    calories
                    protein
                    carbs
                    fat
                    fiber
                    sugar
                    sodium
                  }
                  totalCalories
                  totalProtein
                  totalCarbs
                  totalFat
                }
              }
            }
            """
            # Convert snake_case to camelCase
            variables = {
                "mealId": arguments["meal_id"],
                "userId": arguments["user_id"]
            }
            result = await gql_client.execute(query, variables)
            meal = result.get("meals", {}).get("meal")

            if meal is None:
                return [
                    TextContent(
                        type="text",
                        text=f"Meal not found: {arguments['meal_id']}",
                    )
                ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps(meal, indent=2),
                )
            ]

        elif name == "get_meal_history":
            query = """
            query GetHistory($userId: String!, $startDate: DateTime, $endDate: DateTime, 
                            $mealType: String, $limit: Int!, $offset: Int!) {
              meals {
                mealHistory(userId: $userId, startDate: $startDate, endDate: $endDate,
                           mealType: $mealType, limit: $limit, offset: $offset) {
                  meals {
                    id
                    timestamp
                    mealType
                    dishName
                    totalCalories
                    totalProtein
                  }
                  totalCount
                  hasMore
                }
              }
            }
            """
            # Convert snake_case to camelCase
            variables = {
                "userId": arguments["user_id"],
                "startDate": arguments.get("start_date"),
                "endDate": arguments.get("end_date"),
                "mealType": arguments.get("meal_type"),
                "limit": arguments.get("limit", 20),
                "offset": arguments.get("offset", 0)
            }
            result = await gql_client.execute(query, variables)
            history = result.get("meals", {}).get("mealHistory", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(history, indent=2),
                )
            ]

        elif name == "search_meals":
            query = """
            query SearchMeals($userId: String!, $queryText: String!, $limit: Int!, $offset: Int!) {
              meals {
                search(userId: $userId, queryText: $queryText, limit: $limit, offset: $offset) {
                  meals {
                    id
                    timestamp
                    dishName
                    entries { name calories }
                    totalCalories
                  }
                  totalCount
                }
              }
            }
            """
            # Convert snake_case to camelCase
            variables = {
                "userId": arguments["user_id"],
                "queryText": arguments["query_text"],
                "limit": arguments.get("limit", 20),
                "offset": arguments.get("offset", 0)
            }
            result = await gql_client.execute(query, variables)
            search_results = result.get("meals", {}).get("search", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(search_results, indent=2),
                )
            ]

        elif name == "get_daily_summary":
            query = """
            query DailySummary($userId: String!, $date: DateTime!) {
              meals {
                dailySummary(userId: $userId, date: $date) {
                  date
                  totalCalories
                  totalProtein
                  totalCarbs
                  totalFat
                  totalFiber
                  totalSugar
                  totalSodium
                  mealCount
                  breakdownByType
                }
              }
            }
            """
            # Convert snake_case to camelCase
            variables = {
                "userId": arguments["user_id"],
                "date": arguments["date"]
            }
            result = await gql_client.execute(query, variables)
            summary = result.get("meals", {}).get("dailySummary", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(summary, indent=2),
                )
            ]

        elif name == "get_summary_range":
            query = """
            query SummaryRange($userId: String!, $startDate: DateTime!, $endDate: DateTime!, $groupBy: GroupByPeriod!) {
              meals {
                summaryRange(userId: $userId, startDate: $startDate, endDate: $endDate, groupBy: $groupBy) {
                  periods {
                    period
                    startDate
                    endDate
                    totalCalories
                    totalProtein
                    totalCarbs
                    totalFat
                    mealCount
                    breakdownByType
                  }
                  total {
                    totalCalories
                    totalProtein
                    mealCount
                  }
                }
              }
            }
            """
            # Convert snake_case to camelCase
            variables = {
                "userId": arguments["user_id"],
                "startDate": arguments["start_date"],
                "endDate": arguments["end_date"],
                "groupBy": arguments.get("group_by", "DAY")
            }
            result = await gql_client.execute(query, variables)
            summary_range = result.get("meals", {}).get("summaryRange", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(summary_range, indent=2),
                )
            ]

        elif name == "update_meal":
            query = """
            mutation UpdateMeal($input: UpdateMealInput!) {
              meals {
                updateMeal(input: $input) {
                  ... on UpdateMealSuccess {
                    meal {
                      id
                      mealType
                      timestamp
                      notes
                      totalCalories
                    }
                  }
                  ... on UpdateMealError {
                    code
                    message
                  }
                }
              }
            }
            """
            # Build input with only provided fields
            input_data = {
                "mealId": arguments["meal_id"],
                "userId": arguments["user_id"],
            }
            if "meal_type" in arguments:
                input_data["mealType"] = arguments["meal_type"]
            if "timestamp" in arguments:
                input_data["timestamp"] = arguments["timestamp"]
            if "notes" in arguments:
                input_data["notes"] = arguments["notes"]

            result = await gql_client.execute(query, {"input": input_data})
            update_result = result.get("meals", {}).get("updateMeal", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(update_result, indent=2),
                )
            ]

        elif name == "delete_meal":
            query = """
            mutation DeleteMeal($mealId: String!, $userId: String!) {
              meals {
                deleteMeal(mealId: $mealId, userId: $userId) {
                  ... on DeleteMealSuccess {
                    mealId
                    message
                  }
                  ... on DeleteMealError {
                    code
                    message
                  }
                }
              }
            }
            """
            # Convert snake_case to camelCase
            variables = {
                "mealId": arguments["meal_id"],
                "userId": arguments["user_id"]
            }
            result = await gql_client.execute(query, variables)
            delete_result = result.get("meals", {}).get("deleteMeal", {})

            return [
                TextContent(
                    type="text",
                    text=json.dumps(delete_result, indent=2),
                )
            ]

        else:
            return [
                TextContent(
                    type="text",
                    text=f"Unknown tool: {name}",
                )
            ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error executing {name}: {str(e)}",
            )
        ]


async def main():
    """Run the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
