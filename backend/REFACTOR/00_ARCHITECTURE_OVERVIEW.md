# 🏗️ Nutrifit Backend - Architecture Overview

**Data:** 3 Novembre 2025  
**Versione:** 3.0  
**Status:** Production Ready - 4 Domains Implemented

---

## 📋 Table of Contents

1. [Vision & Goals](#vision--goals)
2. [Architecture Principles](#architecture-principles)
3. [Domain Model](#domain-model)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [Integration Points](#integration-points)
7. [Implemented Domains](#implemented-domains)

---

## 🎯 Vision & Goals

### Vision
Costruire un sistema completo di fitness tracking modulare, manutenibile e performante con **4 domini core**:
1. **Meal Domain**: AI-powered food tracking (OpenAI Vision, OpenFoodFacts, USDA)
2. **Activity Domain**: Health data sync and calorie tracking
3. **Nutritional Profile Domain**: Personalized BMR/TDEE/Macro calculation + ML forecasting
4. **Goal Tracking**: Cross-domain analytics and progress monitoring

### Goals
- ✅ **Manutenibilità**: Clean Architecture + DDD per tutti i domini
- ✅ **Performance**: Caching aggressivo, circuit breakers, async operations
- ✅ **Innovazione**: ML-powered insights (weight forecasting, adaptive TDEE)
- ✅ **Testing**: >90% coverage, complete E2E validation
- ✅ **Disaccoppiamento**: Ports & Adapters per sostituibilità
- ✅ **Scalabilità**: Multi-domain architecture pronta per microservices

---

## 🏛️ Architecture Principles

### 1. Clean Architecture (Onion Architecture)
```
┌─────────────────────────────────────────────┐
│          External Interfaces                │
│   (GraphQL, REST API, Events)               │
├─────────────────────────────────────────────┤
│          Infrastructure Layer               │
│   (OpenAI, USDA, MongoDB, Redis)            │
├─────────────────────────────────────────────┤
│          Application Layer                  │
│   (Commands, Queries, Orchestrators)        │
├─────────────────────────────────────────────┤
│          Domain Layer                       │
│   (Entities, Value Objects, Services)       │
└─────────────────────────────────────────────┘
```

**Dependency Rule**: Le dipendenze puntano SEMPRE verso il centro (Domain).

### 2. Domain-Driven Design (DDD)

- **Aggregates**: Meal (root), MealEntry (entity)
- **Value Objects**: Quantity, Confidence, NutrientProfile
- **Domain Services**: FoodRecognitionService, NutritionEnrichmentService
- **Domain Events**: MealAnalyzed, MealConfirmed, MealUpdated
- **Repositories**: IMealRepository (interface)

### 3. CQRS (Command Query Responsibility Segregation)

**Commands** (Write):
- `AnalyzeMealPhotoCommand`
- `ConfirmAnalysisCommand`
- `UpdateMealCommand`

**Queries** (Read):
- `GetMealQuery`
- `ListMealsQuery`
- `DailySummaryQuery`
- `GetSummaryRangeQuery` (multi-day aggregates)
- `GetAggregateRangeQuery` (activity multi-day aggregates)

### 4. Ports & Adapters (Hexagonal Architecture)

**Ports** (Interfaces in Domain):
- `IMealRepository`
- `INutritionProvider`
- `IVisionProvider`
- `IEventBus`

**Adapters** (Implementations in Infrastructure):
- `InMemoryMealRepository` / `MongoMealRepository`
- `USDANutritionProvider`
- `OpenAIVisionProvider`
- `InMemoryEventBus` / `RedisEventBus`

---

## 🧠 Domain Model

### Core Concepts

#### 1. **Meal** (Aggregate Root)
```
Meal
├── id: UUID
├── user_id: str
├── timestamp: datetime
├── meal_type: str (BREAKFAST | LUNCH | DINNER | SNACK)
├── entries: list[MealEntry]
└── totals: NutrientTotals
```

**Invariants**:
- Un Meal deve avere almeno 1 MealEntry
- I totali devono essere sempre la somma degli entries
- Timestamp non può essere nel futuro

#### 2. **MealEntry** (Entity)
```
MealEntry
├── id: UUID
├── meal_id: UUID
├── name: str
├── quantity_g: float
├── nutrients: NutrientProfile
├── source: str (PHOTO | BARCODE | DESCRIPTION | MANUAL)
├── confidence: float
└── metadata: EntryMetadata
```

#### 3. **NutrientProfile** (Value Object)
```
NutrientProfile
├── calories: int
├── protein: float
├── carbs: float
├── fat: float
├── fiber: float?
├── sugar: float?
├── sodium: float?
└── source: str (USDA | BARCODE_DB | CATEGORY | AI_ESTIMATE)
```

### Capabilities (Bounded Contexts)

#### 1. **Nutrition Capability**
Responsabile di arricchire alimenti con dati nutrizionali.

**Services**:
- `NutritionEnrichmentService`
  - Cascade strategy: USDA → Category Profile → Generic Fallback
  - Cache USDA responses (TTL 30 giorni)
  - Circuit breaker su API calls

**Value Objects**:
- `MacroNutrients` (calories, protein, carbs, fat)
- `MicroNutrients` (fiber, sugar, sodium, vitamins)

#### 2. **Recognition Capability**
Responsabile di identificare alimenti da foto/testo.

**Services**:
- `FoodRecognitionService`
  - OpenAI Vision API
  - Structured outputs (Pydantic)
  - System prompt >1024 token (caching)

**Entities**:
- `RecognizedFood` (label, display_name, quantity, confidence)

**Value Objects**:
- `Confidence` (0.0 - 1.0)
- `FoodLabel` (validated string)

#### 3. **Barcode Capability**
Responsabile di lookup prodotti da barcode.

**Services**:
- `BarcodeService`
  - OpenFoodFacts API
  - Cache prodotti
  - Fallback a categoria se non trovato

---

## 🛠️ Technology Stack

### Core
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **GraphQL**: Strawberry GraphQL

### AI & External APIs
- **OpenAI**: v2.5.0+ (Structured Outputs)
- **USDA**: FoodData Central API v1
- **OpenFoodFacts**: API v2

### Persistence
- **Development**: In-Memory Repository
- **Production**: MongoDB (Atlas)
- **Cache**: Redis (optional)

### Testing
- **Unit**: pytest
- **Integration**: pytest + httpx mocks
- **E2E**: pytest + GraphQL client

### Resilience
- **Circuit Breaker**: `circuitbreaker` library
- **Retry**: `tenacity` library
- **Rate Limiting**: Custom implementation

### DevOps
- **Package Manager**: `uv`
- **Linting**: `ruff`
- **Formatting**: `black`
- **Type Checking**: `mypy`

---

## 📁 Project Structure

```
backend/
│
├── domain/                          # Domain Layer (Pure Business Logic)
│   ├── meal/
│   │   ├── nutrition/               # Nutrition Capability
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   ├── services/
│   │   │   └── ports/
│   │   │
│   │   ├── recognition/             # Recognition Capability
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   ├── services/
│   │   │   └── ports/
│   │   │
│   │   ├── barcode/                 # Barcode Capability
│   │   │   ├── services/
│   │   │   └── ports/
│   │   │
│   │   └── core/                    # Core Meal Domain
│   │       ├── entities/            # Meal, MealEntry
│   │       ├── value_objects/       # MealId, Quantity, Timestamp
│   │       ├── events/              # MealAnalyzed, MealConfirmed
│   │       ├── exceptions/          # DomainError hierarchy
│   │       └── factories/           # MealFactory
│   │
│   └── shared/                      # Shared Kernel
│       └── ports/                   # IMealRepository, IEventBus
│
├── application/                     # Application Layer (Use Cases)
│   └── meal/
│       ├── commands/                # CQRS Write Operations
│       │   ├── analyze_photo.py
│       │   ├── analyze_barcode.py
│       │   ├── analyze_description.py
│       │   ├── confirm_analysis.py
│       │   ├── update_meal.py
│       │   └── delete_meal.py
│       │
│       ├── queries/                 # CQRS Read Operations
│       │   ├── get_meal.py
│       │   ├── list_meals.py
│       │   ├── search_meals.py
│       │   └── daily_summary.py
│       │
│       ├── orchestrators/           # Complex Workflows
│       │   ├── photo_orchestrator.py
│       │   ├── barcode_orchestrator.py
│       │   └── description_orchestrator.py
│       │
│       ├── dtos/                    # Data Transfer Objects
│       │   ├── meal_dto.py
│       │   └── analysis_dto.py
│       │
│       └── event_handlers/          # Domain Event Handlers
│           ├── meal_analyzed_handler.py
│           └── meal_confirmed_handler.py
│
├── infrastructure/                  # Infrastructure Layer (External Dependencies)
│   ├── ai/
│   │   ├── openai_client.py         # OpenAI v2.5.0 client
│   │   └── prompts/
│   │       └── food_recognition.py
│   │
│   ├── external_apis/
│   │   ├── usda/
│   │   │   ├── client.py            # USDA API client
│   │   │   ├── mapper.py            # USDA → NutrientProfile mapper
│   │   │   └── categories.py        # Category fallback profiles
│   │   │
│   │   └── openfoodfacts/
│   │       ├── client.py            # OpenFoodFacts API client
│   │       └── mapper.py            # OFF → NutrientProfile mapper
│   │
│   ├── persistence/
│   │   ├── in_memory/
│   │   │   └── meal_repository.py   # InMemoryMealRepository
│   │   │
│   │   ├── mongodb/
│   │   │   ├── meal_repository.py   # MongoMealRepository
│   │   │   └── migrations/
│   │   │
│   │   └── redis/
│   │       └── cache_repository.py  # Redis cache implementation
│   │
│   └── events/
│       ├── in_memory_bus.py         # InMemoryEventBus
│       └── redis_bus.py             # RedisEventBus (pub/sub)
│
├── graphql/                         # GraphQL Layer (API)
│   ├── schema.graphql               # Schema definition
│   └── resolvers/
│       └── meal/
│           ├── queries.py           # Query resolvers
│           └── mutations.py         # Mutation resolvers
│
├── api/                             # FastAPI Application
│   ├── dependencies.py              # DI Container
│   ├── middleware.py                # Auth, logging, etc.
│   └── main.py                      # FastAPI app
│
└── tests/                           # Test Suite
    ├── unit/                        # Unit tests (fast, isolated)
    │   ├── domain/
    │   └── application/
    │
    ├── integration/                 # Integration tests (with mocks)
    │   ├── infrastructure/
    │   └── graphql/
    │
    └── e2e/                         # End-to-end tests (full flow)
        └── meal_flows/
```

---

## 🔌 Integration Points

### 1. GraphQL API

#### Queries
```graphql
type Query {
  # Meal queries (namespace: meals)
  meals {
    meal(id: ID!, userId: ID!): Meal
    mealHistory(userId: ID!, filter: MealFilter, pagination: PaginationInput): MealConnection!
    search(userId: ID!, query: String!): [Meal!]!
    dailySummary(userId: ID!, date: Date!): NutritionSummary!
    summaryRange(userId: ID!, startDate: DateTime!, endDate: DateTime!, groupBy: GroupByPeriod!): RangeSummaryResult!
  }
  
  # Activity queries (namespace: activity)
  activity {
    entries(userId: ID!, after: String, before: String, limit: Int): [ActivityEvent!]!
    syncEntries(date: String!, userId: ID, after: String, limit: Int): [HealthTotalsDelta!]!
    aggregateRange(userId: ID!, startDate: String!, endDate: String!, groupBy: GroupByPeriod!): ActivityRangeResult!
  }
  
  # Utility queries (namespace: atomic)
  atomic {
    recognizeFood(photoUrl: String!): FoodRecognitionResult!
    enrichNutrients(label: String!, quantityG: Float!): NutrientProfile!
    searchFoodByBarcode(barcode: String!): Product
  }
}
```

#### Mutations
```graphql
type Mutation {
  # Analysis mutations (2-step process)
  analyzeMealPhoto(input: PhotoAnalysisInput!): MealAnalysis!
  analyzeMealBarcode(input: BarcodeAnalysisInput!): MealAnalysis!
  analyzeMealDescription(input: DescriptionAnalysisInput!): MealAnalysis!
  
  # Confirmation mutations
  confirmMealAnalysis(analysisId: ID!, confirmedItemIds: [ID!]!): Meal!
  
  # CRUD mutations
  updateMeal(id: ID!, updates: MealUpdateInput!): Meal!
  deleteMeal(id: ID!): Boolean!
}
```

### 2. OpenAI Integration

**Version**: 2.5.0+  
**Model**: `gpt-4o-mini-2024-07-18`  
**Features**:
- Structured outputs (native Pydantic support)
- Prompt caching (system prompt >1024 tokens)
- Circuit breaker (5 failures → 60s timeout)

### 3. USDA Integration

**API**: FoodData Central v1  
**Endpoints**:
- `/foods/search` - Search foods
- `/food/{fdcId}` - Get food details

**Cache Strategy**:
- TTL: 30 giorni
- Key pattern: `usda:{label}:{version}`
- Backend: Redis (prod) / In-Memory (dev)

### 4. OpenFoodFacts Integration

**API**: v2  
**Endpoints**:
- `/api/v2/product/{barcode}` - Get product by barcode

**Cache Strategy**:
- TTL: 7 giorni
- Key pattern: `off:{barcode}`

### 5. Event Bus

**Events Published**:
- `MealAnalyzed` - When AI analysis completes
- `MealConfirmed` - When user confirms meal
- `MealUpdated` - When meal is modified
- `MealDeleted` - When meal is deleted

**Event Consumers**:
- Analytics service
- Notification service
- Audit log service

---

## 🎯 Next Steps

1. Read: `01_IMPLEMENTATION_GUIDE.md` - Detailed implementation plan
2. Read: `02_DOMAIN_LAYER.md` - Domain layer specifications
3. Read: `03_APPLICATION_LAYER.md` - Application layer specifications
4. Read: `04_INFRASTRUCTURE_LAYER.md` - Infrastructure layer specifications
5. Read: `05_TESTING_STRATEGY.md` - Testing approach and examples

---

## 📚 References

- **Clean Architecture**: Robert C. Martin
- **Domain-Driven Design**: Eric Evans
- **CQRS**: Greg Young
- **Hexagonal Architecture**: Alistair Cockburn

---

## 🎯 Implemented Domains

### 1. 🍽️ Meal Domain (Phase 7)
**Status**: ✅ Production Ready  
**Purpose**: AI-powered food tracking and nutrition analysis

**Core Features**:
- Photo analysis (OpenAI Vision GPT-4o-mini)
- Barcode scanning (OpenFoodFacts API)
- Text description parsing
- USDA nutrition enrichment
- Daily/weekly/monthly summaries

**Key Entities**:
- `Meal` (aggregate root)
- `MealEntry` (entity)
- `NutrientProfile` (value object)

**GraphQL API**:
```graphql
query {
  meals {
    meal(id: ID!, userId: ID!): Meal
    mealHistory(...): MealConnection!
    dailySummary(userId: ID!, date: Date!): NutritionSummary!
    summaryRange(...): RangeSummaryResult!  # Multi-day aggregates
  }
}

mutation {
  analyzeMealPhoto(input: PhotoAnalysisInput!): MealAnalysis!
  confirmMealAnalysis(analysisId: ID!, ...): Meal!
}
```

**Test Coverage**: 95% (120+ tests)

---

### 2. 🏃 Activity Domain (Phase 8)
**Status**: ✅ Production Ready  
**Purpose**: Health data synchronization and activity tracking

**Core Features**:
- Minute-by-minute activity events
- Cumulative health totals (steps, calories, HR)
- Delta calculation for sync optimization
- Deduplication on (userId, timestamp)
- Multi-day aggregates with flexible grouping

**Key Entities**:
- `ActivityEvent` (minute-level data)
- `HealthTotalsDelta` (cumulative snapshots)

**GraphQL API**:
```graphql
query {
  activity {
    entries(userId: ID!, ...): [ActivityEvent!]!
    syncEntries(date: String!, ...): [HealthTotalsDelta!]!
    aggregateRange(...): ActivityRangeResult!  # Multi-day aggregates
  }
}

mutation {
  syncActivityEvents(input: SyncActivityInput!): SyncResult!
  syncHealthTotals(input: SyncHealthTotalsInput!): SyncHealthResult!
}
```

**Test Coverage**: 92% (85+ tests)

---

### 3. 📊 Nutritional Profile Domain (Phase 9)
**Status**: ✅ Production Ready + ML Enhanced  
**Purpose**: Personalized nutrition calculation and progress tracking

**Core Features**:
- BMR calculation (Mifflin-St Jeor formula)
- TDEE calculation (5 activity levels)
- Goal-based macro splits (CUT/MAINTAIN/BULK)
- Progress tracking with deficit/macro monitoring
- **ML-Powered**:
  - Weight forecasting (ARIMA, ExponentialSmoothing, LinearRegression)
  - Trend analysis (direction + magnitude)
  - Adaptive TDEE (Kalman Filter)
  - Weekly automated recalculation

**Key Entities**:
- `NutritionalProfile` (aggregate root)
- `ProgressRecord` (entity)
- `UserData`, `Goal`, `MacroSplit` (value objects)

**ML Services**:
- `WeightForecastService`: 4 time series models
- `KalmanTDEEService`: Adaptive TDEE estimation
- `TDEERecalculationPipeline`: Weekly background job

**GraphQL API**:
```graphql
query {
  nutritionalProfile {
    profile(profileId: String, userId: String): NutritionalProfileType
    progressScore(profileId: String!, ...): ProgressScore!
    forecastWeight(profileId: String!, ...): WeightForecastType!  # ML-powered
  }
}

mutation {
  createProfile(input: CreateProfileInput!): NutritionalProfileType!
  updateProfile(input: UpdateProfileInput!): NutritionalProfileType!
  recordProgress(input: RecordProgressInput!): ProgressRecordType!
}
```

**Test Coverage**: 94% (264 tests including 74 ML tests)

---

### 4. 🎯 Cross-Domain Integration
**Status**: ✅ Validated via E2E Tests  
**Purpose**: Enable data flow between domains

**Integration Points**:
1. **Meal → Profile**: Daily calorie/macro consumption
2. **Activity → Profile**: Active calories burned
3. **Profile**: Calculates calorie balance (IN - OUT)

**E2E Validation**:
- `test_all_domains_e2e.sh`: Complete 4-domain workflow
- Energy balance calculation: Meals (IN) vs Activity (OUT)
- Progress tracking with real cross-domain data

---

## 📝 Recent Updates (v3.0 - 3 Nov 2025)

### Major Features Added
- **ML Weight Forecasting**: 4 adaptive time series models with automatic selection
- **Trend Analysis**: Direction (decreasing/increasing/stable) + magnitude detection
- **Adaptive TDEE**: Kalman Filter for metabolic adaptation tracking
- **Weekly Pipeline**: Automated TDEE recalculation (APScheduler)
- **Complete E2E Testing**: 4-domain integration validation

### Architecture Enhancements
- **ML Infrastructure**: scipy, pandas, statsmodels integration
- **Background Jobs**: APScheduler for recurring tasks
- **Trend Detection**: Plateau handling as actionable insight (0.5kg threshold)
- **Repository Pattern**: Consistent factory pattern across all domains

### API Enhancements
- **`forecastWeight` query**: ML-powered weight predictions with confidence intervals
- **Range queries**: Multi-day aggregates for meals and activity (DAY/WEEK/MONTH)
- **Trend fields**: `trendDirection` and `trendMagnitude` in forecast response

### Quality Improvements
- **Test Coverage**: 94% overall (264 tests in nutritional profile domain)
- **E2E Scripts**: 3 comprehensive test scripts (profile, ML, all-domains)
- **Documentation**: Complete architecture and API reference

---

**Last Updated**: 3 Novembre 2025  
**Maintainer**: Development Team  
**Version**: 3.0 - Multi-Domain Production Ready
