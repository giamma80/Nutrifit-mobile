# Nutrifit Nutritional Profile MCP Server

Model Context Protocol server for the Nutrifit Nutritional Profile domain.

## Features

### 👤 **Profile Management**
- `get_nutritional_profile` - Get complete profile with BMR/TDEE/targets
- `create_nutritional_profile` - Initial profile setup with auto-calculations
- `update_nutritional_profile` - Update weight, goals, activity level

### 📈 **Progress Tracking**
- `get_progress_score` - Analyze progress over date range
- `record_progress` - Log daily weight + calories + macros

## Installation

```bash
cd MCP/nutritional-profile-mcp
pip install -e .
```

## Configuration

Set GraphQL endpoint (defaults to `http://localhost:8080/graphql`):

```bash
export GRAPHQL_ENDPOINT=https://your-backend.com/graphql
```

## Usage with Claude Desktop

Add to config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "nutrifit-profile": {
      "command": "python",
      "args": ["/path/to/Nutrifit-mobile/MCP/nutritional-profile-mcp/server.py"]
    }
  }
}
```

## Example Workflows

### Profile setup
```
User: "Set up my nutritional profile: 30yo male, 180cm, 85kg, moderately active, want to lose weight to 75kg"
Claude uses: create_nutritional_profile
→ BMR calculated: 1,830 kcal/day
→ TDEE: 2,836 kcal/day (BMR * 1.55)
→ Daily target: 2,336 kcal (TDEE - 500 for weight loss)
Claude: "Profile created! Your daily calorie target is 2,336 kcal..."
```

### Weight check-in
```
User: "I weighed myself today: 83.5kg"
Claude uses: update_nutritional_profile (currentWeight: 83.5)
→ BMR/TDEE recalculated
Claude: "Great progress! Down 1.5kg. Updated your targets..."
```

### Progress review
```
User: "How's my progress this month?"
Claude uses: get_progress_score (startDate: 2024-01-01, endDate: 2024-01-31)
→ Returns weight change, avg calories, adherence rate
Claude: "This month: -2.1kg, 85% adherence rate, avg deficit -450 kcal/day..."
```

### Daily progress log
```
User: "Log today's progress: 83.5kg, ate 2,200 kcal, burned 450 kcal"
Claude uses: record_progress
→ Calculates deficit: -450 kcal
Claude: "Progress logged! You're 136 kcal under your target today."
```

## Key Calculations

### BMR (Mifflin-St Jeor)
- **Men**: 10 × weight(kg) + 6.25 × height(cm) - 5 × age + 5
- **Women**: 10 × weight(kg) + 6.25 × height(cm) - 5 × age - 161

### TDEE (Total Daily Energy Expenditure)
- **Sedentary**: BMR × 1.2
- **Lightly Active**: BMR × 1.375
- **Moderately Active**: BMR × 1.55
- **Very Active**: BMR × 1.725
- **Extra Active**: BMR × 1.9

### Daily Calorie Target
- **CUT** (weight loss): TDEE - 500 kcal
- **MAINTAIN**: TDEE
- **BULK** (muscle gain): TDEE + 300 kcal

### Default Macro Split
- **Protein**: 30% (balanced)
- **Carbs**: 40%
- **Fat**: 30%

## Data Models

### Gender
- `MALE`, `FEMALE`, `OTHER`

### Activity Level
- `SEDENTARY` - Little/no exercise
- `LIGHTLY_ACTIVE` - Exercise 1-3 days/week
- `MODERATELY_ACTIVE` - Exercise 3-5 days/week
- `VERY_ACTIVE` - Exercise 6-7 days/week
- `EXTRA_ACTIVE` - Athlete, physical job + exercise

### Goal Type
- `CUT` - Weight loss (calorie deficit)
- `MAINTAIN` - Weight maintenance (TDEE)
- `BULK` - Muscle gain (calorie surplus)

## Cross-Domain Integration

The Nutritional Profile domain integrates with:

1. **Meal Domain**: Provides `caloriesConsumed` for progress tracking
2. **Activity Domain**: Provides `caloriesBurned` for TDEE validation

Typical flow:
```
1. User logs meals → total calories consumed
2. User syncs activity → total calories burned
3. recordProgress ties them together → daily deficit/surplus calculated
4. progressScore analyzes trends → adherence rate, weight change
```

## API Reference

See `/backend/REFACTOR/graphql-api-reference.md` for complete GraphQL documentation.

## License

See root LICENSE file.
