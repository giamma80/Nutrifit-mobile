# 🏗️ Meal Domain - Architecture Overview

**Data:** 22 Ottobre 2025  
**Versione:** 2.0  
**Status:** Architecture Definition

---

## 📋 Table of Contents

1. [Vision & Goals](#vision--goals)
2. [Architecture Principles](#architecture-principles)
3. [Domain Model](#domain-model)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [Integration Points](#integration-points)

---

## 🎯 Vision & Goals

### Vision
Costruire un sistema di meal tracking modulare, manutenibile e performante che supporti:
- Analisi AI di foto pasto (OpenAI Vision)
- Lookup barcode (OpenFoodFacts)
- Descrizione testuale
- Arricchimento nutrizionale (USDA)

### Goals
- ✅ **Manutenibilità**: Clean Architecture + DDD
- ✅ **Performance**: Caching aggressivo, circuit breakers
- ✅ **Innovazione**: Nuove capabilities senza breaking changes
- ✅ **Testing**: >90% coverage, test pyramid
- ✅ **Disaccoppiamento**: Ports & Adapters per sostituibilità

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
  # Meal queries
  meal(id: ID!): Meal
  mealHistory(userId: ID!, filter: MealFilter, pagination: PaginationInput): MealConnection!
  searchMeals(userId: ID!, query: String!): [Meal!]!
  dailySummary(userId: ID!, date: Date!): NutritionSummary!
  
  # Utility queries (atomic operations)
  recognizeFood(photoUrl: String!): FoodRecognitionResult!
  enrichNutrients(label: String!, quantityG: Float!): NutrientProfile!
  searchFoodByBarcode(barcode: String!): Product
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

**Last Updated**: 22 Ottobre 2025  
**Maintainer**: Development Team
