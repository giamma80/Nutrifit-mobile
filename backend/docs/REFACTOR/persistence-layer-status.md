# 🗄️ Persistence Layer - Stato Attuale

**Version:** 2.0  
**Date:** 12 Novembre 2025  
**Status:** ✅ Architettura Unificata - ⏳ MongoDB Implementation Pending

---

## 🎯 Executive Summary

Il layer di persistenza è stato **completamente unificato** attraverso tutti i domini con un'architettura coerente basata sul pattern Repository + Factory. Tutti e tre i domini (Meal, NutritionalProfile, Activity) ora usano la stessa configurazione e lo stesso pattern architetturale.

**Stato Corrente:**
- ✅ **Architettura Unificata** - Pattern coerente tra tutti i domini
- ✅ **Configurazione Globale** - Singola variabile `REPOSITORY_BACKEND`
- ✅ **InMemory Funzionante** - Tutti i test passano (922/922)
- ✅ **MongoDB Atlas Setup** - Database configurato e pronto
- ⏳ **MongoDB Repositories** - Implementazione pendente (Phase 7.1)

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
- ⏳ MongoDB: `NotImplementedError` - Implementation pending

**Test Coverage:**
- ✅ Unit tests: Factory + InMemory
- ⏳ Integration tests: MongoDB (pending)

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
- ⏳ MongoDB: `NotImplementedError` - Implementation pending

**Test Coverage:**
- ✅ Unit tests: Factory + InMemory
- ⏳ Integration tests: MongoDB (pending)

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
- [x] Test coverage per InMemory (922 test passing)
- [x] Aggiornare test factory per REPOSITORY_BACKEND

### ⏳ Pending (Phase 7.1)

- [ ] **MongoMealRepository**
  - [ ] Implementare CRUD operations
  - [ ] Implementare search con filtri
  - [ ] Gestire mapping domain ↔ MongoDB
  - [ ] Unit tests con mock
  - [ ] Integration tests con Atlas
  
- [ ] **MongoProfileRepository**
  - [ ] Implementare CRUD operations
  - [ ] Implementare progress tracking
  - [ ] Gestire calcoli aggregati
  - [ ] Unit tests con mock
  - [ ] Integration tests con Atlas
  
- [ ] **MongoActivityRepository**
  - [ ] Implementare batch event ingestion
  - [ ] Implementare snapshot/delta tracking
  - [ ] Gestire aggregazioni temporali
  - [ ] Unit tests con mock
  - [ ] Integration tests con Atlas

- [ ] **Factory Updates**
  - [ ] Rimuovere NotImplementedError da meal factory
  - [ ] Rimuovere NotImplementedError da profile factory
  - [ ] Rimuovere NotImplementedError da activity factory
  - [ ] Gestire connection pooling
  - [ ] Configurare retry logic

- [ ] **Production Readiness**
  - [ ] Performance testing
  - [ ] Load testing
  - [ ] Migration scripts (InMemory → MongoDB)
  - [ ] Backup/restore procedures
  - [ ] Monitoring e alerting

---

## 🎯 Stima Implementazione MongoDB

### Effort per Repository

| Repository | Complessità | Stima | Priorità |
|-----------|-------------|-------|----------|
| MongoMealRepository | Media | 2-3h | 🔴 Alta |
| MongoProfileRepository | Media | 2-3h | 🟡 Media |
| MongoActivityRepository | Alta | 3-4h | 🟢 Bassa |
| Testing + Integration | Media | 2-3h | 🔴 Alta |
| **TOTALE** | - | **10-13h** | - |

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

### Test Summary (12 Nov 2025)

```
======================== test session starts =========================
collected 942 items

922 passed, 20 skipped, 0 failed
```

**Coverage per Dominio:**

| Dominio | Unit Tests | Integration Tests | MongoDB Tests |
|---------|-----------|------------------|---------------|
| Meal | ✅ 150+ | ✅ 15+ | ⏳ 0 |
| NutritionalProfile | ✅ 120+ | ✅ 10+ | ⏳ 0 |
| Activity | ✅ 56+ (14 new) | ✅ 7+ | ⏳ 0 |
| **TOTALE** | **✅ 326+** | **✅ 32+** | **⏳ 0** |

---

## 🚀 Next Steps

### Immediate (This Sprint)

1. Implementare `MongoMealRepository`
2. Aggiornare meal factory per rimuovere NotImplementedError
3. Scrivere integration tests MongoDB per Meal
4. Documentare pattern per altri domini

### Short Term (Next Sprint)

1. Implementare `MongoProfileRepository`
2. Implementare `MongoActivityRepository`
3. Complete test coverage MongoDB
4. Performance benchmarking

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
