# Nutrifit MCP Servers

Model Context Protocol servers for the Nutrifit GraphQL API.

This directory contains 4 MCP servers, each exposing a distinct domain of the Nutrifit backend as AI-accessible tools.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│            AI Assistants (Claude, GPT, etc.)                │
└────────────────────┬─────────────────────────────────────────┘
                     │ MCP Protocol (stdio)
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                       MCP Servers                            │
│  ┌───────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ User  │  │   Meal   │  │ Activity │  │  Nutritional  │  │
│  │  MCP  │  │   MCP    │  │   MCP    │  │  Profile MCP  │  │
│  └───┬───┘  └─────┬────┘  └─────┬────┘  └───────┬───────┘  │
└──────┼────────────┼─────────────┼────────────────┼──────────┘
       │            │             │                │
       │ GraphQL    │ GraphQL     │ GraphQL        │ GraphQL
       │            │             │                │
┌──────▼────────────▼─────────────▼────────────────▼──────────┐
│               Nutrifit GraphQL Backend                       │
│  ┌──────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ User │  │   Meal   │  │ Activity │  │  Nutritional  │  │
│  │Domain│  │  Domain  │  │  Domain  │  │Profile Domain │  │
│  └──────┘  └──────────┘  └──────────┘  └───────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## 📦 Servers

### 1. User MCP (`user-mcp/`)

**6 tools** for user authentication and profile management.

**Capabilities:**

- 🔐 Authentication (JWT token validation, user creation)
- 👤 User management (profile retrieval, preferences update)
- 🔍 User lookup (by ID, email, Auth0 sub)

**Tool Parameter Convention:**
All MCP tools use **snake_case** for input parameters, which are automatically converted to **camelCase** for GraphQL variables.

**Example:**

```python
# MCP Tool Call (snake_case)
get_user_by_id(user_id="550e8400-e29b-41d4-a716-446655440000")

# GraphQL Variable (camelCase)
{"userId": "550e8400-e29b-41d4-a716-446655440000"}
```

This convention applies to all 4 MCP servers for consistency.

**Usage Example:**

```
User: "Get my profile"
→ get_current_user()
→ Returns: {id, email, name, preferences}
```

### 2. Meal MCP (`meal-mcp/`)

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

### 3. Activity MCP (`activity-mcp/`)

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

### 4. Nutritional Profile MCP (`nutritional-profile-mcp/`)

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

**Metodo Consigliato: FastMCP (Refactored)**

FastMCP offre un'implementazione più pulita e mantenibile con -60% di codice:

```bash
cd /Users/giamma/workspace/Nutrifit-mobile/MCP
uv venv
uv pip install fastmcp httpx pydantic
```

**Metodo Legacy: Vanilla MCP (server.py)**

Per retrocompatibilità, i server vanilla sono ancora disponibili:

```bash
cd /Users/giamma/workspace/Nutrifit-mobile/MCP
uv venv
uv pip install mcp httpx pydantic
```

### FastMCP vs Vanilla: Comparison

| Feature | Vanilla MCP (server.py) | FastMCP (server_fastmcp.py) |
|---------|-------------------------|------------------------------|
| **Code Lines** | 534-1166 lines per server | 265-315 lines (-60%) |
| **Boilerplate** | Manual Tool schemas, list_tools(), call_tool() | Auto-generated via decorators |
| **Type Safety** | Manual validation | Pydantic models |
| **Documentation** | Separate docstrings | Docstrings → tool descriptions |
| **Maintenance** | Higher complexity | Cleaner, easier to extend |
| **Performance** | Same runtime performance | Same runtime performance |

**Esempio Confronto (user-mcp):**

```python
# ❌ Vanilla MCP (534 lines)
class GraphQLClient:
    def __init__(self): ...
    async def execute(self, query, variables): ...
    async def close(self): ...

async def list_tools():
    return [Tool(name="get_current_user", inputSchema={...})]

async def call_tool(name, arguments):
    if name == "get_current_user":
        # 50+ lines of routing logic

# ✅ FastMCP (265 lines)
from fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP("Nutrifit User")

@mcp.tool()
async def get_current_user() -> dict:
    """Get authenticated user profile."""
    return await graphql_query(query)
```

**Vantaggi FastMCP:**

- ✅ **Type-safe:** Pydantic valida automaticamente gli input
- ✅ **Auto-schema:** Type hints → JSON schema automatico
- ✅ **DRY:** Elimina duplicazione tra docstrings e tool descriptions
- ✅ **Manutenibilità:** Codice più leggibile e facile da estendere
- ✅ **Testing:** Funzioni standalone più facili da testare

**Step 2:** Verifica l'installazione:

```bash
source .venv/bin/activate
python meal-mcp/server_fastmcp.py  # FastMCP
# oppure
python meal-mcp/server.py          # Vanilla
```

### Configuration

I server si connettono al backend GraphQL. L'endpoint di default è `http://localhost:8080/graphql`.

Per cambiare endpoint, imposta la variabile d'ambiente `GRAPHQL_ENDPOINT` nella config di Claude Desktop (vedi sotto).

### Claude Desktop Setup

#### Config FastMCP (Consigliata)

**Location:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "nutrifit-user": {
      "command": "/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python",
      "args": [
        "/Users/giamma/workspace/Nutrifit-mobile/MCP/user-mcp/server_fastmcp.py"
      ],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql"
      }
    },
    "nutrifit-meal": {
      "command": "/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python",
      "args": [
        "/Users/giamma/workspace/Nutrifit-mobile/MCP/meal-mcp/server_fastmcp.py"
      ],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql"
      }
    },
    "nutrifit-activity": {
      "command": "/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python",
      "args": [
        "/Users/giamma/workspace/Nutrifit-mobile/MCP/activity-mcp/server_fastmcp.py"
      ],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql"
      }
    },
    "nutrifit-profile": {
      "command": "/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python",
      "args": [
        "/Users/giamma/workspace/Nutrifit-mobile/MCP/nutritional-profile-mcp/server_fastmcp.py"
      ],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql"
      }
    }
  }
}
```

#### Config Vanilla MCP (Legacy)

Per usare i server vanilla `server.py`, cambia semplicemente i path:

```json
{
  "mcpServers": {
    "nutrifit-user": {
      "command": "/Users/giamma/workspace/Nutrifit-mobile/MCP/.venv/bin/python",
      "args": [
        "/Users/giamma/workspace/Nutrifit-mobile/MCP/user-mcp/server.py"
      ],
      "env": {
        "GRAPHQL_ENDPOINT": "http://localhost:8080/graphql"
      }
    }
  }
}
```

**Note Importanti:**

- ✅ **FastMCP:** Usa `server_fastmcp.py` per implementazione moderna (consigliata)
- 🔧 **Vanilla:** Usa `server.py` per implementazione legacy
- 📌 Usa path assoluti per Python e script
- 🔄 Riavvia Claude Desktop dopo modifiche alla config
- 🔌 Verifica con icona 🔌 in Claude Desktop UI

## 📚 Tool Description Best Practices

**NEW:** Tutti i tool FastMCP seguono le [MCP Tool Description Best Practices](./MCP_TOOL_DESCRIPTION_BEST_PRACTICES.md).

**Le 7 Regole per Descrizioni Efficaci:**

1. **🎨 Visual Anchors** - Emoji strategici per attention bias
2. **📋 Imperativi Chiari** - MUST/REQUIRED/BEFORE per disambiguare
3. **🔄 Workflow Sequenziali** - Step-by-step per tool complessi
4. **📊 Args Dettagliati** - Enum con pipe notation, formati, defaults
5. **📦 Return Specifici** - Shape esatta dei dati, no "object"
6. **💡 Esempi Concreti** - Codice reale con valori concreti
7. **⚠️ Edge Cases** - Errori, idempotency, performance

**Esempio descrizione ottimizzata:**

```python
@mcp.tool()
async def sync_activity_events(input: SyncActivityEventsInput) -> dict:
    """⬆️ Batch sync minute-level activity events (IDEMPOTENT).
    
    ⚠️ USE THIS for syncing data from HealthKit/GoogleFit.
    
    Idempotency guarantee:
    - Same idempotency_key → skips duplicate events
    - Safe to retry on network failure
    
    Workflow:
    1. Collect events from device
    2. Generate unique idempotency_key
    3. Call sync_activity_events
    4. If fails → retry with SAME key
    
    Args:
        input: Batch sync data
            - user_id: User UUID (required)
            - events: Array of ActivityEventInput (required)
                * timestamp: ISO 8601
                * steps, calories_out: Optional metrics
            - source: → "APPLE_HEALTH" | "GOOGLE_FIT" | "MANUAL"
            - idempotency_key: Unique deduplication key (required)
    
    Returns:
        SyncResult:
        - syncedCount: NEW events created
        - skippedCount: Duplicates skipped
    
    Example:
        result = await sync_activity_events(
            user_id="uuid",
            events=[{"timestamp": "2025-11-17T10:00:00Z", "steps": 150}],
            source="APPLE_HEALTH",
            idempotency_key="healthkit-sync-20251117-100000"
        )
    """
```

Consulta il [documento completo](./MCP_TOOL_DESCRIPTION_BEST_PRACTICES.md) per template, esempi comparativi e checklist di validazione.

## 💡 Usage Patterns

### FastMCP Tool Examples

**user-mcp** (6 tools):

```python
# Get authenticated user
await get_current_user()

# Create user with preferences
await authenticate_or_create(input=AuthenticateOrCreateInput(
    auth0_sub="auth0|123",
    email="user@example.com",
    name="John Doe"
))

# Update preferences
await update_preferences(input=UpdatePreferencesInput(
    language="it",
    theme="dark",
    notifications=True
))
```

**activity-mcp** (5 tools):

```python
# Query activities
await get_activity_entries(input=GetActivityEntriesInput(
    user_id="550e8400-...",
    start_date="2025-11-10",
    end_date="2025-11-17"
))

# Sync from HealthKit
await sync_activity_events(input=SyncActivityEventsInput(
    user_id="550e8400-...",
    events=[
        ActivityEventInput(timestamp="2025-11-17T10:00:00Z", steps=1500, calories_out=80),
        ActivityEventInput(timestamp="2025-11-17T11:00:00Z", steps=2100, calories_out=110)
    ],
    source="APPLE_HEALTH",
    idempotency_key="healthkit-sync-20251117"
))

# Aggregate weekly stats
await aggregate_activity_range(input=AggregateActivityRangeInput(
    user_id="550e8400-...",
    start_date="2025-11-10",
    end_date="2025-11-17",
    group_by="DAY"
))
```

**meal-mcp** (15 tools):

```python
# Analyze meal photo
await analyze_meal_photo(input=AnalyzeMealPhotoInput(
    user_id="550e8400-...",
    image_url="https://storage.example.com/meals/photo.jpg"
))

# Search by barcode
await search_food_by_barcode(barcode="8001505005707")

# Get daily summary
await get_daily_summary(user_id="550e8400-...", date="2025-11-17")
```

**nutritional-profile-mcp** (6 tools):

```python
# Create profile
await create_nutritional_profile(input=CreateNutritionalProfileInput(
    user_id="550e8400-...",
    current_weight=85.0,
    target_weight=75.0,
    height=175,
    age=30,
    gender="MALE",
    activity_level="MODERATELY_ACTIVE",
    goal_type="LOSE_WEIGHT"
))

# Record progress
await record_progress(input=RecordProgressInput(
    user_id="550e8400-...",
    date="2025-11-17",
    weight=83.5,
    calories_consumed=1850.0,
    consumed_protein=120.0
))

# Get adherence score
await get_progress_score(input=GetProgressScoreInput(
    user_id="550e8400-...",
    start_date="2025-10-01",
    end_date="2025-10-31"
))

# ML forecast
await forecast_weight(input=ForecastWeightInput(
    profile_id="profile-uuid",
    days_ahead=30,
    confidence_level=0.95
))
```

### Cross-Domain Workflows

The MCP servers integrate seamlessly to provide comprehensive nutrition tracking:

#### Daily Nutrition Tracking

```text
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
cd MCP/user-mcp && pytest
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
- **MCP Protocol:** <https://modelcontextprotocol.io/docs>
- **Repository Issues:** GitHub issue tracker

---

**Built with ❤️ for Nutrifit**
