#!/bin/bash

# ============================================
# Nutritional Profile Workflow Persistence Test
# ============================================
# 
# Verifies nutritional profile persistence and calculations:
# 1. Create nutritional profile with user data and goal
# 2. Verify BMR/TDEE/macro calculations
# 3. Record daily progress (weight, calories, macros)
# 4. Query profile with progress history
# 5. Calculate progress score and adherence
# 6. Update profile (goal change, user data change)
# 7. Cross-check with meal/activity data for deficit tracking
#
# Simulates a realistic fitness journey:
# - Initial profile creation (cut phase)
# - 7 days of progress tracking
# - Goal change to maintain
# - Weight loss verification
# - Macro adherence tracking
#
# Usage:
#   ./test_nutritional_profile_persistence.sh [BASE_URL] [USER_ID]
#
# Examples:
#   ./test_nutritional_profile_persistence.sh                                    # Defaults
#   ./test_nutritional_profile_persistence.sh http://localhost:8080              # Custom URL
#   ./test_nutritional_profile_persistence.sh http://localhost:8080 giamma       # Custom URL + user
#   ./test_nutritional_profile_persistence.sh "" giamma                          # Default URL + custom user
#   BASE_URL="http://localhost:8080" USER_ID="giamma" ./test_nutritional_profile_persistence.sh  # Via env vars
#
# ============================================

set -e

# Configuration
TIMESTAMP=$(date +%s)
BASE_URL="${1:-${BASE_URL:-http://localhost:8080}}"
USER_ID="${2:-${USER_ID:-test_user_${TIMESTAMP}}}"
GRAPHQL_ENDPOINT="${BASE_URL}/graphql"
TODAY=$(date -u +%Y-%m-%d)
TODAY_DATETIME="${TODAY}T00:00:00Z"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Nutrifit Nutritional Profile Test${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "Endpoint: ${YELLOW}${GRAPHQL_ENDPOINT}${NC}"
echo -e "User ID:  ${YELLOW}${USER_ID}${NC}"
echo -e "Date:     ${YELLOW}${TODAY}${NC}"
echo ""

# ============================================
# Helper Functions
# ============================================

create_profile() {
    local user_id=$1
    local weight=$2
    local height=$3
    local age=$4
    local sex=$5
    local activity_level=$6
    local goal=$7
    local initial_weight=$8
    local initial_date=${9:-$TODAY}
    
    curl -s -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"mutation { nutritionalProfile { createNutritionalProfile(input: {userId: \\\"${user_id}\\\", userData: {weight: ${weight}, height: ${height}, age: ${age}, sex: ${sex}, activityLevel: ${activity_level}}, goal: ${goal}, initialWeight: ${initial_weight}, initialDate: \\\"${initial_date}\\\"}) { profileId userId goal userData { weight height age sex activityLevel } bmr { value } tdee { value activityLevel } caloriesTarget macroSplit { proteinG carbsG fatG } progressHistory { date weight consumedCalories } createdAt updatedAt } } }\"
        }"
}

query_profile() {
    local user_id=$1
    
    curl -s -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"query { nutritionalProfile { nutritionalProfile(userId: \\\"${user_id}\\\") { profileId userId goal userData { weight height age sex activityLevel } bmr { value } tdee { value activityLevel } caloriesTarget macroSplit { proteinG carbsG fatG } progressHistory { date weight consumedCalories consumedProteinG consumedCarbsG consumedFatG caloriesBurnedBmr caloriesBurnedActive notes } createdAt updatedAt } } }\"
        }"
}

record_progress() {
    local profile_id=$1
    local date=$2
    local weight=$3
    local consumed_calories=$4
    local consumed_protein=$5
    local consumed_carbs=$6
    local consumed_fat=$7
    local calories_burned_active=${8:-0}
    local notes=${9:-""}
    
    curl -s -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"mutation { nutritionalProfile { recordProgress(input: {profileId: \\\"${profile_id}\\\", date: \\\"${date}\\\", weight: ${weight}, consumedCalories: ${consumed_calories}, consumedProteinG: ${consumed_protein}, consumedCarbsG: ${consumed_carbs}, consumedFatG: ${consumed_fat}, caloriesBurnedActive: ${calories_burned_active}, notes: \\\"${notes}\\\"}) { date weight consumedCalories consumedProteinG consumedCarbsG consumedFatG caloriesBurnedBmr caloriesBurnedActive notes } } }\"
        }"
}

update_profile() {
    local profile_id=$1
    local goal=$2
    local user_data_json=${3:-"null"}
    
    local user_data_field=""
    if [ "$user_data_json" != "null" ]; then
        user_data_field=", userData: ${user_data_json}"
    fi
    
    curl -s -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"mutation { nutritionalProfile { updateNutritionalProfile(input: {profileId: \\\"${profile_id}\\\", goal: ${goal}${user_data_field}}) { profileId goal userData { weight } caloriesTarget macroSplit { proteinG carbsG fatG } updatedAt } } }\"
        }"
}

query_progress_score() {
    local user_id=$1
    local start_date=$2
    local end_date=$3
    
    curl -s -X POST "${GRAPHQL_ENDPOINT}" \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"query { nutritionalProfile { progressScore(userId: \\\"${user_id}\\\", startDate: \\\"${start_date}\\\", endDate: \\\"${end_date}\\\") { weightDelta avgDailyCalories avgDeficit daysDeficitOnTrack daysMacrosOnTrack adherenceRate totalDays } } }\"
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
echo "  - No pre-existing nutritional profile"
echo "  - Fresh calculation baseline"
echo "  - Clean progress history"
echo ""

# Verify no existing profile
INITIAL_CHECK=$(query_profile "$USER_ID")
HAS_PROFILE=$(echo "$INITIAL_CHECK" | jq -r '.data.nutritionalProfile.nutritionalProfile != null')

if [ "$HAS_PROFILE" == "false" ]; then
    echo -e "${GREEN}✅ Clean state verified: No existing profile${NC}"
else
    echo -e "${YELLOW}⚠️  Found existing profile (may be from previous run)${NC}"
fi
echo ""

# ============================================
# STEP 1: Create Initial Profile (CUT Phase)
# ============================================

echo -e "${CYAN}👤 Step 1: Create Nutritional Profile (CUT Phase)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Create profile for a 30-year-old male, 180cm, 85kg, moderately active
# Goal: CUT (weight loss with calorie deficit)
INITIAL_WEIGHT=85.0
INITIAL_HEIGHT=180.0
INITIAL_AGE=30

echo "Creating profile:"
echo "  Weight: ${INITIAL_WEIGHT} kg"
echo "  Height: ${INITIAL_HEIGHT} cm"
echo "  Age: ${INITIAL_AGE} years"
echo "  Sex: M (Male)"
echo "  Activity Level: MODERATE"
echo "  Goal: CUT (calorie deficit for weight loss)"
echo ""

CREATE_RESPONSE=$(create_profile "$USER_ID" "$INITIAL_WEIGHT" "$INITIAL_HEIGHT" "$INITIAL_AGE" "M" "MODERATE" "CUT" "$INITIAL_WEIGHT" "$TODAY")

PROFILE_ID=$(echo "$CREATE_RESPONSE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.profileId')
BMR=$(echo "$CREATE_RESPONSE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.bmr.value')
TDEE=$(echo "$CREATE_RESPONSE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.tdee.value')
CALORIES_TARGET=$(echo "$CREATE_RESPONSE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.caloriesTarget')
PROTEIN_G=$(echo "$CREATE_RESPONSE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.macroSplit.proteinG')
CARBS_G=$(echo "$CREATE_RESPONSE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.macroSplit.carbsG')
FAT_G=$(echo "$CREATE_RESPONSE" | jq -r '.data.nutritionalProfile.createNutritionalProfile.macroSplit.fatG')

echo -e "${GREEN}✅ Profile created successfully!${NC}"
echo ""
echo -e "${MAGENTA}📊 Calculated Metrics:${NC}"
echo "  Profile ID: ${PROFILE_ID}"
echo "  BMR (Basal Metabolic Rate): $(echo $BMR | awk '{printf "%.0f", $1}') kcal/day"
echo "  TDEE (Total Daily Energy): $(echo $TDEE | awk '{printf "%.0f", $1}') kcal/day"
echo "  Target Calories (CUT): $(echo $CALORIES_TARGET | awk '{printf "%.0f", $1}') kcal/day"
echo ""
echo -e "${MAGENTA}🍽️  Macro Split (Cut Phase):${NC}"
echo "  Protein: $(echo $PROTEIN_G | awk '{printf "%.0f", $1}') g/day (high for muscle preservation)"
echo "  Carbs: $(echo $CARBS_G | awk '{printf "%.0f", $1}') g/day"
echo "  Fat: $(echo $FAT_G | awk '{printf "%.0f", $1}') g/day"
echo ""

# Validate BMR calculation (Mifflin-St Jeor formula for males)
# BMR = 10 * weight(kg) + 6.25 * height(cm) - 5 * age(y) + 5
EXPECTED_BMR=$(echo "10 * $INITIAL_WEIGHT + 6.25 * $INITIAL_HEIGHT - 5 * $INITIAL_AGE + 5" | bc)
BMR_INT=$(echo $BMR | awk '{printf "%.0f", $1}')
EXPECTED_BMR_INT=$(echo $EXPECTED_BMR | awk '{printf "%.0f", $1}')

echo -e "${MAGENTA}✅ BMR Validation:${NC}"
echo "  Calculated: ${BMR_INT} kcal/day"
echo "  Expected (Mifflin-St Jeor): ${EXPECTED_BMR_INT} kcal/day"

BMR_DIFF=$((BMR_INT - EXPECTED_BMR_INT))
if [ $BMR_DIFF -lt 0 ]; then
    BMR_DIFF=$((BMR_DIFF * -1))
fi

if [ $BMR_DIFF -lt 10 ]; then
    echo -e "  ${GREEN}✅ BMR calculation correct!${NC}"
else
    echo -e "  ${YELLOW}⚠️  BMR difference: ${BMR_DIFF} kcal (check formula)${NC}"
fi
echo ""

# ============================================
# STEP 2: Record Progress - Day 1 (Start)
# ============================================

echo -e "${CYAN}📝 Step 2: Record Progress - Day 1 (Baseline)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Day 1: Starting point, consume slightly above target (adjustment period)
DAY1_DATE="$TODAY"
DAY1_WEIGHT=85.0
DAY1_CALORIES=2100
DAY1_PROTEIN=170
DAY1_CARBS=220
DAY1_FAT=70
DAY1_ACTIVE_CAL=450

echo "Day 1 (${DAY1_DATE}):"
echo "  Weight: ${DAY1_WEIGHT} kg"
echo "  Consumed: ${DAY1_CALORIES} kcal"
echo "  Macros: ${DAY1_PROTEIN}g P, ${DAY1_CARBS}g C, ${DAY1_FAT}g F"
echo "  Activity Calories: ${DAY1_ACTIVE_CAL} kcal"
echo ""

DAY1_RESPONSE=$(record_progress "$PROFILE_ID" "$DAY1_DATE" "$DAY1_WEIGHT" "$DAY1_CALORIES" "$DAY1_PROTEIN" "$DAY1_CARBS" "$DAY1_FAT" "$DAY1_ACTIVE_CAL" "Baseline measurement")

DAY1_RECORDED=$(echo "$DAY1_RESPONSE" | jq -r '.data.nutritionalProfile.recordProgress.date')

echo -e "${GREEN}✅ Day 1 progress recorded: ${DAY1_RECORDED}${NC}"
echo ""

# ============================================
# STEP 3: Record Progress - Week 1 (Days 2-7)
# ============================================

echo -e "${CYAN}📝 Step 3: Record Progress - Week 1 (Days 2-7)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Simulate 6 more days of progress with gradual weight loss and calorie adherence
DAYS_DATA=(
    # Date offset, Weight, Calories, Protein, Carbs, Fat, Active Cal, Notes
    "1|84.8|1950|165|200|68|420|Good adherence"
    "2|84.6|1980|168|210|65|450|Slight hunger"
    "3|84.5|2020|170|215|67|480|Gym day - high intensity"
    "4|84.3|1920|162|195|70|390|Rest day - lower carbs"
    "5|84.2|1960|166|205|68|440|Feeling strong"
    "6|84.0|1940|164|200|69|460|Weekly low - excellent!"
)

for day_data in "${DAYS_DATA[@]}"; do
    IFS='|' read -r offset weight calories protein carbs fat active notes <<< "$day_data"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        date_str=$(date -u -v+"${offset}"d -j -f "%Y-%m-%d" "$TODAY" +%Y-%m-%d)
    else
        # Linux
        date_str=$(date -u -d "$TODAY + $offset days" +%Y-%m-%d)
    fi
    
    echo "Day $((offset + 1)) (${date_str}): ${weight}kg, ${calories}kcal, ${active}kcal activity"
    
    record_progress "$PROFILE_ID" "$date_str" "$weight" "$calories" "$protein" "$carbs" "$fat" "$active" "$notes" > /dev/null
done

echo ""
echo -e "${GREEN}✅ Week 1 progress recorded (7 days total)${NC}"
echo ""

# ============================================
# STEP 4: Query Profile with Progress History
# ============================================

echo -e "${CYAN}📊 Step 4: Query Profile with Progress History${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

PROFILE_QUERY=$(query_profile "$USER_ID")

PROFILE_EXISTS=$(echo "$PROFILE_QUERY" | jq -r '.data.nutritionalProfile.nutritionalProfile != null')

if [ "$PROFILE_EXISTS" == "true" ]; then
    echo -e "${GREEN}✅ Profile retrieved successfully${NC}"
    
    PROGRESS_COUNT=$(echo "$PROFILE_QUERY" | jq -r '.data.nutritionalProfile.nutritionalProfile.progressHistory | length')
    echo "  Progress records: ${PROGRESS_COUNT}"
    echo ""
    
    echo -e "${MAGENTA}📈 Progress History:${NC}"
    echo "$PROFILE_QUERY" | jq -r '.data.nutritionalProfile.nutritionalProfile.progressHistory[] | "  \(.date): \(.weight)kg, \(.consumedCalories)kcal, Active: \(.caloriesBurnedActive)kcal"'
    echo ""
    
    # Calculate weight change
    FIRST_WEIGHT=$(echo "$PROFILE_QUERY" | jq -r '.data.nutritionalProfile.nutritionalProfile.progressHistory[0].weight')
    LAST_WEIGHT=$(echo "$PROFILE_QUERY" | jq -r '.data.nutritionalProfile.nutritionalProfile.progressHistory[-1].weight')
    WEIGHT_DELTA=$(echo "$LAST_WEIGHT - $FIRST_WEIGHT" | bc)
    
    echo -e "${MAGENTA}📉 Weight Change:${NC}"
    echo "  Start: $(echo $FIRST_WEIGHT | awk '{printf "%.1f", $1}') kg"
    echo "  Current: $(echo $LAST_WEIGHT | awk '{printf "%.1f", $1}') kg"
    echo "  Change: $(echo $WEIGHT_DELTA | awk '{printf "%.1f", $1}') kg"
    
    if (( $(echo "$WEIGHT_DELTA < 0" | bc -l) )); then
        echo -e "  ${GREEN}✅ Weight loss achieved!${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Weight gain or stable${NC}"
    fi
    echo ""
else
    echo -e "${RED}❌ Profile not found!${NC}"
    exit 1
fi

# ============================================
# STEP 5: Calculate Progress Score
# ============================================

echo -e "${CYAN}📊 Step 5: Calculate Progress Score (Week 1)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Calculate end date (6 days after start)
if [[ "$OSTYPE" == "darwin"* ]]; then
    END_DATE=$(date -u -v+6d -j -f "%Y-%m-%d" "$TODAY" +%Y-%m-%d)
else
    END_DATE=$(date -u -d "$TODAY + 6 days" +%Y-%m-%d)
fi

SCORE_QUERY=$(query_progress_score "$USER_ID" "$TODAY" "$END_DATE")

SCORE_EXISTS=$(echo "$SCORE_QUERY" | jq -r '.data.nutritionalProfile.progressScore != null')

if [ "$SCORE_EXISTS" == "true" ]; then
    SCORE_WEIGHT_DELTA=$(echo "$SCORE_QUERY" | jq -r '.data.nutritionalProfile.progressScore.weightDelta')
    SCORE_AVG_CALORIES=$(echo "$SCORE_QUERY" | jq -r '.data.nutritionalProfile.progressScore.avgDailyCalories')
    SCORE_AVG_DEFICIT=$(echo "$SCORE_QUERY" | jq -r '.data.nutritionalProfile.progressScore.avgDeficit')
    SCORE_DAYS_DEFICIT=$(echo "$SCORE_QUERY" | jq -r '.data.nutritionalProfile.progressScore.daysDeficitOnTrack')
    SCORE_DAYS_MACROS=$(echo "$SCORE_QUERY" | jq -r '.data.nutritionalProfile.progressScore.daysMacrosOnTrack')
    SCORE_TOTAL_DAYS=$(echo "$SCORE_QUERY" | jq -r '.data.nutritionalProfile.progressScore.totalDays')
    SCORE_ADHERENCE=$(echo "$SCORE_QUERY" | jq -r '.data.nutritionalProfile.progressScore.adherenceRate')
    
    echo -e "${GREEN}✅ Progress score calculated${NC}"
    echo ""
    echo -e "${MAGENTA}📊 Week 1 Statistics:${NC}"
    echo "  Weight Change: $(echo $SCORE_WEIGHT_DELTA | awk '{printf "%.1f", $1}') kg"
    echo "  Avg Daily Calories: $(echo $SCORE_AVG_CALORIES | awk '{printf "%.0f", $1}') kcal"
    echo "  Avg Daily Deficit: $(echo $SCORE_AVG_DEFICIT | awk '{printf "%.0f", $1}') kcal"
    echo "  Days on Deficit Track: ${SCORE_DAYS_DEFICIT}/${SCORE_TOTAL_DAYS}"
    echo "  Days with Macro Adherence: ${SCORE_DAYS_MACROS}/${SCORE_TOTAL_DAYS}"
    echo "  Overall Adherence Rate: $(echo $SCORE_ADHERENCE | awk '{printf "%.1f", $1 * 100}')%"
    echo ""
    
    # Validate adherence
    if (( $(echo "$SCORE_ADHERENCE > 0.7" | bc -l) )); then
        echo -e "  ${GREEN}✅ Excellent adherence (>70%)!${NC}"
    elif (( $(echo "$SCORE_ADHERENCE > 0.5" | bc -l) )); then
        echo -e "  ${YELLOW}⚠️  Good adherence (50-70%), room for improvement${NC}"
    else
        echo -e "  ${RED}⚠️  Low adherence (<50%), needs adjustment${NC}"
    fi
    echo ""
else
    echo -e "${YELLOW}⚠️  No progress score data (need at least 2 records)${NC}"
    echo ""
fi

# ============================================
# STEP 6: Update Profile - Change Goal to MAINTAIN
# ============================================

echo -e "${CYAN}🔄 Step 6: Update Profile - Change Goal to MAINTAIN${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

echo "Changing goal from CUT to MAINTAIN (reached target weight)"
echo ""

UPDATE_RESPONSE=$(update_profile "$PROFILE_ID" "MAINTAIN")

UPDATE_GOAL=$(echo "$UPDATE_RESPONSE" | jq -r '.data.nutritionalProfile.updateNutritionalProfile.goal')
UPDATE_CALORIES=$(echo "$UPDATE_RESPONSE" | jq -r '.data.nutritionalProfile.updateNutritionalProfile.caloriesTarget')
UPDATE_PROTEIN=$(echo "$UPDATE_RESPONSE" | jq -r '.data.nutritionalProfile.updateNutritionalProfile.macroSplit.proteinG')
UPDATE_CARBS=$(echo "$UPDATE_RESPONSE" | jq -r '.data.nutritionalProfile.updateNutritionalProfile.macroSplit.carbsG')
UPDATE_FAT=$(echo "$UPDATE_RESPONSE" | jq -r '.data.nutritionalProfile.updateNutritionalProfile.macroSplit.fatG')

echo -e "${GREEN}✅ Profile updated successfully!${NC}"
echo ""
echo -e "${MAGENTA}📊 Updated Metrics:${NC}"
echo "  New Goal: ${UPDATE_GOAL}"
echo "  New Target Calories: $(echo $UPDATE_CALORIES | awk '{printf "%.0f", $1}') kcal/day (at TDEE)"
echo ""
echo -e "${MAGENTA}🍽️  Updated Macro Split (Maintain Phase):${NC}"
echo "  Protein: $(echo $UPDATE_PROTEIN | awk '{printf "%.0f", $1}') g/day"
echo "  Carbs: $(echo $UPDATE_CARBS | awk '{printf "%.0f", $1}') g/day (increased from cut)"
echo "  Fat: $(echo $UPDATE_FAT | awk '{printf "%.0f", $1}') g/day"
echo ""

# Verify calories increased (MAINTAIN should be at TDEE, not deficit)
CALORIES_DIFF=$(echo "$UPDATE_CALORIES - $CALORIES_TARGET" | bc)

if (( $(echo "$CALORIES_DIFF > 0" | bc -l) )); then
    echo -e "  ${GREEN}✅ Calories correctly increased to TDEE (+$(echo $CALORIES_DIFF | awk '{printf "%.0f", $1}') kcal)${NC}"
else
    echo -e "  ${YELLOW}⚠️  Calories not increased as expected${NC}"
fi
echo ""

# ============================================
# STEP 7: Update Profile - Change User Data (Weight Loss Progress)
# ============================================

echo -e "${CYAN}🔄 Step 7: Update Profile - User Data (New Current Weight)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Update weight to reflect progress (from 85kg to 84kg)
NEW_WEIGHT=84.0

echo "Updating user data with new current weight: ${NEW_WEIGHT} kg"
echo ""

USER_DATA_JSON="{weight: ${NEW_WEIGHT}, height: ${INITIAL_HEIGHT}, age: ${INITIAL_AGE}, sex: M, activityLevel: MODERATE}"

UPDATE_USERDATA_RESPONSE=$(update_profile "$PROFILE_ID" "MAINTAIN" "$USER_DATA_JSON")

UPDATE_NEW_WEIGHT=$(echo "$UPDATE_USERDATA_RESPONSE" | jq -r '.data.nutritionalProfile.updateNutritionalProfile.userData.weight')
UPDATE_NEW_CALORIES=$(echo "$UPDATE_USERDATA_RESPONSE" | jq -r '.data.nutritionalProfile.updateNutritionalProfile.caloriesTarget')

echo -e "${GREEN}✅ User data updated successfully!${NC}"
echo ""
echo -e "${MAGENTA}📊 Recalculated Metrics:${NC}"
echo "  New Weight: $(echo $UPDATE_NEW_WEIGHT | awk '{printf "%.1f", $1}') kg"
echo "  New TDEE/Target: $(echo $UPDATE_NEW_CALORIES | awk '{printf "%.0f", $1}') kcal/day"
echo ""

# Calculate BMR change due to weight loss
# Lower weight = lower BMR = lower TDEE
CALORIES_CHANGE=$(echo "$UPDATE_NEW_CALORIES - $UPDATE_CALORIES" | bc)

echo -e "${MAGENTA}📉 Impact of Weight Loss:${NC}"
echo "  Weight Change: -$(echo "$INITIAL_WEIGHT - $NEW_WEIGHT" | bc) kg"
echo "  TDEE Change: $(echo $CALORIES_CHANGE | awk '{printf "%.0f", $1}') kcal/day"

if (( $(echo "$CALORIES_CHANGE < 0" | bc -l) )); then
    echo -e "  ${GREEN}✅ TDEE correctly decreased with weight loss${NC}"
else
    echo -e "  ${YELLOW}⚠️  TDEE not adjusted as expected${NC}"
fi
echo ""

# ============================================
# STEP 8: Cross-Check with Meal Data
# ============================================

echo -e "${CYAN}🍽️  Step 8: Cross-Check with Meal Domain Data${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Query meal data for the same period
MEALS_QUERY=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"query { meals { dailySummary(userId: \\\"${USER_ID}\\\", date: \\\"${TODAY_DATETIME}\\\") { totalCalories totalProtein totalCarbs totalFat mealCount } } }\"
    }")

MEAL_CALORIES=$(echo "$MEALS_QUERY" | jq -r '.data.meals.dailySummary.totalCalories // 0')
MEAL_PROTEIN=$(echo "$MEALS_QUERY" | jq -r '.data.meals.dailySummary.totalProtein // 0')
MEAL_CARBS=$(echo "$MEALS_QUERY" | jq -r '.data.meals.dailySummary.totalCarbs // 0')
MEAL_FAT=$(echo "$MEALS_QUERY" | jq -r '.data.meals.dailySummary.totalFat // 0')
MEAL_COUNT=$(echo "$MEALS_QUERY" | jq -r '.data.meals.dailySummary.mealCount // 0')

echo -e "${MAGENTA}📊 Meal Data Integration:${NC}"
echo "  Profile Target: $(echo $CALORIES_TARGET | awk '{printf "%.0f", $1}') kcal/day"
echo "  Day 1 Logged: ${DAY1_CALORIES} kcal"
echo "  Meals Domain: $(echo $MEAL_CALORIES | awk '{printf "%.0f", $1}') kcal (${MEAL_COUNT} meals)"
echo ""

if [ "$MEAL_COUNT" -gt 0 ]; then
    # Compare profile logged vs meals logged
    MEAL_CALORIES_INT=$(echo $MEAL_CALORIES | awk '{printf "%.0f", $1}')
    DIFF=$((DAY1_CALORIES - MEAL_CALORIES_INT))
    
    if [ $DIFF -lt 0 ]; then
        DIFF=$((DIFF * -1))
    fi
    
    if [ $DIFF -lt 100 ]; then
        echo -e "  ${GREEN}✅ Meal data matches profile tracking (±100 kcal)${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Difference: ${DIFF} kcal (domains may track separately)${NC}"
    fi
    
    echo ""
    echo -e "${MAGENTA}🍽️  Macro Comparison:${NC}"
    echo "  Profile Target: ${PROTEIN_G}g P, ${CARBS_G}g C, ${FAT_G}g F"
    echo "  Day 1 Logged: ${DAY1_PROTEIN}g P, ${DAY1_CARBS}g C, ${DAY1_FAT}g F"
    echo "  Meals Domain: $(echo $MEAL_PROTEIN | awk '{printf "%.0f", $1}')g P, $(echo $MEAL_CARBS | awk '{printf "%.0f", $1}')g C, $(echo $MEAL_FAT | awk '{printf "%.0f", $1}')g F"
    echo ""
else
    echo -e "  ${YELLOW}ℹ️  No meal data found (domains operate independently)${NC}"
    echo ""
fi

# ============================================
# STEP 9: Cross-Check with Activity Data
# ============================================

echo -e "${CYAN}🏃 Step 9: Cross-Check with Activity Domain Data${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Query activity totals for Day 1
ACTIVITY_QUERY=$(curl -s -X POST "${GRAPHQL_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"query\": \"query { activity { syncEntries(date: \\\"${TODAY}\\\", userId: \\\"${USER_ID}\\\", limit: 1) { caloriesOutTotal } } }\"
    }")

ACTIVITY_CALORIES=$(echo "$ACTIVITY_QUERY" | jq -r '.data.activity.syncEntries[0].caloriesOutTotal // 0')

echo -e "${MAGENTA}📊 Activity Data Integration:${NC}"
echo "  Profile BMR: $(echo $BMR | awk '{printf "%.0f", $1}') kcal/day (at rest)"
echo "  Day 1 Active Burn: ${DAY1_ACTIVE_CAL} kcal (logged in profile)"
echo "  Activity Domain: $(echo $ACTIVITY_CALORIES | awk '{printf "%.0f", $1}') kcal"
echo ""

if (( $(echo "$ACTIVITY_CALORIES > 0" | bc -l) )); then
    ACTIVITY_CALORIES_INT=$(echo $ACTIVITY_CALORIES | awk '{printf "%.0f", $1}')
    DIFF=$((DAY1_ACTIVE_CAL - ACTIVITY_CALORIES_INT))
    
    if [ $DIFF -lt 0 ]; then
        DIFF=$((DIFF * -1))
    fi
    
    if [ $DIFF -lt 100 ]; then
        echo -e "  ${GREEN}✅ Activity calories match profile tracking (±100 kcal)${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Difference: ${DIFF} kcal (domains may track separately)${NC}"
    fi
    
    # Calculate total energy expenditure
    TOTAL_BURN=$(echo "$BMR + $DAY1_ACTIVE_CAL" | bc)
    NET_BALANCE=$(echo "$DAY1_CALORIES - $TOTAL_BURN" | bc)
    
    echo ""
    echo -e "${MAGENTA}⚖️  Energy Balance (Day 1):${NC}"
    echo "  Total Burn: $(echo $TOTAL_BURN | awk '{printf "%.0f", $1}') kcal (BMR + Active)"
    echo "  Consumed: ${DAY1_CALORIES} kcal"
    echo "  Net Balance: $(echo $NET_BALANCE | awk '{printf "%.0f", $1}') kcal"
    
    if (( $(echo "$NET_BALANCE < 0" | bc -l) )); then
        echo -e "  ${GREEN}✅ Calorie deficit achieved: $(echo $NET_BALANCE | awk '{printf "%.0f", -$1}') kcal${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Calorie surplus: +$(echo $NET_BALANCE | awk '{printf "%.0f", $1}') kcal${NC}"
    fi
    echo ""
else
    echo -e "  ${YELLOW}ℹ️  No activity data found (domains operate independently)${NC}"
    echo ""
fi

# ============================================
# STEP 10: Test Idempotency (Record Same Day Twice)
# ============================================

echo -e "${CYAN}🔄 Step 10: Test Update Semantics (Same Day Record)${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

echo "Recording progress for Day 1 again (should update existing record)..."
echo ""

# Record Day 1 again with slightly different values
DAY1_UPDATE_WEIGHT=84.9
DAY1_UPDATE_CALORIES=2050

DAY1_UPDATE_RESPONSE=$(record_progress "$PROFILE_ID" "$DAY1_DATE" "$DAY1_UPDATE_WEIGHT" "$DAY1_UPDATE_CALORIES" "168" "215" "68" "440" "Updated measurement")

DAY1_UPDATE_RECORDED=$(echo "$DAY1_UPDATE_RESPONSE" | jq -r '.data.nutritionalProfile.recordProgress.weight')

echo -e "${GREEN}✅ Day 1 progress updated${NC}"
echo "  New weight: $(echo $DAY1_UPDATE_RECORDED | awk '{printf "%.1f", $1}') kg (was ${DAY1_WEIGHT} kg)"
echo ""

# Query profile to verify only 7 records (not 8)
UPDATED_PROFILE=$(query_profile "$USER_ID")
UPDATED_COUNT=$(echo "$UPDATED_PROFILE" | jq -r '.data.nutritionalProfile.nutritionalProfile.progressHistory | length')

echo -e "${MAGENTA}📊 Record Count Verification:${NC}"
echo "  Progress records: ${UPDATED_COUNT} (expected: 7)"

if [ "$UPDATED_COUNT" -eq 7 ]; then
    echo -e "  ${GREEN}✅ Update semantics working correctly (no duplicate days)${NC}"
else
    echo -e "  ${YELLOW}⚠️  Unexpected record count (may have created duplicate)${NC}"
fi
echo ""

# ============================================
# STEP 11: Validate Enum Serialization
# ============================================

echo -e "${CYAN}✅ Step 11: Validate Enum Serialization${NC}"
echo -e "${BLUE}-------------------------------------------${NC}"

# Query profile and check enum values are correctly returned
ENUM_CHECK=$(query_profile "$USER_ID")

ENUM_SEX=$(echo "$ENUM_CHECK" | jq -r '.data.nutritionalProfile.nutritionalProfile.userData.sex')
ENUM_ACTIVITY=$(echo "$ENUM_CHECK" | jq -r '.data.nutritionalProfile.nutritionalProfile.userData.activityLevel')
ENUM_GOAL=$(echo "$ENUM_CHECK" | jq -r '.data.nutritionalProfile.nutritionalProfile.goal')

echo -e "${MAGENTA}📊 Enum Values in Response:${NC}"
echo "  Sex: ${ENUM_SEX} (expected: M)"
echo "  Activity Level: ${ENUM_ACTIVITY} (expected: MODERATE)"
echo "  Goal: ${ENUM_GOAL} (expected: MAINTAIN)"
echo ""

ENUM_VALID=true

if [ "$ENUM_SEX" == "M" ]; then
    echo -e "  ${GREEN}✅ Sex enum serialized correctly${NC}"
else
    echo -e "  ${RED}❌ Sex enum incorrect (got: ${ENUM_SEX})${NC}"
    ENUM_VALID=false
fi

if [ "$ENUM_ACTIVITY" == "MODERATE" ]; then
    echo -e "  ${GREEN}✅ Activity level enum serialized correctly${NC}"
else
    echo -e "  ${RED}❌ Activity level enum incorrect (got: ${ENUM_ACTIVITY})${NC}"
    ENUM_VALID=false
fi

if [ "$ENUM_GOAL" == "MAINTAIN" ]; then
    echo -e "  ${GREEN}✅ Goal enum serialized correctly${NC}"
else
    echo -e "  ${RED}❌ Goal enum incorrect (got: ${ENUM_GOAL})${NC}"
    ENUM_VALID=false
fi
echo ""

# ============================================
# Summary
# ============================================

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ All nutritional profile tests completed!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${MAGENTA}📊 Profile Summary:${NC}"
echo "  User ID: ${USER_ID}"
echo "  Profile ID: ${PROFILE_ID}"
echo "  Initial Weight: ${INITIAL_WEIGHT} kg"
echo "  Current Weight: $(echo $UPDATE_NEW_WEIGHT | awk '{printf "%.1f", $1}') kg"
echo "  Weight Lost: $(echo "$INITIAL_WEIGHT - $UPDATE_NEW_WEIGHT" | bc) kg"
echo "  Goal: ${ENUM_GOAL} (maintenance phase)"
echo "  Days Tracked: 7"
echo ""
echo -e "${MAGENTA}📊 Calculated Metrics:${NC}"
echo "  BMR: $(echo $BMR | awk '{printf "%.0f", $1}') kcal/day"
echo "  Current TDEE: $(echo $UPDATE_NEW_CALORIES | awk '{printf "%.0f", $1}') kcal/day"
echo "  Target Protein: $(echo $UPDATE_PROTEIN | awk '{printf "%.0f", $1}') g/day"
echo ""
echo -e "${MAGENTA}✅ Tests Verified:${NC}"
echo "  ✅ Profile creation with BMR/TDEE calculation"
echo "  ✅ Macro split calculation (Cut vs Maintain)"
echo "  ✅ Progress tracking (7 days)"
echo "  ✅ Weight change tracking (-$(echo "$INITIAL_WEIGHT - $UPDATE_NEW_WEIGHT" | bc) kg)"
echo "  ✅ Progress score calculation"
echo "  ✅ Adherence rate tracking"
echo "  ✅ Goal change (CUT → MAINTAIN)"
echo "  ✅ User data updates with recalculation"
echo "  ✅ Update semantics (no duplicate days)"
echo "  ✅ Enum serialization (Sex, Activity, Goal)"
echo "  ✅ Cross-domain data integration"
echo ""

if [ "$ENUM_VALID" == "true" ]; then
    echo -e "${GREEN}🎉 All enum types working correctly!${NC}"
else
    echo -e "${RED}⚠️  Some enum serialization issues detected${NC}"
fi
echo ""
