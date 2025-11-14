# 📖 Nutrifit Backend - Complete Multi-Domain Documentation

**Version:** 3.1  
**Date:** 13 Novembre 2025  
**Status:** 🟢 Production Ready - 4 Domains Implemented + MongoDB 100% Validated

---

## 🎯 Overview

Questa documentazione descrive l'**architettura completa del backend Nutrifit** con **4 domini implementati**, seguendo i principi di **Clean Architecture**, **Domain-Driven Design (DDD)**, **CQRS**, e **Ports & Adapters** (Hexagonal Architecture).

### 🏗️ Implemented Domains

1. **🍽️ Meal Domain** - AI-powered food tracking (OpenAI Vision, USDA, OpenFoodFacts)
2. **🏃 Activity Domain** - Health data sync and calorie tracking
3. **📊 Nutritional Profile Domain** - BMR/TDEE calculation + **ML-powered forecasting**
4. **🎯 Cross-Domain Integration** - Energy balance and progress analytics

### ✨ ML Capabilities

- **Weight Forecasting**: 4 adaptive time series models (ARIMA, ExponentialSmoothing, LinearRegression, SimpleTrend)
- **Trend Analysis**: Direction (decreasing/increasing/stable) + magnitude detection
- **Adaptive TDEE**: Kalman Filter for metabolic adaptation tracking
- **Weekly Pipeline**: Automated TDEE recalculation via APScheduler

---

## 📚 Documentation Index

### Core Documentation

| # | Document | Description | Estimated Time |
|---|----------|-------------|----------------|
| **00** | [Architecture Overview](./00_ARCHITECTURE_OVERVIEW.md) | Vision, principles, project structure | 30 min read |
| **01** | [Implementation Guide](./01_IMPLEMENTATION_GUIDE.md) | 7-phase roadmap (~80-100h total) | 45 min read |
| **02** | [Domain Layer](./02_DOMAIN_LAYER.md) | Entities, value objects, services, ports | 60 min read |
| **03** | [Application Layer](./03_APPLICATION_LAYER.md) | CQRS commands/queries, orchestrators | 45 min read |
| **04** | [Infrastructure Layer](./04_INFRASTRUCTURE_LAYER.md) | OpenAI, USDA, OpenFoodFacts, repositories | 60 min read |
| **05** | [Testing Strategy](./05_TESTING_STRATEGY.md) | TDD, unit/integration/e2e tests | 45 min read |
| **06** | [GraphQL API](./06_GRAPHQL_API.md) | Complete schema, resolvers, SpectaQL | 60 min read |

### 🎯 Implementation Tracking

| Document | Description | Purpose |
|----------|-------------|---------|
| **[📋 IMPLEMENTATION TRACKER](./IMPLEMENTATION_TRACKER.md)** | **77 tasks (100% complete) - Phase 10 MongoDB Validated** | Track progress, manage issues, verify completion |
| **[🗄️ PERSISTENCE LAYER STATUS](../docs/REFACTOR/persistence-layer-status.md)** | **MongoDB Atlas integration - 12/12 tests passing** | Technical architecture and validation results |

**Key Features:**
- ✅ Detailed task breakdown by phase (P0-P10)
- ✅ Each task has: ID, description, reference doc, expected result, status
- ✅ Progress overview and completion tracking
- ✅ Critical path identification
- ✅ Status legend and commit conventions

**Phase 10 MongoDB Validation:**
- ✅ 12/12 integration tests passing on production MongoDB Atlas
- ✅ 4 repositories implemented (Activity, Meal, Profile, Generic)
- ✅ 1,471 production lines + 414 test lines
- ✅ Dual-collection architecture (events + snapshots)
- ✅ 9 indexes optimized for query patterns
- ✅ Execution time: 4.94s on Atlas free tier

**Total Reading Time:** ~5 hours  
**Total Implementation Time:** ~80-100 hours (2-3 weeks)

---

## 🚀 Quick Start

### For Developers Starting Implementation

> **📋 PRIMA DI INIZIARE**: Consulta [IMPLEMENTATION_TRACKER.md](./IMPLEMENTATION_TRACKER.md) per la lista completa di task e subtask. Ogni task ha un ID univoco, riferimenti alla documentazione, e criteri di completamento.

---

#### **Step 0: Upgrade Dependencies (CRITICAL - Do This First!)**

**OpenAI 1.45.0 → 2.5.0+ è BLOCKING per il refactor.**

```bash
# 1. Aggiorna pyproject.toml
cd backend
```

Modifica `pyproject.toml`:
```toml
# [project.dependencies]
# BEFORE:
openai = "1.45.0"
httpx = "0.28.1"

# AFTER:
openai = "^2.5.0"        # Structured outputs + prompt caching
httpx = "^0.28.1"        # Compatibile con OpenAI 2.5+
circuitbreaker = "^1.4.0"  # Circuit breaker pattern
tenacity = "^8.2.0"        # Retry logic
pydantic = "^2.0"          # Validazione (già richiesto da Strawberry)
```

**Perché OpenAI 2.5.0+ è necessario:**
- ✅ **Structured Outputs**: Validazione nativa Pydantic (no parsing JSON manuale)
- ✅ **Prompt Caching**: System prompt >1024 token → 50% costo ridotto
- ✅ **Reliability**: Schema enforcement lato server OpenAI
- ✅ **Type Safety**: Integrazione Pydantic diretta

```bash
# 2. Installa dipendenze
uv sync

# 3. Verifica versione OpenAI
uv run python -c "import openai; print(f'OpenAI: {openai.__version__}')"
# Expected: 2.5.0+

# 4. Verifica nuove dipendenze
uv run python -c "from circuitbreaker import circuit; from tenacity import retry; print('✅ OK')"

# 5. Commit
git add pyproject.toml uv.lock
git commit -m "build(deps): upgrade openai to 2.5.0+ for structured outputs"
```

---

#### **Step 1: Read Architecture Overview**

**Documento**: [00_ARCHITECTURE_OVERVIEW.md](./00_ARCHITECTURE_OVERVIEW.md)
- Understand vision and principles
- Review project structure
- Familiarize with technology stack

---

#### **Step 2: Follow Implementation Guide**

**Documento**: [01_IMPLEMENTATION_GUIDE.md](./01_IMPLEMENTATION_GUIDE.md)
- Start with **Phase 0: Cleanup Selettivo** (3-4h) - preserva client esterni
- Progress through 7 phases sequentially
- Check milestones after each phase

---

#### **Step 3: Reference Layer Docs as Needed**

- **Domain** ([02](./02_DOMAIN_LAYER.md)): When implementing entities, value objects, services
- **Application** ([03](./03_APPLICATION_LAYER.md)): When implementing commands, queries, orchestrators
- **Infrastructure** ([04](./04_INFRASTRUCTURE_LAYER.md)): When adapting USDA/OpenFoodFacts clients
- **Testing** ([05](./05_TESTING_STRATEGY.md)): Write tests alongside implementation (TDD)
- **GraphQL** ([06](./06_GRAPHQL_API.md)): When implementing resolvers

---

## ⚠️ CRITICAL: Legacy Code Management

### � **STRATEGIA: Cleanup Selettivo + Adattamento Client**

**Philosophy**: Preservare codice testato e funzionante, rimuovere solo architettura obsoleta.

---

### ✅ What to PRESERVE & ADAPT (Working Code)

#### ✅ External Service Clients (Da Adattare, NON Cancellare)

**Questi client sono risultato di sperimentazione funzionante:**

1. **USDA Client** (`backend/ai_models/usda_client.py`)
   - ✅ **Preservare**: Logica matching label → USDA foods
   - ✅ **Preservare**: Fallback categories
   - ✅ **Preservare**: Caching
   - 🔄 **Adattare**: Implementare port `INutritionProvider`
   - 🔄 **Aggiungere**: Circuit breaker + retry logic

2. **OpenFoodFacts Client** (`backend/openfoodfacts/adapter.py`)
   - ✅ **Preservare**: Logica barcode lookup
   - ✅ **Preservare**: Parsing response
   - ✅ **Preservare**: Image URL extraction
   - 🔄 **Adattare**: Implementare port `IBarcodeProvider`
   - 🔄 **Aggiungere**: Circuit breaker

3. **Prompts OpenAI** (`backend/ai_models/meal_photo_prompt.py`)
   - ✅ **Preservare**: System prompt esistente
   - ✅ **Preservare**: User prompt templates
   - 🔄 **Adattare**: Formato per OpenAI 2.5.0+ structured outputs

4. **Nutrient Enrichment** (`backend/ai_models/nutrient_enrichment.py`)
   - ✅ **Preservare**: Logica enrichment
   - 🔄 **Adattare**: Integrare con nuova architettura

**Approach**: **Adattamento**, non riscrittura. Spostare in `infrastructure/` e implementare ports.

---

### 🗑️ What to REMOVE (Old Architecture)

**Philosophy**: Rimuovere solo architettura obsoleta, non logica funzionante.

#### ❌ Remove Old Domain Code (Selective)
```bash
# Rimuovere SOLO architettura vecchia, NON client esterni
cd backend/domain/meal
rm -rf adapters/ application/ entities/ events/ model/ pipeline/ port/ ports/ service/ value_objects/
rm -f errors.py integration.py meal_photo_refactor.md
```

**What gets deleted:**
- ❌ Old entities (architettura precedente)
- ❌ Old value objects (design precedente)
- ❌ Old services (pattern precedente)
- ❌ Old ports/adapters (pattern precedente)
- ❌ **Old unit tests** (accoppiati a vecchia implementazione)

**What gets PRESERVED:**
- ✅ `backend/ai_models/` (USDA, prompts, enrichment)
- ✅ `backend/openfoodfacts/` (barcode lookup)

**Why remove old tests?**
- Old tests are coupled to old implementation
- Failing tests block development
- New TDD approach creates better tests
- Test coverage will be >90% with new tests

#### ❌ Remove Old Application Code
- ❌ Old use cases (replaced by CQRS commands/queries)
- ❌ Old orchestration logic (replaced by orchestrators)

#### ❌ Remove Old GraphQL Code
- ❌ `backend/graphql/meal_resolver.py` (obsolete)
- ❌ `backend/graphql/types_meal.py` (obsolete)

**Golden Rule**: Remove **architecture**, preserve **working logic**.

---

### ✅ What to KEEP (Critical Infrastructure)

#### ✅ GitHub Actions (`.github/workflows/`)
**Keep ALL workflow files:**
- CI/CD pipelines
- Test automation
- Deployment workflows
- Code quality checks

**Action Required:** Review and update if needed (e.g., add new test paths)

```yaml
# Example: Update test paths in CI
- name: Run tests
  run: |
    uv run pytest backend/tests/unit backend/tests/integration \
      --cov=backend \
      --cov-report=xml
```

---

#### ✅ Docker Configuration

**Keep and extend:**
- `backend/Dockerfile` ✅
- `docker-compose.yml` (if exists) ✅

**Extend Dockerfile for new structure:**
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy new structure
COPY backend/domain ./backend/domain
COPY backend/application ./backend/application
COPY backend/infrastructure ./backend/infrastructure
COPY backend/graphql ./backend/graphql

# Install dependencies
COPY pyproject.toml ./
RUN pip install -e .

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Add docker-compose.yml for local development:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - USDA_API_KEY=${USDA_API_KEY}
      - MONGODB_URL=${MONGODB_URL:-mongodb://mongo:27017}
      - REDIS_URL=${REDIS_URL:-redis://redis:6379}
    depends_on:
      - mongo
      - redis
    volumes:
      - ./backend:/app/backend  # Hot reload

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  mongo_data:
  redis_data:
```

**⚠️ ACTION REQUIRED (Phase 3, Step 3.6):**
- ✅ Creare `docker-compose.yml` nella root del progetto (template sopra)
- 🔄 Aggiornare `make.sh` con target Docker
- 🔄 Aggiornare `Makefile` per proxy ai target Docker

**Aggiornamenti necessari in make.sh:**
```bash
#!/bin/bash
# Aggiungi questi target:

docker-up() {
    echo "🐳 Starting Docker services..."
    docker-compose up -d
}

docker-down() {
    echo "🛑 Stopping Docker services..."
    docker-compose down
}

docker-logs() {
    echo "📋 Docker logs..."
    docker-compose logs -f backend
}

docker-restart() {
    echo "🔄 Restarting Docker services..."
    docker-compose restart backend
}
```

**Aggiornamenti necessari in Makefile:**
```makefile
# Aggiungi questi proxy:
docker-up:
	@$(SCRIPT) docker-up

docker-down:
	@$(SCRIPT) docker-down

docker-logs:
	@$(SCRIPT) docker-logs

docker-restart:
	@$(SCRIPT) docker-restart
```

**Usage dopo setup:**
```bash
# Start all services (MongoDB + Redis + Backend)
make docker-up

# View logs
make docker-logs

# Restart backend only
make docker-restart

# Stop all services
make docker-down
```

---

#### ✅ Render Configuration (`render.yaml`)

**Keep and verify:**
- Service definitions
- Environment variables
- Build commands
- Health checks

**Example verification:**
```yaml
# render.yaml
services:
  - type: web
    name: nutrifit-backend
    env: python
    buildCommand: pip install -e .
    startCommand: uvicorn backend.app:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
      - key: OPENAI_API_KEY
        sync: false  # Set in Render dashboard
      - key: USDA_API_KEY
        sync: false
      - key: MONGODB_URL
        sync: false
```

**Action Required:** Ensure `buildCommand` and `startCommand` work with new structure.

---

#### ✅ Makefile (ALL Targets)

**Keep entire Makefile and use it for ALL lifecycle operations.**

**Example Makefile targets:**
```makefile
# Makefile

.PHONY: help install test lint format typecheck quality run docs clean

help:
	@echo "Nutrifit Backend - Make Targets"
	@echo "================================"
	@echo "install       Install dependencies"
	@echo "test          Run all tests"
	@echo "test-unit     Run unit tests only"
	@echo "test-int      Run integration tests"
	@echo "test-e2e      Run E2E tests"
	@echo "lint          Run Ruff linter"
	@echo "format        Run Black formatter"
	@echo "typecheck     Run MyPy type checker"
	@echo "quality       Run all quality checks (lint + format + typecheck)"
	@echo "run           Run development server"
	@echo "docs          Generate GraphQL API docs (SpectaQL)"
	@echo "clean         Clean cache and temp files"

install:
	uv pip install -e ".[dev]"

test:
	uv run pytest backend/tests/ -v --cov=backend --cov-report=html --cov-report=term

test-unit:
	uv run pytest backend/tests/unit/ -v

test-int:
	uv run pytest backend/tests/integration/ -v -m integration

test-e2e:
	uv run pytest backend/tests/e2e/ -v -m e2e

lint:
	uv run ruff check backend/

format:
	uv run black backend/ --check

format-fix:
	uv run black backend/

typecheck:
	uv run mypy --strict backend/

quality: lint format typecheck
	@echo "✅ All quality checks passed"

run:
	uv run uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

docs:
	@echo "📚 Generating GraphQL API documentation..."
	@python backend/scripts/export_schema.py
	@npx spectaql spectaql.yaml
	@echo "✅ Documentation generated at: backend/docs/REFACTOR/NEW/api/index.html"

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov coverage.xml .coverage
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t nutrifit-backend:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env nutrifit-backend:latest

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

docker-compose-logs:
	docker-compose logs -f backend

log:
	tail -f backend/logs/*.log
```

**Usage in refactor:**
```bash
# Phase 0: Cleanup
make clean

# Phase 1-6: Development
make install
make test-unit        # Run after each implementation
make quality          # Before commit
make run              # Test manually

# Phase 7: Production ready
make test             # Full test suite
make quality          # All checks pass
make docs             # Generate API docs
make docker-build     # Build image
```

---

#### ✅ End-to-End Test Scripts

**New comprehensive test scripts** (added 27 Ottobre 2025):

**Meal Persistence Testing:**
```bash
# Test complete meal workflows (photo + barcode analysis)
cd backend
./scripts/test_meal_persistence.sh

# Custom configuration
./scripts/test_meal_persistence.sh http://localhost:8080 giamma
BASE_URL=http://staging.com USER_ID=test-staging ./scripts/test_meal_persistence.sh
```

**What it tests:**
- ✅ Photo analysis workflow (upload → analyze → confirm)
- ✅ Barcode analysis workflow (barcode → analyze → confirm)
- ✅ Search meals functionality
- ✅ Daily summary aggregation
- ✅ Cross-verification with activity data
- ✅ Image URL persistence (barcode products)

**Activity Persistence Testing:**
```bash
# Test activity workflows (440 events, realistic simulation)
cd backend
./scripts/test_activity_persistence.sh

# Custom configuration
./scripts/test_activity_persistence.sh http://localhost:8080 giamma
```

**What it tests:**
- ✅ 440 minute-by-minute activity events
- ✅ 10+ workout types (walks, gym cardio, strength training)
- ✅ syncHealthTotals (3 cumulative snapshots)
- ✅ Deduplication and idempotency
- ✅ Realistic daily simulation (~19,683 steps, ~1,168 kcal)

**Script Features:**
- Parametric BASE_URL and USER_ID (CLI args + env vars)
- Default fallback: `http://localhost:8080` + unique user per run
- Timeout handling on all HTTP calls (--max-time 10)
- Clean state verification for rieseguibilità
- Comprehensive output with validation

**Files:**
- `backend/scripts/test_meal_persistence.sh` (493 lines)
- `backend/scripts/test_activity_persistence.sh` (755 lines)
- Total: 1248 lines of comprehensive test logic

---

#### ✅ Configuration Files

**Keep:**
- ✅ `pyproject.toml` (update dependencies)
- ✅ `pytest.ini` (update test paths)
- ✅ `.gitignore`
- ✅ `.env.example`
- ✅ `README.md` (update for new structure)

**Update `pyproject.toml` dependencies:**
```toml
[project]
dependencies = [
    "fastapi>=0.104.0",
    "strawberry-graphql>=0.200.0",
    "openai>=2.5.0",          # ⚠️ Important version
    "pydantic>=2.0",
    "httpx>=0.25.0",
    "motor>=3.3.0",           # MongoDB async driver
    "redis>=5.0.0",
    "circuitbreaker>=1.4.0",  # New
    "tenacity>=8.2.0",        # New
    "structlog>=23.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.5.0",
    "ruff>=0.1.0",
    "black>=23.0.0",
]
```

**Update `pytest.ini` paths:**
```ini
[pytest]
testpaths = backend/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slow, real APIs)
    e2e: End-to-end tests (very slow, full workflows)
    slow: Slow tests (mark for skip in CI)
```

---

### 📋 Phase 0 Checklist: What to Keep/Remove

```bash
# Phase 0: Cleanup & Preparation

# 1. KEEP these files/folders
# ✅ .github/workflows/          (all GitHub Actions)
# ✅ backend/Dockerfile
# ✅ docker-compose.yml
# ✅ render.yaml
# ✅ Makefile
# ✅ pyproject.toml             (update dependencies)
# ✅ pytest.ini                 (update paths)
# ✅ .gitignore
# ✅ .env.example

# 2. REMOVE old meal domain code
rm -rf backend/domain/meal/entities/         # Old entities
rm -rf backend/domain/meal/value_objects/    # Old value objects
rm -rf backend/domain/meal/services/         # Old services
rm -rf backend/domain/meal/repositories/     # Old repositories

# 3. REMOVE old tests (if failing due to removed code)
# Evaluate each test file:
# - If test is for removed code → DELETE
# - If test is for kept code → KEEP and update
rm -rf backend/tests/test_old_meal_*.py     # Old meal tests

# 4. REMOVE old application code
rm -rf backend/application/meal/use_cases/   # Old use cases (replaced by CQRS)

# 5. REMOVE old GraphQL code (if incompatible)
rm -rf backend/graphql/resolvers/old_meal/   # Old resolvers

# 6. CREATE new structure (keep __init__.py files)
mkdir -p backend/domain/meal/{core,nutrition,recognition,barcode}
mkdir -p backend/application/meal/{commands,queries,orchestrators}
mkdir -p backend/infrastructure/{ai,external_apis,persistence}
mkdir -p backend/tests/{unit,integration,e2e}

# 7. VERIFY kept files still work
make install
make lint      # Should pass (even with empty structure)
make typecheck # Should pass

# 8. COMMIT clean slate
git add .
git commit -m "refactor(meal): Phase 0 - Clean slate with new structure

BREAKING CHANGE: Removed old meal domain code
- Removed old entities, services, repositories
- Removed incompatible tests
- Created new domain structure (core, nutrition, recognition, barcode)
- Created CQRS application structure (commands, queries, orchestrators)
- Kept: GitHub Actions, Docker, Render config, Makefile

Refs: backend/docs/REFACTOR/NEW/01_IMPLEMENTATION_GUIDE.md Phase 0"
```

---

### 🎯 Golden Rule

> **"When in doubt, DELETE old code. New architecture = new code."**

**Exceptions:**
- ✅ Infrastructure config (Docker, Render, GitHub Actions, Makefile)
- ✅ Tests for code that's NOT being refactored
- ✅ Shared utilities (if compatible)
- ✅ Environment configuration

**Everything else:** Fresh start with new architecture.

---

---

## 🏗️ Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│                   GraphQL Layer (06)                    │
│  Mutations: analyzeMealPhoto, confirmMealAnalysis, ... │
│  Queries: meal, mealHistory, dailySummary, ...         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Application Layer (03)                     │
│  • Commands (AnalyzeMealPhotoCommand, ...)              │
│  • Queries (GetMealQuery, ...)                          │
│  • Orchestrators (PhotoOrchestrator, ...)               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                Domain Layer (02)                        │
│  Core: Meal, MealEntry, MealFactory                     │
│  Capabilities: Nutrition, Recognition, Barcode          │
│  Ports: IVisionProvider, INutritionProvider, ...        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│             Infrastructure Layer (04)                   │
│  • OpenAI Vision Provider (v2.5.0)                      │
│  • USDA Nutrition Provider                              │
│  • OpenFoodFacts Barcode Provider                       │
│  • InMemoryMealRepository → MongoMealRepository         │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

### What This Refactor Delivers

#### 1. 📸 AI-Powered Photo Recognition
- **OpenAI Vision v2.5.0** with structured outputs
- **Prompt caching** (>1024 tokens) for cost optimization
- **USDA-compatible labels** for precise nutrient matching
- **Confidence scoring** for each recognized item

**GraphQL Operation:** `analyzeMealPhoto`  
**Implementation:** [04_INFRASTRUCTURE_LAYER.md § OpenAI Integration](./04_INFRASTRUCTURE_LAYER.md#openai-integration)

---

#### 2. 🏷️ Barcode Scanning
- **OpenFoodFacts API** integration
- **Image URL extraction** (product photo saved with meal)
- **USDA fallback** when nutrients unavailable
- **Circuit breaker** for resilience

**GraphQL Operation:** `analyzeMealBarcode`  
**Implementation:** [04_INFRASTRUCTURE_LAYER.md § OpenFoodFacts Integration](./04_INFRASTRUCTURE_LAYER.md#openfoodfacts-integration)

---

#### 3. 🥗 Nutrition Enrichment
- **USDA FoodData Central** integration
- **Smart label matching** (specific labels → precise results)
- **Cascade strategy** (USDA → Category → Fallback)
- **Per-100g scaling** to actual quantities

**GraphQL Operation:** `enrichNutrients` (utility)  
**Implementation:** [04_INFRASTRUCTURE_LAYER.md § USDA Integration](./04_INFRASTRUCTURE_LAYER.md#usda-integration)

---

#### 4. ✅ 2-Step Confirmation
- **Unconfirmed meals** after AI analysis
- **User review & selection** of recognized items
- **Confirmation flow** removes uncertainty
- **Domain events** for auditability

**GraphQL Operations:** `analyzeMealPhoto` → `confirmMealAnalysis`  
**Implementation:** [03_APPLICATION_LAYER.md § Commands](./03_APPLICATION_LAYER.md#cqrs-commands)

---

#### 5. 📊 Daily Summaries
- **Aggregated nutrition** by day
- **Breakdown by meal type** (breakfast, lunch, dinner, snack)
- **Meal history** with filters
- **Text search** across meals

**GraphQL Operations:** `dailySummary`, `mealHistory`, `searchMeals`  
**Implementation:** [03_APPLICATION_LAYER.md § Queries](./03_APPLICATION_LAYER.md#cqrs-queries)

---

## 🔧 Technology Stack

### Core Technologies
- **Python 3.11+**: Type hints, async/await
- **FastAPI**: Web framework
- **Strawberry GraphQL**: Schema-first GraphQL
- **Pydantic v2**: Data validation

### AI & External APIs
- **OpenAI v2.5.0**: Vision + structured outputs + prompt caching
- **USDA FoodData Central v1**: Nutrition data
- **OpenFoodFacts API v2**: Barcode lookup

### Persistence
- **InMemoryRepository**: Development/testing
- **MongoRepository**: Production (with Motor driver)
- **Redis**: Optional caching + event bus

### Resilience
- **circuitbreaker**: Circuit breaker pattern
- **tenacity**: Retry logic with exponential backoff
- **httpx**: Async HTTP client

### Testing
- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting

### Documentation
- **SpectaQL**: Auto-generated GraphQL API docs

---

## 📖 Implementation Phases

### Phase 0: Cleanup & Preparation (2-3 hours)
**Goal:** Analyze dependencies, remove old code, create new structure

**Actions:**
1. Analyze dependencies: `grep -r "from backend.domain.meal"`
2. Remove old code
3. Create new folder structure
4. Install dependencies: `openai ^2.5.0`, `circuitbreaker`, etc.

**Deliverable:** Clean slate ready for implementation

**Guide:** [01_IMPLEMENTATION_GUIDE.md § Phase 0](./01_IMPLEMENTATION_GUIDE.md#phase-0-cleanup--preparation)

---

### Phase 1: Domain Layer - Core (8-10 hours)
**Goal:** Implement core domain entities, value objects, events

**Tasks:**
- Value objects: `MealId`, `Quantity`, `Timestamp`, `Confidence`
- Entities: `MealEntry`, `Meal` (aggregate root)
- Domain events: `MealAnalyzed`, `MealConfirmed`, etc.
- Exceptions: `MealDomainError` hierarchy
- Factory: `MealFactory`
- Ports: `IVisionProvider`, `INutritionProvider`, `IBarcodeProvider`, `IMealRepository`

**Deliverable:** Domain core with 100% test coverage

**Guide:** [02_DOMAIN_LAYER.md § Core Domain](./02_DOMAIN_LAYER.md#core-domain)

---

### Phase 2: Domain Layer - Capabilities (12-15 hours)
**Goal:** Implement domain services for nutrition, recognition, barcode

**Tasks:**
- **Nutrition Capability**: `NutrientProfile`, `NutritionEnrichmentService`
- **Recognition Capability**: `RecognizedFood`, `FoodRecognitionService`
- **Barcode Capability**: `BarcodeService`

**Deliverable:** Complete domain layer

**Guide:** [02_DOMAIN_LAYER.md § Capabilities](./02_DOMAIN_LAYER.md#nutrition-capability)

---

### Phase 3: Infrastructure Layer (15-18 hours)
**Goal:** Implement adapters for external dependencies

**Tasks:**
- **OpenAI**: `OpenAIClient`, `OpenAIVisionProvider`, system prompt (>1024 tokens)
- **USDA**: `USDAClient`, `USDAMapper`, `USDANutritionProvider`
- **OpenFoodFacts**: `OpenFoodFactsClient`, `OpenFoodFactsBarcodeProvider`
- **Repository**: `InMemoryMealRepository`
- **Event Bus**: `InMemoryEventBus`
- Circuit breakers on all external APIs

**Deliverable:** Infrastructure adapters with integration tests

**Guide:** [04_INFRASTRUCTURE_LAYER.md](./04_INFRASTRUCTURE_LAYER.md)

---

### Phase 4: Application Layer (10-12 hours)
**Goal:** Implement CQRS commands, queries, orchestrators

**Tasks:**
- **Commands**: `AnalyzeMealPhotoCommand`, `ConfirmAnalysisCommand`, etc.
- **Queries**: `GetMealQuery`, `ListMealsQuery`, `DailySummaryQuery`
- **Orchestrators**: `PhotoOrchestrator`, `BarcodeOrchestrator`
- Event handlers

**Deliverable:** Complete application layer

**Guide:** [03_APPLICATION_LAYER.md](./03_APPLICATION_LAYER.md)

---

### Phase 5: GraphQL Layer (8-10 hours)
**Goal:** Implement GraphQL schema and resolvers

**⚠️ CRITICAL STRATEGY:** Implement **atomic queries FIRST** (testing utilities), then aggregate queries, then mutations.

**Tasks:**
1. **Atomic queries FIRST** (3h): `recognizeFood`, `enrichNutrients`, `searchFoodByBarcode`
   - Test OpenAI Vision in isolation
   - Test USDA enrichment in isolation
   - Test OpenFoodFacts lookup in isolation
   - Validate GraphQL schema and types
   - Fast feedback without orchestration complexity
2. **Aggregate queries** (2h): `meal`, `mealHistory`, `dailySummary`
3. **Mutations LAST** (3h): `analyzeMealPhoto`, `confirmMealAnalysis`, etc.
   - Complex orchestration only after atomic operations validated

**Rationale:**
- Atomic queries test business logic independently
- Debug individual capabilities before orchestration
- Faster development cycle (no dependencies)
- Better error isolation
- Perfect examples for SpectaQL documentation

**Deliverable:** Complete GraphQL API with test-first approach

**Guide:** [06_GRAPHQL_API.md](./06_GRAPHQL_API.md) + [01_IMPLEMENTATION_GUIDE.md § Phase 5](./01_IMPLEMENTATION_GUIDE.md#phase-5-graphql-layer-8-10-ore)

---

### Phase 6: Testing & Quality (8-10 hours)
**Goal:** Achieve >90% test coverage

**Tasks:**
- Unit tests: Domain + Application
- Integration tests: Infrastructure (real APIs)
- E2E tests: Complete workflows
- MyPy strict mode: `mypy --strict backend/`
- Ruff linting: `ruff check backend/`
- Black formatting: `black backend/`

**Deliverable:** >90% coverage, all quality gates pass

**Guide:** [05_TESTING_STRATEGY.md](./05_TESTING_STRATEGY.md)

---

### Phase 7: MongoDB Migration (6-8 hours, optional)
**Goal:** Migrate from InMemory to MongoDB

**Tasks:**
- Implement `MongoMealRepository`
- Migration script: InMemory → MongoDB
- Update dependency injection
- Performance testing

**Deliverable:** Production-ready persistence

**Guide:** [01_IMPLEMENTATION_GUIDE.md § Phase 7](./01_IMPLEMENTATION_GUIDE.md#phase-7-mongodb-migration)

---

## 🧪 Testing Strategy

### Test Pyramid

```
      /\
     /E2E\      ← Few (5-15s each, full workflows)
    /------\
   /INTEGR.\   ← Some (1-5s each, real APIs)
  /----------\
 /   UNIT     \ ← Many (<100ms each, isolated)
/--------------\
```

### TDD Workflow

1. **RED**: Write failing test
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Improve code quality

### Best Practices
- ✅ **Dependency Injection** > Mocking internals
- ✅ **Real Pydantic models** > Stubs
- ✅ **One behavior per test**
- ✅ **Clear test names** (`test_<action>_<context>_<result>`)
- ✅ **AAA pattern** (Arrange-Act-Assert)

**Guide:** [05_TESTING_STRATEGY.md](./05_TESTING_STRATEGY.md)

---

## 🌐 GraphQL API

### Mutations (6 total)

1. **`analyzeMealPhoto`**: Photo → AI recognition → USDA enrichment → Save
2. **`analyzeMealBarcode`**: Barcode → OpenFoodFacts → USDA fallback → Save
3. **`analyzeMealDescription`**: Text → AI extraction → USDA enrichment → Save
4. **`confirmMealAnalysis`**: Review AI results → Confirm selected items
5. **`updateMeal`**: Edit dish name, quantities
6. **`deleteMeal`**: Soft delete

### Queries (7 total)

**Aggregate Queries** (data retrieval):
1. **`meal`**: Get single meal by ID
2. **`mealHistory`**: List meals with filters (date, type, pagination)
3. **`searchMeals`**: Text search across meals
4. **`dailySummary`**: Daily nutrition aggregation

**⚡ Atomic Queries** (testing utilities - **implement FIRST**):
5. **`recognizeFood`**: Test OpenAI Vision in isolation (no persistence)
6. **`enrichNutrients`**: Test USDA enrichment in isolation
7. **`searchFoodByBarcode`**: Test OpenFoodFacts lookup in isolation

**Why atomic queries are critical:**
- ✅ Test business logic before orchestration
- ✅ Debug individual capabilities independently
- ✅ Validate GraphQL schema early
- ✅ Fast feedback loop (no dependencies)
- ✅ Perfect examples for SpectaQL docs
- ✅ Mobile app experimentation without side effects

### Documentation

**Auto-generated with SpectaQL:**
```bash
# Generate docs
make docs

# Output: backend/docs/REFACTOR/NEW/api/index.html
```

**Guide:** [06_GRAPHQL_API.md § SpectaQL Documentation](./06_GRAPHQL_API.md#spectaql-documentation)

---

## 🎓 Learning Resources

### Domain-Driven Design (DDD)
- 📖 **Eric Evans** - "Domain-Driven Design: Tackling Complexity in the Heart of Software"
- 📖 **Vaughn Vernon** - "Implementing Domain-Driven Design"
- 🎥 **Martin Fowler** - [Bounded Context](https://martinfowler.com/bliki/BoundedContext.html)

### Clean Architecture
- 📖 **Robert C. Martin (Uncle Bob)** - "Clean Architecture"
- 🎥 **Uncle Bob** - [Clean Architecture and Design](https://www.youtube.com/watch?v=2dKZ-dWaCiU)

### CQRS
- 📖 **Greg Young** - "CQRS Documents"
- 🎥 **Martin Fowler** - [CQRS](https://martinfowler.com/bliki/CQRS.html)

### Hexagonal Architecture
- 📖 **Alistair Cockburn** - [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)

---

## 🔍 Key Decisions & Rationale

### 1. Hybrid Domain Structure

**Decision:** Capabilities (nutrition/, recognition/, barcode/) with DDD structure inside

**Rationale:**
- Isolates teams by capability
- Maintains DDD benefits within each capability
- Easier to split into microservices later

**Reference:** [00_ARCHITECTURE_OVERVIEW.md § Project Structure](./00_ARCHITECTURE_OVERVIEW.md#project-structure)

---

### 2. CQRS in Application Layer

**Decision:** Separate commands/ and queries/ with dedicated handlers

**Rationale:**
- Clear separation of write/read operations
- Different scaling strategies (writes < reads)
- Easier to optimize queries independently

**Reference:** [03_APPLICATION_LAYER.md § CQRS Commands](./03_APPLICATION_LAYER.md#cqrs-commands)

---

### 3. Orchestrators in Application Layer

**Decision:** Place orchestrators in `application/orchestrators/`, NOT in domain

**Rationale:**
- Orchestrators coordinate multiple domain services (application concern)
- Domain should not know about orchestration logic
- Easier to test in isolation

**Reference:** [03_APPLICATION_LAYER.md § Orchestrators](./03_APPLICATION_LAYER.md#orchestrators)

---

### 4. Ports & Adapters (Hexagonal)

**Decision:** Domain defines interfaces (ports), Infrastructure implements (adapters)

**Rationale:**
- **Dependency Inversion**: Infrastructure depends on Domain
- Easy to swap implementations (InMemory → MongoDB)
- Testability (mock at boundaries)

**Reference:** [02_DOMAIN_LAYER.md § Ports](./02_DOMAIN_LAYER.md#ports)

---

### 5. Domain Events

**Decision:** Implement full event system with IEventBus

**Rationale:**
- Auditability (track all meal changes)
- Analytics (meal analysis metrics)
- Future integrations (notifications, sync)
- Loose coupling between components

**Reference:** [02_DOMAIN_LAYER.md § Domain Events](./02_DOMAIN_LAYER.md#domain-events)

---

### 6. OpenAI v2.5.0 with Prompt Caching

**Decision:** Use structured outputs + >1024 token system prompt

**Rationale:**
- **Cost reduction**: 50% savings on repeated calls
- **Reliability**: Native Pydantic validation
- **Performance**: Cached prompts → faster responses
- **USDA compatibility**: Prompt emphasizes specific labels

**Reference:** [04_INFRASTRUCTURE_LAYER.md § OpenAI Integration](./04_INFRASTRUCTURE_LAYER.md#openai-integration)

---

### 7. InMemory First, MongoDB Later

**Decision:** Start with InMemoryMealRepository, migrate to MongoDB in Phase 7

**Rationale:**
- **Fast development**: No DB setup needed
- **Easy testing**: Clear state between tests
- **Gradual migration**: Validate architecture first
- **Ports & Adapters**: Seamless swap thanks to IMealRepository

**Reference:** [04_INFRASTRUCTURE_LAYER.md § Repositories](./04_INFRASTRUCTURE_LAYER.md#repositories)

---

## 🚨 Critical Implementation Notes

### 1. OpenAI System Prompt MUST BE >1024 Tokens

**Why?** Prompt caching only works for prompts >1024 tokens.

**Verification:**
```python
from infrastructure.ai.prompts.food_recognition import FOOD_RECOGNITION_SYSTEM_PROMPT

token_count = len(FOOD_RECOGNITION_SYSTEM_PROMPT) // 4
assert token_count >= 1024, f"Too short: {token_count} tokens"
```

**Reference:** [04_INFRASTRUCTURE_LAYER.md § System Prompt](./04_INFRASTRUCTURE_LAYER.md#3-system-prompt-1024-tokens---critical)

---

### 2. USDA Labels Must Be Specific

**Problem:** Vague labels → 500+ USDA results → confusion

**Solution:** OpenAI generates specific labels:
- ❌ "chicken" → ✅ "chicken breast, roasted"
- ❌ "potato" → ✅ "potato, boiled"
- ❌ "egg" → ✅ "eggs" (plural)

**Reference:** [04_INFRASTRUCTURE_LAYER.md § Why USDA Precision Matters](./04_INFRASTRUCTURE_LAYER.md#why-usda-precision-matters)

---

### 3. OpenFoodFacts MUST Return image_url

**Why?** User scans barcode → expects to see product photo

**Implementation:**
```python
product = await openfoodfacts_client.get_product(barcode)
assert product["image_url"], "Image URL required"
```

**Where saved?** `MealEntry.image_url`

**Reference:** [04_INFRASTRUCTURE_LAYER.md § Image URL Handling](./04_INFRASTRUCTURE_LAYER.md#️-critical-image-url-handling)

---

### 4. All Tests MUST Reference GraphQL Operation

**Example:**
```python
def test_analyze_photo_handler():
    """
    Test photo analysis command handler.
    
    GraphQL Operation: analyzeMealPhoto
    """
    pass
```

**Why?** Traceability from API → Implementation → Tests

**Reference:** [05_TESTING_STRATEGY.md § Best Practices](./05_TESTING_STRATEGY.md#7-always-check-graphql-operation)

---

## 📊 Success Metrics

### Code Quality
- ✅ **Test Coverage:** >90% (target: 95%)
- ✅ **Type Coverage:** 100% (MyPy strict mode)
- ✅ **Linting:** Ruff with no errors
- ✅ **Formatting:** Black (consistent style)

### Performance
- ✅ **Photo Analysis:** <5s end-to-end
- ✅ **Barcode Lookup:** <2s end-to-end
- ✅ **Query Response:** <500ms (cached)
- ✅ **OpenAI Cache Hit Rate:** >50% after warmup

### Reliability
- ✅ **Circuit Breaker:** Max 5 failures before open
- ✅ **Retry Logic:** 3 attempts with exponential backoff
- ✅ **Error Handling:** Type-safe Union types in GraphQL
- ✅ **Domain Invariants:** Always validated

---

## 🤝 Contributing

### Development Workflow

1. **Create feature branch**: `git checkout -b feature/meal-domain-refactor`
2. **Follow TDD**: Write test → Implement → Refactor
3. **Run quality checks**: `make quality`
4. **Commit with conventional commits**: `feat(meal): implement MealEntry scaling`
5. **Push and create PR**: Include tests and documentation updates

### Quality Gates (CI/CD)

```bash
# All must pass before merge
make lint      # Ruff + Black
make typecheck # MyPy strict
make test      # PyTest with coverage
make docs      # SpectaQL generation
```

---

## 📞 Support

### Questions?

- **Slack**: `#backend-meal-domain`
- **Email**: backend-team@nutrifit.app
- **Issue Tracker**: GitHub Issues with `meal-domain` label

### Reporting Issues

When reporting issues, include:
1. **GraphQL operation** affected (e.g., `analyzeMealPhoto`)
2. **Layer** where issue occurs (Domain/Application/Infrastructure/GraphQL)
3. **Steps to reproduce**
4. **Expected vs actual behavior**
5. **Relevant logs** (use `make log`)

---

## 🎉 Conclusion

This documentation provides a **complete, production-ready blueprint** for refactoring the Nutrifit Meal domain.

### Next Steps

1. ✅ **Read** [00_ARCHITECTURE_OVERVIEW.md](./00_ARCHITECTURE_OVERVIEW.md) (30 min)
2. ✅ **Start** [01_IMPLEMENTATION_GUIDE.md](./01_IMPLEMENTATION_GUIDE.md) Phase 0 (2-3h)
3. ✅ **Implement** Phases 1-7 sequentially (~80-100h total)
4. ✅ **Test** as you go (TDD approach)
5. ✅ **Deploy** with confidence 🚀

### Total Time Investment

- **Reading documentation**: ~5 hours
- **Implementation**: ~80-100 hours (2-3 weeks)
- **Testing & refinement**: Included in phases
- **Total**: ~3 weeks for complete refactor

### Expected Outcomes

✅ Clean, maintainable architecture  
✅ >90% test coverage  
✅ Type-safe codebase  
✅ AI-powered meal recognition  
✅ Accurate nutrition tracking  
✅ Production-ready persistence  
✅ Auto-generated API documentation  

---

## 📊 Current Implementation Status

### Domain Completion Summary

| Domain | Status | Features | Tests | Coverage |
|--------|--------|----------|-------|----------|
| **Meal** | ✅ Complete | Photo/Barcode/Text analysis, USDA enrichment, Daily summaries | 120+ | 95% |
| **Activity** | ✅ Complete | Event sync, Health totals, Deduplication, Aggregates | 85+ | 92% |
| **Nutritional Profile** | ✅ Complete + ML | BMR/TDEE/Macros, Progress tracking, **ML forecasting**, **Trend analysis** | 264 | 94% |
| **Cross-Domain** | ✅ Validated | Energy balance (IN-OUT), Integration workflows | E2E | 100% |

### ML Enhancement Status

**Phase 9 Step 2: COMPLETED** ✅

- ✅ Weight Forecasting (4 models with auto-selection)
- ✅ Trend Analysis (direction + magnitude, plateau detection)
- ✅ Adaptive TDEE (Kalman Filter)
- ✅ Weekly Pipeline (APScheduler background jobs)
- ✅ 74 ML-specific tests (100% coverage)
- ✅ E2E validation (test_ml_workflow.sh)

**Key Metrics:**
- Total tests passing: **469** (120 Meal + 85 Activity + 264 Profile)
- Overall coverage: **94%** average
- E2E scripts: **3** (meal, activity, all-domains)
- Response time: **30-170ms** (ML forecasting)

### GraphQL API Coverage

```graphql
# Implemented Namespaces
query {
  meals { ... }                    # ✅ 4 queries + 3 utility queries
  activity { ... }                 # ✅ 3 queries
  nutritionalProfile { ... }       # ✅ 3 queries (including ML forecastWeight)
}

mutation {
  meals { ... }                    # ✅ 6 mutations
  activity { ... }                 # ✅ 2 mutations
  nutritionalProfile { ... }       # ✅ 4 mutations
}
```

**New ML Queries:**
- `forecastWeight`: Weight predictions with confidence intervals
- `trendDirection`/`trendMagnitude`: Actionable trend insights

### Production Readiness

**✅ Complete:**
- Clean Architecture across all domains
- Comprehensive test coverage (>90% all domains)
- E2E validation (4-domain integration)
- ML-powered insights (weight forecasting, adaptive TDEE)
- GraphQL API documentation (SpectaQL ready)
- Background job scheduling (APScheduler)

**🚀 Ready for:**
- Production deployment
- Mobile app integration
- Monitoring/observability setup
- Performance optimization
- Feature expansion (LLM feedback, social features, etc.)

---

## 🎯 Next Steps

### For New Features

1. **LLM Feedback** (Phase 9 Step 3) - Motivational insights via OpenAI
2. **Meal Planning** - ML-powered meal recommendations
3. **Exercise Recommendations** - Personalized workout suggestions
4. **Social Features** - Goal sharing and community challenges

### For Operations

1. **Monitoring** - Set up observability (logs, metrics, traces)
2. **Performance** - Optimize hot paths, add caching where needed
3. **Scaling** - Prepare for horizontal scaling (stateless design ready)
4. **Security** - Implement rate limiting, API authentication

### For Documentation

1. **API Docs** - Generate SpectaQL documentation for all domains
2. **Architecture Decision Records** - Document key technical decisions
3. **Runbooks** - Create operational guides for common scenarios
4. **Mobile SDK** - Create GraphQL client SDK for mobile apps

---

**Last Updated:** 3 Novembre 2025  
**Version:** 3.0  
**Status:** 🟢 Production Ready - Multi-Domain Architecture Complete

**The foundation is solid. Time to scale! 🚀**
