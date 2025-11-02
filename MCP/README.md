# Nutrifit MCP Servers

Model Context Protocol servers for the Nutrifit GraphQL API.

This directory contains 3 MCP servers, each exposing a distinct domain of the Nutrifit backend as AI-accessible tools.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│         AI Assistants (Claude, GPT, etc.)          │
└──────────────┬──────────────────────────────────────┘
               │ MCP Protocol (stdio)
               │
┌──────────────▼──────────────────────────────────────┐
│                  MCP Servers                        │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │  Meal    │  │ Activity │  │    Nutritional  │  │
│  │   MCP    │  │   MCP    │  │   Profile MCP   │  │
│  └─────┬────┘  └─────┬────┘  └────────┬────────┘  │
└────────┼─────────────┼────────────────┼────────────┘
         │             │                │
         │ GraphQL     │ GraphQL        │ GraphQL
         │             │                │
┌────────▼─────────────▼────────────────▼────────────┐
│             Nutrifit GraphQL Backend               │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │   Meal   │  │ Activity │  │   Nutritional   │  │
│  │  Domain  │  │  Domain  │  │ Profile Domain  │  │
│  └──────────┘  └──────────┘  └─────────────────┘  │
└────────────────────────────────────────────────────┘
```

## 📦 Servers

### 1. Meal MCP (`meal-mcp/`)
**14 tools** for comprehensive meal tracking and nutrition analysis.

**Capabilities:**
- 🔍 Food discovery (barcode lookup, AI recognition, USDA enrichment)
- 🍽️ Meal analysis (photo/barcode → nutrition data)
- 📊 Query meals (history, search, daily/range summaries)
- ✏️ Meal management (update, delete)

**Example:**
```
User: "Analyze this meal photo"
→ analyze_meal_photo
→ Returns: chicken breast (250 kcal), rice (130 kcal), broccoli (55 kcal)
```

### 2. Activity MCP (`activity-mcp/`)
**5 tools** for activity tracking and health data synchronization.

**Capabilities:**
- 📊 Query activity (granular events, aggregated summaries)
- 🔄 Sync from devices (HealthKit/GoogleFit batch import)
- 📈 Trend analysis (daily/weekly/monthly grouping)

**Example:**
```
User: "How many steps did I walk this week?"
→ aggregate_activity_range (groupBy: DAY)
→ Returns: 67,234 steps total, 2,450 calories burned
```

### 3. Nutritional Profile MCP (`nutritional-profile-mcp/`)
**5 tools** for profile management and progress tracking.

**Capabilities:**
- 👤 Profile CRUD (create, read, update with BMR/TDEE calculations)
- 📈 Progress tracking (daily weight + calories + macros)
- 📊 Progress analysis (adherence rate, weight trends)

**Example:**
```
User: "How's my progress this month?"
→ get_progress_score (last 30 days)
→ Returns: -2.1kg, 85% adherence, avg -450 kcal deficit
```

## 🚀 Quick Start

### Installation

**Step 1:** Crea un virtual environment condiviso e installa le dipendenze:

```bash
cd /Users/giamma/workspace/Nutrifit-mobile/MCP
uv venv
uv pip install mcp httpx pydantic
```

Questo crea un `.venv/` nella cartella MCP con tutte le dipendenze necessarie per i 3 server.

**Step 2:** Verifica l'installazione:

```bash
source .venv/bin/activate
python meal-mcp/server.py --help  # Dovrebbe avviarsi senza errori
```

### Configuration

I server si connettono al backend GraphQL. L'endpoint di default è `http://localhost:8080/graphql`.

Per cambiare endpoint, imposta la variabile d'ambiente `GRAPHQL_ENDPOINT` nella config di Claude Desktop (vedi sotto).

### Claude Desktop Setup

Aggiungi i 3 server alla config di Claude Desktop:

**Location:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nutrifit-meal": {
      "command": "/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python",
      "args": [
        "/Users/giamma/workspace/Nutrifit-mobile/MCP/meal-mcp/server.py"
      ],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql"
      }
    },
    "nutrifit-activity": {
      "command": "/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python",
      "args": [
        "/Users/giamma/workspace/Nutrifit-mobile/MCP/activity-mcp/server.py"
      ],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql"
      }
    },
    "nutrifit-profile": {
      "command": "/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python",
      "args": [
        "/Users/giamma/workspace/Nutrifit-mobile/MCP/nutritional-profile-mcp/server.py"
      ],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql"
      }
    }
  }
}
```

**Importante:** 
- Usa il path assoluto al Python del venv: `/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python`
- Usa path assoluti agli script server.py
- Dopo aver aggiornato la config, riavvia Claude Desktop completamente

## 💡 Usage Patterns

### Cross-Domain Workflows

The MCP servers integrate seamlessly to provide comprehensive nutrition tracking:

#### Daily Nutrition Tracking
```
1. User: "I just ate this meal [photo]"
   → Meal MCP: analyze_meal_photo
   → Returns: 850 kcal detected

2. User: "I walked 10,000 steps today"
   → Activity MCP: sync_activity_events
   → Returns: 450 kcal burned

3. User: "Log my progress: 83.5kg"
   → Profile MCP: record_progress
   → Calculates: -400 kcal deficit (850 - 450 - 800 target deficit)
```

#### Weekly Review
```
1. User: "Show my nutrition this week"
   → Meal MCP: get_summary_range (groupBy: DAY, 7 days)
   → Returns: Daily calorie breakdown

2. User: "And my activity?"
   → Activity MCP: aggregate_activity_range (groupBy: DAY, 7 days)
   → Returns: Daily steps/calories burned

3. User: "How am I doing on my goals?"
   → Profile MCP: get_progress_score (7 days)
   → Returns: Weight change, adherence rate, macro tracking
```

#### Goal Adjustment
```
1. User: "I want to increase my daily target by 200 kcal"
   → Profile MCP: update_nutritional_profile
   → Recalculates BMR/TDEE/targets

2. User: "Show today's remaining calories"
   → Meal MCP: get_daily_summary (today)
   → Activity MCP: aggregate_activity_range (today)
   → Returns: 1,500 kcal consumed, 400 burned, 300 remaining
```

## 🔧 Development

### Run Tests

```bash
# Test each server
cd MCP/meal-mcp && pytest
cd MCP/activity-mcp && pytest
cd MCP/nutritional-profile-mcp && pytest
```

### Format Code

```bash
black **/*.py
ruff check **/*.py
```

### Debugging

Enable MCP debug logging in Claude Desktop config:

```json
{
  "mcpServers": {
    "nutrifit-meal": {
      "command": "python",
      "args": ["-u", "/path/to/server.py"],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql",
        "MCP_DEBUG": "true"
      }
    }
  }
}
```

Check logs:
- **macOS:** `~/Library/Logs/Claude/mcp*.log`
- **Windows:** `%APPDATA%\Claude\logs\mcp*.log`

## 📚 API Reference

Each MCP server maps directly to the GraphQL API documented in:

**`/backend/REFACTOR/graphql-api-reference.md`**

This 2,500+ line document contains:
- Complete query/mutation signatures
- Input/output type definitions
- Workflow examples
- Best practices
- Cross-domain integration patterns

## 🏷️ Tool Naming Convention

MCP tools follow this naming pattern:

- **Queries:** `get_*` (e.g., `get_meal`, `get_nutritional_profile`)
- **Mutations:** Action verbs (e.g., `create_*`, `update_*`, `sync_*`, `record_*`)
- **Atomic operations:** Descriptive names (e.g., `search_food_by_barcode`, `recognize_food`)
- **Analysis:** `analyze_*` (e.g., `analyze_meal_photo`)

## 🔐 Security Considerations

1. **Authentication:** Currently, MCP servers use direct GraphQL access. For production:
   - Add JWT token authentication
   - Pass tokens via environment variables
   - Implement token refresh logic

2. **User Isolation:** All tools require `userId` parameter. Ensure:
   - User IDs are validated
   - Cross-user access is prevented
   - Rate limiting is applied

3. **Data Privacy:**
   - Health data is sensitive (GDPR, HIPAA considerations)
   - Implement audit logging for all mutations
   - Encrypt data at rest and in transit

## 📝 License

See root LICENSE file.

## 🤝 Contributing

When adding new tools:

1. **Update GraphQL schema first** (`backend/graphql/schema.graphql`)
2. **Document in API reference** (`backend/REFACTOR/graphql-api-reference.md`)
3. **Implement GraphQL resolver** (appropriate domain resolver file)
4. **Add MCP tool** (appropriate MCP server)
5. **Update README** (this file + specific server README)
6. **Add tests** (`pytest` test cases)

## 🐛 Troubleshooting

### Server not appearing in Claude Desktop

1. Check config file path: `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Validate JSON syntax (use `jq` or online validator)
3. Ensure absolute paths to server.py files
4. Restart Claude Desktop completely

### GraphQL connection errors

1. Verify backend is running: `curl http://localhost:8080/graphql`
2. Check `GRAPHQL_ENDPOINT` environment variable
3. Test with GraphQL playground: `http://localhost:8080/graphql`
4. Review backend logs for errors

### Tool calls failing

1. Check MCP logs (see Debugging section)
2. Verify GraphQL query syntax against schema
3. Test query directly in GraphQL playground
4. Ensure required parameters are provided

### Import errors

1. Verify MCP SDK installed: `pip install mcp`
2. Check Python version: `python --version` (requires 3.11+)
3. Reinstall dependencies: `pip install -e .`

## 📧 Support

For issues or questions:
- **GraphQL API:** See `/backend/REFACTOR/graphql-api-reference.md`
- **MCP Protocol:** https://modelcontextprotocol.io/docs
- **Repository Issues:** GitHub issue tracker

---

**Built with ❤️ for Nutrifit**
