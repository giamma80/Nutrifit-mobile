# Nutrifit Activity MCP Server

Model Context Protocol server for the Nutrifit Activity & Health domain.

## Features

### 📊 **Activity Queries**
- `get_activity_entries` - Granular activity events (steps, calories, heart rate)
- `get_activity_sync_entries` - Delta sync (created/updated/deleted since last sync)
- `aggregate_activity_range` - Aggregated data with DAY/WEEK/MONTH grouping

### 🔄 **Data Synchronization**
- `sync_activity_events` - Batch sync granular events from HealthKit/GoogleFit
- `sync_health_totals` - Sync daily cumulative totals

## Installation

```bash
cd MCP/activity-mcp
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
    "nutrifit-activity": {
      "command": "python",
      "args": ["/path/to/Nutrifit-mobile/MCP/activity-mcp/server.py"]
    }
  }
}
```

## Example Workflows

### Daily activity check
```
User: "How many steps did I walk today?"
Claude uses: get_activity_entries (startDate: today, type: STEPS)
→ Returns granular step events
Claude: "You've walked 8,432 steps so far today..."
```

### Weekly report
```
User: "Show me my activity this week"
Claude uses: aggregate_activity_range (groupBy: DAY, last 7 days)
→ Returns daily totals
Claude: "This week: 67,234 steps total, 2,450 calories burned..."
```

### Sync from device
```
User: "Sync my health data from today"
Claude uses: sync_activity_events
→ Batch import from HealthKit/GoogleFit
Claude: "Synced 142 activity events successfully"
```

## Data Models

### Activity Event Types
- `STEPS` - Step count
- `CALORIES` - Calories burned
- `DISTANCE` - Distance traveled (km)
- `HEART_RATE` - Heart rate (bpm)
- `SLEEP` - Sleep duration (minutes)

### Data Sources
- `HEALTHKIT` - iOS Health app
- `GOOGLEFIT` - Google Fit
- `MANUAL` - User-entered data

### Aggregation Periods
- `DAY` - Daily totals
- `WEEK` - Weekly summaries
- `MONTH` - Monthly aggregates

## Architecture

```
┌─────────────────┐
│  HealthKit/     │
│  GoogleFit      │
└────────┬────────┘
         │
┌────────▼────────┐
│  Activity MCP   │
│    Server       │
└────────┬────────┘
         │ GraphQL
         │
┌────────▼────────┐
│   Nutrifit      │
│   Backend       │
└─────────────────┘
```

## API Reference

See `/backend/REFACTOR/graphql-api-reference.md` for complete GraphQL documentation.

## License

See root LICENSE file.
