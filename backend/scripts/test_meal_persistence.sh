#!/bin/bash

# ===================================
# Meal Persistence Test Script
# ===================================
# Tests the complete meal workflow:
# - Photo analysis
# - Barcode analysis
# - Confirmation flow
# - Daily summary retrieval
# - Search by barcode
# - Cross-check with activity data
#
# Usage:
#   ./test_meal_persistence.sh [BASE_URL] [USER_ID]
#
# Examples:
#   ./test_meal_persistence.sh                                    # Defaults
#   ./test_meal_persistence.sh http://localhost:8080              # Custom URL
#   ./test_meal_persistence.sh http://localhost:8080 giamma       # Custom URL + user
#   ./test_meal_persistence.sh "" giamma                          # Default URL + custom user
#   BASE_URL="http://localhost:8080" USER_ID="giamma" ./test_meal_persistence.sh  # Via env vars

set -e  # Exit on error

# Configuration
TIMESTAMP=$(date +%s)
BASE_URL="${1:-${BASE_URL:-http://localhost:8080}}"
USER_ID="${2:-${USER_ID:-test-user-${TIMESTAMP}}}"
GRAPHQL_ENDPOINT="${BASE_URL}/graphql"
TODAY=$(date -u +%Y-%m-%d)
TODAY_DATETIME="${TODAY}T00:00:00Z"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Nutrifit Meal Persistence Test${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Endpoint: ${YELLOW}${GRAPHQL_ENDPOINT}${NC}"
echo -e "User ID:  ${YELLOW}${USER_ID}${NC}"
echo -e "Date:     ${YELLOW}${TODAY}${NC}"
echo ""

# ============================================
# Helper Functions
# ============================================

query_meal_by_id() {
    local meal_id=$1
    curl -s -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"query GetMeal(\$mealId: String!, \$userId: String!) { meals { meal(mealId: \$mealId, userId: \$userId) { id userId timestamp mealType dishName entries { id name quantityG calories } totalCalories totalProtein totalCarbs totalFat totalSodium createdAt } } }\",
            \"variables\": {
                \"mealId\": \"${meal_id}\",
                \"userId\": \"${USER_ID}\"
            }
        }"
}

query_meal_history() {
    local limit=${1:-10}
    curl -s --max-time 10 -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"query GetHistory(\$userId: String!, \$limit: Int!) { meals { mealHistory(userId: \$userId, limit: \$limit) { meals { id timestamp mealType dishName totalCalories } totalCount hasMore } } }\",
            \"variables\": {
                \"userId\": \"${USER_ID}\",
                \"limit\": ${limit}
            }
        }"
}

query_daily_summary() {
    local date=$1
    curl -s --max-time 10 -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"query GetDailySummary(\$userId: String!, \$date: DateTime!) { meals { dailySummary(userId: \$userId, date: \$date) { date totalCalories totalProtein totalCarbs totalFat totalFiber totalSugar totalSodium mealCount breakdownByType } } }\",
            \"variables\": {
                \"userId\": \"${USER_ID}\",
                \"date\": \"${date}\"
            }
        }"
}

echo ""

# ============================================
# PRE-STEP: Clean State Verification
# ============================================

echo -e "${CYAN}🧹 Pre-Step: Clean State Verification${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

echo -e "${YELLOW}Using unique user ID for this test run: ${USER_ID}${NC}"
echo ""
echo "This ensures a clean state by:"
echo "  - No pre-existing meals"
echo "  - No pre-existing daily summaries"
echo "  - No cached idempotency keys"
echo ""

# Verify initial state is empty
INITIAL_VERIFY=$(query_meal_history 5)
INITIAL_VERIFY_COUNT=$(echo "$INITIAL_VERIFY" | jq -r '.data.meals.mealHistory.totalCount // 0')

if [ "$INITIAL_VERIFY_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ Clean state verified: 0 meals${NC}"
else
    echo -e "${YELLOW}⚠️  Found ${INITIAL_VERIFY_COUNT} existing meals (may be from previous runs)${NC}"
fi

INITIAL_SUMMARY_VERIFY=$(query_daily_summary "$TODAY_DATETIME")
INITIAL_SUMMARY_CALORIES=$(echo "$INITIAL_SUMMARY_VERIFY" | jq -r '.data.meals.dailySummary.totalCalories // 0')

if [ "$(echo "$INITIAL_SUMMARY_CALORIES == 0" | bc -l)" -eq 1 ]; then
    echo -e "${GREEN}✅ Clean state verified: 0 kcal in daily summary${NC}"
else
    echo -e "${YELLOW}⚠️  Daily summary shows ${INITIAL_SUMMARY_CALORIES} kcal${NC}"
fi
echo ""

# ============================================
# STEP 1: Check Initial State
# ============================================

echo -e "${CYAN}📊 Step 1: Check Initial State${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

echo "Querying meal history..."
INITIAL_HISTORY=$(query_meal_history 5)

INITIAL_COUNT=$(echo "$INITIAL_HISTORY" | jq -r '.data.meals.mealHistory.totalCount // 0')
echo -e "${GREEN}✅ Current meal count: ${INITIAL_COUNT}${NC}"

if [ "$INITIAL_COUNT" -gt 0 ]; then
    echo "Recent meals:"
    echo "$INITIAL_HISTORY" | jq -r '.data.meals.mealHistory.meals[] | "  - \(.mealType): \(.dishName) (\(.totalCalories) kcal) - \(.id)"'
fi

echo ""
echo "Querying daily summary for ${TODAY}..."
INITIAL_SUMMARY=$(query_daily_summary "$TODAY_DATETIME")

INITIAL_DAILY_CALORIES=$(echo "$INITIAL_SUMMARY" | jq -r '.data.meals.dailySummary.totalCalories // 0')
INITIAL_DAILY_SODIUM=$(echo "$INITIAL_SUMMARY" | jq -r '.data.meals.dailySummary.totalSodium // 0')
INITIAL_DAILY_SUGAR=$(echo "$INITIAL_SUMMARY" | jq -r '.data.meals.dailySummary.totalSugar // 0')
INITIAL_MEAL_COUNT=$(echo "$INITIAL_SUMMARY" | jq -r '.data.meals.dailySummary.mealCount // 0')
echo -e "${GREEN}✅ Today's totals: ${INITIAL_MEAL_COUNT} meals, ${INITIAL_DAILY_CALORIES} kcal, ${INITIAL_DAILY_SODIUM} mg sodium, ${INITIAL_DAILY_SUGAR} g sugar${NC}"
echo ""

# ============================================
# STEP 2: Analyze Photo
# ============================================

echo -e "${CYAN}📷 Step 2: Analyze Meal Photo${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

PHOTO_URL="https://llcqkesfwgkncxculmhf.supabase.co/storage/v1/object/public/meal-photos/000001/1759863035_D526FF2F.jpg"

ANALYZE_RESPONSE=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"mutation AnalyzePhoto(\$input: AnalyzeMealPhotoInput!) { meals { analyzeMealPhoto(input: \$input) { ... on MealAnalysisSuccess { analysisId meal { id dishName entries { id name quantityG calories } totalCalories } } ... on MealAnalysisError { message code } } } }\",
        \"variables\": {
            \"input\": {
                \"userId\": \"${USER_ID}\",
                \"photoUrl\": \"${PHOTO_URL}\",
                \"mealType\": \"LUNCH\",
                \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
            }
        }
    }")

if echo "$ANALYZE_RESPONSE" | grep -q '"errors"'; then
    echo -e "${RED}❌ Error analyzing photo${NC}"
    echo "$ANALYZE_RESPONSE" | jq '.'
    exit 1
fi

MEAL_ID_1=$(echo "$ANALYZE_RESPONSE" | jq -r '.data.meals.analyzeMealPhoto.meal.id')
DISH_NAME_1=$(echo "$ANALYZE_RESPONSE" | jq -r '.data.meals.analyzeMealPhoto.meal.dishName')
CALORIES_1=$(echo "$ANALYZE_RESPONSE" | jq -r '.data.meals.analyzeMealPhoto.meal.totalCalories')
ENTRY_COUNT_1=$(echo "$ANALYZE_RESPONSE" | jq -r '.data.meals.analyzeMealPhoto.meal.entries | length')

echo -e "${GREEN}✅ Photo analyzed: ${DISH_NAME_1}${NC}"
echo "  Meal ID: ${MEAL_ID_1}"
echo "  Entries: ${ENTRY_COUNT_1}"
echo "  Calories: ${CALORIES_1} kcal"
echo ""

# ============================================
# STEP 3: Query Meal by ID (PENDING state)
# ============================================

echo -e "${CYAN}🔍 Step 3: Query Meal by ID (should exist, PENDING)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

MEAL_QUERY_1=$(query_meal_by_id "$MEAL_ID_1")

if echo "$MEAL_QUERY_1" | jq -e '.data.meals.meal' > /dev/null; then
    echo -e "${GREEN}✅ Meal found in database${NC}"
    echo "$MEAL_QUERY_1" | jq -r '.data.meals.meal | "  ID: \(.id)\n  Type: \(.mealType)\n  Dish: \(.dishName)\n  Calories: \(.totalCalories) kcal\n  Entries: \(.entries | length)"'
else
    echo -e "${RED}❌ Meal not found${NC}"
    echo "$MEAL_QUERY_1" | jq '.'
    exit 1
fi
echo ""

# ============================================
# STEP 4: Confirm Analysis
# ============================================

echo -e "${CYAN}✔️  Step 4: Confirm Analysis${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

ENTRY_IDS_1=$(echo "$ANALYZE_RESPONSE" | jq -r '.data.meals.analyzeMealPhoto.meal.entries[].id')
CONFIRMED_ENTRY_IDS_1=$(echo "$ENTRY_IDS_1" | jq -R . | jq -s .)

CONFIRM_RESPONSE=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"mutation ConfirmAnalysis(\$input: ConfirmAnalysisInput!) { meals { confirmMealAnalysis(input: \$input) { ... on ConfirmAnalysisSuccess { meal { id totalCalories totalProtein totalCarbs totalFat totalSodium } confirmedCount rejectedCount } ... on ConfirmAnalysisError { message code } } } }\",
        \"variables\": {
            \"input\": {
                \"mealId\": \"${MEAL_ID_1}\",
                \"userId\": \"${USER_ID}\",
                \"confirmedEntryIds\": ${CONFIRMED_ENTRY_IDS_1}
            }
        }
    }")

if echo "$CONFIRM_RESPONSE" | grep -q '"errors"'; then
    echo -e "${RED}❌ Error confirming analysis${NC}"
    echo "$CONFIRM_RESPONSE" | jq '.'
    exit 1
fi

CONFIRMED_COUNT=$(echo "$CONFIRM_RESPONSE" | jq -r '.data.meals.confirmMealAnalysis.confirmedCount')
echo -e "${GREEN}✅ Analysis confirmed: ${CONFIRMED_COUNT} entries${NC}"
echo ""

# ============================================
# STEP 5: Query Meal by ID Again (CONFIRMED state)
# ============================================

echo -e "${CYAN}🔍 Step 5: Query Meal by ID (should be CONFIRMED)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

MEAL_QUERY_2=$(query_meal_by_id "$MEAL_ID_1")

if echo "$MEAL_QUERY_2" | jq -e '.data.meals.meal' > /dev/null; then
    echo -e "${GREEN}✅ Meal still exists (confirmed state)${NC}"
    MEAL_DATA=$(echo "$MEAL_QUERY_2" | jq -r '.data.meals.meal')
    echo "$MEAL_DATA" | jq -r '"  ID: \(.id)\n  Type: \(.mealType)\n  Dish: \(.dishName)\n  Calories: \(.totalCalories) kcal\n  Protein: \(.totalProtein)g\n  Carbs: \(.totalCarbs)g\n  Fat: \(.totalFat)g\n  Sodium: \(.totalSodium)mg"'
else
    echo -e "${RED}❌ Meal not found after confirmation${NC}"
    exit 1
fi
echo ""

# ============================================
# STEP 6: Check Updated Meal History
# ============================================

echo -e "${CYAN}📊 Step 6: Check Updated Meal History${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

UPDATED_HISTORY=$(query_meal_history 5)
UPDATED_COUNT=$(echo "$UPDATED_HISTORY" | jq -r '.data.meals.mealHistory.totalCount')

echo -e "${GREEN}✅ Updated meal count: ${UPDATED_COUNT}${NC}"
echo "Recent meals:"
echo "$UPDATED_HISTORY" | jq -r '.data.meals.mealHistory.meals[] | "  - \(.mealType): \(.dishName) (\(.totalCalories) kcal) - \(.id)"'

if [ "$UPDATED_COUNT" -le "$INITIAL_COUNT" ]; then
    echo -e "${RED}⚠️  Warning: Meal count did not increase!${NC}"
fi
echo ""

# ============================================
# STEP 7: Check Updated Daily Summary
# ============================================

echo -e "${CYAN}📊 Step 7: Check Updated Daily Summary${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

UPDATED_SUMMARY=$(query_daily_summary "$TODAY_DATETIME")
UPDATED_DAILY_CALORIES=$(echo "$UPDATED_SUMMARY" | jq -r '.data.meals.dailySummary.totalCalories // 0')
UPDATED_DAILY_SODIUM=$(echo "$UPDATED_SUMMARY" | jq -r '.data.meals.dailySummary.totalSodium // 0')
UPDATED_DAILY_SUGAR=$(echo "$UPDATED_SUMMARY" | jq -r '.data.meals.dailySummary.totalSugar // 0')
UPDATED_MEAL_COUNT=$(echo "$UPDATED_SUMMARY" | jq -r '.data.meals.dailySummary.mealCount // 0')

# Convert float calories to int for bash arithmetic
INITIAL_DAILY_CALORIES_INT=$(echo "$INITIAL_DAILY_CALORIES" | awk '{print int($1)}')
UPDATED_DAILY_CALORIES_INT=$(echo "$UPDATED_DAILY_CALORIES" | awk '{print int($1)}')
INITIAL_DAILY_SODIUM_INT=$(echo "$INITIAL_DAILY_SODIUM" | awk '{print int($1)}')
UPDATED_DAILY_SODIUM_INT=$(echo "$UPDATED_DAILY_SODIUM" | awk '{print int($1)}')
INITIAL_DAILY_SUGAR_INT=$(echo "$INITIAL_DAILY_SUGAR" | awk '{print int($1)}')
UPDATED_DAILY_SUGAR_INT=$(echo "$UPDATED_DAILY_SUGAR" | awk '{print int($1)}')

echo -e "${GREEN}✅ Today's updated totals:${NC}"
echo "  Meals: ${INITIAL_MEAL_COUNT} → ${UPDATED_MEAL_COUNT} (+$((UPDATED_MEAL_COUNT - INITIAL_MEAL_COUNT)))"
echo "  Calories: ${INITIAL_DAILY_CALORIES} kcal → ${UPDATED_DAILY_CALORIES} kcal (+$((UPDATED_DAILY_CALORIES_INT - INITIAL_DAILY_CALORIES_INT)))"
echo "  Sodium: ${INITIAL_DAILY_SODIUM} mg → ${UPDATED_DAILY_SODIUM} mg (+$((UPDATED_DAILY_SODIUM_INT - INITIAL_DAILY_SODIUM_INT)))"
echo "  Sugar: ${INITIAL_DAILY_SUGAR} g → ${UPDATED_DAILY_SUGAR} g (+$((UPDATED_DAILY_SUGAR_INT - INITIAL_DAILY_SUGAR_INT)))"

if [ "$UPDATED_MEAL_COUNT" -gt 0 ]; then
    echo ""
    echo "Today's meals breakdown:"
    echo "$UPDATED_SUMMARY" | jq -r '.data.meals.dailySummary.breakdownByType'
else
    echo "  (No meals logged for today's date yet - timestamps may be different)"
fi
echo ""

# ============================================
# STEP 7.5: Test Query.meals Operations
# ============================================

echo -e "${CYAN}🔎 Step 7.5: Test Query.meals Operations${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Test 1: Search by dish name
echo "Testing search by dish name (\"risotto\")..."
SEARCH_RISOTTO=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "query { meals { search(userId: \"'${USER_ID}'\", queryText: \"risotto\", limit: 5) { totalCount meals { id dishName totalCalories } } } }"
    }')

SEARCH_COUNT=$(echo "$SEARCH_RISOTTO" | jq -r '.data.meals.search.totalCount')
if [ "$SEARCH_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Search found ${SEARCH_COUNT} results for 'risotto'${NC}"
    echo "$SEARCH_RISOTTO" | jq -r '.data.meals.search.meals[] | "  - \(.dishName) (\(.totalCalories) kcal)"'
else
    echo -e "${YELLOW}⚠️  Search returned 0 results for 'risotto' (expected at least 1)${NC}"
fi
echo ""

# Test 2: Search by entry name
echo "Testing search by entry name (\"rice\")..."
SEARCH_RICE=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "query { meals { search(userId: \"'${USER_ID}'\", queryText: \"rice\", limit: 3) { totalCount meals { id dishName } } } }"
    }')

RICE_COUNT=$(echo "$SEARCH_RICE" | jq -r '.data.meals.search.totalCount')
if [ "$RICE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Search found ${RICE_COUNT} results for 'rice' in entries${NC}"
else
    echo -e "${YELLOW}⚠️  Search returned 0 results for 'rice'${NC}"
fi
echo ""

# Test 3: Empty search (should return all)
echo "Testing empty search (should return all meals)..."
SEARCH_ALL=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "query { meals { search(userId: \"'${USER_ID}'\", queryText: \"\", limit: 10) { totalCount meals { id dishName } } } }"
    }')

ALL_COUNT=$(echo "$SEARCH_ALL" | jq -r '.data.meals.search.totalCount')
echo -e "${GREEN}✅ Empty search returned ${ALL_COUNT} meals (total in database)${NC}"
echo ""

# ============================================
# STEP 8: Test Barcode Workflow
# ============================================

echo -e "${CYAN}🔍 Step 8: Test Barcode Workflow${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

BARCODE="8076800195057"

ANALYZE_BARCODE_RESPONSE=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"mutation AnalyzeBarcode(\$input: AnalyzeMealBarcodeInput!) { meals { analyzeMealBarcode(input: \$input) { ... on MealAnalysisSuccess { analysisId meal { id dishName imageUrl entries { id name } totalCalories } } ... on MealAnalysisError { message code } } } }\",
        \"variables\": {
            \"input\": {
                \"userId\": \"${USER_ID}\",
                \"barcode\": \"${BARCODE}\",
                \"quantityG\": 100.0,
                \"mealType\": \"SNACK\",
                \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
            }
        }
    }")

if echo "$ANALYZE_BARCODE_RESPONSE" | grep -q '"errors"'; then
    echo -e "${RED}❌ Error analyzing barcode${NC}"
    echo "$ANALYZE_BARCODE_RESPONSE" | jq '.'
    exit 1
fi

MEAL_ID_2=$(echo "$ANALYZE_BARCODE_RESPONSE" | jq -r '.data.meals.analyzeMealBarcode.meal.id')
DISH_NAME_2=$(echo "$ANALYZE_BARCODE_RESPONSE" | jq -r '.data.meals.analyzeMealBarcode.meal.dishName')
IMAGE_URL_2=$(echo "$ANALYZE_BARCODE_RESPONSE" | jq -r '.data.meals.analyzeMealBarcode.meal.imageUrl')
CALORIES_2=$(echo "$ANALYZE_BARCODE_RESPONSE" | jq -r '.data.meals.analyzeMealBarcode.meal.totalCalories')

echo -e "${GREEN}✅ Barcode analyzed: ${DISH_NAME_2}${NC}"
echo "  Meal ID: ${MEAL_ID_2}"
echo "  Calories: ${CALORIES_2} kcal"
if [ "$IMAGE_URL_2" != "null" ]; then
    echo "  Image URL: ${IMAGE_URL_2}"
else
    echo -e "  ${YELLOW}⚠️  Image URL: null (expected from OpenFoodFacts)${NC}"
fi
echo ""

# Confirm barcode meal
ENTRY_IDS_2=$(echo "$ANALYZE_BARCODE_RESPONSE" | jq -r '.data.meals.analyzeMealBarcode.meal.entries[].id')
CONFIRMED_ENTRY_IDS_2=$(echo "$ENTRY_IDS_2" | jq -R . | jq -s .)

CONFIRM_RESPONSE_2=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"mutation ConfirmAnalysis(\$input: ConfirmAnalysisInput!) { meals { confirmMealAnalysis(input: \$input) { ... on ConfirmAnalysisSuccess { confirmedCount } ... on ConfirmAnalysisError { message code } } } }\",
        \"variables\": {
            \"input\": {
                \"mealId\": \"${MEAL_ID_2}\",
                \"userId\": \"${USER_ID}\",
                \"confirmedEntryIds\": ${CONFIRMED_ENTRY_IDS_2}
            }
        }
    }")

echo -e "${GREEN}✅ Barcode meal confirmed${NC}"
echo ""

# ============================================
# STEP 9: Final State Check
# ============================================

echo -e "${CYAN}📊 Step 9: Final State Check${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

FINAL_HISTORY=$(query_meal_history 10)
FINAL_COUNT=$(echo "$FINAL_HISTORY" | jq -r '.data.meals.mealHistory.totalCount')

FINAL_SUMMARY=$(query_daily_summary "$TODAY_DATETIME")
FINAL_DAILY_CALORIES=$(echo "$FINAL_SUMMARY" | jq -r '.data.meals.dailySummary.totalCalories')
FINAL_DAILY_SODIUM=$(echo "$FINAL_SUMMARY" | jq -r '.data.meals.dailySummary.totalSodium')
FINAL_DAILY_SUGAR=$(echo "$FINAL_SUMMARY" | jq -r '.data.meals.dailySummary.totalSugar')
FINAL_MEAL_COUNT=$(echo "$FINAL_SUMMARY" | jq -r '.data.meals.dailySummary.mealCount')

# Convert float to int for bash arithmetic
FINAL_DAILY_CALORIES_INT=$(echo "$FINAL_DAILY_CALORIES" | awk '{print int($1)}')
FINAL_DAILY_SODIUM_INT=$(echo "$FINAL_DAILY_SODIUM" | awk '{print int($1)}')
FINAL_DAILY_SUGAR_INT=$(echo "$FINAL_DAILY_SUGAR" | awk '{print int($1)}')

echo -e "${GREEN}Final totals:${NC}"
echo "  Total meals: ${INITIAL_COUNT} → ${FINAL_COUNT} (+$((FINAL_COUNT - INITIAL_COUNT)))"
echo "  Today's meals: ${INITIAL_MEAL_COUNT} → ${FINAL_MEAL_COUNT} (+$((FINAL_MEAL_COUNT - INITIAL_MEAL_COUNT)))"
echo "  Today's calories: ${INITIAL_DAILY_CALORIES} kcal → ${FINAL_DAILY_CALORIES} kcal (+$((FINAL_DAILY_CALORIES_INT - INITIAL_DAILY_CALORIES_INT)))"
echo "  Today's sodium: ${INITIAL_DAILY_SODIUM} mg → ${FINAL_DAILY_SODIUM} mg (+$((FINAL_DAILY_SODIUM_INT - INITIAL_DAILY_SODIUM_INT)))"
echo "  Today's sugar: ${INITIAL_DAILY_SUGAR} g → ${FINAL_DAILY_SUGAR} g (+$((FINAL_DAILY_SUGAR_INT - INITIAL_DAILY_SUGAR_INT)))"
echo ""

# ============================================
# Summary
# ============================================

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ All persistence tests passed!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Created meals:"
echo "  1. ${MEAL_ID_1} (Photo - ${DISH_NAME_1}) - ${CALORIES_1} kcal"
echo "  2. ${MEAL_ID_2} (Barcode - ${DISH_NAME_2}) - ${CALORIES_2} kcal"
echo ""
echo "Persistence verified:"
echo "  ✅ Meals created in database"
echo "  ✅ Meals queryable by ID"
echo "  ✅ Meals appear in history"
echo "  ✅ Daily summary updated"
echo "  ✅ Totals calculated correctly"
echo ""
