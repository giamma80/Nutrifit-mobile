# 🚀 Deployment & Production Guide

**Data:** 23 Ottobre 2025  
**Versione:** 1.0  
**Status:** Production Ready Guide

---

## 📋 Table of Contents

1. [Deployment Strategy](#deployment-strategy)
2. [Environment Configuration](#environment-configuration)
3. [Feature Flags](#feature-flags)
4. [Blue-Green Deployment](#blue-green-deployment)
5. [MongoDB Migration](#mongodb-migration)
6. [Monitoring & Alerts](#monitoring--alerts)
7. [Rollback Procedures](#rollback-procedures)
8. [Performance Optimization](#performance-optimization)

---

## 🎯 Deployment Strategy

### Context: Pre-Launch Application

**Status**: Applicazione NON ancora lanciata, zero user base in produzione.

**Strategy**: Direct deployment senza rollout graduale. Nessun traffico da migrare, nessun downtime da gestire.

### Phase-by-Phase Deployment Plan

| Phase | Deployment | Production Impact | Rollback Risk |
|-------|------------|-------------------|---------------|
| **Phase 0-1** | None | Zero (local dev only) | N/A |
| **Phase 2** | None | Zero (domain layer, tests only) | N/A |
| **Phase 3** | Infrastructure | Zero (no users yet) | Low |
| **Phase 4** | Application | Zero (no users yet) | Low |
| **Phase 5** | GraphQL API | Zero (no users yet) | Low |
| **Phase 6** | Testing | Zero (QA validation) | N/A |
| **Phase 7** | MongoDB | Zero (empty database) | None |

---

## 🔐 Environment Configuration

### Required Environment Variables

```bash
# .env.production

# ===== Application =====
APP_ENV=production
APP_VERSION=2.0.0
LOG_LEVEL=INFO

# ===== Feature Flags =====
FEATURE_FLAG_NEW_MEAL_DOMAIN=false  # Start disabled
ROLLOUT_PERCENTAGE=0                # Gradual rollout 0-100

# ===== External APIs =====
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-vision-preview
OPENAI_MAX_RETRIES=3
OPENAI_TIMEOUT_SECONDS=30

USDA_API_KEY=...
USDA_BASE_URL=https://api.nal.usda.gov/fdc/v1

OPENFOODFACTS_BASE_URL=https://world.openfoodfacts.org/api/v2

# ===== Database =====
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/nutrifit?retryWrites=true&w=majority
MONGODB_DATABASE=nutrifit_production
MONGODB_MAX_POOL_SIZE=50
MONGODB_MIN_POOL_SIZE=10

# ===== Cache =====
REDIS_URL=redis://redis.example.com:6379/0
REDIS_MAX_CONNECTIONS=50
REDIS_SOCKET_TIMEOUT=5

# ===== Circuit Breaker =====
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# ===== Monitoring =====
SENTRY_DSN=https://...@sentry.io/...
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

GRAFANA_API_KEY=...
```

---

## 🚩 Feature Flags (Optional)

### Pre-Launch Context

**NON NECESSARI per il launch iniziale** (zero user base da proteggere).

Feature flags utili per:
- ✅ Testing in staging prima del deploy
- ✅ Kill switch di emergenza post-launch
- ❌ ~~Rollout graduale~~ (non applicabile pre-launch)

### Minimal Implementation

```python
# infrastructure/feature_flags.py

import os

class FeatureFlags:
    """Simple kill switch for emergency rollback."""
    
    @staticmethod
    def is_new_meal_domain_enabled() -> bool:
        """Global killswitch (default: enabled)."""
        return os.getenv("FEATURE_FLAG_NEW_MEAL_DOMAIN", "true").lower() == "true"
```

### Usage in Resolvers (Optional)

```python
# graphql/resolvers/meal/analyze_meal_photo.py

@strawberry.mutation
async def analyze_meal_photo(
    self,
    info: Info,
    photo_url: str,
    dish_hint: Optional[str] = None
) -> MealAnalysisResult:
    """Analyze meal photo."""
    
    # Direct implementation (no legacy code to fall back to)
    command = AnalyzeMealPhotoCommand(
        user_id=info.context.user_id,
        photo_url=photo_url,
        dish_hint=dish_hint
    )
    return await command_handler.execute(command)
```

---

## � Direct Deployment (Pre-Launch)

### Strategy Overview

**Context**: Applicazione pre-launch, zero user base esistente.

**Strategy**: Direct deployment del refactor completo in un'unica fase.

```
┌─────────────────────────────────────────────────────┐
│              Load Balancer (Render/AWS)             │
│                                                     │
│              Traffic: 100% Refactored Code          │
└──────────────────┬──────────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │  Production        │
         │  Refactored Code   │
         │  (Phases 0-7)      │
         └────────────────────┘
```

---

### One-Step Deployment Plan

#### **Day 1: Complete Deployment**

```bash
# 1. Run full test suite
cd backend
make test          # All 124 tests passing
make lint          # Zero errors
make typecheck     # Zero errors

# 2. Deploy to production
git checkout refactor
git push origin refactor

# Deploy via Render (automatic)
render deploy --branch refactor

# 3. Verify deployment
curl https://api.nutrifit.app/health  # Should return 200
curl https://api.nutrifit.app/graphql -d '{"query": "{ __schema { types { name } } }"}'
```

**Monitoring (First 24h)**:
- ✅ API health checks every 5 minutes
- ✅ Error rate < 1% (expected: 0% with no users)
- ✅ OpenAI API connectivity verified
- ✅ USDA API connectivity verified
- ✅ MongoDB connection stable

**Success Criteria**: All health checks pass, zero errors

---

### Pre-Deployment Checklist

```bash
# 1. Environment variables configured
✅ OPENAI_API_KEY set
✅ USDA_API_KEY set
✅ MONGODB_URL set
✅ REDIS_URL set (optional for launch)

# 2. External services verified
✅ OpenAI API key valid (test with curl)
✅ USDA API key valid (1000 req/hour limit confirmed)
✅ MongoDB cluster accessible
✅ Redis cluster accessible (if using)

# 3. Code quality verified
✅ All tests passing (124/124)
✅ 100% coverage on domain layer
✅ Zero lint errors
✅ Zero type errors
✅ GraphQL schema exported

# 4. Documentation complete
✅ README.md updated
✅ API documentation generated (SpectaQL)
✅ Environment variables documented
✅ Deployment guide reviewed
```

---

### Post-Deployment Validation

#### Smoke Tests (Run Immediately)

```bash
# Test 1: GraphQL introspection
curl -X POST https://api.nutrifit.app/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __schema { queryType { name } } }"}'

# Expected: {"data": {"__schema": {"queryType": {"name": "Query"}}}}

# Test 2: Health endpoint
curl https://api.nutrifit.app/health

# Expected: {"status": "healthy", "version": "2.0.0"}

# Test 3: Analyze meal photo (end-to-end)
curl -X POST https://api.nutrifit.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_USER_TOKEN" \
  -d '{
    "query": "mutation { analyzeMealPhoto(photoUrl: \"https://example.com/test.jpg\") { mealId status } }"
  }'

# Expected: {"data": {"analyzeMealPhoto": {"mealId": "...", "status": "ANALYZED"}}}
```

---

### Rollout Decision Matrix (Simplified)

| Metric | Threshold | Action if Failed |
|--------|-----------|------------------|
| Health checks | 100% pass | Investigate immediately |
| GraphQL schema | Valid introspection | Fix schema export |
| OpenAI connectivity | 200 response | Check API key |
| USDA connectivity | 200 response | Check API key |
| MongoDB connection | 200 response | Check connection string |

---

## 🗄️ MongoDB Setup (Phase 7)

### Pre-Launch Context

**Scenario**: Database vuoto, nessun dato esistente da migrare.

**Strategy**: Direct MongoDB implementation, nessuna migrazione necessaria.

```
┌─────────────────┐
│  Application    │
│                 │
│  Write ─────────┤
│                 │
│  Read ──────────┤
│                 │
│      MongoDB    │
│   (Empty DB)    │
└─────────────────┘
    Day 1
```

---

### Direct MongoDB Implementation

```python
# infrastructure/persistence/mongodb_repository.py

class MongoMealRepository:
    """Direct MongoDB implementation (no InMemory fallback)."""
    
    def __init__(self, mongo_client: AsyncIOMotorClient):
        self._db = mongo_client[os.getenv("MONGODB_DATABASE")]
        self._meals = self._db["meals"]
    
    async def save(self, meal: Meal) -> None:
        """Save meal to MongoDB."""
        await self._meals.update_one(
            {"_id": meal.id},
            {"$set": meal.to_dict()},
            upsert=True
        )
    
    async def get_by_id(self, meal_id: str) -> Optional[Meal]:
        """Get meal from MongoDB."""
        doc = await self._meals.find_one({"_id": meal_id})
        return Meal.from_dict(doc) if doc else None
```

**Configuration**:
```bash
MEAL_REPOSITORY_MODE=mongodb  # Direct MongoDB (default)
```

---

### Database Initialization

```python
# scripts/init_mongodb.py

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def init_mongodb():
    """Initialize MongoDB indexes and collections."""
    
    client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
    db = client[os.getenv("MONGODB_DATABASE")]
    meals = db["meals"]
    
    # Create indexes
    await meals.create_index([
        ("user_id", 1),
        ("timestamp", -1)
    ], name="user_meals_by_date")
    
    await meals.create_index([
        ("user_id", 1),
        ("status", 1),
        ("timestamp", -1)
    ], name="user_meals_by_status")
    
    print("✅ MongoDB initialized successfully")
    client.close()

if __name__ == "__main__":
    asyncio.run(init_mongodb())
```

**Run initialization**:
```bash
# Run once after deployment
uv run python scripts/init_mongodb.py
```

---

### Dependency Injection

```python
# infrastructure/di.py

def get_meal_repository() -> IMealRepository:
    """Get meal repository (MongoDB only)."""
    mongo_client = get_mongo_client()
    return MongoMealRepository(mongo_client)
```

**No dual-write needed** (nessun dato esistente da preservare)

---

## 📊 Monitoring & Alerts

### Key Metrics Dashboard

#### 1. API Performance Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **analyzeMealPhoto** latency (p99) | <5s | >10s |
| **confirmMealAnalysis** latency (p99) | <1s | >3s |
| **dailySummary** latency (p99) | <500ms | >2s |
| GraphQL error rate | <1% | >3% |

#### 2. External API Health

| Service | Target Success Rate | Alert Threshold |
|---------|---------------------|-----------------|
| OpenAI Vision | >98% | <95% |
| USDA FoodData | >95% | <90% |
| OpenFoodFacts | >90% | <85% |

#### 3. Cache Performance

| Cache Type | Target Hit Rate | Alert Threshold |
|------------|----------------|-----------------|
| OpenAI prompt cache | >50% | <30% |
| USDA search results | >70% | <50% |
| Daily summary | >80% | <60% |

#### 4. Circuit Breaker Status

| Service | Status | Action |
|---------|--------|--------|
| OpenAI | CLOSED (green) | Normal operation |
| OpenAI | HALF_OPEN (yellow) | Testing recovery |
| OpenAI | OPEN (red) | **ALERT** Service down |

---

### Grafana Dashboard Configuration

```yaml
# grafana/meal-domain-dashboard.json

{
  "dashboard": {
    "title": "Meal Domain Refactor - Production Metrics",
    "panels": [
      {
        "title": "Meal Analysis Success Rate",
        "targets": [
          {
            "expr": "sum(rate(meal_analysis_success[5m])) / sum(rate(meal_analysis_total[5m]))"
          }
        ]
      },
      {
        "title": "External API Latency (p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, openai_request_duration_seconds)"
          },
          {
            "expr": "histogram_quantile(0.99, usda_request_duration_seconds)"
          }
        ]
      },
      {
        "title": "Circuit Breaker States",
        "targets": [
          {
            "expr": "circuit_breaker_state{service='openai'}"
          }
        ]
      }
    ]
  }
}
```

---

### Sentry Error Tracking

```python
# infrastructure/monitoring/sentry_setup.py

import sentry_sdk
from sentry_sdk.integrations.strawberry import StrawberryIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
    traces_sample_rate=0.1,  # 10% of transactions
    profiles_sample_rate=0.1,
    integrations=[
        StrawberryIntegration(),
    ],
    before_send=filter_sensitive_data,
)

def filter_sensitive_data(event, hint):
    """Remove sensitive data before sending to Sentry."""
    # Remove API keys, user data, etc.
    if "request" in event:
        if "headers" in event["request"]:
            event["request"]["headers"].pop("Authorization", None)
    return event
```

**Usage in code**:
```python
try:
    result = await handler.execute(command)
except Exception as e:
    sentry_sdk.capture_exception(e, extra={
        "user_id": command.user_id,
        "meal_id": command.meal_id,
        "operation": "analyzeMealPhoto"
    })
    raise
```

---

### Alert Rules (PagerDuty/Slack)

#### Critical Alerts (Immediate Response)

1. **OpenAI Circuit Breaker Open**
   - Condition: `circuit_breaker_state{service="openai"} == 2` (OPEN)
   - Action: Page on-call engineer
   - Escalation: 5 minutes

2. **Error Rate Spike**
   - Condition: Error rate > 5% for 5 minutes
   - Action: Slack #backend-alerts + page on-call
   - Escalation: 10 minutes

3. **MongoDB Connection Lost**
   - Condition: `mongodb_connections == 0`
   - Action: Page database team + backend on-call
   - Escalation: Immediate

#### Warning Alerts (Review During Business Hours)

1. **High OpenAI Cost**
   - Condition: Spend > $100/hour
   - Action: Slack #backend-alerts
   - Review: Next business day

2. **Low Cache Hit Rate**
   - Condition: Cache hit rate < 30%
   - Action: Slack #backend-alerts
   - Review: Optimize caching strategy

3. **Slow Query Performance**
   - Condition: p99 latency > 8s (but < 10s alert threshold)
   - Action: Log for review
   - Review: Weekly performance meeting

---

## 🔄 Rollback Procedures (Pre-Launch)

### Context

**Scenario**: Pre-launch deployment, zero user data at risk.

**Strategy**: Simple rollback via git revert, nessun traffico da gestire.

---

### Immediate Rollback (< 5 minutes)

#### Git Revert (Only Option Needed)

```bash
# 1. Find the refactor deployment commit
git log --oneline --grep="deploy" -n 5

# 2. Revert to previous working commit
git revert <refactor_commit_sha>

# 3. Push to trigger redeploy
git push origin refactor

# 4. Render auto-deploys reverted code
# Wait ~3 minutes for deployment

# 5. Verify rollback
curl https://api.nutrifit.app/health
```

**Result**: Complete rollback in ~5 minutes, zero data loss (empty database).

---

### Rollback Decision Criteria

| Issue | Severity | Action |
|-------|----------|--------|
| Health checks fail | **CRITICAL** | Rollback immediately |
| OpenAI API errors | **HIGH** | Fix API key → redeploy |
| USDA API errors | **HIGH** | Fix API key → redeploy |
| MongoDB connection fail | **CRITICAL** | Fix connection string → redeploy |
| GraphQL schema invalid | **HIGH** | Fix schema export → redeploy |
| Performance issues | **LOW** | Monitor, optimize next sprint |

---

### Post-Rollback Actions

```bash
# 1. Identify root cause
git log --oneline refactor

# 2. Fix locally
git checkout refactor
# Apply fixes...

# 3. Re-run tests
make test
make lint

# 4. Redeploy when ready
git push origin refactor
```

**No data migration rollback needed** (database starts empty)

---

## ⚡ Performance Optimization

### 1. OpenAI Prompt Caching

**Goal**: >50% cache hit rate after warmup

**Strategy**:
- System prompt must be >1024 tokens (automatic caching)
- Stable prompt across requests (no dynamic content in system)
- User messages vary (photo URL, hints)

**Verification**:
```python
# Log cache hits from OpenAI response headers
cache_hit = response.headers.get("X-Cache-Status") == "HIT"
logger.info(f"OpenAI cache hit: {cache_hit}")
```

---

### 2. USDA Search Result Caching

```python
# Redis cache configuration
REDIS_TTL_USDA_SEARCH = 86400  # 24 hours

async def get_usda_foods(self, label: str) -> list:
    cache_key = f"usda:search:{label}"
    
    # Try cache first
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Call API
    results = await self._fetch_from_api(label)
    
    # Cache for 24h
    await redis.setex(cache_key, REDIS_TTL_USDA_SEARCH, json.dumps(results))
    
    return results
```

---

### 3. Daily Summary Pre-computation

```python
# Background job: Compute daily summaries at midnight
@celery.task
async def precompute_daily_summaries():
    """Pre-compute yesterday's summaries for all users."""
    yesterday = date.today() - timedelta(days=1)
    
    active_users = await user_repo.get_active_users()
    
    for user_id in active_users:
        summary = await compute_daily_summary(user_id, yesterday)
        
        # Cache for 24h
        cache_key = f"summary:daily:{user_id}:{yesterday}"
        await redis.setex(cache_key, 86400, summary.json())
```

---

### 4. Database Indexing

```python
# MongoDB indexes for meal queries

# Index 1: User meals by timestamp (most common query)
db.meals.create_index([
    ("user_id", 1),
    ("timestamp", -1)
])

# Index 2: Text search on dish names
db.meals.create_index([
    ("dish_name", "text"),
    ("entries.name", "text")
])

# Index 3: Daily summary aggregation
db.meals.create_index([
    ("user_id", 1),
    ("timestamp", -1),
    ("status", 1)
])
```

---

## 📝 Deployment Checklist (Pre-Launch)

### Pre-Deployment (Day -1)

- [ ] All tests passing (`make test` → 124/124 ✅)
- [ ] Lint checks pass (`make lint` → 0 errors ✅)
- [ ] Type checks pass (`make typecheck` → 0 errors ✅)
- [ ] Code review approved (merge to `refactor` branch)
- [ ] Documentation updated (README, REFACTOR/*.md)
- [ ] Environment variables configured in Render dashboard
- [ ] External API keys validated (OpenAI, USDA, MongoDB)
- [ ] GraphQL schema exported (`make export-schema`)

### Deployment (Day 0)

- [ ] Deploy to production (`git push origin refactor`)
- [ ] Wait for Render build completion (~3-5 min)
- [ ] Run smoke tests (see below)
- [ ] Verify health checks pass
- [ ] Initialize MongoDB indexes (`python scripts/init_mongodb.py`)
- [ ] Test end-to-end meal analysis flow

### Post-Deployment (Day 0-1)

- [ ] Monitor health checks every 5 minutes (first hour)
- [ ] Verify OpenAI API connectivity (test with sample photo)
- [ ] Verify USDA API connectivity (test search query)
- [ ] Check application logs for errors (zero expected)
- [ ] Validate GraphQL introspection works
- [ ] Update documentation with production URLs

### Rollback Criteria (Simplified)

- [ ] Health checks fail (> 1 failure)
- [ ] OpenAI API unreachable
- [ ] USDA API unreachable
- [ ] MongoDB connection fails
- [ ] GraphQL schema invalid

---

**Last Updated**: 23 Ottobre 2025  
**Maintainer**: Development Team  
**Status**: ✅ Ready for Production
