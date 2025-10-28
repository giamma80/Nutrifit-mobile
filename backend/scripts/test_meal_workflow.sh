#!/bin/bash

# ============================================
# Meal Analysis Workflow Test Script
# ============================================
# 
# Tests the 2-step meal analysis workflow:
# 1. analyzeMealPhoto or analyzeMealBarcode
# 2. confirmMealAnalysis
#
# Usage:
#   ./test_meal_workflow.sh [base_url] [user_id]
#
# Examples:
#   ./test_meal_workflow.sh                              # localhost, test_user
#   ./test_meal_workflow.sh http://localhost:8080        # localhost, test_user
#   ./test_meal_workflow.sh https://api.nutrifit.app     # production, test_user
#   ./test_meal_workflow.sh http://localhost:8080 00001  # localhost, custom user
#
# ============================================

set -e  # Exit on error

# Configuration
BASE_URL="${1:-http://localhost:8080}"
USER_ID="${2:-test_user}"
GRAPHQL_ENDPOINT="${BASE_URL}/graphql"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Nutrifit Meal Workflow Test${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Endpoint: ${YELLOW}${GRAPHQL_ENDPOINT}${NC}"
echo -e "User ID:  ${YELLOW}${USER_ID}${NC}"
echo ""

# ============================================
# TEST 1: Photo Analysis → Confirm
# ============================================

echo -e "${GREEN}🧪 Test 1: Photo Analysis Workflow${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

PHOTO_URL="https://llcqkesfwgkncxculmhf.supabase.co/storage/v1/object/public/meal-photos/000001/1759863035_D526FF2F.jpg"

echo "Step 1: Analyzing meal photo..."
echo "Photo: ${PHOTO_URL}"

ANALYZE_PHOTO_RESPONSE=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"mutation AnalyzePhoto(\$input: AnalyzeMealPhotoInput!) { meal { analyzeMealPhoto(input: \$input) { ... on MealAnalysisSuccess { meal { id entries { id name quantityG calories protein carbs fat sodium } totalCalories totalProtein totalCarbs totalFat totalSodium } analysisId } ... on MealAnalysisError { message code } } } }\",
    \"variables\": {
      \"input\": {
        \"userId\": \"${USER_ID}\",
        \"photoUrl\": \"${PHOTO_URL}\",
        \"mealType\": \"LUNCH\"
      }
    }
  }")

# Check for errors
if echo "$ANALYZE_PHOTO_RESPONSE" | grep -q '"errors"'; then
  echo -e "${RED}❌ Error analyzing photo:${NC}"
  echo "$ANALYZE_PHOTO_RESPONSE" | jq '.'
  exit 1
fi

# Extract meal ID and entry IDs
MEAL_ID=$(echo "$ANALYZE_PHOTO_RESPONSE" | jq -r '.data.meal.analyzeMealPhoto.meal.id')
ENTRY_IDS=$(echo "$ANALYZE_PHOTO_RESPONSE" | jq -r '.data.meal.analyzeMealPhoto.meal.entries[].id')
ENTRY_COUNT=$(echo "$ENTRY_IDS" | wc -l | tr -d ' ')

echo -e "${GREEN}✅ Photo analyzed successfully!${NC}"
echo "Meal ID: ${MEAL_ID}"
echo "Entries detected: ${ENTRY_COUNT}"
echo ""
echo "Detected foods:"
echo "$ANALYZE_PHOTO_RESPONSE" | jq -r '.data.meal.analyzeMealPhoto.meal.entries[] | "  - \(.name): \(.quantityG)g → \(.calories) kcal"'
echo ""

# Convert entry IDs to JSON array
CONFIRMED_ENTRY_IDS=$(echo "$ENTRY_IDS" | jq -R . | jq -s .)

echo "Step 2: Confirming all entries..."

CONFIRM_RESPONSE=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"mutation ConfirmAnalysis(\$input: ConfirmAnalysisInput!) { meal { confirmMealAnalysis(input: \$input) { ... on ConfirmAnalysisSuccess { meal { id entries { id name quantityG calories } totalCalories totalProtein totalCarbs totalFat totalSodium } confirmedCount rejectedCount } ... on ConfirmAnalysisError { message code } } } }\",
    \"variables\": {
      \"input\": {
        \"mealId\": \"${MEAL_ID}\",
        \"userId\": \"${USER_ID}\",
        \"confirmedEntryIds\": ${CONFIRMED_ENTRY_IDS}
      }
    }
  }")

# Check for errors
if echo "$CONFIRM_RESPONSE" | grep -q '"errors"'; then
  echo -e "${RED}❌ Error confirming analysis:${NC}"
  echo "$CONFIRM_RESPONSE" | jq '.'
  exit 1
fi

CONFIRMED_COUNT=$(echo "$CONFIRM_RESPONSE" | jq -r '.data.meal.confirmMealAnalysis.confirmedCount')
TOTAL_CALORIES=$(echo "$CONFIRM_RESPONSE" | jq -r '.data.meal.confirmMealAnalysis.meal.totalCalories')
TOTAL_PROTEIN=$(echo "$CONFIRM_RESPONSE" | jq -r '.data.meal.confirmMealAnalysis.meal.totalProtein')
TOTAL_CARBS=$(echo "$CONFIRM_RESPONSE" | jq -r '.data.meal.confirmMealAnalysis.meal.totalCarbs')
TOTAL_FAT=$(echo "$CONFIRM_RESPONSE" | jq -r '.data.meal.confirmMealAnalysis.meal.totalFat')
TOTAL_SODIUM=$(echo "$CONFIRM_RESPONSE" | jq -r '.data.meal.confirmMealAnalysis.meal.totalSodium')

echo -e "${GREEN}✅ Analysis confirmed successfully!${NC}"
echo "Confirmed entries: ${CONFIRMED_COUNT}/${ENTRY_COUNT}"
echo ""
echo "Final nutrition totals:"
echo "  Calories: ${TOTAL_CALORIES} kcal"
echo "  Protein:  ${TOTAL_PROTEIN} g"
echo "  Carbs:    ${TOTAL_CARBS} g"
echo "  Fat:      ${TOTAL_FAT} g"
echo "  Sodium:   ${TOTAL_SODIUM} mg"
echo ""

# ============================================
# TEST 2: Barcode Analysis → Confirm
# ============================================

echo -e "${GREEN}🧪 Test 2: Barcode Analysis Workflow${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

BARCODE="8076800195057"

echo "Step 1: Analyzing barcode..."
echo "Barcode: ${BARCODE}"

ANALYZE_BARCODE_RESPONSE=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"mutation AnalyzeBarcode(\$input: AnalyzeMealBarcodeInput!) { meal { analyzeMealBarcode(input: \$input) { ... on MealAnalysisSuccess { meal { id entries { id name quantityG calories protein carbs fat sodium } totalCalories totalProtein totalCarbs totalFat totalSodium } analysisId } ... on MealAnalysisError { message code } } } }\",
    \"variables\": {
      \"input\": {
        \"userId\": \"${USER_ID}\",
        \"barcode\": \"${BARCODE}\",
        \"quantityG\": 100.0,
        \"mealType\": \"SNACK\"
      }
    }
  }")

# Check for errors
if echo "$ANALYZE_BARCODE_RESPONSE" | grep -q '"errors"'; then
  echo -e "${RED}❌ Error analyzing barcode:${NC}"
  echo "$ANALYZE_BARCODE_RESPONSE" | jq '.'
  exit 1
fi

# Extract meal ID and entry IDs
MEAL_ID_2=$(echo "$ANALYZE_BARCODE_RESPONSE" | jq -r '.data.meal.analyzeMealBarcode.meal.id')
ENTRY_IDS_2=$(echo "$ANALYZE_BARCODE_RESPONSE" | jq -r '.data.meal.analyzeMealBarcode.meal.entries[].id')
ENTRY_COUNT_2=$(echo "$ENTRY_IDS_2" | wc -l | tr -d ' ')

echo -e "${GREEN}✅ Barcode analyzed successfully!${NC}"
echo "Meal ID: ${MEAL_ID_2}"
echo "Entries detected: ${ENTRY_COUNT_2}"
echo ""
echo "Detected product:"
echo "$ANALYZE_BARCODE_RESPONSE" | jq -r '.data.meal.analyzeMealBarcode.meal.entries[] | "  - \(.name): \(.quantityG)g → \(.calories) kcal"'
echo ""

# Convert entry IDs to JSON array
CONFIRMED_ENTRY_IDS_2=$(echo "$ENTRY_IDS_2" | jq -R . | jq -s .)

echo "Step 2: Confirming all entries..."

CONFIRM_RESPONSE_2=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"mutation ConfirmAnalysis(\$input: ConfirmAnalysisInput!) { meal { confirmMealAnalysis(input: \$input) { ... on ConfirmAnalysisSuccess { meal { id entries { id name quantityG calories } totalCalories totalProtein totalCarbs totalFat totalSodium } confirmedCount rejectedCount } ... on ConfirmAnalysisError { message code } } } }\",
    \"variables\": {
      \"input\": {
        \"mealId\": \"${MEAL_ID_2}\",
        \"userId\": \"${USER_ID}\",
        \"confirmedEntryIds\": ${CONFIRMED_ENTRY_IDS_2}
      }
    }
  }")

# Check for errors
if echo "$CONFIRM_RESPONSE_2" | grep -q '"errors"'; then
  echo -e "${RED}❌ Error confirming analysis:${NC}"
  echo "$CONFIRM_RESPONSE_2" | jq '.'
  exit 1
fi

CONFIRMED_COUNT_2=$(echo "$CONFIRM_RESPONSE_2" | jq -r '.data.meal.confirmMealAnalysis.confirmedCount')
TOTAL_CALORIES_2=$(echo "$CONFIRM_RESPONSE_2" | jq -r '.data.meal.confirmMealAnalysis.meal.totalCalories')
TOTAL_PROTEIN_2=$(echo "$CONFIRM_RESPONSE_2" | jq -r '.data.meal.confirmMealAnalysis.meal.totalProtein')
TOTAL_CARBS_2=$(echo "$CONFIRM_RESPONSE_2" | jq -r '.data.meal.confirmMealAnalysis.meal.totalCarbs')
TOTAL_FAT_2=$(echo "$CONFIRM_RESPONSE_2" | jq -r '.data.meal.confirmMealAnalysis.meal.totalFat')
TOTAL_SODIUM_2=$(echo "$CONFIRM_RESPONSE_2" | jq -r '.data.meal.confirmMealAnalysis.meal.totalSodium')

echo -e "${GREEN}✅ Analysis confirmed successfully!${NC}"
echo "Confirmed entries: ${CONFIRMED_COUNT_2}/${ENTRY_COUNT_2}"
echo ""
echo "Final nutrition totals:"
echo "  Calories: ${TOTAL_CALORIES_2} kcal"
echo "  Protein:  ${TOTAL_PROTEIN_2} g"
echo "  Carbs:    ${TOTAL_CARBS_2} g"
echo "  Fat:      ${TOTAL_FAT_2} g"
echo "  Sodium:   ${TOTAL_SODIUM_2} mg"
echo ""

# ============================================
# Summary
# ============================================

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ All tests completed successfully!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Test 1 (Photo):   ${MEAL_ID}"
echo "  → ${CONFIRMED_COUNT} entries, ${TOTAL_CALORIES} kcal"
echo ""
echo "Test 2 (Barcode): ${MEAL_ID_2}"
echo "  → ${CONFIRMED_COUNT_2} entries, ${TOTAL_CALORIES_2} kcal"
echo ""
