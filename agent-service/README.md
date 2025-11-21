# Nutrifit Agent Service

AI-powered nutritional assistant service using **FastAPI**, **Strands Agents**, and **MCP** integration.

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│  Agent Service (FastAPI)            │
│  ├─ REST API endpoints              │
│  ├─ SSE streaming                   │
│  ├─ Auth0 JWT verification          │
│  └─ Redis caching (optional)        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Strands Agent Engine               │
│  ├─ Claude Sonnet 4 (via Bedrock)  │
│  ├─ Tool orchestration              │
│  └─ Conversation management         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  MCP Servers (4 subprocess)         │
│  ├─ user-mcp (6 tools)              │
│  ├─ meal-mcp (15 tools)             │
│  ├─ activity-mcp (5 tools)          │
│  └─ profile-mcp (6 tools)           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Nutrifit Backend (GraphQL/REST)    │
└─────────────────────────────────────┘
```

## 📋 Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Auth0 account with API configured
- AWS account (for Bedrock access)

## 🚀 Quick Start

### Local Development (without Docker)

```bash
# 1. Install dependencies
cd agent-service
pip install -e .

# 2. Copy environment file
cp .env.example .env

# 3. Configure environment variables
# Edit .env with your Auth0, AWS, and backend URLs

# 4. Run the service
python app.py
```

### Docker Compose (recommended)

```bash
# 1. From project root
docker-compose up -d agent-service

# 2. Check health
curl http://localhost:8000/health

# 3. View logs
docker-compose logs -f agent-service
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `AUTH0_DOMAIN` | Auth0 tenant domain | `your-tenant.eu.auth0.com` |
| `AUTH0_AUDIENCE` | API identifier | `https://api.nutrifit.app` |
| `GRAPHQL_ENDPOINT` | Backend GraphQL URL | `http://nutrifit-backend:8080/graphql` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379` |
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `STRANDS_MODEL` | Strands model ID | `anthropic.claude-sonnet-4-20250514-v1:0` |

See `.env.example` for complete list.

## 📡 API Endpoints

### Health Check

```bash
GET /health

Response:
{
  "status": "healthy",
  "timestamp": "2025-11-20T10:00:00Z",
  "version": "0.1.0",
  "mcp_clients": {
    "user": "ready",
    "meal": "ready",
    "activity": "ready",
    "profile": "ready"
  },
  "redis": "connected",
  "agent_stats": {
    "initialized": true,
    "active_agents": 2,
    "total_tools": 32
  }
}
```

### Chat (Non-Streaming)

```bash
POST /api/agent/chat
Authorization: Bearer <jwt_token>

Request:
{
  "message": "Analizza il mio ultimo pasto",
  "conversation_id": "optional-id"
}

Response:
{
  "response": "Ho trovato il tuo ultimo pasto...",
  "conversation_id": "abc123",
  "tool_calls": ["meal_get_meal_history"],
  "processing_time_ms": 1234
}
```

### Chat (Streaming with SSE)

```bash
GET /api/agent/stream-sse?message=Ciao
Authorization: Bearer <jwt_token>

Response (SSE stream):
data: Ciao! Come
data:  posso
data:  aiutarti
data:  oggi?
data: [DONE]
```

### Get Conversation History

```bash
GET /api/agent/history?conversation_id=abc123
Authorization: Bearer <jwt_token>

Response:
{
  "conversation_id": "abc123",
  "messages": [
    {"user": "Ciao", "assistant": "Ciao! Come posso aiutarti?"},
    {"user": "Analizza pasto", "assistant": "Ecco l'analisi..."}
  ]
}
```

### Delete Session

```bash
DELETE /api/agent/session
Authorization: Bearer <jwt_token>

Response:
{
  "message": "Session deleted for user auth0|123"
}
```

## 🔐 Authentication

All endpoints (except `/health`) require Auth0 JWT token:

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/agent/chat
```

Token must include:

- `sub`: User ID (Auth0 subject)
- `aud`: Correct audience
- `iss`: Auth0 issuer

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific test
pytest tests/test_auth.py -v
```

## 🐳 Docker Build

```bash
# Build image
docker build -t nutrifit-agent:latest -f agent-service/Dockerfile .

# Run container
docker run -p 8000:8000 \
  --env-file agent-service/.env \
  nutrifit-agent:latest
```

## 📊 Monitoring

### Logs

```bash
# Docker Compose logs
docker-compose logs -f agent-service

# Container logs
docker logs -f nutrifit-agent
```

### Metrics

- Health endpoint: `/health`
- Agent stats: Number of active agents, tool usage
- Redis status: Connection state, cache hit rate

## 🔧 Troubleshooting

### MCP Clients Not Initializing

```bash
# Check MCP servers are accessible
docker exec -it nutrifit-agent ls -la /app/MCP

# Test MCP server manually
docker exec -it nutrifit-agent python /app/MCP/user-mcp/server_fastmcp.py
```

### Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker exec -it nutrifit-redis redis-cli ping
```

### Auth0 Token Invalid

```bash
# Verify JWKS is accessible
curl https://<AUTH0_DOMAIN>/.well-known/jwks.json

# Check token claims
# Use jwt.io to decode token and verify aud, iss, exp
```

## 📚 Development

### Project Structure

```
agent-service/
├── app.py                 # Main FastAPI application
├── pyproject.toml         # Dependencies
├── Dockerfile             # Multi-stage build
├── .env.example           # Environment template
├── auth/
│   ├── __init__.py
│   └── middleware.py      # JWT verification
├── agents/
│   ├── __init__.py
│   └── nutrifit_agent.py  # Agent manager
└── tests/
    └── ...
```

### Adding New Endpoints

1. Add route in `app.py`
2. Use `get_current_user` dependency for auth
3. Get agent with `agent_manager.get_agent_for_user()`
4. Add tests in `tests/`

### Modifying Agent Behavior

Edit `agents/nutrifit_agent.py`:

- Instructions: Modify agent personality/goals
- Model: Change `STRANDS_MODEL` env var
- Tools: MCP servers auto-discovered

## 🚀 Deployment

See main project `DEPLOY.md` for Render deployment instructions.

Key points:

- Use Render Starter plan ($7/month) for production
- Configure environment variables in Render dashboard
- Enable health checks at `/health`
- Monitor logs via Render dashboard

## 📄 License

Part of Nutrifit project. See root LICENSE file.

## 🤝 Contributing

1. Create feature branch from `main`
2. Make changes in `agent-service/`
3. Add tests
4. Submit PR with description

---

**Status**: ✅ Ready for development
**Last Updated**: 2025-11-20
