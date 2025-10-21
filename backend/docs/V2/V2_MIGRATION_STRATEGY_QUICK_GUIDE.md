# 🎯 V2 Migration Strategy - Quick Reference

**Data:** 20 Ottobre 2025  
**Strategia:** Parallel Development in `backend/v2/` folder  

---

## 📌 TL;DR

✅ **Tutto il nuovo codice** va in `backend/v2/` (isolato dal vecchio)  
✅ **V1 rimane attivo** durante lo sviluppo (zero downtime)  
✅ **Switch atomico** a fine refactoring con feature flag  
✅ **Rollback immediato** se necessario  

---

## 🗂️ Classificazione Codice

### 🟢 A) MANTIENI PER COMPATIBILITÀ (Elimina dopo)

**Codice V1 deprecato ma necessario durante transizione**

```
backend/
├── graphql/mutations/meal_mutations.py    # ⚠️ logMeal() - DEPRECATO
├── graphql/queries/meal_queries.py        # ⚠️ product() - DEPRECATO  
└── domain/meal/meal_service.py            # ⚠️ Vecchia logica - DEPRECATO
```

**Azioni**:
- ✅ Aggiungi `@deprecated` decorator
- ✅ Logga warning
- ⏰ **Elimina in Fase 11** (dopo switch)

---

### 🔵 B) MANTIENI INALTERATO (No Touch)

**Codice fuori scope del refactoring**

```
backend/
├── domain/activity/                       # ✅ Activity tracking
├── graphql/mutations/activity_mutations.py # ✅ Activity mutations
├── graphql/queries/activity_queries.py    # ✅ Activity queries
├── infrastructure/logging/                # ✅ Structlog config
└── api/middleware.py                      # ✅ CORS, auth
```

**Azioni**:
- ❌ **NO modifiche**
- ✅ Importa in V2 se necessario (shared config)

---

### 🟡 C) MODIFICA IN V1 (Extend)

**Codice da estendere per supportare V2**

```
backend/
├── graphql/schema.py                      # 🔧 Merge V1+V2 resolvers
├── graphql/context.py                     # 🔧 Add V2 DI container
├── infrastructure/config/settings.py      # 🔧 Add V2 env vars
└── api/main.py                            # 🔧 Mount V2 services
```

**Azioni**:
- ✅ **AGGIUNGI** accanto al vecchio (no replace)
- ✅ Feature flag `enable_v2_meal_api`
- ✅ Testa che V1 continui a funzionare

**Esempio - schema.py**:
```python
# Merge V1 + V2
from .queries.meal_queries import MealQueriesV1
from .v2.queries.meal_queries import MealQueriesV2

@strawberry.type
class Query(MealQueriesV1, MealQueriesV2, ActivityQueries):
    pass
```

---

### 🟢 D) CODICE NUOVO (V2 Folder)

**Tutto il refactoring in isolamento**

```
backend/v2/                                # 🆕 TUTTO QUI
├── domain/                                # Business logic
│   ├── meal/
│   │   ├── recognition/                   # AI Vision
│   │   ├── nutrition/                     # USDA enrichment
│   │   ├── barcode/                       # OpenFoodFacts
│   │   ├── orchestration/                 # Coordinators
│   │   └── persistence/                   # Repository interfaces
│   └── shared/
│
├── infrastructure/                        # External integrations
│   ├── database/                          # MongoDB
│   ├── cache/                             # Redis
│   ├── ai/                                # OpenAI client
│   └── external_apis/                     # USDA, OpenFoodFacts
│
├── application/                           # Use cases
│   └── meal/
│       ├── analyze_photo.py
│       ├── analyze_barcode.py
│       ├── analyze_description.py
│       └── confirm_meal.py
│
├── graphql/                               # V2 resolvers
│   ├── queries/
│   │   ├── food_recognition.py           # recognizeFood
│   │   ├── nutrition.py                  # enrichNutrients
│   │   └── barcode_search.py             # searchFoodByBarcode
│   └── mutations/
│       ├── analyze_meal.py               # analyze*
│       └── confirm_meal.py               # confirm*
│
├── tests/                                 # ⚠️ CRITICO: Tests V2 qui
│   ├── unit/                              #            NON in backend/tests/
│   ├── integration/
│   └── e2e/
│
└── docs/                                  # ⚠️ CRITICO: Docs V2 qui
    ├── architecture.md                    #            NON in backend/docs/
    ├── api_examples.md
    └── testing_guide.md
```

**Azioni**:
- ✅ Sviluppa in completo isolamento
- ✅ Non dipendere da V1 (eccetto shared config)
- ✅ Test coverage 100% prima del merge

---

## 🔄 Workflow di Sviluppo

### Fase 0-9: Sviluppo Parallelo

```
backend/
├── v2/              # 🆕 Sviluppo attivo qui
├── domain/          # 🔵 V1 - No touch (activity)
├── graphql/         # 🟡 V1 - Estendi (add V2 resolvers)
└── api/             # 🟡 V1 - Estendi (mount V2)
```

**V1 continua a servire tutto il traffico**  
**V2 esposto solo con feature flag OFF**

### Fase 10: Testing Parallelo

```python
# .env
ENABLE_V2_MEAL_API=false  # Default: V1 only

# Gradual rollout
ENABLE_V2_MEAL_API=true   # Internal testing
# → 10% users → 50% users → 100% users
```

### Fase 11: Switch & Cleanup

**Step 1**: Enable V2
```bash
ENABLE_V2_MEAL_API=true
```

**Step 2**: Monitor (1 settimana)

**Step 3**: Cleanup
```bash
# Promuovi V2 a root
mv backend/v2/* backend/
rmdir backend/v2

# Elimina V1 deprecato
rm backend/graphql/mutations/meal_mutations.py  # logMeal
rm backend/graphql/queries/meal_queries_v1.py   # product
rm backend/domain/meal/meal_service.py          # old logic
```

---

## 🚫 Import Rules

### ✅ V2 può importare da V1 (shared only)

```python
# OK
from backend.infrastructure.logging import structlog_config
from backend.infrastructure.config import settings
from backend.api.middleware import auth_middleware
```

### ❌ V2 NON deve importare da V1 (domain)

```python
# NEVER
from backend.domain.meal import MealService
from backend.models import MealEntry
```

### ❌ V1 NON deve importare da V2

```python
# NEVER
from backend.v2.domain.meal import ...
```

**Eccezione**: `graphql/schema.py` può importare entrambi per merge

---

## 💾 Database Strategy

### Opzione A: Separate databases (RACCOMANDATO)

```yaml
# docker-compose.yml
mongodb-v1:
  ports: ["27017:27017"]  # Legacy
  
mongodb-v2:
  ports: ["27018:27017"]  # V2
```

### Opzione B: Same DB, different collections

```javascript
// V1
db.meals_v1
db.activity_events

// V2
db.meals
db.meal_analysis
```

---

## 🎯 GraphQL Naming

### Durante sviluppo (V1 + V2 coesistono)

```graphql
type Query {
  # V2 - New names
  recognizeFood(...)          # 🆕
  enrichNutrients(...)        # 🆕
  searchFoodByBarcode(...)    # 🆕 (rename of product)
  
  # V1 - Old names (deprecated)
  product(...)                # ⚠️ DEPRECATO
  mealEntries(...)            # ✅ Keep
}

type Mutation {
  # V2 - New workflow
  analyzeMealPhoto(...)       # 🆕
  confirmMealPhoto(...)       # 🆕
  
  # V1 - Old (deprecated)  
  logMeal(...)                # ⚠️ DEPRECATO
  updateMeal(...)             # ✅ Keep (V2 reimplementa)
}
```

---

## 🔙 Rollback Plan

Se V2 ha problemi:

**Step 1**: Disable V2 (instant rollback)
```bash
ENABLE_V2_MEAL_API=false
```

**Step 2**: Investigate & fix

**Step 3**: Re-enable gradualmente

**Worst case**: Delete `backend/v2/` folder → V1 still works!

---

## ✅ Checklist Pre-Switch

Prima di abilitare V2 in produzione:

- [ ] ✅ V2 test coverage >90%
- [ ] ✅ V1 API ancora funzionante
- [ ] ✅ Feature flag testata (ON/OFF)
- [ ] ✅ Data migration script pronto
- [ ] ✅ Rollback plan documentato
- [ ] ✅ Monitoring attivo su V2
- [ ] ✅ Performance benchmark V2 > V1
- [ ] ✅ Breaking changes comunicati
- [ ] ✅ Documentation aggiornata

---

## 📋 Summary Table

| Categoria | Dove | Azione | Elimina Quando |
|-----------|------|--------|----------------|
| **A) Compatibilità** | V1 root | Depreca | Fase 11 |
| **B) Inalterato** | V1 root | No touch | Mai |
| **C) Modifica** | V1 root | Extend | - |
| **D) Nuovo** | `v2/` | Sviluppa | Promuovi a root |

---

## 🎓 Best Practices

1. **Isolamento**: V2 è completamente indipendente
2. **Tests in v2/**: TUTTI i test V2 vanno in `backend/v2/tests/` (NON in `backend/tests/`)
3. **Docs in v2/**: TUTTA la documentazione V2 va in `backend/v2/docs/` (NON in `backend/docs/`)
4. **Testing**: Test V2 in isolamento prima del merge
5. **Feature Flag**: Controllo granulare del rollout
6. **Monitoring**: Metriche separate V1 vs V2
7. **Documentation**: Aggiorna durante sviluppo, non dopo
8. **Communication**: Avvisa team dei breaking changes

**Rationale tests/docs in v2/**:
- ✅ Isolamento completo del refactoring
- ✅ Nessun conflitto con test/docs V1
- ✅ Facile promozione a root in Fase 11
- ✅ Clear ownership (test V2 testano solo V2)


---

## 🔗 Link Utili

- **Roadmap completa**: `NUTRIFIT_MEAL_REFACTOR_COMPLETE.md`
- **Sezione dettagliata**: Vedi "📁 STRATEGIA MIGRAZIONE V1 → V2"
- **Repository**: https://github.com/giamma80/Nutrifit-mobile

---

**🎉 Questa strategia garantisce zero downtime e rollback sicuro!**
