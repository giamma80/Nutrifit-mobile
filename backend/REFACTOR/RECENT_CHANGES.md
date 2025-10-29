# 📝 Recent Changes - 29 Ottobre 2025

**Summary**: Range query APIs (v2.1), timezone fixes, legacy test cleanup (Phase 8), documentation updates.

---

## 🧹 Cleanup (Phase 8) - 29 Ottobre 2025

### 1. Legacy Test Cleanup (P8.2 Completed)

**Removed**: 21 legacy test files (2356 lines) that used old OpenAI adapter system.

**Categories Removed**:
1. **OpenAI Adapter Tests** (8 files): 
   - test_gpt4v_adapter_success.py
   - test_gpt4v_adapter_parse_error.py
   - test_gpt4v_adapter_partial_response.py
   - test_gpt4v_adapter_timeout_fallback.py
   - test_gpt4v_adapter_transient_error_fallback.py
   - test_gpt4v_adapter_enrichment.py
   - test_inference_adapter.py
   - test_inference_adapter_selection.py

2. **Prompt v3 Tests** (3 files):
   - test_prompt_v3.py
   - test_integration_v3.py
   - test_dish_title_italian.py

3. **USDA Integration Tests** (6 files):
   - test_simple_usda.py
   - test_usda_connectivity.py
   - test_usda_fallback.py
   - test_usda_integration.py
   - test_nutrient_enrichment.py
   - test_end_to_end_enrichment.py

4. **Feature Tests** (3 files):
   - test_improved_usda_labels.py
   - test_normalization_unit.py
   - test_ai_meal_photo_metrics_sentinel.py

5. **Dependency Test** (1 file):
   - test_openai_integration_deps.py

**Replacement Coverage**:
- OpenAI: `tests/unit/infrastructure/test_openai_client.py` (15 tests)
- USDA: `tests/test_e2e_usda_enrichment.py` (19 tests)
- Integration: `tests/integration/infrastructure/` (comprehensive)

**Impact**:
- ✅ **Test Suite Clean**: 640 tests passing (was 661), 1 skipped
- ✅ **Architecture Aligned**: Only new system tested
- ✅ **Maintenance Reduced**: -2356 lines of obsolete code
- ✅ **Clarity Improved**: No confusion about which system to use

**Deferred**: P8.1 (Remove legacy adapter files) - Files kept for backward compatibility but not tested.

**Commit**: `d7368e9` - "chore: remove 21 legacy test files using old OpenAI adapter"

---

## 🚀 New Features (v2.1)

### 1. Range Query APIs

**Added**: Two new GraphQL APIs for efficient multi-day aggregations.

**APIs**:
```graphql
# Nutrition aggregates across multiple days
meals {
  summaryRange(
    userId: ID!
    startDate: String!  # ISO date (YYYY-MM-DD)
    endDate: String!
    groupBy: GroupByPeriod!  # DAY, WEEK, MONTH
  ): RangeSummaryResult!
}

# Activity aggregates across multiple days
activity {
  aggregateRange(
    userId: ID!
    startDate: String!
    endDate: String!
    groupBy: GroupByPeriod!
  ): ActivityRangeResult!
}
```

**Key Features**:
- **Flexible Grouping**: DAY, WEEK (Mon-Sun), MONTH boundaries
- **Server-Side Aggregation**: 1 query instead of N daily queries
- **Comprehensive Metrics**: Full nutrition totals + activity stats
- **Period Summaries**: Individual period data + grand total

**Use Cases**:
- 📊 Weekly nutrition dashboard (1 query vs 7)
- 📈 Monthly progress reports
- 🎯 Goal tracking with period comparisons
- 🔍 Trend analysis across time ranges

**Implementation**:
- `GetSummaryRangeQueryHandler`: Meal domain range queries
- `GetAggregateRangeQueryHandler`: Activity domain range queries
- `GroupByPeriod` enum: Shared domain type in `domain/shared/types.py`

---

## 🔧 Infrastructure Improvements

### 1. Atomic Timezone Parser

**Added**: Reusable timezone parsing utility.

**File**: `graphql/utils/datetime_helpers.py`

**Function**:
```python
def parse_datetime_to_naive_utc(dt_string: str) -> datetime:
    """Parse ISO datetime string to naive UTC datetime.
    
    Handles:
    - Timezone-aware strings (2025-01-01T12:00:00Z)
    - Naive strings (2025-01-01T12:00:00)
    - Normalizes to naive UTC for consistent comparisons
    """
```

**Benefits**:
- ✅ DRY: Single source of truth for datetime parsing
- ✅ Consistent: Same logic across meal and activity flows
- ✅ Robust: Handles both naive and aware datetime strings
- ✅ Testable: Isolated unit for timezone logic

---

## �🐛 Bug Fixes

### 1. Timezone Comparison Error (CRITICAL)

**Issue**: `TypeError: can't compare offset-naive and offset-aware datetimes` in meal repository.

**Root Cause**: 
- `Meal.timestamp` is timezone-aware (UTC)
- Query date filters use naive datetimes
- Direct comparison failed

**Fix Applied**:
```python
# File: infrastructure/persistence/in_memory/meal_repository.py

def get_by_user_and_date_range(self, user_id, start_date, end_date):
    return [
        meal for meal in self._meals.values()
        if meal.user_id == user_id
        and start_date <= meal.timestamp.replace(tzinfo=None) <= end_date  # ✅ Normalize to naive
    ]
```

**Impact**:
- ✅ All range queries now work correctly
- ✅ No data loss or incorrect filtering
- ✅ 28/28 integration tests passing

### 2. Activity Repository Not Implemented

**Issue**: `list_events()` raised `NotImplementedError`.

**Fix Applied**:
```python
# File: repository/activities.py

def list_events(self, user_id=None, start_time=None, end_time=None, limit=None):
    # Full implementation with date filtering, user filtering, limit application
    events = list(self._events.values())
    
    if user_id:
        events = [e for e in events if e.user_id == user_id]
    if start_time:
        events = [e for e in events if parse_iso(e.timestamp) >= start_time]
    if end_time:
        events = [e for e in events if parse_iso(e.timestamp) <= end_time]
    if limit:
        events = events[:limit]
    
    return events
```

**Impact**:
- ✅ Activity range queries functional
- ✅ Proper date filtering
- ✅ All activity tests passing (16/16)

### 3. macOS Date Command Compatibility

**Issue**: Test scripts used Linux `date -d` which doesn't work on macOS.

**Fix Applied**:
```bash
# Platform-agnostic date calculation
YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
WEEK_AGO=$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d "7 days ago" +%Y-%m-%d)
```

**Impact**:
- ✅ Test scripts work on macOS and Linux
- ✅ CI/CD compatibility

---

## 🐛 Bug Fixes (Previous)

### 1. Barcode ImageUrl Persistence (CRITICAL)

**Issue**: Meals analyzed via barcode were missing product images (`imageUrl: null` in GraphQL response).

**Root Cause**: 
- `BarcodeOrchestrator.analyze()` wasn't passing `product.image_url` from OpenFoodFacts to `MealFactory`
- OpenFoodFacts API correctly returned product images, but they were being ignored

**Fix Applied**:
```python
# File: backend/application/meal/orchestrators/barcode_orchestrator.py (lines 169-177)

# BEFORE:
food_dict = {
    "label": product.name,
    "display_name": product.display_name(),
    "quantity_g": quantity_g,
    "confidence": 1.0,
    "category": None,
}

# AFTER:
food_dict = {
    "label": product.name,
    "display_name": product.display_name(),
    "quantity_g": quantity_g,
    "confidence": 1.0,
    "category": None,
    "barcode": barcode,              # ✅ Added: Store barcode in entry metadata
    "image_url": product.image_url,  # ✅ Added: Preserve product image from OpenFoodFacts
}
```

**Impact**:
- 🎯 **UX Improvement**: Users now see product photos when scanning barcodes
- 🔄 **Consistency**: Both photo analysis and barcode workflows display images
- ✅ **Data Completeness**: OpenFoodFacts image_url data no longer lost

**Validation**:
```bash
$ ./backend/scripts/test_meal_persistence.sh giamma
✅ Barcode analyzed: BARILLA NORGE ASbarilla - SPAGHETTI N° 5
  Meal ID: 3a6e848c-31fa-413e-b357-1fdef2f45c55
  Calories: 359 kcal
  Image URL: https://images.openfoodfacts.org/images/products/807/680/019/5057/front_en.3428.400.jpg
```

**Commit**: `fix(barcode): preserve image_url from OpenFoodFacts in BarcodeOrchestrator`

---

## 🧪 Test Infrastructure Enhancements

### 2. Comprehensive End-to-End Test Scripts

**Context**: Need for flexible, comprehensive testing across different environments (dev, staging, production).

**New Test Scripts Created**:

#### A. Meal Persistence Testing (`test_meal_persistence.sh` - 493 lines)

**Features**:
- ✅ Photo analysis workflow (upload image → analyze → confirm)
- ✅ Barcode analysis workflow (barcode → analyze → confirm)
- ✅ Search meals functionality
- ✅ Daily summary aggregation
- ✅ Cross-verification with activity data (steps → calories)
- ✅ Image URL persistence validation

**Usage**:
```bash
# Default: localhost:8080 with unique test user
./backend/scripts/test_meal_persistence.sh

# Custom BASE_URL and USER_ID
./backend/scripts/test_meal_persistence.sh http://localhost:8080 giamma

# Environment variables
BASE_URL=http://staging.com USER_ID=test-staging ./backend/scripts/test_meal_persistence.sh
```

#### B. Activity Persistence Testing (`test_activity_persistence.sh` - 755 lines)

**Features**:
- ✅ 440 minute-by-minute activity events
- ✅ 10+ workout types (walks, gym cardio, strength training)
- ✅ Realistic daily simulation:
  - ~19,683 steps
  - ~1,168 kcal burned
  - HR avg 95 bpm
- ✅ syncHealthTotals testing (3 cumulative snapshots)
- ✅ Deduplication and idempotency validation

**Workout Types Tested**:
1. Morning walk (30 min, 7:00-7:30)
2. Gym cardio session (45 min, 8:00-8:45)
3. Lunch walk (15 min, 12:30-12:45)
4. Afternoon walk (20 min, 15:00-15:20)
5. Gym strength training (30 min, 18:00-18:30)
6. Light activity periods (300 min distributed throughout day)

**Usage**:
```bash
# Default configuration
./backend/scripts/test_activity_persistence.sh

# Custom configuration
./backend/scripts/test_activity_persistence.sh http://localhost:8080 giamma
```

#### Script Features (Both Scripts)

**Parameterization**:
- CLI arguments: `./script.sh [BASE_URL] [USER_ID]`
- Environment variables: `BASE_URL=... USER_ID=... ./script.sh`
- Smart defaults: `http://localhost:8080` + `test-user-${TIMESTAMP}`

**Reliability**:
- Timeout handling: `--max-time 10` on all curl calls
- Clean state verification: Each run uses unique user_id
- Port correction: Default 8080 (was incorrectly 8000)

**Output**:
- Comprehensive validation messages
- Color-coded success/failure indicators
- Detailed response inspection

**Total Coverage**: 1248 lines of comprehensive test logic

**Impact**:
- 🚀 **E2E Validation**: Complete meal + activity workflows tested
- 🔧 **Flexibility**: Works seamlessly across dev, staging, production
- 🎯 **Reproducibility**: Unique user per run, clean state guaranteed
- ✅ **Comprehensive Coverage**: All critical user journeys validated

**Commits**:
- `feat(test): add comprehensive test scripts for meal and activity persistence`
- `fix(test): parameterize BASE_URL and USER_ID in test scripts`
- `fix(test): correct default port from 8000 to 8080`

---

## 📝 Documentation Improvements

### 3. GraphQL API Type Corrections

**Context**: Activity API documentation had type inconsistencies that didn't match the actual GraphQL schema.

**Issues Fixed**:

#### A. ActivityMinuteInput Type Mismatches

**BEFORE** (Incorrect):
```graphql
input ActivityMinuteInput {
  ts: DateTime!           # ❌ DateTime type doesn't exist in GraphQL
  steps: Int! = 0         # ❌ Default syntax incorrect
  hrAvg: Int!             # ❌ Should be Float (heart rate can be decimal)
  source: ActivitySource! # ❌ Should be optional with default MANUAL
}
```

**AFTER** (Corrected):
```graphql
input ActivityMinuteInput {
  ts: String!             # ✅ ISO 8601 string format
  steps: Int              # ✅ Optional with default 0
  hrAvg: Float            # ✅ Float for heart rate precision
  source: ActivitySource  # ✅ Optional with default MANUAL
}
```

#### B. ActivityEvent Fields Incorrect

**BEFORE** (Documented non-existent fields):
```graphql
type ActivityEvent {
  id: ID!                 # ❌ Field doesn't exist
  timestamp: DateTime!    # ❌ Wrong field name (should be `ts`)
  distance: Float         # ❌ Field doesn't exist
  activeMinutes: Int      # ❌ Field doesn't exist
  # ... other fields
}
```

**AFTER** (Corrected):
```graphql
type ActivityEvent {
  ts: String!             # ✅ Correct timestamp field (ISO 8601)
  userId: String!
  steps: Int!
  hrAvg: Float
  workoutType: WorkoutType
  intensity: IntensityLevel
  source: ActivitySource!
  # ✅ No id, distance, or activeMinutes fields
}
```

#### C. HealthTotalsDelta Clarification

**Issue**: Documentation was ambiguous about whether values were delta increments or cumulative totals.

**Added Clarification**:
```graphql
"""
HealthTotalsDelta: DELTA INCREMENTS (not cumulative totals)

These are incremental values to ADD to cumulative totals:
- steps: Steps to ADD to cumulative total
- calories: Calories to ADD to cumulative total  
- activeMinutes: Minutes to ADD to cumulative total

Usage:
  cumulativeTotal += delta.steps
"""
```

**Impact**:
- 🎯 **Accuracy**: Documentation now matches actual GraphQL schema
- 🔧 **Developer Clarity**: No more confusion about optional fields and types
- ✅ **API Consistency**: Activity API types correctly documented

**File Modified**: `backend/REFACTOR/graphql-api-reference.md` (~50 lines corrected)

**Commit**: `fix(docs): correct Activity API types in graphql-api-reference.md`

---

## 📊 Test Results

**After All Changes**:
- ✅ **668 tests passing** (was 605 before changes)
- ✅ **make lint clean** (flake8 + mypy on 256 files)
- ✅ **0 known bugs** in meal/activity workflows
- ✅ **E2E validation complete** for all critical user journeys

---

## 🔗 Related Documentation

For complete details on all changes, see:
- [IMPLEMENTATION_TRACKER.md](./IMPLEMENTATION_TRACKER.md#changelog) - Full changelog with commit references
- [README.md](./README.md#end-to-end-test-scripts) - Test script usage guide
- [graphql-api-reference.md](./graphql-api-reference.md) - Complete GraphQL API documentation

---

## 🎯 Next Steps

1. ✅ All bug fixes validated and documented
2. ✅ Test infrastructure comprehensive and flexible
3. ✅ Documentation accurate and up-to-date
4. 🔄 Ready to resume main refactoring work (Phase 8: Legacy Cleanup)

---

**Date**: 27 Ottobre 2025  
**Status**: ✅ All changes validated and documented  
**Test Coverage**: 668/668 tests passing
