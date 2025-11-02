# Nutrifit Meal MCP Server

Model Context Protocol server for the Nutrifit Meal Domain.

## Features

This MCP exposes comprehensive meal tracking and nutrition analysis capabilities:

### � **Image Upload**
- `upload_meal_image` - Upload image to Supabase Storage (returns URL for analyze_meal_photo)

### �🔍 **Food Discovery (Atomic Operations)**
- `search_food_by_barcode` - Lookup products by barcode (OpenFoodFacts)
- `recognize_food` - AI vision food recognition from photos/text
- `enrich_nutrients` - Get detailed nutrition from USDA database

### 🍽️ **Meal Analysis**
- `analyze_meal_photo` - End-to-end photo analysis (recognize + enrich + create meal)
- `analyze_meal_barcode` - Barcode-based meal creation
- `confirm_meal_analysis` - Confirm/reject detected food items

### 📊 **Meal Queries**
- `get_meal` - Get single meal details
- `get_meal_history` - Paginated meal history with filters
- `search_meals` - Full-text search across meals
- `get_daily_summary` - Daily nutrition totals
- `get_summary_range` - Weekly/monthly summaries with flexible grouping

### ✏️ **Meal Management**
- `update_meal` - Update meal type, timestamp, notes
- `delete_meal` - Delete meals

## Installation

```bash
cd MCP/meal-mcp
pip install -e .
```

## Configuration

The server connects to the Nutrifit GraphQL backend at `http://localhost:8080/graphql` by default.

To use a different endpoint, set the `GRAPHQL_ENDPOINT` environment variable:

```bash
export GRAPHQL_ENDPOINT=https://your-backend.com/graphql
```

## Usage with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "nutrifit-meal": {
      "command": "python",
      "args": ["/path/to/Nutrifit-mobile/MCP/meal-mcp/server.py"]
    }
  }
}
```

## Example Workflows

### Analyze a meal photo (with image upload)
```
User: "I just ate this meal [photo]"
Claude uses: upload_meal_image (with image data)
→ Returns: {"url": "https://...supabase.co/.../user123/20251102_abc_meal.jpg"}
Claude uses: analyze_meal_photo (with photo_url from upload)
→ Returns detected foods with nutrition
Claude: "I detected: chicken breast (150g, 250 kcal), rice (100g, 130 kcal)..."

User: "Confirm the chicken and rice"
Claude uses: confirm_meal_analysis
→ Meal saved permanently
```

### Daily nutrition check
```
User: "How many calories did I eat today?"
Claude uses: get_daily_summary
→ Returns total calories, macros, meal count
Claude: "Today you've had 1,850 kcal from 3 meals..."
```

### Weekly report
```
User: "Show me my nutrition for this week"
Claude uses: get_summary_range (groupBy: DAY)
→ Returns 7 days of data + totals
Claude: "This week: 12,450 kcal total, avg 1,779 kcal/day..."
```

## API Reference

See `/backend/REFACTOR/graphql-api-reference.md` for complete GraphQL API documentation.

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black server.py
ruff check server.py
```

## Architecture

```
┌─────────────────┐
│  Claude/AI      │
│   Assistant     │
└────────┬────────┘
         │ MCP Protocol
         │
┌────────▼────────┐
│   Meal MCP      │
│    Server       │
└────────┬────────┘
         │ GraphQL
         │
┌────────▼────────┐
│   Nutrifit      │
│   Backend       │
└─────────────────┘
```

The MCP server acts as a bridge between AI assistants and the Nutrifit GraphQL API,
translating high-level user intents into structured GraphQL queries and mutations.

## License

See root LICENSE file.
