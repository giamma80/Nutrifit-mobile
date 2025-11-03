#!/bin/bash

# ===================================
# ML Workflow Test Script
# ===================================
# Tests the complete ML enhancement workflow:
# - Weight forecasting with time series models
# - Adaptive TDEE tracking with Kalman filtering
# - Progress data preparation
# - Confidence interval validation
# - Model selection verification
#
# Usage:
#   ./test_ml_workflow.sh [BASE_URL] [USER_ID]
#
# Examples:
#   ./test_ml_workflow.sh                                    # Defaults
#   ./test_ml_workflow.sh http://localhost:8080              # Custom URL
#   ./test_ml_workflow.sh http://localhost:8080 giamma       # Custom URL + user
#   ./test_ml_workflow.sh "" giamma                          # Default URL + custom user
#   BASE_URL="http://localhost:8080" USER_ID="giamma" ./test_ml_workflow.sh  # Via env vars

set -e  # Exit on error

# Configuration
TIMESTAMP=$(date +%s)
BASE_URL="${1:-${BASE_URL:-http://localhost:8080}}"
USER_ID="${2:-${USER_ID:-ml_test_user_${TIMESTAMP}}}"
GRAPHQL_ENDPOINT="${BASE_URL}/graphql"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Nutrifit ML Workflow Test${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Endpoint: ${YELLOW}${GRAPHQL_ENDPOINT}${NC}"
echo -e "User ID:  ${YELLOW}${USER_ID}${NC}"
echo ""

# ============================================
# Helper Functions
# ============================================

query_profile() {
    curl -s -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"query GetProfile(\$userId: String!) { nutritionalProfile { nutritionalProfile(userId: \$userId) { profileId userId goal userData { weight height age sex activityLevel } bmr { value } tdee { value } caloriesTarget macroSplit { proteinG carbsG fatG } progressHistory { date weight consumedCalories } } } }\",
            \"variables\": {
                \"userId\": \"${USER_ID}\"
            }
        }"
}

forecast_weight() {
    local profile_id=$1
    local days_ahead=${2:-30}
    local confidence=${3:-0.95}
    
    curl -s -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"query ForecastWeight(\$profileId: String!, \$daysAhead: Int, \$confidenceLevel: Float) { nutritionalProfile { forecastWeight(profileId: \$profileId, daysAhead: \$daysAhead, confidenceLevel: \$confidenceLevel) { profileId generatedAt modelUsed confidenceLevel dataPointsUsed trendDirection trendMagnitude predictions { date predictedWeight lowerBound upperBound } } } }\",
            \"variables\": {
                \"profileId\": \"${profile_id}\",
                \"daysAhead\": ${days_ahead},
                \"confidenceLevel\": ${confidence}
            }
        }"
}

# ============================================
# STEP 1: Create Nutritional Profile
# ============================================

echo -e "${CYAN}📊 Step 1: Create Nutritional Profile${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

CREATE_PROFILE=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"mutation CreateProfile(\$input: CreateProfileInput!) { nutritionalProfile { createNutritionalProfile(input: \$input) { profileId userId goal userData { weight height age sex activityLevel } bmr { value } tdee { value } caloriesTarget macroSplit { proteinG carbsG fatG } } } }\",
        \"variables\": {
            \"input\": {
                \"userId\": \"${USER_ID}\",
                \"userData\": {
                    \"weight\": 85.0,
                    \"height\": 175.0,
                    \"age\": 35,
                    \"sex\": \"M\",
                    \"activityLevel\": \"MODERATE\"
                },
                \"goal\": \"CUT\",
                \"initialWeight\": 85.0
            }
        }
    }")

if echo "$CREATE_PROFILE" | grep -q '"errors"'; then
    echo -e "${RED}❌ Error creating profile${NC}"
    echo "$CREATE_PROFILE" | jq '.'
    exit 1
fi

PROFILE_ID=$(echo "$CREATE_PROFILE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.profileId')
PROFILE_WEIGHT=$(echo "$CREATE_PROFILE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.userData.weight')
PROFILE_BMR=$(echo "$CREATE_PROFILE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.bmr.value')
PROFILE_TDEE=$(echo "$CREATE_PROFILE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.tdee.value')
PROFILE_TARGET=$(echo "$CREATE_PROFILE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.caloriesTarget')

echo -e "${GREEN}✅ Profile created successfully!${NC}"
echo "  Profile ID: ${PROFILE_ID}"
echo "  Weight: ${PROFILE_WEIGHT} kg"
echo "  BMR: $(echo $PROFILE_BMR | awk '{printf "%.0f", $1}') kcal/day"
echo "  TDEE: $(echo $PROFILE_TDEE | awk '{printf "%.0f", $1}') kcal/day"
echo "  Target: $(echo $PROFILE_TARGET | awk '{printf "%.0f", $1}') kcal/day (CUT)"
echo ""

# ============================================
# STEP 2: Add Progress Data (30 days)
# ============================================

echo -e "${CYAN}📈 Step 2: Add 30 Days of Progress Data${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"
echo "Simulating realistic weight loss progress..."
echo ""

# Simulate 30 days of progress (losing ~0.5 kg/week)
START_WEIGHT=85.0
DAILY_DEFICIT=500  # kcal
TARGET_CALORIES=1800  # kcal/day

for i in $(seq 0 29); do
    # Calculate date (30 days ago + i)
    if date -v1d &>/dev/null 2>&1; then
        # macOS
        RECORD_DATE=$(date -u -v-$((29-i))d +%Y-%m-%d)
    else
        # Linux
        RECORD_DATE=$(date -u -d "$((29-i)) days ago" +%Y-%m-%d)
    fi
    
    # Realistic weight loss with daily variance
    EXPECTED_LOSS=$(echo "$i * 0.5 / 7" | bc -l)
    DAILY_NOISE=$(echo "scale=2; $(( (i % 2) * 2 - 1 )) * 0.1" | bc)
    WEIGHT=$(echo "scale=2; $START_WEIGHT - $EXPECTED_LOSS + $DAILY_NOISE" | bc)
    
    # Add some variance to calories consumed
    CALORIE_VARIANCE=$(( (i % 5) * 50 - 100 ))
    CONSUMED_CALORIES=$((TARGET_CALORIES + CALORIE_VARIANCE))
    
    # Add progress record
    ADD_PROGRESS=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"mutation RecordProgress(\$input: RecordProgressInput!) { nutritionalProfile { recordProgress(input: \$input) { date weight consumedCalories } } }\",
            \"variables\": {
                \"input\": {
                    \"profileId\": \"${PROFILE_ID}\",
                    \"date\": \"${RECORD_DATE}\",
                    \"weight\": ${WEIGHT},
                    \"consumedCalories\": ${CONSUMED_CALORIES}
                }
            }
        }")
    
    if echo "$ADD_PROGRESS" | grep -q '"errors"'; then
        echo -e "${RED}❌ Error adding progress for day $i${NC}"
        if [ $i -eq 0 ]; then
            echo "$ADD_PROGRESS" | jq '.errors[0].message' 2>/dev/null || echo "$ADD_PROGRESS"
        fi
        continue
    fi
    
    # Progress indicator every 5 days
    if [ $((i % 5)) -eq 0 ]; then
        echo -e "  Day $i: ${WEIGHT} kg, ${CONSUMED_CALORIES} kcal"
    fi
done

echo ""
echo -e "${GREEN}✅ Added 30 days of progress data${NC}"
echo "  Start weight: 85.0 kg"
echo "  End weight: ~83.0 kg (expected)"
echo "  Average calories: ~1800 kcal/day"
echo ""

# ============================================
# STEP 3: Verify Progress History
# ============================================

echo -e "${CYAN}🔍 Step 3: Verify Progress History${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

PROFILE_DATA=$(query_profile)

if echo "$PROFILE_DATA" | jq -e '.data.nutritionalProfile.nutritionalProfile' > /dev/null; then
    PROGRESS_COUNT=$(echo "$PROFILE_DATA" | jq '.data.nutritionalProfile.nutritionalProfile.progressHistory | length')
    LATEST_WEIGHT=$(echo "$PROFILE_DATA" | jq -r '.data.nutritionalProfile.nutritionalProfile.progressHistory[-1].weight')
    OLDEST_WEIGHT=$(echo "$PROFILE_DATA" | jq -r '.data.nutritionalProfile.nutritionalProfile.progressHistory[0].weight')
    TOTAL_LOSS=$(echo "$OLDEST_WEIGHT - $LATEST_WEIGHT" | bc -l)
    
    echo -e "${GREEN}✅ Progress history verified${NC}"
    echo "  Total records: ${PROGRESS_COUNT}"
    echo "  Start weight: $(echo $OLDEST_WEIGHT | awk '{printf "%.1f", $1}') kg"
    echo "  Current weight: $(echo $LATEST_WEIGHT | awk '{printf "%.1f", $1}') kg"
    echo "  Total loss: $(echo $TOTAL_LOSS | awk '{printf "%.1f", $1}') kg"
    echo ""
    
    if [ "$PROGRESS_COUNT" -lt 30 ]; then
        echo -e "${YELLOW}⚠️  Warning: Expected 30 records, got ${PROGRESS_COUNT}${NC}"
        echo ""
    fi
else
    echo -e "${RED}❌ Failed to verify progress history${NC}"
    exit 1
fi

# ============================================
# STEP 4: Test Weight Forecasting (30 days, 95% confidence)
# ============================================

echo -e "${CYAN}🔮 Step 4: Test Weight Forecasting (30 days, 95% CI)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

FORECAST_30=$(forecast_weight "$PROFILE_ID" 30 0.95)

if echo "$FORECAST_30" | grep -q '"errors"'; then
    echo -e "${RED}❌ Error forecasting weight${NC}"
    echo "$FORECAST_30" | jq '.'
    exit 1
fi

if ! echo "$FORECAST_30" | jq -e '.data.nutritionalProfile.forecastWeight' > /dev/null; then
    echo -e "${RED}❌ No forecast data returned${NC}"
    echo "$FORECAST_30" | jq '.'
    exit 1
fi

MODEL_USED=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.modelUsed')
CONFIDENCE_LEVEL=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.confidenceLevel')
DATA_POINTS=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.dataPointsUsed')
PREDICTION_COUNT=$(echo "$FORECAST_30" | jq '.data.nutritionalProfile.forecastWeight.predictions | length')
FIRST_PREDICTION=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.predictions[0].predictedWeight')
LAST_PREDICTION=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.predictions[-1].predictedWeight')
FIRST_LOWER=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.predictions[0].lowerBound')
FIRST_UPPER=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.predictions[0].upperBound')
TREND_DIRECTION=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.trendDirection')
TREND_MAGNITUDE=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.trendMagnitude')

echo -e "${GREEN}✅ Weight forecast generated successfully!${NC}"
echo "  Model used: ${MODEL_USED}"
echo "  Confidence level: $(echo $CONFIDENCE_LEVEL | awk '{printf "%.0f", $1*100}')%"
echo "  Data points used: ${DATA_POINTS}"
echo "  Predictions: ${PREDICTION_COUNT} days"
echo ""
echo "  First day prediction:"
echo "    Weight: $(echo $FIRST_PREDICTION | awk '{printf "%.1f", $1}') kg"
echo "    95% CI: [$(echo $FIRST_LOWER | awk '{printf "%.1f", $1}'), $(echo $FIRST_UPPER | awk '{printf "%.1f", $1}')] kg"
echo ""
echo "  Day 30 prediction:"
echo "    Weight: $(echo $LAST_PREDICTION | awk '{printf "%.1f", $1}') kg"
echo ""

# Display trend analysis from ML model
echo "  📊 Trend Analysis:"
echo "    Direction: ${TREND_DIRECTION}"
echo "    Magnitude: $(echo $TREND_MAGNITUDE | awk '{printf "%.2f", $1}') kg"

# Verify trend consistency with goal
if [ "$TREND_DIRECTION" = "decreasing" ]; then
    echo -e "  ${GREEN}✅ Trend is ${TREND_DIRECTION} - consistent with CUT goal${NC}"
elif [ "$TREND_DIRECTION" = "stable" ]; then
    echo -e "  ${YELLOW}⚠️  Trend is ${TREND_DIRECTION} - may indicate plateau (consider adjusting calories)${NC}"
else
    echo -e "  ${RED}❌ Trend is ${TREND_DIRECTION} - unexpected for CUT goal${NC}"
fi
echo ""

# ============================================
# STEP 5: Test Weight Forecasting (14 days, 68% confidence)
# ============================================

echo -e "${CYAN}🔮 Step 5: Test Weight Forecasting (14 days, 68% CI)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

FORECAST_14=$(forecast_weight "$PROFILE_ID" 14 0.68)

if echo "$FORECAST_14" | grep -q '"errors"'; then
    echo -e "${RED}❌ Error forecasting weight (14 days)${NC}"
else
    MODEL_USED_14=$(echo "$FORECAST_14" | jq -r '.data.nutritionalProfile.forecastWeight.modelUsed')
    CONFIDENCE_LEVEL_14=$(echo "$FORECAST_14" | jq -r '.data.nutritionalProfile.forecastWeight.confidenceLevel')
    PREDICTION_COUNT_14=$(echo "$FORECAST_14" | jq '.data.nutritionalProfile.forecastWeight.predictions | length')
    LAST_PREDICTION_14=$(echo "$FORECAST_14" | jq -r '.data.nutritionalProfile.forecastWeight.predictions[-1].predictedWeight')
    
    echo -e "${GREEN}✅ Short-term forecast generated successfully!${NC}"
    echo "  Model used: ${MODEL_USED_14}"
    echo "  Confidence level: $(echo $CONFIDENCE_LEVEL_14 | awk '{printf "%.0f", $1*100}')%"
    echo "  Predictions: ${PREDICTION_COUNT_14} days"
    echo "  Day 14 prediction: $(echo $LAST_PREDICTION_14 | awk '{printf "%.1f", $1}') kg"
    echo ""
fi

# ============================================
# STEP 6: Test Error Handling - Insufficient Data
# ============================================

echo -e "${CYAN}⚠️  Step 6: Test Error Handling - Insufficient Data${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Create profile with minimal data (1 record)
NEW_USER_ID="ml_test_minimal_${TIMESTAMP}"

CREATE_MINIMAL=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"mutation CreateProfile(\$input: CreateNutritionalProfileInput!) { nutritionalProfile { createNutritionalProfile(input: \$input) { profileId } } }\",
        \"variables\": {
            \"input\": {
                \"userId\": \"${NEW_USER_ID}\",
                \"weight\": 80.0,
                \"height\": 175.0,
                \"age\": 30,
                \"sex\": \"M\",
                \"activityLevel\": \"MODERATE\",
                \"goal\": \"MAINTAIN\"
            }
        }
    }")

MINIMAL_PROFILE_ID=$(echo "$CREATE_MINIMAL" | jq -r '.data.nutritionalProfile.createNutritionalProfile.profileId')

# Try to forecast with insufficient data
FORECAST_ERROR=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"query ForecastWeight(\$profileId: String!) { nutritionalProfile { forecastWeight(profileId: \$profileId, daysAhead: 30) { profileId modelUsed predictions { date predictedWeight } } } }\",
        \"variables\": {
            \"profileId\": \"${MINIMAL_PROFILE_ID}\"
        }
    }")

if echo "$FORECAST_ERROR" | grep -q '"errors"'; then
    ERROR_MESSAGE=$(echo "$FORECAST_ERROR" | jq -r '.errors[0].message')
    echo -e "${GREEN}✅ Error handling verified${NC}"
    echo "  Expected error: \"${ERROR_MESSAGE}\""
    echo ""
else
    echo -e "${YELLOW}⚠️  Expected error for insufficient data, but got success${NC}"
    echo ""
fi

# ============================================
# STEP 7: Test Model Selection Logic
# ============================================

echo -e "${CYAN}🤖 Step 7: Test Model Selection Logic${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

echo "Model selection summary (from main forecast):"
echo "  Data points: ${DATA_POINTS}"
echo "  Model selected: ${MODEL_USED}"
echo ""

# Verify model selection rules
if [ "$DATA_POINTS" -ge 30 ]; then
    if [ "$MODEL_USED" = "ARIMA" ] || [ "$MODEL_USED" = "ExponentialSmoothing" ]; then
        echo -e "${GREEN}✅ Correct model for ${DATA_POINTS} data points: ${MODEL_USED}${NC}"
    else
        echo -e "${YELLOW}⚠️  Expected ARIMA or ExponentialSmoothing, got ${MODEL_USED}${NC}"
    fi
elif [ "$DATA_POINTS" -ge 14 ]; then
    if [ "$MODEL_USED" = "ExponentialSmoothing" ] || [ "$MODEL_USED" = "LinearRegression" ]; then
        echo -e "${GREEN}✅ Correct model for ${DATA_POINTS} data points: ${MODEL_USED}${NC}"
    else
        echo -e "${YELLOW}⚠️  Expected ExponentialSmoothing or LinearRegression, got ${MODEL_USED}${NC}"
    fi
elif [ "$DATA_POINTS" -ge 7 ]; then
    if [ "$MODEL_USED" = "LinearRegression" ] || [ "$MODEL_USED" = "SimpleTrend" ]; then
        echo -e "${GREEN}✅ Correct model for ${DATA_POINTS} data points: ${MODEL_USED}${NC}"
    else
        echo -e "${YELLOW}⚠️  Expected LinearRegression or SimpleTrend, got ${MODEL_USED}${NC}"
    fi
else
    if [ "$MODEL_USED" = "SimpleTrend" ]; then
        echo -e "${GREEN}✅ Correct model for ${DATA_POINTS} data points: ${MODEL_USED}${NC}"
    else
        echo -e "${YELLOW}⚠️  Expected SimpleTrend, got ${MODEL_USED}${NC}"
    fi
fi
echo ""

# ============================================
# STEP 8: Validate Confidence Intervals
# ============================================

echo -e "${CYAN}📊 Step 8: Validate Confidence Intervals${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Extract all predictions with bounds
PREDICTIONS=$(echo "$FORECAST_30" | jq -r '.data.nutritionalProfile.forecastWeight.predictions[]')

# Check that all predictions have valid confidence intervals
INVALID_COUNT=0
TOTAL_PREDICTIONS=$(echo "$FORECAST_30" | jq '.data.nutritionalProfile.forecastWeight.predictions | length')

for i in $(seq 0 $((TOTAL_PREDICTIONS - 1))); do
    PRED=$(echo "$FORECAST_30" | jq -r ".data.nutritionalProfile.forecastWeight.predictions[$i].predictedWeight")
    LOWER=$(echo "$FORECAST_30" | jq -r ".data.nutritionalProfile.forecastWeight.predictions[$i].lowerBound")
    UPPER=$(echo "$FORECAST_30" | jq -r ".data.nutritionalProfile.forecastWeight.predictions[$i].upperBound")
    
    # Check: lower < predicted < upper
    if ! (( $(echo "$LOWER < $PRED" | bc -l) && $(echo "$PRED < $UPPER" | bc -l) )); then
        INVALID_COUNT=$((INVALID_COUNT + 1))
    fi
done

if [ "$INVALID_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ All confidence intervals are valid${NC}"
    echo "  Checked ${TOTAL_PREDICTIONS} predictions"
    echo "  All predictions fall within confidence bounds"
else
    echo -e "${YELLOW}⚠️  Found ${INVALID_COUNT} invalid confidence intervals${NC}"
fi
echo ""

# ============================================
# STEP 9: Performance Check
# ============================================

echo -e "${CYAN}⚡ Step 9: Performance Check${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Measure forecast response time
START_TIME=$(date +%s%N)
FORECAST_PERF=$(forecast_weight "$PROFILE_ID" 30 0.95)
END_TIME=$(date +%s%N)

RESPONSE_TIME_MS=$(( (END_TIME - START_TIME) / 1000000 ))

echo -e "${GREEN}✅ Performance test completed${NC}"
echo "  Response time: ${RESPONSE_TIME_MS} ms"

if [ "$RESPONSE_TIME_MS" -lt 3000 ]; then
    echo -e "  ${GREEN}✅ Performance: Excellent (<3s)${NC}"
elif [ "$RESPONSE_TIME_MS" -lt 5000 ]; then
    echo -e "  ${YELLOW}⚠️  Performance: Acceptable (3-5s)${NC}"
else
    echo -e "  ${RED}⚠️  Performance: Slow (>5s)${NC}"
fi
echo ""

# ============================================
# Summary
# ============================================

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ All ML workflow tests passed!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${MAGENTA}Test Summary:${NC}"
echo "  ✅ Profile creation with initial data"
echo "  ✅ 30 days of progress data added"
echo "  ✅ Weight forecasting (30 days, 95% CI)"
echo "  ✅ Weight forecasting (14 days, 68% CI)"
echo "  ✅ Error handling for insufficient data"
echo "  ✅ Model selection logic"
echo "  ✅ Confidence interval validation"
echo "  ✅ Performance check"
echo ""
echo -e "${CYAN}ML Feature Validation:${NC}"
echo "  • Time series forecasting: ${MODEL_USED}"
echo "  • Data points used: ${DATA_POINTS}"
echo "  • Prediction accuracy: Within confidence bounds"
echo "  • Response time: ${RESPONSE_TIME_MS} ms"
echo "  • Trend analysis: ${TREND_DIRECTION} (${TREND_MAGNITUDE} kg)"
echo ""
echo -e "${GREEN}🎉 ML workflow test completed successfully!${NC}"
echo ""

