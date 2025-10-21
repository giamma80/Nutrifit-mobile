# Nutrifit V2 - Refactored Meal System

**Version:** 2.0.0  
**Status:** In Development  
**Architecture:** Clean Architecture + Domain-Driven Design

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    GraphQL API Layer                    │
│                  (Strawberry GraphQL)                   │
├─────────────────────────────────────────────────────────┤
│                  Application Layer                      │
│              (Use Cases + Orchestration)                │
├─────────────────────────────────────────────────────────┤
│                    Domain Layer                         │
│         (Business Logic + Domain Models)                │
├─────────────────────────────────────────────────────────┤
│                Infrastructure Layer                     │
│        (DB, Cache, External APIs, AI Clients)           │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Three Input Modalities

### 1. 📸 Photo Analysis
**Flow:** Photo → AI Vision (OpenAI) → Food Recognition → USDA Enrichment

```graphql
mutation {
  analyzeMealPhoto(input: {
    photoUrl: "https://example.com/meal.jpg"
    userId: "user_123"
    dishHint: "pasta carbonara"
  }) {
    id
    status
    items {
      label
      displayName
      quantityG
      confidence
      nutrients {
        calories
        protein
        carbs
        fat
      }
    }
    totalCalories
  }
}
```

### 2. 🔍 Barcode Scan
**Flow:** Barcode → OpenFoodFacts → Product Lookup → Nutrient Scaling

```graphql
mutation {
  analyzeMealBarcode(input: {
    barcode: "3017620422003"
    userId: "user_123"
    quantityG: 250
  }) {
    id
    status
    items {
      displayName
      nutrients {
        calories
        protein
      }
    }
  }
}
```

### 3. 💬 Text Description
**Flow:** Text → AI Extraction → USDA Enrichment

```graphql
mutation {
  analyzeMealDescription(input: {
    description: "I ate pizza and salad for lunch"
    userId: "user_123"
  }) {
    id
    status
    items {
      displayName
      quantityG
      nutrients {
        calories
      }
    }
  }
}
```

---

## 🔄 Two-Phase Workflow

### Phase 1: **Analyze** (Temporary Storage)
- User provides input (photo/barcode/text)
- System analyzes and enriches with nutrients
- Result stored in `meal_analysis` collection (24h TTL)
- Status: `PENDING`
- User reviews and edits

### Phase 2: **Confirm** (Persistent Storage)
- User confirms which items to log
- Selected items persisted to `meals` collection
- Analysis deleted from temporary storage
- Status: `COMPLETED`

```graphql
# Phase 1: Analyze
mutation {
  analyzeMealPhoto(input: {...}) {
    id  # analysis_abc123
    items { ... }
  }
}

# Phase 2: Confirm
mutation {
  confirmMealPhoto(input: {
    analysisId: "analysis_abc123"
    acceptedIndexes: [0, 1]  # Accept first 2 items
    userId: "user_123"
  }) {
    createdMeals {
      id
      name
      calories
    }
  }
}
```

---

## 📁 Project Structure

```
backend/v2/
├── domain/                      # Business logic (NO external dependencies)
│   ├── meal/
│   │   ├── recognition/         # AI food recognition
│   │   ├── nutrition/           # USDA nutrient enrichment
│   │   ├── barcode/             # OpenFoodFacts barcode lookup
│   │   ├── orchestration/       # Coordinate atomic services
│   │   └── persistence/         # Meal storage logic
│   └── shared/                  # Value objects, base classes
│
├── infrastructure/              # External integrations
│   ├── database/                # MongoDB repositories
│   ├── cache/                   # Redis caching
│   ├── ai/                      # OpenAI client
│   ├── external_apis/           # USDA, OpenFoodFacts
│   └── config/                  # Settings
│
├── application/                 # Use cases
│   └── meal/                    # Meal use cases
│
├── graphql/                     # API layer
│   ├── queries/                 # Atomic read operations
│   ├── mutations/               # Orchestrated write operations
│   └── types/                   # GraphQL types
│
├── tests/                       # V2 test suite
│   ├── unit/                    # Fast, isolated tests
│   ├── integration/             # DB + external service tests
│   └── e2e/                     # Complete user flows
│
├── scripts/                     # Utilities
│   └── setup_mongodb.py         # Initialize MongoDB
│
└── docs/                        # V2 documentation
    ├── architecture.md
    ├── api_examples.md
    └── testing_guide.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- MongoDB 6.0+
- Redis 7.0+ (optional, for caching)
- OpenAI API Key
- USDA API Key

### 1. Setup MongoDB

```bash
# Start MongoDB
docker run -d -p 27017:27017 mongo:6.0

# Initialize collections and indexes
cd backend
python v2/scripts/setup_mongodb.py
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# backend/.env
OPENAI_API_KEY=sk-...
USDA_API_KEY=your_key
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=nutrifit
REDIS_URI=redis://localhost:6379
ENABLE_V2_MEAL_API=true
```

### 4. Run Tests

```bash
cd backend/v2

# Unit tests (fast)
pytest tests/unit -v

# Integration tests
pytest tests/integration -v --requires-mongodb

# E2E tests
pytest tests/e2e -v

# Coverage report
pytest --cov=backend.v2 --cov-report=html
```

### 5. Start Development Server

```bash
cd backend
uvicorn app:app --reload --port 8000
```

---

## 🧪 Testing Strategy

### Unit Tests (>90% Coverage)
- **Location:** `tests/unit/`
- **Scope:** Isolated component testing
- **Speed:** Fast (<1s per test)
- **Mocking:** All external dependencies

```bash
pytest tests/unit/domain/meal/recognition/test_service.py -v
```

### Integration Tests
- **Location:** `tests/integration/`
- **Scope:** DB operations, external APIs
- **Speed:** Moderate (~5s per test)
- **Requirements:** MongoDB, Redis

```bash
pytest tests/integration -v --requires-mongodb
```

### E2E Tests
- **Location:** `tests/e2e/`
- **Scope:** Complete user flows
- **Speed:** Slow (~10s per test)
- **Requirements:** Full system running

```bash
pytest tests/e2e -v
```

---

## 📊 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API Latency (p95) | <1500ms | TBD |
| Cache Hit Rate | >85% | TBD |
| Recognition Accuracy | >80% | TBD |
| Cost per Request | <$0.035 | TBD |
| Test Coverage | >90% | TBD |

---

## 🔍 Key Features

### ✅ Dependency Injection
- Constructor injection throughout
- Interface-based dependencies (Protocol)
- Easy to test with mocks

### ✅ Caching Strategy
- USDA responses cached (1h TTL)
- OpenAI responses cached (24h TTL)
- Reduces API costs by ~80%

### ✅ Retry Logic
- Exponential backoff for transient failures
- Max 3 retries
- Rate limit handling

### ✅ Idempotency
- Duplicate detection via idempotency keys
- Safe retries
- Prevents double-logging

### ✅ Batch Operations
- Bulk meal inserts (single DB query)
- 10x faster than N+1 queries

### ✅ Atomic Transactions
- MongoDB sessions
- All-or-nothing confirmations
- Automatic rollback on error

---

## 📖 Documentation

- [Complete Refactor Guide](../docs/V2/NUTRIFIT_MEAL_REFACTOR_COMPLETE.md)
- [Migration Strategy](../docs/V2/V2_MIGRATION_STRATEGY_QUICK_GUIDE.md)
- [Critical Reminders](../docs/V2/V2_CRITICAL_REMINDERS.md)
- [Best Practices](../docs/V2/V2_SERVICE_EXAMPLES_AND_BEST_PRACTICES.md)

---

## 🛠️ Development Guidelines

### Code Quality Requirements
- ✅ MyPy strict mode (0 errors)
- ✅ Ruff linting (pass)
- ✅ Black formatting
- ✅ Test coverage >90%
- ✅ Docstrings on all public APIs

### Git Commit Convention
```
feat(meal): add photo analysis orchestrator
fix(nutrition): handle missing USDA nutrients
test(barcode): add barcode service unit tests
docs(api): update GraphQL schema examples
```

### Pre-Commit Checklist
- [ ] All tests pass (`pytest`)
- [ ] MyPy passes (`mypy backend/v2`)
- [ ] Linting passes (`ruff check backend/v2`)
- [ ] Formatting applied (`black backend/v2`)
- [ ] Coverage >90% (`pytest --cov`)

---

## 🚦 Development Status

### Phase 0: Setup ✅
- [x] Directory structure
- [x] MongoDB initialization
- [x] Configuration files

### Phase 1: Foundation (In Progress)
- [ ] Domain models
- [ ] Value objects
- [ ] Exceptions

### Phase 2-11: TBD
See [NUTRIFIT_MEAL_REFACTOR_COMPLETE.md](../docs/V2/NUTRIFIT_MEAL_REFACTOR_COMPLETE.md) for complete roadmap.

---

## 🤝 Contributing

1. Follow architecture guidelines
2. Write tests first (TDD)
3. Use dependency injection
4. Document with examples
5. Keep domain layer pure (no infrastructure)

---

## 📞 Support

- **Documentation:** `backend/docs/V2/`
- **Issues:** GitHub Issues
- **Slack:** #nutrifit-v2-dev

---

**Built with ❤️ using Clean Architecture + DDD**
