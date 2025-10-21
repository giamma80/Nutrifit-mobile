# ⚠️ V2 CRITICAL REMINDERS

**LETTO PRIMA DI INIZIARE IL REFACTORING**

---

## 🚨 ERRORI COMUNI DA EVITARE

### ❌ Errore #1: Tests in Backend Root

**SBAGLIATO**:
```
backend/
├── tests/
│   └── test_meal_v2.py          ❌ NO! Non qui!
└── v2/
    └── domain/
```

**CORRETTO**:
```
backend/
├── tests/                        ✅ Solo test V1 (activity)
│   └── test_activity.py
└── v2/
    ├── domain/
    └── tests/                    ✅ Test V2 qui!
        └── unit/
            └── test_meal.py
```

**Perché**: Tenere i test V2 in `backend/tests/` crea:
- Accoppiamento con V1
- Difficoltà nel capire cosa testa cosa
- Problemi durante la promozione a root

---

### ❌ Errore #2: Docs in Backend Root

**SBAGLIATO**:
```
backend/
├── docs/
│   └── meal_v2_api.md           ❌ NO! Non qui!
└── v2/
    └── domain/
```

**CORRETTO**:
```
backend/
├── docs/                        ✅ Solo docs V1 generali
│   └── activity_api.md
└── v2/
    ├── domain/
    └── docs/                    ✅ Docs V2 qui!
        └── meal_api.md
```

**Perché**: Docs V2 in root crea:
- Confusione su quale documentazione leggere
- Difficoltà nel tracciare cosa documenta V2 vs V1
- Merge complicato in Fase 11

---

### ❌ Errore #3: Import V1 Domain da V2

**SBAGLIATO**:
```python
# backend/v2/domain/meal/service.py

from backend.domain.meal.meal_service import MealService  ❌ NO!

class NewMealService:
    def __init__(self, old_service: MealService):
        self.old = old_service  # Accoppiamento con V1!
```

**CORRETTO**:
```python
# backend/v2/domain/meal/service.py

# V2 è completamente indipendente ✅
# Non importa MAI da backend.domain.meal

class NewMealService:
    def __init__(self, recognition_service, nutrition_service):
        # Solo dipendenze V2
        pass
```

**Eccezioni** (shared OK):
```python
# backend/v2/application/meal/analyze.py

# Questi import sono OK ✅
from backend.infrastructure.config import settings      # Shared config
from backend.infrastructure.logging import get_logger  # Shared logging
```

---

### ❌ Errore #4: Modificare Files V1 Non Necessari

**SBAGLIATO**:
```python
# backend/domain/activity/activity_service.py

# ❌ NO! Questo è V1 mantieni inalterato
def process_activity(self, data):
    # Aggiungo nuova logica V2...  # ERRORE!
```

**CORRETTO**:
- ✅ Non toccare `backend/domain/activity/` (mantieni inalterato)
- ✅ Non toccare `backend/graphql/mutations/activity_mutations.py`
- ✅ Modifica SOLO i "merge points": `schema.py`, `context.py`, `main.py`, `settings.py`

---

### ❌ Errore #5: Dimenticare Feature Flag

**SBAGLIATO**:
```python
# backend/api/main.py

# ❌ NO! V2 sempre attivo
from backend.v2.graphql.schema import schema_v2
app.add_route("/graphql", GraphQLApp(schema=schema_v2))
```

**CORRETTO**:
```python
# backend/api/main.py

# ✅ Feature flag per controllo
from backend.infrastructure.config import settings

if settings.enable_v2_meal_api:
    from backend.v2.graphql.schema import schema_v2
    schema = merge_schemas(schema_v1, schema_v2)
else:
    schema = schema_v1  # Rollback sicuro

app.add_route("/graphql", GraphQLApp(schema=schema))
```

---

## ✅ CHECKLIST PRIMA DI COMMITTARE

Ogni volta che committi codice V2, verifica:

- [ ] ✅ Nuovo codice è in `backend/v2/` (non in backend/ root)
- [ ] ✅ Test V2 sono in `backend/v2/tests/` (non in backend/tests/)
- [ ] ✅ Docs V2 sono in `backend/v2/docs/` (non in backend/docs/)
- [ ] ✅ Import V2 NON usa `from backend.domain.meal` (vecchio)
- [ ] ✅ Import V2 usa solo shared config/logging da V1
- [ ] ✅ Files V1 non toccati (eccetto merge points)
- [ ] ✅ Feature flag `enable_v2_meal_api` implementato
- [ ] ✅ Test V2 passano in isolamento
- [ ] ✅ V1 ancora funzionante (test V1 passano)

---

## 📂 QUICK REFERENCE: DOVE VA COSA

| Cosa | Dove VA | Dove NON va |
|------|---------|-------------|
| Domain logic V2 | `v2/domain/meal/` | ❌ `backend/domain/meal/` |
| Infrastructure V2 | `v2/infrastructure/` | ❌ `backend/infrastructure/` |
| Application V2 | `v2/application/meal/` | ❌ `backend/application/meal/` |
| GraphQL V2 | `v2/graphql/` | ❌ `backend/graphql/` |
| **Tests V2** | `v2/tests/` | ❌ `backend/tests/` |
| **Docs V2** | `v2/docs/` | ❌ `backend/docs/` |
| Config V2 vars | `backend/infrastructure/config/settings.py` | ✅ Extend in-place |
| DI Container V2 | `backend/graphql/context.py` | ✅ Extend in-place |
| FastAPI mount | `backend/api/main.py` | ✅ Extend in-place |

---

## 🎯 MANTIENI QUESTA REGOLA SEMPLICE

> **"Se è nuovo per il refactoring meal, va in `v2/`"**
> 
> **"Se è shared (config, logging), estendi in V1"**
> 
> **"Se è V1 activity/sync, NON TOCCARE"**

---

## 🔗 Link Utili

- **Roadmap Completa**: `NUTRIFIT_MEAL_REFACTOR_COMPLETE.md`
- **Quick Guide**: `V2_MIGRATION_STRATEGY_QUICK_GUIDE.md`
- **Sezione Dettagliata**: Cerca "📁 STRATEGIA MIGRAZIONE V1 → V2"

---

## 💡 IN DUBBIO?

Se non sei sicuro dove mettere qualcosa, chiediti:

1. **È nuovo codice per meal refactor?** → `v2/`
2. **È test per nuovo codice meal?** → `v2/tests/`
3. **È documentazione nuovo meal API?** → `v2/docs/`
4. **È config/logging condiviso?** → Estendi in V1
5. **È codice activity esistente?** → NON TOCCARE (V1)

---

**🎉 Seguendo queste regole, il refactoring sarà pulito e sicuro!**
