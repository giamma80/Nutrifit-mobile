# 🗄️ Persistence Layer - Stato Attuale

**Version:** 2.1  
**Date:** 12 Novembre 2025  
**Status:** ✅ Architettura Unificata - ✅ MongoDB Meal & Profile Implemented - ⏳ Activity Pending

---

## 🎯 Executive Summary

Il layer di persistenza è stato **completamente unificato** attraverso tutti i domini con un'architettura coerente basata sul pattern Repository + Factory. Tutti e tre i domini (Meal, NutritionalProfile, Activity) ora usano la stessa configurazione e lo stesso pattern architetturale.

**Stato Corrente:**
- ✅ **Architettura Unificata** - Pattern coerente tra tutti i domini
- ✅ **Configurazione Globale** - Singola variabile `REPOSITORY_BACKEND`
- ✅ **InMemory Funzionante** - Tutti i test passano (780/780)
- ✅ **MongoDB Atlas Setup** - Database configurato e pronto
- ✅ **MongoDB Meal & Profile** - Implementati e testati (2/3 domini)
- ⏳ **MongoDB Activity** - Implementazione pendente (3-4h stimate)

---

## 🏗️ Architettura Unificata

### Pattern Repository + Factory

Tutti e tre i domini seguono lo stesso pattern:

```
Domain Layer
├── repository.py          # IRepository interface (port)
└── model/                 # Domain entities

Infrastructure Layer
├── persistence/
│   ├── {domain}_repository_factory.py    # Factory singleton
│   ├── inmemory/
│   │   └── {domain}_repository.py        # InMemory implementation
│   └── mongodb/
│       └── {domain}_repository.py        # MongoDB implementation (TODO)
```

### Configurazione Unificata

**Unica variabile per tutti i domini:**

```bash
# .env
REPOSITORY_BACKEND=inmemory  # o mongodb

# MongoDB credentials (solo se REPOSITORY_BACKEND=mongodb)
MONGODB_USER=nutrifit_app
MONGODB_PASSWORD=your_password
MONGODB_URI=mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@cluster.net/nutrifit
MONGODB_DATABASE=nutrifit
```

**Prima dell'unificazione (DEPRECATO):**
```bash
# ❌ Vecchio pattern (NON PIÙ USATO)
MEAL_REPOSITORY=inmemory
PROFILE_REPOSITORY=mongodb
ACTIVITY_REPOSITORY=inmemory
```

---

## 📊 Stato per Dominio

### 1. Meal Domain

**Architettura:**
```
domain/meal/core/
└── ports/
    └── repository.py           # IMealRepository

infrastructure/persistence/
├── factory.py                  # create_meal_repository()
├── in_memory/
│   └── meal_repository.py      # ✅ InMemoryMealRepository
└── mongodb/
    └── meal_repository.py      # ⏳ MongoMealRepository (TODO)
```

**Status:**
- ✅ Interface: `IMealRepository` definita
- ✅ Factory: `create_meal_repository()` con `REPOSITORY_BACKEND`
- ✅ InMemory: `InMemoryMealRepository` completo e testato
- ✅ **MongoDB: `MongoMealRepository` implementato** ⭐ NEW

**Test Coverage:**
- ✅ Unit tests: Factory + InMemory + MongoDB (12 tests)
- ✅ Integration tests: Structure created (requires MongoDB URI)

---

### 2. NutritionalProfile Domain

**Architettura:**
```
domain/nutritional_profile/core/
└── ports/
    └── repository.py                    # IProfileRepository

infrastructure/persistence/
├── nutritional_profile_factory.py       # create_profile_repository()
├── in_memory/
│   └── profile_repository.py            # ✅ InMemoryProfileRepository
└── mongodb/
    └── profile_repository.py            # ⏳ MongoProfileRepository (TODO)
```

**Status:**
- ✅ Interface: `IProfileRepository` definita
- ✅ Factory: `create_profile_repository()` con `REPOSITORY_BACKEND`
- ✅ InMemory: `InMemoryProfileRepository` completo e testato
- ✅ **MongoDB: `MongoProfileRepository` implementato** ⭐ NEW

**Test Coverage:**
- ✅ Unit tests: Factory + InMemory + MongoDB (12 tests)
- ✅ Integration tests: Structure ready (requires MongoDB URI)

---

### 3. Activity Domain

**Architettura (REFACTORED):**
```
domain/activity/
├── repository.py                        # ✅ IActivityRepository (NEW)
└── application/                         # Services refactored

infrastructure/persistence/
├── activity_repository_factory.py       # ✅ create_activity_repository()
├── inmemory/
│   └── activity_repository.py           # ✅ InMemoryActivityRepository
└── mongodb/
    └── activity_repository.py           # ⏳ MongoActivityRepository (TODO)
```

**Refactoring Completato:**
- ✅ **Eliminato codice legacy:**
  - ❌ `domain/activity/ports/` (ActivityEventsPort, ActivitySnapshotsPort)
  - ❌ `domain/activity/adapters/` (ActivityEventsAdapter, ActivitySnapshotsAdapter)
- ✅ **Creato pattern unificato:**
  - ✅ `IActivityRepository` - Interfaccia unificata
  - ✅ `InMemoryActivityRepository` - Wrappa repository legacy
  - ✅ `activity_repository_factory.py` - Factory con REPOSITORY_BACKEND
- ✅ **Refactored application layer:**
  - Services usano `IActivityRepository` invece di 2 ports separati
  - Integration layer usa repository factory

**Status:**
- ✅ Interface: `IActivityRepository` unifica eventi + snapshots
- ✅ Factory: `create_activity_repository()` con `REPOSITORY_BACKEND`
- ✅ InMemory: `InMemoryActivityRepository` wrappa legacy repos
- ⏳ MongoDB: `NotImplementedError` - Implementation pending

**Test Coverage:**
- ✅ Unit tests: 14 nuovi test per repository + factory
- ✅ Integration tests: Activity ingest funzionante
- ⏳ MongoDB tests: Pending

---

## 🔧 MongoDB Atlas Setup

### Database Configurazione

**Cluster:**
- Provider: MongoDB Atlas
- Tier: M0 Sandbox (free)
- Region: Configurabile
- Database: `nutrifit`

**Collections Create:**
```javascript
// 1. meals
{
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "user_id", "timestamp"],
      properties: {
        _id: { bsonType: "string" },
        user_id: { bsonType: "string" },
        timestamp: { bsonType: "string" },
        components: { bsonType: "array" }
      }
    }
  }
}
// Indexes: user_id, timestamp, (user_id + timestamp)

// 2. nutritional_profiles
{
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "user_id"],
      properties: {
        _id: { bsonType: "string" },
        user_id: { bsonType: "string" },
        bmr: { bsonType: "double" },
        tdee: { bsonType: "double" }
      }
    }
  }
}
// Indexes: user_id (unique)

// 3. activity_events
{
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "user_id", "timestamp"],
      properties: {
        _id: { bsonType: "string" },
        user_id: { bsonType: "string" },
        timestamp: { bsonType: "string" },
        steps: { bsonType: "int" },
        calories_out: { bsonType: "double" }
      }
    }
  }
}
// Indexes: user_id, timestamp, (user_id + timestamp)
```

**Initialization Script:**
```bash
cd backend
uv run python scripts/init_mongodb_atlas.py
```

### Dependencies

**Motor (Async MongoDB Driver):**
```toml
# pyproject.toml
[project]
dependencies = [
    "motor>=3.7.1",  # ✅ Installed
]
```

**Helper Utilities:**
```python
# infrastructure/config.py
def get_mongodb_uri() -> str:
    """Expand ${VAR} placeholders in MONGODB_URI"""
    
def get_mongodb_database() -> str:
    """Get database name with default fallback"""
```

---

## 📋 Implementation Checklist

### ✅ Completato

- [x] Unificare configurazione con `REPOSITORY_BACKEND`
- [x] Creare interfacce repository per tutti i domini
- [x] Implementare InMemory repositories
- [x] Creare factory pattern uniforme
- [x] Refactoring Activity domain (eliminare ports/adapters)
- [x] Setup MongoDB Atlas con schema validation
- [x] Installare motor driver
- [x] Creare helper MongoDB utilities
- [x] Scrivere script inizializzazione Atlas
- [x] Test coverage per InMemory (780 test passing)
- [x] Aggiornare test factory per REPOSITORY_BACKEND
- [x] **Creare MongoBaseRepository con pattern riusabili** ⭐ NEW
- [x] **Implementare MongoMealRepository completo** ⭐ NEW
- [x] **Implementare MongoProfileRepository completo** ⭐ NEW
- [x] **Aggiornare factories (rimosso NotImplementedError)** ⭐ NEW
- [x] **Fix mypy/flake8 type errors (331 files clean)** ⭐ NEW

### ⏳ Pending

- [x] ~~**MongoMealRepository**~~ ✅ COMPLETATO
  - [x] Implementare CRUD operations
  - [x] Implementare search con filtri
  - [x] Gestire mapping domain ↔ MongoDB
  - [x] Unit tests con mock
  - [x] Integration tests structure
  
- [x] ~~**MongoProfileRepository**~~ ✅ COMPLETATO
  - [x] Implementare CRUD operations
  - [x] Implementare progress tracking
  - [x] Gestire calcoli aggregati
  - [x] Unit tests con mock
  - [x] Integration tests structure
  
- [ ] **MongoActivityRepository**
  - [ ] Implementare batch event ingestion
  - [ ] Implementare snapshot/delta tracking
  - [ ] Gestire aggregazioni temporali
  - [ ] Unit tests con mock
  - [ ] Integration tests con Atlas

- [ ] **Factory Updates**
  - [x] Rimuovere NotImplementedError da meal factory ✅
  - [x] Rimuovere NotImplementedError da profile factory ✅
  - [ ] Rimuovere NotImplementedError da activity factory (pending)
  - [x] Gestire connection pooling (motor handles automatically) ✅
  - [x] Configurare retry logic (implemented in MongoBaseRepository) ✅

- [ ] **Production Readiness**
  - [ ] Performance testing
  - [ ] Load testing
  - [ ] Migration scripts (InMemory → MongoDB)
  - [ ] Backup/restore procedures
  - [ ] Monitoring e alerting

---

## �️ MongoDB Implementation (NEW - 12 Nov)

### MongoBaseRepository Pattern

**File:** `infrastructure/persistence/mongodb/base.py`

Classe astratta generica che fornisce pattern comuni per tutti i repository MongoDB:

```python
class MongoBaseRepository(ABC, Generic[TEntity]):
    """Base class for MongoDB repositories.
    
    Provides:
    - Connection management (motor AsyncIOMotorClient)
    - Document ↔ Entity mapping (abstract methods)
    - Error handling with logging
    - UUID/datetime conversion helpers
    - Common CRUD operations (_find_one, _update_one, etc.)
    """
    
    @property
    @abstractmethod
    def collection_name(self) -> str:
        """MongoDB collection name."""
        
    @abstractmethod
    def to_document(self, entity: TEntity) -> Dict[str, Any]:
        """Convert domain entity to MongoDB document."""
        
    @abstractmethod
    def from_document(self, doc: Dict[str, Any]) -> TEntity:
        """Convert MongoDB document to domain entity."""
```

**Key Features:**
- 🔌 **Auto-connection**: Legge `MONGODB_URI` da env
- 🔄 **Retry logic**: Error handling con logging
- 📝 **Type-safe**: Generic[TEntity] per type checking
- 🛠️ **Helper methods**: UUID/datetime conversion
- 🔒 **Thread-safe**: Motor gestisce connection pooling

### MongoMealRepository

**File:** `infrastructure/persistence/mongodb/meal_repository.py`

Implementazione completa con:
- ✅ CRUD operations (save, get_by_id, delete)
- ✅ Pagination (limit/offset)
- ✅ Date range queries
- ✅ MealEntry embedded documents
- ✅ UUID string conversion
- ✅ Timezone-aware datetime handling

**Document Schema:**
```javascript
{
  "_id": "uuid-string",
  "user_id": "string",
  "timestamp": "ISO8601",
  "meal_type": "LUNCH",
  "entries": [
    {
      "id": "uuid-string",
      "name": "Pasta",
      "quantity_g": 150.0,
      "calories": 200,
      ...
    }
  ],
  "total_calories": 200,
  ...
}
```

### MongoProfileRepository

**File:** `infrastructure/persistence/mongodb/profile_repository.py`

Implementazione con:
- ✅ NutritionalProfile CRUD
- ✅ UserData nested object mapping
- ✅ ProgressRecord array handling
- ✅ Enum ActivityLevel conversion
- ✅ find_by_user_id for profile lookup

**Document Schema:**
```javascript
{
  "_id": "profile-id",
  "user_id": "string",
  "user_data": {
    "weight": 75.0,
    "height": 175.0,
    "age": 30,
    "sex": "M",
    "activity_level": "moderate"
  },
  "goal": "cut",
  "bmr": 1850.0,
  "tdee": 2567.5,
  "progress_history": [
    {
      "record_id": "uuid",
      "date": "2025-11-12",
      "weight": 74.5,
      ...
    }
  ]
}
```

### Type Safety & Linting

**All checks passing:**
- ✅ Mypy: 331 files, 0 errors
- ✅ Flake8: 0 errors
- ✅ 780 unit tests passing

**Key fixes applied:**
- Type parameters for `AsyncIOMotorClient[Dict[str, Any]]`
- Type parameters for `AsyncIOMotorCollection[Dict[str, Any]]`
- `Tuple[str, int]` for sort specifications
- `X | None` instead of `Optional[X]` (Python 3.10+)

---

## �🎯 Stima Implementazione MongoDB

### Effort per Repository

| Repository | Complessità | Stima | Status | Tempo Effettivo |
|-----------|-------------|-------|--------|-----------------|
| MongoMealRepository | Media | 2-3h | ✅ DONE | ~2.5h |
| MongoProfileRepository | Media | 2-3h | ✅ DONE | ~2h |
| MongoActivityRepository | Alta | 3-4h | ⏳ Pending | - |
| Testing + Integration | Media | 2-3h | ✅ DONE | ~1h |
| **TOTALE** | - | **10-13h** | **66% Complete** | **~5.5h / 10h** |

### Ordine Consigliato

1. **MongoMealRepository** (più semplice)
   - CRUD base ben definito
   - Entità semplice (Meal + Components)
   - Pochi edge cases

2. **MongoProfileRepository** (medio)
   - CRUD + calcoli aggregati
   - Progress records con timeline
   - Più business logic

3. **MongoActivityRepository** (più complesso)
   - Dual nature (Events + Snapshots)
   - Batch operations
   - Aggregazioni temporali complesse
   - Delta calculations

---

## 🔄 Migration Path

### Step 1: Development (Current)

```bash
REPOSITORY_BACKEND=inmemory  # Fast, no external deps
```

### Step 2: Testing (After Implementation)

```bash
REPOSITORY_BACKEND=mongodb
MONGODB_URI=mongodb://localhost:27017  # Local MongoDB
```

### Step 3: Staging

```bash
REPOSITORY_BACKEND=mongodb
MONGODB_URI=mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@staging-cluster
```

### Step 4: Production

```bash
REPOSITORY_BACKEND=mongodb
MONGODB_URI=mongodb+srv://${MONGODB_USER}:${MONGODB_PASSWORD}@prod-cluster
```

**No Downtime Migration:**
1. Deploy con REPOSITORY_BACKEND=inmemory (nessun cambio)
2. Run migration script per popolare MongoDB da InMemory
3. Validare data consistency
4. Switch REPOSITORY_BACKEND=mongodb
5. Monitor performance e errors

---

## 📊 Test Status

### Test Summary (12 Nov 2025 - Updated 13:00)

```
======================== test session starts =========================
collected 780 items

780 passed, 0 failed
```

**Coverage per Dominio:**

| Dominio | Unit Tests | Integration Tests | MongoDB Tests |
|---------|-----------|------------------|---------------|
| Meal | ✅ 150+ | ✅ 15+ | ✅ 12 (factory + repo) |
| NutritionalProfile | ✅ 120+ | ✅ 10+ | ✅ 12 (factory + repo) |
| Activity | ✅ 56+ (14 new) | ✅ 7+ | ⏳ 0 |
| **TOTALE** | **✅ 326+** | **✅ 32+** | **✅ 24** |

---

## 🚀 Next Steps

### ✅ Completed This Session

1. ✅ Implementato `MongoMealRepository` con pattern riusabile
2. ✅ Implementato `MongoProfileRepository` con mapping completo
3. ✅ Creato `MongoBaseRepository` per pattern comuni
4. ✅ Aggiornate factories (rimosso NotImplementedError)
5. ✅ Fix mypy/flake8 (331 files clean)
6. ✅ 780 test passing

### Immediate (Next Session)

1. **Implementare `MongoActivityRepository`** (3-4h stimate)
   - Dual nature: Events + Snapshots
   - Batch ingestion con deduplication
   - Delta calculation
   - Aggregazioni temporali
2. Aggiornare activity factory
3. Integration tests per Activity
4. Validazione end-to-end con MongoDB Atlas

### Short Term

1. Performance benchmarking con dataset reale
2. Load testing (concurrent operations)
3. Migration scripts (InMemory → MongoDB)
4. Backup/restore procedures

### Medium Term

1. Migration automation scripts
2. Production monitoring setup
3. Backup/restore procedures
4. Performance optimization

---

## 📚 References

- [Commit 61fb528](https://github.com/giamma80/Nutrifit-mobile/commit/61fb528) - Architecture unification
- [MongoDB Atlas](https://www.mongodb.com/atlas) - Cluster setup
- [Motor Documentation](https://motor.readthedocs.io/) - Async driver
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html) - Martin Fowler

---

**Last Updated:** 12 Novembre 2025  
**Maintainer:** Gianmarco Morelli
