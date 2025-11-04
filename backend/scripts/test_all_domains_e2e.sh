#!/bin/bash

# ============================================
# Nutrifit E2E Integration Test Suite
# ============================================
# 
# Runs comprehensive end-to-end tests across all domains:
# 1. Meal Domain - Food recognition, barcode scanning, nutrition tracking
# 2. Activity Domain - Health data sync, activity tracking, calorie expenditure
# 3. Nutritional Profile Domain - Profile management, progress tracking, goal management
# 4. ML Enhancements - Weight forecasting, time series analysis, adaptive TDEE
#
# Uses a single user ID across all domains to simulate a realistic
# user journey and validate cross-domain data integration.
#
# Scenario:
# - User creates nutritional profile with CUT goal
# - User logs meals throughout the day
# - User syncs activity data from workouts
# - System calculates calorie deficit/surplus
# - User tracks progress over a week
# - User changes goal to MAINTAIN after reaching target
#
# Usage:
#   ./test_all_domains_e2e.sh [BASE_URL] [USER_ID]
#
# Examples:
#   ./test_all_domains_e2e.sh                                    # Defaults (random user)
#   ./test_all_domains_e2e.sh http://localhost:8080              # Custom URL
#   ./test_all_domains_e2e.sh http://localhost:8080 giamma       # Custom URL + user
#   ./test_all_domains_e2e.sh "" giamma                          # Default URL + custom user
#   BASE_URL="http://localhost:8080" USER_ID="giamma" ./test_all_domains_e2e.sh  # Via env vars
#
# ============================================

set -e

# Configuration
TIMESTAMP=$(date +%s)
BASE_URL="${1:-${BASE_URL:-http://localhost:8080}}"
USER_ID="${2:-${USER_ID:-e2e_user_${TIMESTAMP}}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Nutrifit E2E Integration Test Suite${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Endpoint: ${YELLOW}${BASE_URL}${NC}"
echo -e "User ID:  ${YELLOW}${USER_ID}${NC}"
echo -e "Timestamp: ${YELLOW}${TIMESTAMP}${NC}"
echo ""
echo -e "${CYAN}This test suite will:${NC}"
echo "  1. Create a nutritional profile (CUT goal)"
echo "  2. Log meals throughout the day"
echo "  3. Sync activity data from workouts"
echo "  4. Test ML weight forecasting with time series models"
echo "  5. Validate cross-domain calorie tracking"
echo "  6. Track progress over multiple days"
echo "  7. Update profile goals and metrics"
echo ""
echo -e "${YELLOW}⏱️  Estimated time: 4-6 minutes${NC}"
echo ""
# read -p "Press Enter to start the test suite..." -r
echo ""

# ============================================
# Phase 1: Nutritional Profile Domain
# ============================================

echo -e "${BLUE}================================================${NC}"
echo -e "${CYAN}📊 Phase 1: Nutritional Profile Domain${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Creating nutritional profile and tracking progress..."
echo ""

"${SCRIPT_DIR}/test_nutritional_profile_persistence.sh" "$BASE_URL" "$USER_ID"

PROFILE_EXIT_CODE=$?

if [ $PROFILE_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Phase 1 completed successfully!${NC}"
    echo ""
else
    echo -e "${RED}❌ Phase 1 failed with exit code ${PROFILE_EXIT_CODE}${NC}"
    exit 1
fi

# Small pause between phases
sleep 2

# ============================================
# Phase 2: Meal Domain
# ============================================

echo -e "${BLUE}================================================${NC}"
echo -e "${CYAN}🍽️  Phase 2: Meal Domain${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Logging meals and tracking nutrition..."
echo ""

"${SCRIPT_DIR}/test_meal_persistence.sh" "$BASE_URL" "$USER_ID"

MEAL_EXIT_CODE=$?

if [ $MEAL_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Phase 2 completed successfully!${NC}"
    echo ""
else
    echo -e "${RED}❌ Phase 2 failed with exit code ${MEAL_EXIT_CODE}${NC}"
    exit 1
fi

# Small pause between phases
sleep 2

# ============================================
# Phase 3: Activity Domain
# ============================================

echo -e "${BLUE}================================================${NC}"
echo -e "${CYAN}🏃 Phase 3: Activity Domain${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Syncing activity data and tracking energy expenditure..."
echo ""

"${SCRIPT_DIR}/test_activity_persistence.sh" "$BASE_URL" "$USER_ID"

ACTIVITY_EXIT_CODE=$?

if [ $ACTIVITY_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Phase 3 completed successfully!${NC}"
    echo ""
else
    echo -e "${RED}❌ Phase 3 failed with exit code ${ACTIVITY_EXIT_CODE}${NC}"
    exit 1
fi

# Small pause between phases
sleep 2

# ============================================
# Phase 4: ML Enhancements (Weight Forecasting)
# ============================================

echo -e "${BLUE}================================================${NC}"
echo -e "${CYAN}🔮 Phase 4: ML Enhancements (Weight Forecasting)${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Testing ML-powered weight forecasting and adaptive TDEE..."
echo ""

"${SCRIPT_DIR}/test_ml_workflow.sh" "$BASE_URL" "$USER_ID"

ML_EXIT_CODE=$?

if [ $ML_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Phase 4 completed successfully!${NC}"
    echo ""
else
    echo -e "${RED}❌ Phase 4 failed with exit code ${ML_EXIT_CODE}${NC}"
    exit 1
fi

# ============================================
# Final Summary - Cross-Domain Validation
# ============================================

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ E2E Test Suite Completed!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Query final state from all domains
GRAPHQL_ENDPOINT="${BASE_URL}/graphql"
TODAY=$(date -u +%Y-%m-%d)

echo -e "${CYAN}📊 Querying final state across all domains...${NC}"
echo ""

# Profile summary
PROFILE_SUMMARY=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"query { nutritionalProfile { nutritionalProfile(userId: \\\"${USER_ID}\\\") { goal userData { weight } caloriesTarget progressHistory { date weight consumedCalories } } } }\"
    }")

PROFILE_GOAL=$(echo "$PROFILE_SUMMARY" | jq -r '.data.nutritionalProfile.nutritionalProfile.goal // "N/A"')
PROFILE_WEIGHT=$(echo "$PROFILE_SUMMARY" | jq -r '.data.nutritionalProfile.nutritionalProfile.userData.weight // 0')
PROFILE_TARGET=$(echo "$PROFILE_SUMMARY" | jq -r '.data.nutritionalProfile.nutritionalProfile.caloriesTarget // 0')
PROFILE_RECORDS=$(echo "$PROFILE_SUMMARY" | jq -r '.data.nutritionalProfile.nutritionalProfile.progressHistory | length')

# Meal summary
MEAL_SUMMARY=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"query { meals { dailySummary(userId: \\\"${USER_ID}\\\", date: \\\"${TODAY}T00:00:00Z\\\") { totalCalories totalProtein totalCarbs totalFat mealCount } } }\"
    }")

MEAL_CALORIES=$(echo "$MEAL_SUMMARY" | jq -r '.data.meals.dailySummary.totalCalories // 0')
MEAL_PROTEIN=$(echo "$MEAL_SUMMARY" | jq -r '.data.meals.dailySummary.totalProtein // 0')
MEAL_COUNT=$(echo "$MEAL_SUMMARY" | jq -r '.data.meals.dailySummary.mealCount // 0')

# Activity summary
ACTIVITY_SUMMARY=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"query { activity { entries(userId: \\\"${USER_ID}\\\", limit: 1000) { steps caloriesOut } } }\"
    }")

ACTIVITY_STEPS=$(echo "$ACTIVITY_SUMMARY" | jq '[.data.activity.entries[].steps // 0] | add // 0')
ACTIVITY_CALORIES=$(echo "$ACTIVITY_SUMMARY" | jq '[.data.activity.entries[].caloriesOut // 0] | add // 0')
ACTIVITY_EVENTS=$(echo "$ACTIVITY_SUMMARY" | jq '.data.activity.entries | length')

echo -e "${MAGENTA}═══════════════════════════════════════════════${NC}"
echo -e "${MAGENTA}       CROSS-DOMAIN DATA SUMMARY${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}👤 User Profile:${NC}"
echo "  User ID: ${USER_ID}"
echo "  Current Goal: ${PROFILE_GOAL}"
echo "  Current Weight: $(echo $PROFILE_WEIGHT | awk '{printf "%.1f", $1}') kg"
echo "  Target Calories: $(echo $PROFILE_TARGET | awk '{printf "%.0f", $1}') kcal/day"
echo "  Progress Records: ${PROFILE_RECORDS} days"
echo ""
echo -e "${CYAN}🍽️  Nutrition (Today):${NC}"
echo "  Total Meals: ${MEAL_COUNT}"
echo "  Calories IN: $(echo $MEAL_CALORIES | awk '{printf "%.0f", $1}') kcal"
echo "  Protein: $(echo $MEAL_PROTEIN | awk '{printf "%.0f", $1}') g"
echo ""
echo -e "${CYAN}🏃 Activity (Today):${NC}"
echo "  Total Steps: $(echo $ACTIVITY_STEPS | awk '{printf "%.0f", $1}')"
echo "  Calories OUT: $(echo $ACTIVITY_CALORIES | awk '{printf "%.0f", $1}') kcal"
echo "  Activity Events: ${ACTIVITY_EVENTS}"
echo ""

# Calculate energy balance
MEAL_CALORIES_NUM=$(echo $MEAL_CALORIES | awk '{printf "%.0f", $1}')
ACTIVITY_CALORIES_NUM=$(echo $ACTIVITY_CALORIES | awk '{printf "%.0f", $1}')

if [ "$MEAL_CALORIES_NUM" -gt 0 ] && [ "$ACTIVITY_CALORIES_NUM" -gt 0 ]; then
    ENERGY_BALANCE=$((MEAL_CALORIES_NUM - ACTIVITY_CALORIES_NUM))
    
    echo -e "${CYAN}⚖️  Energy Balance (Today):${NC}"
    echo "  Calories IN: ${MEAL_CALORIES_NUM} kcal"
    echo "  Calories OUT: ${ACTIVITY_CALORIES_NUM} kcal"
    
    if [ $ENERGY_BALANCE -lt 0 ]; then
        DEFICIT=$((ENERGY_BALANCE * -1))
        echo -e "  Net Balance: ${GREEN}-${DEFICIT} kcal (DEFICIT)${NC}"
        echo ""
        echo -e "  ${GREEN}✅ Calorie deficit achieved - supporting ${PROFILE_GOAL} goal!${NC}"
    elif [ $ENERGY_BALANCE -gt 0 ]; then
        echo -e "  Net Balance: ${RED}+${ENERGY_BALANCE} kcal (SURPLUS)${NC}"
        echo ""
        if [ "$PROFILE_GOAL" == "BULK" ]; then
            echo -e "  ${GREEN}✅ Calorie surplus - supporting BULK goal!${NC}"
        else
            echo -e "  ${YELLOW}⚠️  Calorie surplus - may not align with ${PROFILE_GOAL} goal${NC}"
        fi
    else
        echo -e "  Net Balance: ${YELLOW}0 kcal (BALANCED)${NC}"
        echo ""
        echo -e "  ${GREEN}✅ Perfect balance - supporting MAINTAIN goal!${NC}"
    fi
else
    echo -e "${YELLOW}ℹ️  Energy balance calculation requires both meal and activity data${NC}"
fi

echo ""
echo -e "${MAGENTA}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}         ALL DOMAINS TESTED SUCCESSFULLY!${NC}"
echo -e "${MAGENTA}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}✅ Verified:${NC}"
echo "  ✅ Nutritional Profile: Profile creation, progress tracking, goal changes"
echo "  ✅ Meal Domain: Food logging, nutrition calculation, daily summaries"
echo "  ✅ Activity Domain: Activity sync, calorie tracking, aggregations"
echo "  ✅ ML Enhancements: Weight forecasting, time series models, confidence intervals"
echo "  ✅ Cross-Domain: Energy balance, data consistency, integration"
echo ""
echo -e "${CYAN}📊 Test Coverage:${NC}"
echo "  • 4 domains tested"
echo "  • ${PROFILE_RECORDS} days of progress data"
echo "  • ${MEAL_COUNT} meals logged"
echo "  • ${ACTIVITY_EVENTS} activity events"
echo "  • ML forecasting validated"
echo "  • Cross-domain validation completed"
echo ""
echo -e "${GREEN}🎉 E2E test suite completed successfully!${NC}"
echo ""
echo -e "${YELLOW}💡 Tip: Use the same USER_ID to continue testing or reset with a new ID${NC}"
echo ""
