# Nutrifit E2E Test Scripts

Comprehensive integration test scripts for all Nutrifit domains.

## Available Scripts

### 1. `test_meal_persistence.sh`
Tests the **Meal Domain** with photo recognition, barcode scanning, and nutrition tracking.

**Features tested:**
- Photo meal recognition (AI-based)
- Barcode scanning (Open Food Facts)
- Manual meal creation
- Daily nutrition summaries
- Date range aggregations
- Deduplication and idempotency

**Usage:**
```bash
# Default (random user, localhost:8080)
./test_meal_persistence.sh

# Custom endpoint
./test_meal_persistence.sh http://localhost:8080

# Custom endpoint + user
./test_meal_persistence.sh http://localhost:8080 giamma

# Environment variables
BASE_URL="http://localhost:8080" USER_ID="giamma" ./test_meal_persistence.sh
```

---

### 2. `test_activity_persistence.sh`
Tests the **Activity Domain** with health data sync and calorie tracking.

**Features tested:**
- Minute-by-minute activity events
- Health totals sync (cumulative snapshots)
- Delta calculation
- Activity aggregations (DAY/WEEK/MONTH)
- Deduplication on (userId, timestamp)
- Idempotency keys

**Usage:**
```bash
# Default (random user, localhost:8080)
./test_activity_persistence.sh

# Custom endpoint
./test_activity_persistence.sh http://localhost:8080

# Custom endpoint + user
./test_activity_persistence.sh http://localhost:8080 giamma

# Environment variables
BASE_URL="http://localhost:8080" USER_ID="giamma" ./test_activity_persistence.sh
```

---

### 3. `test_nutritional_profile_persistence.sh`
Tests the **Nutritional Profile Domain** with BMR/TDEE calculations and progress tracking.

**Features tested:**
- Profile creation with BMR/TDEE calculation
- Macro split calculation (Cut/Maintain/Bulk)
- Progress tracking (weight, calories, macros)
- Progress score and adherence rate
- Goal changes with recalculation
- User data updates
- Enum serialization (Sex, Activity Level, Goal)
- Cross-domain integration

**Usage:**
```bash
# Default (random user, localhost:8080)
./test_nutritional_profile_persistence.sh

# Custom endpoint
./test_nutritional_profile_persistence.sh http://localhost:8080

# Custom endpoint + user
./test_nutritional_profile_persistence.sh http://localhost:8080 giamma

# Environment variables
BASE_URL="http://localhost:8080" USER_ID="giamma" ./test_nutritional_profile_persistence.sh
```

---

### 4. `test_all_domains_e2e.sh` 🌟
**Master test suite** that runs all three domain tests in sequence with a single user ID.

**Full E2E scenario:**
1. **Nutritional Profile** - Create profile with CUT goal
2. **Meal Domain** - Log meals throughout the day
3. **Activity Domain** - Sync workout and activity data
4. **Cross-Domain Validation** - Calculate energy balance

**Usage:**
```bash
# Default (random user, localhost:8080)
./test_all_domains_e2e.sh

# Custom endpoint
./test_all_domains_e2e.sh http://localhost:8080

# Custom endpoint + user
./test_all_domains_e2e.sh http://localhost:8080 giamma

# Environment variables
BASE_URL="http://localhost:8080" USER_ID="giamma" ./test_all_domains_e2e.sh
```

**Output:**
- Profile summary (goal, weight, target calories)
- Meal summary (meals logged, calories, macros)
- Activity summary (steps, calories burned)
- **Energy balance** (deficit/surplus calculation)

---

## Common Usage Patterns

### Development Testing
```bash
# Test single domain during development
./test_nutritional_profile_persistence.sh

# Test with specific user
./test_nutritional_profile_persistence.sh "" myuser123
```

### CI/CD Pipeline
```bash
# Full E2E test with unique user per run
./test_all_domains_e2e.sh http://staging.nutrifit.com

# Verify specific domain
./test_meal_persistence.sh http://staging.nutrifit.com test_user_ci
```

### Data Preparation
```bash
# Populate system with test data for demo
USER_ID="demo_user" ./test_all_domains_e2e.sh

# Create multiple users
for i in {1..5}; do
    ./test_all_domains_e2e.sh "" "demo_user_$i"
done
```

### Cross-Domain Validation
```bash
# Use same user across all domains
USER="integration_test_user"
./test_nutritional_profile_persistence.sh "" "$USER"
./test_meal_persistence.sh "" "$USER"
./test_activity_persistence.sh "" "$USER"

# Then validate cross-domain data
curl -X POST http://localhost:8080/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { nutritionalProfile { progressScore(userId: \"'$USER'\", startDate: \"2025-10-31\", endDate: \"2025-11-06\") { weightDelta avgDailyCalories avgDeficit adherenceRate } } }"
  }'
```

---

## Parameter Reference

### Common Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `BASE_URL` | GraphQL endpoint base URL | `http://localhost:8080` |
| `USER_ID` | User identifier for test data | `test_user_<timestamp>` |

### Environment Variables

All scripts support environment variables:

```bash
export BASE_URL="http://localhost:8080"
export USER_ID="my_test_user"

# Now all scripts use these values
./test_nutritional_profile_persistence.sh
./test_meal_persistence.sh
./test_activity_persistence.sh
```

### Positional Arguments

```bash
# Format: script [BASE_URL] [USER_ID]

# Just URL
./test_nutritional_profile_persistence.sh http://localhost:8080

# URL + User
./test_nutritional_profile_persistence.sh http://localhost:8080 giamma

# Skip URL, provide User (use empty string for default URL)
./test_nutritional_profile_persistence.sh "" giamma
```

---

## Test Data Generated

### Nutritional Profile Domain
- 1 profile with BMR/TDEE calculations
- 7 days of progress records
- Weight tracking (85kg → 84kg)
- Macro adherence tracking
- Goal change (CUT → MAINTAIN)

### Meal Domain
- 3-5 meals per day (photo/barcode/manual)
- Daily nutrition totals
- ~2000-2500 kcal consumed
- Protein/carbs/fat breakdown

### Activity Domain
- 440+ minute-by-minute events
- 5 activity sessions (walks, gym)
- 10,000-12,000 steps
- ~800-1000 kcal burned
- 3 health total snapshots

---

## Expected Results

### Individual Domain Tests
Each script validates:
- ✅ Data persistence
- ✅ Calculations (BMR, TDEE, macros, calories)
- ✅ Deduplication
- ✅ Idempotency
- ✅ Enum serialization
- ✅ Date ranges and aggregations

### E2E Test Suite
Validates:
- ✅ Profile creation and tracking
- ✅ Meal logging and summaries
- ✅ Activity sync and totals
- ✅ **Cross-domain energy balance**
- ✅ Data consistency across domains

**Example Energy Balance:**
```
Calories IN:  2100 kcal (meals)
Calories OUT: 2400 kcal (BMR + activity)
Net Balance:  -300 kcal (DEFICIT) ✅
```

---

## Troubleshooting

### Script Not Executable
```bash
chmod +x scripts/*.sh
```

### Connection Refused
```bash
# Check server is running
curl http://localhost:8080/graphql

# Or specify correct URL
./test_all_domains_e2e.sh http://localhost:8000
```

### jq Not Found
```bash
# macOS
brew install jq

# Linux
sudo apt-get install jq
```

### bc Not Found
```bash
# macOS (usually pre-installed)
brew install bc

# Linux
sudo apt-get install bc
```

---

## Output Color Codes

- 🔵 **Blue** - Section headers
- 🟢 **Green** - Success messages, validated data
- 🟡 **Yellow** - Warnings, informational notes
- 🔴 **Red** - Errors, failures
- 🟣 **Magenta** - Summaries, statistics
- 🔷 **Cyan** - Step descriptions

---

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run E2E Tests
  run: |
    cd backend/scripts
    ./test_all_domains_e2e.sh http://localhost:8080 ci_user_${{ github.run_id }}
```

### Exit Codes
- `0` - All tests passed
- `1` - Test failure or error

---

## Development Workflow

1. **During feature development:**
   ```bash
   # Test specific domain
   ./test_nutritional_profile_persistence.sh
   ```

2. **Before committing:**
   ```bash
   # Full E2E validation
   ./test_all_domains_e2e.sh
   ```

3. **For data preparation:**
   ```bash
   # Create demo data
   ./test_all_domains_e2e.sh "" demo_user
   ```

4. **For load testing:**
   ```bash
   # Multiple users in parallel
   for i in {1..10}; do
       ./test_all_domains_e2e.sh "" "load_test_$i" &
   done
   wait
   ```

---

## Notes

- **Random User IDs**: By default, scripts generate unique user IDs with timestamps to ensure clean state
- **Same User**: Specify same USER_ID across scripts to test cross-domain integration
- **Idempotency**: Running scripts multiple times with same user will update existing data
- **Real APIs**: Scripts make real API calls - avoid running against production!

---

## Contributing

When adding new test scenarios:
1. Follow existing script structure
2. Add colored output for clarity
3. Include validation checks
4. Document expected results
5. Update this README

---

## Support

For issues or questions:
1. Check script output for specific error messages
2. Verify server is running and accessible
3. Ensure all dependencies (jq, bc, curl) are installed
4. Check GraphQL endpoint is correct

---

**Last Updated:** 2025-10-31  
**Version:** 1.0.0
