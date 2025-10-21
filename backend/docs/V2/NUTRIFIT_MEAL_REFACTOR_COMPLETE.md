# 🚀 Nutrifit Meal System - Complete Refactor Roadmap

**Data Creazione:** 18 Ottobre 2025  
**Versione Target:** v0.7.0  
**Repository:** https://github.com/giamma80/Nutrifit-mobile  
**Strategia:** Clean Architecture + Domain-Driven Design + Repository Pattern

---

## 📋 EXECUTIVE SUMMARY

### Obiettivo del Refactoring

Ristrutturazione completa del sistema di analisi meal per supportare **3 modalità di input atomiche**:

1. **📷 Photo Analysis** → AI Vision recognition + USDA nutrient enrichment
2. **🔍 Barcode Scan** → Direct product lookup da OpenFoodFacts
3. **📝 Text Description** → AI text extraction + USDA enrichment

### Architettura Target

```
┌─────────────────────────────────────────────────────────────┐
│                     GraphQL API Layer                        │
│  (Queries: atomic services | Mutations: orchestration)       │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                   Application Layer                          │
│  • Orchestrators (analyze* mutations)                        │
│  • Service Coordinators                                      │
│  • Transaction Management                                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                    Domain Layer                              │
│  • Recognition Service (AI Vision)                           │
│  • Nutrition Service (USDA enrichment)                       │
│  • Barcode Service (OpenFoodFacts)                          │
│  • Text Extraction Service (AI)                              │
│  • Business Logic & Value Objects                            │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                 Infrastructure Layer                         │
│  • MongoDB Repository (meals, analysis, sync data)           │
│  • Redis Cache (USDA, OpenAI, barcode responses)            │
│  • External API Clients (OpenAI, USDA, OpenFoodFacts)       │
│  • Rate Limiters & Circuit Breakers                          │
└─────────────────────────────────────────────────────────────┘
```

### Principi Architetturali

1. **Separation of Concerns**: Ogni layer ha responsabilità precise
2. **Dependency Inversion**: Domain layer non dipende da infrastructure
3. **Atomic Services**: Query GraphQL per funzionalità riutilizzabili
4. **Orchestration Pattern**: Mutation GraphQL coordinano servizi atomici
5. **Repository Pattern**: Astrazione persistenza con implementazione MongoDB
6. **Two-Phase Commit**: Analisi temporanea → Revisione utente → Conferma persistenza

### Benefici Attesi

- ✅ **Performance**: -30% costi API, -25% latency media (cache optimization)
- ✅ **Reliability**: 0% parsing errors (structured output vs prompt parsing)
- ✅ **Maintainability**: Service atomicity, clean boundaries, testability 100%
- ✅ **Scalability**: Repository pattern ready per scaling horizontale
- ✅ **User Experience**: Two-phase workflow con preview e conferma

### Breaking Changes

⚠️ **GraphQL Breaking Changes**:
- `logMeal` mutation **RIMOSSA** (deprecata, sostituita da workflow analyze→confirm)
- Query `product(barcode)` **RINOMINATA** a `searchFoodByBarcode(barcode)`
- Tutti i client devono migrare al nuovo workflow

---

## 🎯 ARCHITETTURA DETTAGLIATA

### GraphQL API Schema Evolution

#### 1. Atomic Services (Queries)

```graphql
type Query {
  # 🆕 Servizio atomico: AI Vision recognition
  # Input: URL immagine + hint opzionale
  # Output: Lista cibi riconosciuti con confidence
  recognizeFood(
    imageUrl: String!
    hint: String
  ): FoodRecognitionResult!
  
  # 🆕 Servizio atomico: USDA nutrient enrichment  
  # Input: Label cibo + quantità grammi
  # Output: Profilo nutrizionale completo per quella quantità
  enrichNutrients(
    label: String!
    quantityG: Float!
  ): NutrientProfile!
  
  # ✏️ RENAME: da 'product' a 'searchFoodByBarcode'
  # Mantiene stesso output type: Product
  searchFoodByBarcode(barcode: String!): Product!
  
  # ✅ MANTIENI (esistente)
  mealEntries(
    limit: Int! = 20
    after: String = null
    before: String = null
    userId: String = null
  ): [MealEntry!]!
  
  # ✅ MANTIENI (esistente)
  dailySummary(
    date: String!
    userId: String = null
  ): DailySummary!
}

# 🆕 Nuovo type: risultato recognition
type FoodRecognitionResult {
  items: [RecognizedFoodItem!]!
  dishName: String          # Nome piatto complessivo (es. "Pasta carbonara")
  confidence: Float!        # Confidence media recognition
  processingTimeMs: Int!
}

type RecognizedFoodItem {
  label: String!            # Identificatore (es. "pasta", "chicken")
  displayName: String!      # Nome user-friendly (es. "Spaghetti", "Pollo")
  quantityG: Float!         # Quantità stimata in grammi
  confidence: Float!        # 0.0 - 1.0
  category: String          # Categoria USDA (es. "grains", "meat")
}

# 🆕 Nuovo type: profilo nutrienti
type NutrientProfile {
  # Macronutrienti (per quantità richiesta)
  calories: Int!
  protein: Float!
  carbs: Float!
  fat: Float!
  
  # Micronutrienti opzionali
  fiber: Float
  sugar: Float
  sodium: Float
  
  # Metadata
  source: NutrientSource!
  confidence: Float!
  quantityG: Float!         # Quantità di riferimento
}

enum NutrientSource {
  USDA                      # Database USDA (high confidence)
  BARCODE_DB               # OpenFoodFacts (very high confidence)
  CATEGORY_PROFILE         # Profilo categoria fallback (medium confidence)
  AI_ESTIMATE              # Stima AI (low confidence)
}
```

#### 2. Orchestration Mutations (Analyze)

```graphql
type Mutation {
  # ✏️ REFACTOR INTERNO - mantiene firma esistente
  # Coordina: recognizeFood + enrichNutrients per ogni item
  # NON salva su DB, solo storage temporaneo
  analyzeMealPhoto(
    input: AnalyzeMealPhotoInput!
  ): MealPhotoAnalysis!
  
  # 🆕 Nuovo: analisi da barcode
  # Coordina: searchFoodByBarcode + scaling nutrienti
  # NON salva su DB, solo storage temporaneo
  analyzeMealBarcode(
    input: AnalyzeMealBarcodeInput!
  ): MealPhotoAnalysis!
  
  # 🆕 Nuovo: analisi da descrizione testuale
  # Coordina: AI text extraction + enrichNutrients per ogni item
  # NON salva su DB, solo storage temporaneo
  analyzeMealDescription(
    input: AnalyzeMealDescriptionInput!
  ): MealPhotoAnalysis!
}

# Input types
input AnalyzeMealPhotoInput {
  photoUrl: String!
  userId: String!
  dishHint: String          # Hint per migliorare recognition
  idempotencyKey: String    # Per retry sicuri
}

input AnalyzeMealBarcodeInput {
  barcode: String!
  userId: String!
  quantityG: Float!         # Utente specifica quantità consumata
  idempotencyKey: String
}

input AnalyzeMealDescriptionInput {
  description: String!      # Es: "Pizza margherita e insalata"
  userId: String!
  idempotencyKey: String
}

# Output type (ESISTENTE - mantiene struttura)
type MealPhotoAnalysis {
  id: String!                           # analysisId per confirm
  userId: String!
  status: MealPhotoAnalysisStatus!      # PENDING (awaiting confirmation)
  createdAt: String!
  source: String!                        # "PHOTO" | "BARCODE" | "DESCRIPTION"
  
  # Dati analisi
  photoUrl: String                       # Solo per source=PHOTO
  dishName: String                       # Nome piatto riconosciuto
  items: [MealPhotoItemPrediction!]!    # Items già enriched con nutrienti
  totalCalories: Int                     # Somma calorie items
  
  # Metadata & errors
  rawJson: String                        # Debug: response raw da AI
  idempotencyKeyUsed: String
  analysisErrors: [MealPhotoAnalysisError!]!
  failureReason: MealPhotoAnalysisErrorCode
}

enum MealPhotoAnalysisStatus {
  PENDING       # Analisi completata, attende conferma utente
  COMPLETED     # Confermata e persistita (dopo confirmMeal*)
  FAILED        # Analisi fallita
}

# ESISTENTE - mantiene struttura
type MealPhotoItemPrediction {
  label: String!
  displayName: String
  confidence: Float!
  quantityG: Float
  
  # Nutrienti (già enriched!)
  calories: Int
  protein: Float
  carbs: Float
  fat: Float
  fiber: Float
  sugar: Float
  sodium: Float
  
  enrichmentSource: String              # "USDA" | "BARCODE_DB" | "CATEGORY"
  calorieCorrected: Boolean             # Se AI ha corretto le calorie
}
```

#### 3. Persistence Mutations (Confirm)

```graphql
type Mutation {
  # ✅ ESISTE GIÀ - mantiene firma
  # Legge analisi da storage temporaneo
  # Salva items accettati come MealEntry in MongoDB
  confirmMealPhoto(
    input: ConfirmMealPhotoInput!
  ): ConfirmMealPhotoResult!
  
  # 🆕 Nuovo: conferma barcode (stesso output!)
  confirmMealBarcode(
    input: ConfirmMealInput!
  ): ConfirmMealPhotoResult!
  
  # 🆕 Nuovo: conferma description (stesso output!)
  confirmMealDescription(
    input: ConfirmMealInput!
  ): ConfirmMealPhotoResult!
}

# Input types
input ConfirmMealPhotoInput {
  analysisId: String!
  acceptedIndexes: [Int!]!  # Indici items da confermare (0-based)
  userId: String!
  idempotencyKey: String
}

input ConfirmMealInput {
  analysisId: String!
  acceptedIndexes: [Int!]!
  userId: String!
  idempotencyKey: String
}

# Output type (ESISTENTE - mantiene struttura)
type ConfirmMealPhotoResult {
  analysisId: String!
  createdMeals: [MealEntry!]!   # 1 o più pasti persistiti in MongoDB
}

# ESISTENTE - mantiene struttura
type MealEntry {
  id: String!
  userId: String!
  name: String!
  quantityG: Float!
  timestamp: String!
  barcode: String
  idempotencyKey: String
  nutrientSnapshotJson: String
  
  # Nutrienti denormalizzati (per query veloci)
  calories: Int
  protein: Float
  carbs: Float
  fat: Float
  fiber: Float
  sugar: Float
  sodium: Float
  
  imageUrl: String              # Link a foto originale
}
```

#### 4. CRUD Mutations

```graphql
type Mutation {
  # ✅ MANTIENI
  updateMeal(input: UpdateMealInput!): MealEntry!
  
  # ✅ MANTIENI
  deleteMeal(id: String!): Boolean!
  
  # ❌ ELIMINA (breaking change)
  # logMeal(input: LogMealInput!): MealEntry!
  # Sostituito da workflow: analyzeMeal* → confirmMeal*
}

input UpdateMealInput {
  id: String!
  name: String = null
  quantityG: Float = null
  timestamp: String = null
  barcode: String = null
  userId: String = null
}
```

---

## 📊 USER FLOWS DETTAGLIATI

### Flow 1: Meal Photo Analysis 📷

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: ANALYZE (Temporary, no DB persistence)             │
└─────────────────────────────────────────────────────────────┘

Client                   GraphQL API              Domain Services
  │                          │                           │
  │─── analyzeMealPhoto ────>│                           │
  │    {photoUrl, userId}    │                           │
  │                          │                           │
  │                          │─── recognizeFood ───────>│
  │                          │    (OpenAI Vision API)    │
  │                          │<──────────────────────────│
  │                          │   items: [               │
  │                          │     {label:"pasta",      │
  │                          │      quantityG:200,      │
  │                          │      confidence:0.85}    │
  │                          │   ]                       │
  │                          │                           │
  │                          │─── enrichNutrients ─────>│
  │                          │    (USDA API)             │
  │                          │    for each item          │
  │                          │<──────────────────────────│
  │                          │   NutrientProfile         │
  │                          │                           │
  │                          │─ Save to Redis ──────────>│
  │                          │   (temporary storage)     │
  │                          │   TTL: 1 hour             │
  │                          │                           │
  │<─── MealPhotoAnalysis ───│                           │
  │     {id, status:PENDING, │                           │
  │      items:[...],        │                           │
  │      totalCalories}      │                           │
  │                          │                           │

┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: USER REVIEW (Frontend UI)                          │
└─────────────────────────────────────────────────────────────┘

  • Display items con foto
  • User può:
    - Modificare quantità
    - Rimuovere items
    - Aggiungere items manualmente
    - Confermare o cancellare

┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: CONFIRM (DB Persistence)                           │
└─────────────────────────────────────────────────────────────┘

Client                   GraphQL API           MongoDB Repository
  │                          │                           │
  │─── confirmMealPhoto ────>│                           │
  │    {analysisId,          │                           │
  │     acceptedIndexes}     │                           │
  │                          │                           │
  │                          │─ Load from Redis ───────>│
  │                          │<──────────────────────────│
  │                          │   Analysis data           │
  │                          │                           │
  │                          │─ Save MealEntry ────────>│
  │                          │   (MongoDB meals coll)    │
  │                          │   for each accepted item  │
  │                          │<──────────────────────────│
  │                          │   Created IDs             │
  │                          │                           │
  │                          │─ Delete from Redis ─────>│
  │                          │   (cleanup)               │
  │                          │                           │
  │<─ ConfirmMealPhotoResult │                           │
  │   {createdMeals:[...]}   │                           │
  │                          │                           │
```

**Esempio GraphQL**:

```graphql
# Step 1: Analisi
mutation {
  analyzeMealPhoto(input: {
    photoUrl: "https://storage.example.com/photos/meal-123.jpg"
    userId: "user_12345"
    dishHint: "pasta carbonara"
  }) {
    id                    # "analysis_abc123"
    status                # PENDING
    dishName              # "Spaghetti alla Carbonara"
    items {
      label               # "pasta"
      displayName         # "Spaghetti"
      quantityG           # 200
      confidence          # 0.85
      calories            # 312
      protein             # 12.5
      carbs               # 56.2
      fat                 # 3.8
      enrichmentSource    # "USDA"
    }
    totalCalories         # 850
    photoUrl
  }
}

# Step 2: Conferma (dopo review utente)
mutation {
  confirmMealPhoto(input: {
    analysisId: "analysis_abc123"
    acceptedIndexes: [0, 1, 2]  # Conferma items 0, 1, 2
    userId: "user_12345"
  }) {
    analysisId
    createdMeals {
      id                  # "meal_xyz789" (MongoDB _id)
      name                # "Spaghetti"
      quantityG           # 200
      timestamp           # "2025-10-18T12:30:00Z"
      calories            # 312
      protein             # 12.5
      imageUrl            # Link foto originale
    }
  }
}
```

### Flow 2: Barcode Scan 🔍

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: ANALYZE                                             │
└─────────────────────────────────────────────────────────────┘

Client                   GraphQL API              Domain Services
  │                          │                           │
  │─── analyzeMealBarcode ──>│                           │
  │    {barcode, quantityG}  │                           │
  │                          │                           │
  │                          │─ searchFoodByBarcode ───>│
  │                          │   (OpenFoodFacts API)     │
  │                          │<──────────────────────────│
  │                          │   Product {               │
  │                          │     name, calories/100g   │
  │                          │     nutrients/100g        │
  │                          │   }                       │
  │                          │                           │
  │                          │─ Scale nutrients ────────>│
  │                          │   quantityG × profile/100 │
  │                          │                           │
  │                          │─ Save to Redis ──────────>│
  │                          │                           │
  │<─── MealPhotoAnalysis ───│                           │
  │     {status:PENDING,     │                           │
  │      items:[1 item],     │                           │
  │      confidence:1.0}     │                           │
  │                          │                           │

┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: USER REVIEW (può modificare quantità)              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: CONFIRM                                             │
└─────────────────────────────────────────────────────────────┘
  (stesso flusso di Photo)
```

**Esempio GraphQL**:

```graphql
# Step 1: Analisi
mutation {
  analyzeMealBarcode(input: {
    barcode: "8001234567890"
    userId: "user_12345"
    quantityG: 100
  }) {
    id                    # "analysis_def456"
    status                # PENDING
    dishName              # "Barilla Penne Rigate"
    items {
      label               # "pasta"
      displayName         # "Barilla Penne Rigate"
      quantityG           # 100
      confidence          # 1.0 (barcode = high confidence)
      calories            # 350
      protein             # 12
      enrichmentSource    # "BARCODE_DB"
    }
    totalCalories         # 350
  }
}

# Step 2: Conferma
mutation {
  confirmMealBarcode(input: {
    analysisId: "analysis_def456"
    acceptedIndexes: [0]
    userId: "user_12345"
  }) {
    createdMeals { ... }
  }
}
```

### Flow 3: Text Description 📝

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: ANALYZE                                             │
└─────────────────────────────────────────────────────────────┘

Client                   GraphQL API              Domain Services
  │                          │                           │
  │─ analyzeMealDescription─>│                           │
  │   {description}          │                           │
  │                          │                           │
  │                          │─ AI Text Extraction ────>│
  │                          │   (OpenAI structured)     │
  │                          │<──────────────────────────│
  │                          │   items: [               │
  │                          │     {label:"pizza",      │
  │                          │      quantityG:300},     │
  │                          │     {label:"salad",      │
  │                          │      quantityG:150}      │
  │                          │   ]                       │
  │                          │                           │
  │                          │─ enrichNutrients ────────>│
  │                          │   (USDA) for each item    │
  │                          │                           │
  │                          │─ Save to Redis ──────────>│
  │                          │                           │
  │<─── MealPhotoAnalysis ───│                           │
  │                          │                           │
```

**Esempio GraphQL**:

```graphql
# Step 1: Analisi
mutation {
  analyzeMealDescription(input: {
    description: "Ho mangiato una pizza margherita e un'insalata mista"
    userId: "user_12345"
  }) {
    id                    # "analysis_ghi789"
    status                # PENDING
    items {
      label               # "pizza"
      displayName         # "Pizza Margherita"
      quantityG           # 300 (estimated by AI)
      confidence          # 0.7 (text = lower confidence)
      calories            # 720
      enrichmentSource    # "USDA"
    }
    totalCalories         # 920
  }
}

# Step 2: Conferma
mutation {
  confirmMealDescription(input: {
    analysisId: "analysis_ghi789"
    acceptedIndexes: [0, 1]
    userId: "user_12345"
  }) {
    createdMeals { ... }
  }
}
```

---

## 📁 STRATEGIA MIGRAZIONE V1 → V2

### Approccio: Parallel Development con V2 Folder

**Rationale**: Creare tutto il nuovo codice in una cartella `v2/` separata permette di:
- ✅ Sviluppare senza rischio di regressioni
- ✅ Mantenere V1 funzionante durante lo sviluppo
- ✅ Testare V2 in isolamento
- ✅ Fare switch atomico a fine refactoring
- ✅ Rollback immediato se necessario

---

### Classificazione Codice Esistente

#### 🟢 A) MANTIENI PER COMPATIBILITÀ (Temporary Bridge)

**Cosa**: Codice legacy che deve rimanere attivo durante la transizione ma verrà eliminato

**Dove**: Rimane in V1, viene deprecato gradualmente

**Lista file**:
```
backend/
├── graphql/
│   ├── mutations/
│   │   └── meal_mutations.py          # ⚠️ logMeal() - DEPRECATO
│   └── queries/
│       └── meal_queries.py            # ⚠️ product() - DEPRECATO
│
├── domain/ (o services/)
│   └── meal/
│       └── meal_service.py            # ⚠️ Logica meal legacy
│
└── models/
    └── meal.py                         # ⚠️ MealEntry vecchio formato
```

**Azioni**:
1. Aggiungi decorator `@deprecated` con messaggio
2. Logga warning su ogni chiamata
3. Documenta migration path nel docstring
4. Mantieni funzionante ma NO nuove features
5. **Elimina in Fase 11** (dopo switch a V2)

**Esempio**:
```python
# backend/graphql/mutations/meal_mutations.py

@strawberry.mutation
@deprecated(
    reason="Use analyzeMeal* + confirmMeal* workflow instead",
    category=DeprecationWarning
)
async def log_meal(input: LogMealInput) -> MealEntry:
    """
    ⚠️ DEPRECATED: This mutation will be removed in v0.8.0
    
    Migration path:
    - For barcode: Use analyzeMealBarcode() + confirmMealBarcode()
    - For manual: Use analyzeMealDescription() + confirmMealDescription()
    """
    logger.warning("deprecated_api_call", mutation="logMeal", user=input.user_id)
    # Existing implementation...
```

---

#### 🔵 B) MANTIENI INALTERATO (Keep As-Is)

**Cosa**: Codice funzionante che non è oggetto del refactoring

**Dove**: Rimane in V1, nessuna modifica

**Lista file**:
```
backend/
├── domain/ (o services/)
│   ├── activity/                       # ✅ Sistema activity tracking
│   │   ├── activity_service.py
│   │   ├── health_sync.py
│   │   └── models.py
│   └── sync/                           # ✅ Sync deltas
│       └── sync_service.py
│
├── graphql/
│   ├── mutations/
│   │   └── activity_mutations.py       # ✅ ingestActivityEvents, syncHealthTotals
│   ├── queries/
│   │   ├── activity_queries.py         # ✅ activityEntries, syncEntries
│   │   └── health_queries.py           # ✅ dailySummary (parte activity)
│   └── types/
│       └── activity_types.py           # ✅ ActivityEvent, HealthTotalsDelta, etc.
│
├── infrastructure/
│   ├── cache/
│   │   └── product_cache.py            # ✅ Cache OpenFoodFacts (se esiste)
│   └── logging/
│       └── structlog_config.py         # ✅ Logging setup
│
└── api/
    ├── middleware.py                   # ✅ CORS, auth, etc.
    └── health.py                       # ✅ Health check endpoint
```

**Azioni**:
1. ❌ NO modifiche
2. ✅ Mantieni test esistenti
3. ✅ Verifica che V2 non rompa questi moduli
4. ✅ Importa in V2 se necessario (es. structlog_config)

---

#### 🟡 C) MODIFICA IN V1 (Extend, Not Replace)

**Cosa**: Codice che deve essere aggiornato per supportare V2 ma rimane in V1

**Dove**: Modifica in-place in V1

**Lista file**:
```
backend/
├── graphql/
│   ├── schema.py                       # 🔧 Aggiungi V2 resolvers
│   ├── context.py                      # 🔧 Aggiungi V2 DI container
│   └── schema.graphql                  # 🔧 Merge V1 + V2 schema
│
├── infrastructure/
│   ├── database/
│   │   └── connection.py               # 🔧 Se esiste, estendi per MongoDB
│   └── config/
│       └── settings.py                 # 🔧 Aggiungi nuove env vars
│
└── api/
    └── main.py                         # 🔧 Mount V2 routes, setup V2 services
```

**Azioni**:
1. **NON sostituire** codice esistente
2. **AGGIUNGI** nuovo codice accanto al vecchio
3. **USA** feature flags se necessario
4. **TESTA** che V1 continui a funzionare

**Esempio - schema.py**:
```python
# backend/graphql/schema.py

from strawberry import Schema

# V1 - Existing
from .queries.meal_queries import MealQueries as MealQueriesV1
from .mutations.meal_mutations import MealMutations as MealMutationsV1

# V2 - New
from .v2.queries.meal_queries import MealQueries as MealQueriesV2
from .v2.mutations.meal_mutations import MealMutations as MealMutationsV2

# Merge V1 + V2
@strawberry.type
class Query(MealQueriesV1, MealQueriesV2, ActivityQueries, HealthQueries):
    """Combined V1 + V2 queries."""
    pass

@strawberry.type
class Mutation(MealMutationsV1, MealMutationsV2, ActivityMutations):
    """Combined V1 + V2 mutations."""
    pass

schema = Schema(query=Query, mutation=Mutation)
```

**Esempio - settings.py**:
```python
# backend/infrastructure/config/settings.py

class Settings(BaseSettings):
    # Existing V1 config
    env: str = "development"
    
    # NEW V2 config (add, don't replace)
    openai_api_key: Optional[str] = None  # New
    usda_api_key: Optional[str] = None    # New
    mongodb_uri: str = "mongodb://localhost:27017"  # New
    mongodb_database: str = "nutrifit"    # New
    redis_uri: str = "redis://localhost:6379"  # New
    redis_enabled: bool = False           # New
    
    # Feature flags
    enable_v2_meal_api: bool = False      # New - gradual rollout
```

---

#### 🟢 D) CODICE NUOVO (V2 Folder)

**Cosa**: Tutto il nuovo codice del refactoring

**Dove**: Cartella `backend/v2/` completamente isolata

**Struttura completa**:
```
backend/
└── v2/                                 # 🆕 NEW - Tutto il refactoring
    │
    ├── domain/                         # 🆕 Business Logic (pure Python)
    │   │
    │   ├── meal/
    │   │   ├── recognition/            # 🆕 AI Recognition
    │   │   │   ├── __init__.py
    │   │   │   ├── models.py
    │   │   │   ├── service.py
    │   │   │   ├── prompts.py
    │   │   │   └── text_extractor.py
    │   │   │
    │   │   ├── nutrition/              # 🆕 USDA Enrichment
    │   │   │   ├── __init__.py
    │   │   │   ├── models.py
    │   │   │   ├── service.py
    │   │   │   └── usda/
    │   │   │       ├── mapper.py
    │   │   │       ├── client.py
    │   │   │       ├── cache.py
    │   │   │       └── categories.py
    │   │   │
    │   │   ├── barcode/                # 🆕 Barcode Service
    │   │   │   ├── __init__.py
    │   │   │   ├── models.py
    │   │   │   ├── service.py
    │   │   │   └── openfoodfacts/
    │   │   │       ├── client.py
    │   │   │       └── mapper.py
    │   │   │
    │   │   ├── orchestration/          # 🆕 Multi-service coordination
    │   │   │   ├── __init__.py
    │   │   │   ├── photo_analyzer.py
    │   │   │   ├── barcode_analyzer.py
    │   │   │   ├── text_analyzer.py
    │   │   │   └── models.py
    │   │   │
    │   │   ├── persistence/            # 🆕 Repository interfaces
    │   │   │   ├── __init__.py
    │   │   │   ├── models.py
    │   │   │   ├── repository.py
    │   │   │   └── confirmer.py
    │   │   │
    │   │   └── exceptions.py
    │   │
    │   └── shared/                     # 🆕 Shared domain
    │       ├── value_objects.py
    │       └── errors.py
    │
    ├── infrastructure/                 # 🆕 External integrations
    │   │
    │   ├── database/                   # 🆕 MongoDB
    │   │   ├── __init__.py
    │   │   ├── mongodb.py
    │   │   └── repositories/
    │   │       ├── meal_repository.py
    │   │       └── analysis_repository.py
    │   │
    │   ├── cache/                      # 🆕 Redis/Memory
    │   │   ├── __init__.py
    │   │   ├── redis_client.py
    │   │   └── memory_cache.py
    │   │
    │   ├── ai/                         # 🆕 AI clients
    │   │   ├── __init__.py
    │   │   ├── openai_client.py
    │   │   └── rate_limiter.py
    │   │
    │   └── external_apis/              # 🆕 External APIs
    │       ├── __init__.py
    │       ├── usda_client.py
    │       └── openfoodfacts_client.py
    │
    ├── application/                    # 🆕 Use cases
    │   │
    │   ├── meal/
    │   │   ├── __init__.py
    │   │   ├── analyze_photo.py
    │   │   ├── analyze_barcode.py
    │   │   ├── analyze_description.py
    │   │   ├── confirm_meal.py
    │   │   ├── update_meal.py
    │   │   ├── delete_meal.py
    │   │   └── query_meals.py
    │   │
    │   └── shared/
    │       ├── __init__.py
    │       └── idempotency.py
    │
    ├── graphql/                        # 🆕 GraphQL V2 API
    │   │
    │   ├── queries/
    │   │   ├── __init__.py
    │   │   ├── food_recognition.py     # recognizeFood
    │   │   ├── nutrition.py            # enrichNutrients
    │   │   └── barcode_search.py       # searchFoodByBarcode
    │   │
    │   ├── mutations/
    │   │   ├── __init__.py
    │   │   ├── analyze_meal.py         # analyze*
    │   │   └── confirm_meal.py         # confirm*
    │   │
    │   └── types/
    │       ├── __init__.py
    │       ├── analysis_types.py
    │       └── nutrition_types.py
    │
    ├── tests/                          # 🧪 V2 Test Suite (ISOLATO in v2/)
    │   │                                  # ⚠️ IMPORTANTE: Test V2 NON in backend/tests/
    │   │                                  #              ma in backend/v2/tests/
    │   ├── unit/
    │   │   ├── domain/
    │   │   │   ├── meal/
    │   │   │   │   ├── test_recognition_service.py
    │   │   │   │   ├── test_nutrition_service.py
    │   │   │   │   ├── test_barcode_service.py
    │   │   │   │   ├── test_orchestration.py
    │   │   │   │   └── test_usda_mapper.py
    │   │   │   └── shared/
    │   │   │       └── test_value_objects.py
    │   │   │
    │   │   └── application/
    │   │       └── meal/
    │   │           ├── test_analyze_photo_usecase.py
    │   │           ├── test_confirm_meal_usecase.py
    │   │           └── test_idempotency.py
    │   │
    │   ├── integration/                # Integration tests (with mocks)
    │   │   ├── test_mongodb_repository.py
    │   │   ├── test_redis_cache.py
    │   │   ├── test_usda_client.py
    │   │   └── test_openfoodfacts_client.py
    │   │
    │   ├── e2e/                        # End-to-end tests
    │   │   ├── test_photo_flow.py
    │   │   ├── test_barcode_flow.py
    │   │   └── test_description_flow.py
    │   │
    │   ├── fixtures/
    │   │   ├── meal_fixtures.py
    │   │   ├── api_responses/          # Mock API responses
    │   │   │   ├── openai_vision.json
    │   │   │   ├── usda_search.json
    │   │   │   └── openfoodfacts.json
    │   │   └── images/                 # Test images
    │   │       └── sample_meal.jpg
    │   │
    │   └── conftest.py                 # Pytest configuration
    │
    ├── docs/                           # 📚 V2 Documentation (ISOLATA in v2/)
    │   │                                  # ⚠️ IMPORTANTE: Doc V2 NON in backend/docs/
    │   │                                  #              ma in backend/v2/docs/
    │   ├── architecture.md             # V2 architecture details
    │   ├── domain_models.md            # Domain layer documentation
    │   ├── api_examples.md             # GraphQL examples for V2
    │   ├── testing_guide.md            # How to test V2
    │   ├── migration_guide.md          # V1 → V2 migration for users
    │   └── development_setup.md        # V2 dev environment setup
    │
    └── __init__.py
```

**Azioni**:
1. ✅ Sviluppa in completo isolamento
2. ✅ Non dipendere da V1 (eccetto config condivisa)
3. ✅ Test 100% coverage prima del merge
4. ✅ Documentation inline
5. ✅ **CRITICO**: Tests vanno in `backend/v2/tests/` (NON in `backend/tests/`)
6. ✅ **CRITICO**: Docs vanno in `backend/v2/docs/` (NON in `backend/docs/`)

**Rationale**: Tenere tests e docs in v2/ garantisce:
- Isolamento completo del refactoring
- Nessun conflitto con test V1 esistenti
- Facile promozione a root in Fase 11
- Clear ownership (test V2 testano solo V2)

---

### Workflow di Sviluppo V2

#### Fase 0-9: Sviluppo Parallelo

```
backend/
├── v2/                    # 🆕 Nuovo codice (sviluppo attivo)
│   └── ...
│
├── domain/                # 🔵 V1 - Mantieni inalterato
├── graphql/               # 🟡 V1 - Estendi (add V2 resolvers)
├── infrastructure/        # 🟡 V1 - Estendi (config, MongoDB)
└── api/                   # 🟡 V1 - Estendi (mount V2)
```

**Durante sviluppo**:
- V1 continua a servire traffico
- V2 esposto solo con feature flag `enable_v2_meal_api=true`
- Testing isolato di V2

#### Fase 10: Testing Parallelo

```python
# Feature flag in settings.py
enable_v2_meal_api: bool = False

# Usage in GraphQL schema
if settings.enable_v2_meal_api:
    # Include V2 mutations
    schema = Schema(query=QueryV1AndV2, mutation=MutationV1AndV2)
else:
    # V1 only
    schema = Schema(query=QueryV1, mutation=MutationV1)
```

**Test strategy**:
1. Deploy con flag OFF (V1 only)
2. Abilita flag per internal testing
3. Gradual rollout (10% → 50% → 100%)

#### Fase 11: Switch & Cleanup

**Step 1: Enable V2**
```bash
# .env
ENABLE_V2_MEAL_API=true
```

**Step 2: Monitor (1 settimana)**
- Errori V2
- Performance V2 vs V1
- User feedback

**Step 3: Cleanup (se tutto OK)**
```bash
# Promuovi V2 a root
cd backend

# Sposta contenuto V2 a root (sovrascrive meal logic, aggiunge nuovo)
mv v2/domain/meal domain/                  # Sostituisce meal V1 con V2
mv v2/infrastructure/* infrastructure/     # Aggiunge MongoDB, AI, etc.
mv v2/application/* application/           # Aggiunge use cases V2
mv v2/graphql/* graphql/                   # Merge resolvers V2

# ⚠️ IMPORTANTE: Promuovi anche tests e docs
mv v2/tests/unit tests/unit_v2            # Oppure merge in tests/
mv v2/tests/integration tests/integration_v2
mv v2/tests/e2e tests/e2e_v2
mv v2/docs/* docs/v2/                      # Oppure merge in docs/

# Rimuovi cartella v2 vuota
rmdir v2

# DELETE V1 deprecated files
rm graphql/mutations/meal_mutations_v1.py  # logMeal
rm graphql/queries/meal_queries_v1.py      # product query
rm domain/meal/meal_service_v1.py          # old logic
rm tests/test_legacy_meal.py               # old meal tests
```

**Alternative per tests/docs**:
- **Opzione A** (consigliata): Merge in tests/ root con sottocartelle chiare
- **Opzione B**: Mantieni tests/v2/ e tests/v1/ separati inizialmente


**Step 4: Final structure**
```
backend/
├── domain/                 # Merged: activity (V1) + meal (ex-V2)
│   ├── activity/           # ✅ Kept from V1
│   ├── meal/               # 🆕 Promoted from v2/
│   └── shared/             # 🆕 From v2/
│
├── infrastructure/         # Merged: config (V1) + MongoDB/AI (ex-V2)
│   ├── database/           # 🆕 From v2/
│   ├── cache/              # 🆕 From v2/
│   ├── ai/                 # 🆕 From v2/
│   ├── external_apis/      # 🆕 From v2/
│   ├── config/             # ✅ Kept from V1
│   └── logging/            # ✅ Kept from V1
│
├── application/            # Merged: activity (V1) + meal (ex-V2)
│   ├── activity/           # ✅ Kept from V1
│   ├── meal/               # 🆕 From v2/
│   └── shared/             # 🆕 From v2/
│
├── graphql/                # Merged V1 (activity) + V2 (meal)
│   ├── queries/            # Both V1 activity + V2 meal
│   ├── mutations/          # Both V1 activity + V2 meal
│   ├── types/              # Both V1 + V2
│   ├── schema.py           # Unified
│   └── context.py          # Unified DI
│
├── api/                    # ✅ Kept from V1 (extended)
│
├── tests/                  # Merged: V1 activity + V2 meal
│   ├── unit/               # Both V1 + ex-V2
│   ├── integration/        # Both V1 + ex-V2
│   ├── e2e/                # ex-V2
│   └── fixtures/           # ex-V2
│
├── docs/                   # Merged: V1 + V2
│   ├── architecture.md     # Updated
│   ├── activity_api.md     # ✅ Kept from V1
│   ├── meal_api.md         # 🆕 From v2/
│   └── migration_guide.md  # 🆕 From v2/
│
└── scripts/                # 🆕 From v2/
```


---

### Import Strategy

#### V2 può importare da V1

**OK da importare**:
```python
# V2 code
from backend.infrastructure.logging import structlog_config  # ✅ Shared logging
from backend.infrastructure.config import settings           # ✅ Shared config
from backend.api.middleware import auth_middleware           # ✅ Shared middleware
```

**NON importare**:
```python
# V2 code
from backend.domain.meal import MealService  # ❌ Old meal logic
from backend.models import MealEntry         # ❌ Old models
```

#### V1 NON deve importare da V2

```python
# V1 code
from backend.v2.domain.meal import ...  # ❌ NEVER - keep decoupled
```

**Eccezione**: GraphQL schema.py può importare entrambi per merge

---

### Naming Conventions

#### Durante sviluppo (V1 + V2 coesistono)

**GraphQL**:
```graphql
# V2 usa nomi nuovi (no conflicts)
type Query {
  # V2 - New names
  recognizeFood(...)          # 🆕
  enrichNutrients(...)        # 🆕
  searchFoodByBarcode(...)    # 🆕 (rename of 'product')
  
  # V1 - Keep old names
  product(...)                # ⚠️ DEPRECATED
  mealEntries(...)            # ✅ Keep (no conflict)
}

type Mutation {
  # V2 - New names
  analyzeMealPhoto(...)       # 🆕
  analyzeMealBarcode(...)     # 🆕
  analyzeMealDescription(...) # 🆕
  confirmMealPhoto(...)       # 🆕
  confirmMealBarcode(...)     # 🆕
  confirmMealDescription(...) # 🆕
  
  # V1 - Keep old names
  logMeal(...)                # ⚠️ DEPRECATED
  updateMeal(...)             # ✅ Keep (V2 will reimplement)
  deleteMeal(...)             # ✅ Keep (V2 will reimplement)
}
```

**Python modules**:
```python
# V2 modules
backend.v2.domain.meal.recognition.service    # FoodRecognitionService
backend.v2.domain.meal.nutrition.service      # NutritionEnrichmentService

# V1 modules (no name conflicts)
backend.domain.meal.service                   # MealService (old)
backend.domain.activity.service               # ActivityService (keep)
```

#### Dopo cleanup (solo V2)

Rinomina `v2/` → root:
```bash
mv backend/v2/* backend/
rmdir backend/v2
```

---

### Database Strategy

#### Durante sviluppo

**Opzione A: Separate databases (RACCOMANDATO)**
```yaml
# docker-compose.yml
services:
  mongodb-v1:  # Dati legacy (se hai MongoDB già)
    image: mongo:7.0
    ports: ["27017:27017"]
    
  mongodb-v2:  # Nuovo database refactor
    image: mongo:7.0
    ports: ["27018:27017"]  # Porta diversa!
```

```python
# settings.py
mongodb_v1_uri: str = "mongodb://localhost:27017"  # Legacy
mongodb_v2_uri: str = "mongodb://localhost:27018"  # V2
```

**Opzione B: Same database, different collections**
```javascript
// V1 collections
db.meals_v1
db.activity_events
db.health_totals

// V2 collections
db.meals          // New meal entries
db.meal_analysis  // Temporary analysis
```

#### Dopo switch

**Data migration**:
```python
# scripts/migrate_v1_to_v2.py

async def migrate_meals():
    """Migrate meals from V1 to V2 format."""
    v1_meals = await v1_db.meals_v1.find({}).to_list(None)
    
    for v1_meal in v1_meals:
        v2_meal = transform_meal_v1_to_v2(v1_meal)
        await v2_db.meals.insert_one(v2_meal)
    
    logger.info(f"Migrated {len(v1_meals)} meals")
```

---

### Rollback Plan

Se V2 ha problemi critici:

**Step 1: Disable V2**
```bash
# .env
ENABLE_V2_MEAL_API=false  # Instant rollback to V1
```

**Step 2: Investigate**
- Check logs
- Review metrics
- Identify issue

**Step 3: Fix & Retry**
- Fix in V2
- Re-enable gradually

**Worst case**: Delete `backend/v2/` folder, V1 still works

---

### Summary Table

| Categoria | Azione | Dove | Quando |
|-----------|--------|------|--------|
| **A) Compatibilità** | Depreca ma mantieni | V1 root | Elimina Fase 11 |
| **B) Inalterato** | Nessuna modifica | V1 root | Mantieni sempre |
| **C) Modifica** | Estendi (no replace) | V1 root | Fase 0-9 |
| **D) Nuovo** | Sviluppa isolato | `v2/` folder | Fase 0-10 |

---

### Checklist Pre-Switch

Prima di abilitare V2 in produzione:

- [ ] ✅ V2 test coverage = 60% (business logic)
- [ ] ✅ V1 API ancora funzionante
- [ ] ✅ Feature flag testata (ON/OFF)
- [ ] ✅ Data migration script pronto
- [ ] ✅ Rollback plan documentato
- [ ] ✅ Monitoring attivo su V2
- [ ] ✅ Performance benchmark V2 > V1
- [ ] ✅ Breaking changes comunicati a client
- [ ] ✅ Documentation aggiornata
- [ ] ✅ Team training completato

---

## 🏗️ FILE SYSTEM ARCHITECTURE

### Struttura Completa (V1 + V2 durante refactoring)

```
backend/
├── .env.example                      # Template variabili ambiente
├── .env                              # Config locale (gitignored)
├── pyproject.toml                    # Poetry dependencies
├── pytest.ini                        # Test configuration (shared)
├── mypy.ini                          # Type checking config (shared)
│
├── v2/                               # 🆕 TUTTO IL REFACTORING (100% isolato)
│   │                                    # ⚠️ IMPORTANTE: Tutto V2 va QUI dentro
│   │
│   ├── domain/                       # 🎯 V2 Domain Layer
│   │   │
│   │   ├── meal/
│   │   │   ├── recognition/          # AI Food Recognition
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py
│   │   │   │   ├── service.py
│   │   │   │   ├── prompts.py
│   │   │   │   └── text_extractor.py
│   │   │   │
│   │   │   ├── nutrition/            # USDA Enrichment
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py
│   │   │   │   ├── service.py
│   │   │   │   └── usda/
│   │   │   │       ├── mapper.py
│   │   │   │       ├── client.py
│   │   │   │       ├── cache.py
│   │   │   │       └── categories.py
│   │   │   │
│   │   │   ├── barcode/              # Barcode Service
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py
│   │   │   │   ├── service.py
│   │   │   │   └── openfoodfacts/
│   │   │   │       ├── client.py
│   │   │   │       └── mapper.py
│   │   │   │
│   │   │   ├── orchestration/        # Multi-service coordination
│   │   │   │   ├── __init__.py
│   │   │   │   ├── photo_analyzer.py
│   │   │   │   ├── barcode_analyzer.py
│   │   │   │   ├── text_analyzer.py
│   │   │   │   └── models.py
│   │   │   │
│   │   │   ├── persistence/          # Repository interfaces
│   │   │   │   ├── __init__.py
│   │   │   │   ├── models.py
│   │   │   │   ├── repository.py
│   │   │   │   └── confirmer.py
│   │   │   │
│   │   │   └── exceptions.py
│   │   │
│   │   └── shared/                   # Shared domain
│   │       ├── value_objects.py
│   │       └── errors.py
│   │
│   ├── infrastructure/               # 🔌 V2 Infrastructure Layer
│   │   │
│   │   ├── database/                 # MongoDB Implementation
│   │   │   ├── __init__.py
│   │   │   ├── mongodb.py
│   │   │   └── repositories/
│   │   │       ├── meal_repository.py
│   │   │       └── analysis_repository.py
│   │   │
│   │   ├── cache/                    # Redis/Memory Cache
│   │   │   ├── __init__.py
│   │   │   ├── redis_client.py
│   │   │   └── memory_cache.py
│   │   │
│   │   ├── ai/                       # AI Clients
│   │   │   ├── __init__.py
│   │   │   ├── openai_client.py
│   │   │   └── rate_limiter.py
│   │   │
│   │   └── external_apis/            # External API clients
│   │       ├── __init__.py
│   │       ├── usda_client.py
│   │       └── openfoodfacts_client.py
│   │
│   ├── application/                  # 🎭 V2 Application Layer
│   │   │
│   │   ├── meal/
│   │   │   ├── __init__.py
│   │   │   ├── analyze_photo.py
│   │   │   ├── analyze_barcode.py
│   │   │   ├── analyze_description.py
│   │   │   ├── confirm_meal.py
│   │   │   ├── update_meal.py
│   │   │   ├── delete_meal.py
│   │   │   └── query_meals.py
│   │   │
│   │   └── shared/
│   │       ├── __init__.py
│   │       └── idempotency.py
│   │
│   ├── graphql/                      # 🎨 V2 GraphQL Layer
│   │   │
│   │   ├── queries/
│   │   │   ├── __init__.py
│   │   │   ├── meal_queries.py       # V2 meal queries
│   │   │   ├── food_recognition.py   # recognizeFood
│   │   │   ├── nutrition.py          # enrichNutrients
│   │   │   └── barcode_search.py     # searchFoodByBarcode
│   │   │
│   │   ├── mutations/
│   │   │   ├── __init__.py
│   │   │   ├── analyze_meal.py       # analyze*
│   │   │   └── confirm_meal.py       # confirm*
│   │   │
│   │   └── types/
│   │       ├── __init__.py
│   │       ├── analysis_types.py
│   │       └── nutrition_types.py
│   │
│   ├── tests/                        # 🧪 V2 Test Suite
│   │   │                                # ⚠️ CRITICO: Tests V2 QUI, non in backend/tests/
│   │   ├── unit/
│   │   │   ├── domain/
│   │   │   │   ├── meal/
│   │   │   │   │   ├── test_recognition_service.py
│   │   │   │   │   ├── test_nutrition_service.py
│   │   │   │   │   ├── test_barcode_service.py
│   │   │   │   │   └── test_orchestration.py
│   │   │   │   └── shared/
│   │   │   │       └── test_value_objects.py
│   │   │   │
│   │   │   └── application/
│   │   │       └── meal/
│   │   │           ├── test_analyze_usecase.py
│   │   │           └── test_confirm_usecase.py
│   │   │
│   │   ├── integration/
│   │   │   ├── test_mongodb_repository.py
│   │   │   ├── test_redis_cache.py
│   │   │   └── test_api_clients.py
│   │   │
│   │   ├── e2e/
│   │   │   ├── test_photo_flow.py
│   │   │   ├── test_barcode_flow.py
│   │   │   └── test_description_flow.py
│   │   │
│   │   ├── fixtures/
│   │   │   ├── meal_fixtures.py
│   │   │   ├── api_responses/
│   │   │   └── images/
│   │   │
│   │   └── conftest.py
│   │
│   ├── docs/                         # 📚 V2 Documentation
│   │   │                                # ⚠️ CRITICO: Docs V2 QUI, non in backend/docs/
│   │   ├── architecture.md           # V2 architecture details
│   │   ├── domain_models.md          # Domain layer docs
│   │   ├── api_examples.md           # GraphQL V2 examples
│   │   ├── testing_guide.md          # How to test V2
│   │   ├── migration_guide.md        # V1 → V2 for users
│   │   └── development_setup.md      # V2 dev environment
│   │
│   └── __init__.py
│
├── domain/                           # 🔵 V1 Domain (MANTIENI INALTERATO)
│   ├── activity/                     # ✅ Activity tracking (no refactor)
│   │   ├── __init__.py
│   │   ├── activity_service.py
│   │   ├── health_sync.py
│   │   └── models.py
│   │
│   └── meal/                         # ⚠️ Old meal logic (DEPRECATO)
│       └── meal_service.py           # Will be deleted in Fase 11
│
├── infrastructure/                   # 🟡 V1 Infrastructure (ESTENDI)
│   │
│   ├── config/                       # 🔧 Extend with V2 settings
│   │   ├── __init__.py
│   │   └── settings.py               # Add V2 env vars
│   │
│   ├── logging/                      # 🔵 Keep (shared with V2)
│   │   └── structlog_config.py
│   │
│   └── cache/                        # 🔵 Keep (if exists - OpenFoodFacts cache)
│       └── product_cache.py
│
├── graphql/                          # 🟡 V1 GraphQL (MERGE POINT V1+V2)
│   │
│   ├── schema.graphql                # 🔧 Merge schema V1+V2
│   │
│   ├── queries/
│   │   ├── __init__.py
│   │   ├── meal_queries_v1.py        # ⚠️ Old (product - DEPRECATO)
│   │   ├── activity_queries.py       # 🔵 Keep (no changes)
│   │   └── health_queries.py         # 🔵 Keep (dailySummary)
│   │
│   ├── mutations/
│   │   ├── __init__.py
│   │   ├── meal_mutations_v1.py      # ⚠️ Old (logMeal - DEPRECATO)
│   │   └── activity_mutations.py     # 🔵 Keep (no changes)
│   │
│   ├── types/
│   │   ├── __init__.py
│   │   ├── meal_types.py             # 🔵 Keep (MealEntry, etc.)
│   │   └── activity_types.py         # 🔵 Keep (no changes)
│   │
│   ├── context.py                    # 🔧 Add V2 DI container
│   └── schema.py                     # 🔧 Merge V1+V2 resolvers
│
├── api/                              # 🟡 V1 API (ESTENDI)
│   ├── __init__.py
│   ├── main.py                       # 🔧 Mount V2 services
│   ├── dependencies.py               # 🔧 Add V2 DI setup
│   ├── middleware.py                 # 🔵 Keep (shared)
│   └── health.py                     # 🔵 Keep (shared)
│
├── tests/                            # 🔵 V1 Tests (MANTIENI)
│   ├── test_activity.py              # ✅ Activity tests (keep)
│   ├── test_health.py                # ✅ Health tests (keep)
│   └── test_legacy_meal.py           # ⚠️ Old meal tests (keep until Fase 11)
│
├── scripts/                          # 🛠️ Utility Scripts
│   ├── setup_mongodb.py              # 🆕 MongoDB setup & indexes
│   ├── migrate_v1_to_v2.py           # 🆕 Data migration script
│   └── seed_test_data.py             # 🆕 Test data seeding
│
└── docs/                             # 📚 V1 Documentation (MANTIENI)
    ├── architecture.md               # ✅ Overall architecture
    ├── activity_api.md               # ✅ Activity API docs
    └── deployment.md                 # ✅ Deployment guide
```

### 📝 Legenda

| Simbolo | Significato |
|---------|-------------|
| 🆕 | Codice nuovo (in v2/) |
| 🔵 | Mantieni inalterato (V1) |
| 🟡 | Estendi per supportare V2 |
| ⚠️ | Deprecato (elimina in Fase 11) |
| 🔧 | Modifica in-place |
| ✅ | Keep as-is (no refactor) |

### ⚠️ Note Critiche

1. **Tests in v2/**: TUTTI i test del refactoring vanno in `backend/v2/tests/`, NON in `backend/tests/`
2. **Docs in v2/**: TUTTA la documentazione V2 va in `backend/v2/docs/`, NON in `backend/docs/`
3. **Isolamento**: `v2/` è completamente indipendente da V1 (eccetto shared config)
4. **Merge Points**: Solo `graphql/schema.py` e `api/main.py` importano sia V1 che V2


```

---

## 📦 MONGODB SCHEMA DESIGN

### Collections Structure

```javascript
// Collection: meals
{
  "_id": ObjectId("..."),
  "user_id": "user_12345",
  "name": "Spaghetti alla Carbonara",
  "quantity_g": 200.0,
  "timestamp": ISODate("2025-10-18T12:30:00Z"),
  "source": "PHOTO",  // PHOTO | BARCODE | DESCRIPTION | MANUAL
  
  // Nutrient snapshot (denormalized for fast queries)
  "nutrients": {
    "calories": 312,
    "protein": 12.5,
    "carbs": 56.2,
    "fat": 3.8,
    "fiber": 2.1,
    "sugar": 3.5,
    "sodium": 450.0,
    "source": "USDA",
    "confidence": 0.85
  },
  
  // Optional fields
  "barcode": "8001234567890",
  "image_url": "https://storage.example.com/photos/meal-123.jpg",
  "analysis_id": "analysis_abc123",  // Link to original analysis
  
  // Metadata
  "idempotency_key": "idempot_xyz789",
  "created_at": ISODate("2025-10-18T12:31:00Z"),
  "updated_at": ISODate("2025-10-18T12:31:00Z"),
  "version": 1
}

// Indexes
db.meals.createIndex({ "user_id": 1, "timestamp": -1 })  // Query by user + time
db.meals.createIndex({ "user_id": 1, "created_at": -1 }) // Query by creation
db.meals.createIndex({ "idempotency_key": 1 }, { sparse: true, unique: true })
db.meals.createIndex({ "analysis_id": 1 }, { sparse: true })

// Collection: meal_analysis (temporary storage)
{
  "_id": "analysis_abc123",  // String ID (not ObjectId)
  "user_id": "user_12345",
  "status": "PENDING",  // PENDING | COMPLETED | FAILED
  "source": "PHOTO",
  
  // Analysis data
  "dish_name": "Spaghetti alla Carbonara",
  "items": [
    {
      "label": "pasta",
      "display_name": "Spaghetti",
      "quantity_g": 200.0,
      "confidence": 0.85,
      "nutrients": {
        "calories": 312,
        "protein": 12.5,
        // ...
      },
      "enrichment_source": "USDA"
    }
  ],
  "total_calories": 850,
  
  // Optional fields
  "photo_url": "https://...",
  "raw_json": "{...}",  // Debug: raw AI response
  "errors": [],
  
  // TTL for automatic cleanup
  "created_at": ISODate("2025-10-18T12:30:00Z"),
  "expires_at": ISODate("2025-10-18T13:30:00Z"),  // 1 hour TTL
  
  "idempotency_key": "idempot_xyz789"
}

// Indexes
db.meal_analysis.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })  // TTL index
db.meal_analysis.createIndex({ "user_id": 1, "created_at": -1 })
db.meal_analysis.createIndex({ "idempotency_key": 1 }, { sparse: true, unique: true })

// Collection: activity_events (✅ ESISTENTE - no changes)
// Collection: health_totals (✅ ESISTENTE - no changes)
// Collection: sync_deltas (✅ ESISTENTE - no changes)
```

### Repository Pattern Implementation

```python
# domain/meal/persistence/repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

class IMealRepository(ABC):
    """Interface per persistenza meal (domain layer)."""
    
    @abstractmethod
    async def create(self, meal: MealEntry) -> MealEntry:
        """Crea nuovo meal."""
        pass
    
    @abstractmethod
    async def get_by_id(self, meal_id: str, user_id: str) -> Optional[MealEntry]:
        """Recupera meal per ID."""
        pass
    
    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 20,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None
    ) -> List[MealEntry]:
        """Lista meals di un utente con pagination."""
        pass
    
    @abstractmethod
    async def update(self, meal: MealEntry) -> MealEntry:
        """Aggiorna meal esistente."""
        pass
    
    @abstractmethod
    async def delete(self, meal_id: str, user_id: str) -> bool:
        """Cancella meal."""
        pass
    
    @abstractmethod
    async def exists_by_idempotency_key(
        self,
        idempotency_key: str,
        user_id: str
    ) -> bool:
        """Check se idempotency key già usata."""
        pass
```

```python
# infrastructure/database/repositories/meal_repository.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

class MongoMealRepository(IMealRepository):
    """MongoDB implementation of meal repository."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db.meals
    
    async def create(self, meal: MealEntry) -> MealEntry:
        """Crea nuovo meal in MongoDB."""
        doc = self._to_document(meal)
        
        try:
            result = await self._collection.insert_one(doc)
            meal.id = str(result.inserted_id)
            
            logger.info(
                "meal_created",
                meal_id=meal.id,
                user_id=meal.user_id
            )
            
            return meal
            
        except Exception as e:
            logger.error("meal_create_failed", error=str(e))
            raise
    
    async def get_by_id(
        self,
        meal_id: str,
        user_id: str
    ) -> Optional[MealEntry]:
        """Recupera meal per ID."""
        from bson import ObjectId
        
        try:
            doc = await self._collection.find_one({
                "_id": ObjectId(meal_id),
                "user_id": user_id
            })
            
            if not doc:
                return None
            
            return self._from_document(doc)
            
        except Exception as e:
            logger.error("meal_get_failed", meal_id=meal_id, error=str(e))
            raise
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 20,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None
    ) -> List[MealEntry]:
        """Lista meals con pagination."""
        query = {"user_id": user_id}
        
        if after:
            query["timestamp"] = {"$gt": after}
        if before:
            query["timestamp"] = {"$lt": before}
        
        cursor = self._collection.find(query) \
            .sort("timestamp", -1) \
            .limit(limit)
        
        docs = await cursor.to_list(length=limit)
        
        return [self._from_document(doc) for doc in docs]
    
    async def update(self, meal: MealEntry) -> MealEntry:
        """Aggiorna meal esistente."""
        from bson import ObjectId
        
        doc = self._to_document(meal)
        doc["updated_at"] = datetime.utcnow()
        
        result = await self._collection.update_one(
            {
                "_id": ObjectId(meal.id),
                "user_id": meal.user_id
            },
            {"$set": doc}
        )
        
        if result.matched_count == 0:
            raise ValueError(f"Meal {meal.id} not found")
        
        logger.info("meal_updated", meal_id=meal.id)
        
        return meal
    
    async def delete(self, meal_id: str, user_id: str) -> bool:
        """Cancella meal."""
        from bson import ObjectId
        
        result = await self._collection.delete_one({
            "_id": ObjectId(meal_id),
            "user_id": user_id
        })
        
        deleted = result.deleted_count > 0
        
        if deleted:
            logger.info("meal_deleted", meal_id=meal_id)
        
        return deleted
    
    async def exists_by_idempotency_key(
        self,
        idempotency_key: str,
        user_id: str
    ) -> bool:
        """Check idempotency key."""
        count = await self._collection.count_documents({
            "idempotency_key": idempotency_key,
            "user_id": user_id
        }, limit=1)
        
        return count > 0
    
    def _to_document(self, meal: MealEntry) -> dict:
        """Convert domain model to MongoDB document."""
        return {
            "user_id": meal.user_id,
            "name": meal.name,
            "quantity_g": meal.quantity_g,
            "timestamp": meal.timestamp,
            "source": meal.source,
            "nutrients": {
                "calories": meal.calories,
                "protein": meal.protein,
                "carbs": meal.carbs,
                "fat": meal.fat,
                "fiber": meal.fiber,
                "sugar": meal.sugar,
                "sodium": meal.sodium,
            },
            "barcode": meal.barcode,
            "image_url": meal.image_url,
            "analysis_id": meal.analysis_id,
            "idempotency_key": meal.idempotency_key,
            "created_at": meal.created_at,
            "updated_at": datetime.utcnow(),
            "version": 1
        }
    
    def _from_document(self, doc: dict) -> MealEntry:
        """Convert MongoDB document to domain model."""
        nutrients = doc.get("nutrients", {})
        
        return MealEntry(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            name=doc["name"],
            quantity_g=doc["quantity_g"],
            timestamp=doc["timestamp"],
            source=doc.get("source", "MANUAL"),
            calories=nutrients.get("calories"),
            protein=nutrients.get("protein"),
            carbs=nutrients.get("carbs"),
            fat=nutrients.get("fat"),
            fiber=nutrients.get("fiber"),
            sugar=nutrients.get("sugar"),
            sodium=nutrients.get("sodium"),
            barcode=doc.get("barcode"),
            image_url=doc.get("image_url"),
            analysis_id=doc.get("analysis_id"),
            idempotency_key=doc.get("idempotency_key"),
            created_at=doc.get("created_at"),
        )
```

---

## 🎬 IMPLEMENTATION ROADMAP

### Fase 0: Setup & Preparation (4-5 ore)

**Obiettivo**: Preparare ambiente e dipendenze

#### Task 0.1: Environment Setup
- [ ] Creare `.env.example` con tutte le chiavi necessarie:
  ```bash
  # API Keys
  OPENAI_API_KEY=sk-...
  USDA_API_KEY=your-usda-key
  
  # MongoDB
  MONGODB_URI=mongodb://localhost:27017
  MONGODB_DATABASE=nutrifit
  
  # Redis (optional)
  REDIS_URI=redis://localhost:6379
  REDIS_ENABLED=false
  
  # App Config
  ENV=development
  LOG_LEVEL=INFO
  ```

- [ ] Update `pyproject.toml` dependencies:
  ```toml
  [tool.poetry.dependencies]
  python = "^3.11"
  fastapi = "^0.104.0"
  strawberry-graphql = "^0.216.0"
  motor = "^3.3.0"  # MongoDB async driver
  redis = "^5.0.0"
  httpx = "^0.25.0"
  pydantic = "^2.4.0"
  pydantic-settings = "^2.0.0"
  structlog = "^23.2.0"
  
  [tool.poetry.group.dev.dependencies]
  pytest = "^7.4.0"
  pytest-asyncio = "^0.21.0"
  pytest-cov = "^4.1.0"
  mypy = "^1.6.0"
  black = "^23.10.0"
  ruff = "^0.1.0"
  ```

#### Task 0.2: Docker Setup
- [ ] Creare `docker-compose.yml` per MongoDB:
  ```yaml
  version: '3.8'
  
  services:
    mongodb:
      image: mongo:7.0
      container_name: nutrifit-mongo
      ports:
        - "27017:27017"
      environment:
        MONGO_INITDB_DATABASE: nutrifit
      volumes:
        - mongodb_data:/data/db
        - ./scripts/mongo-init.js:/docker-entrypoint-initdb.d/init.js:ro
      restart: unless-stopped
    
    redis:
      image: redis:7-alpine
      container_name: nutrifit-redis
      ports:
        - "6379:6379"
      restart: unless-stopped
  
  volumes:
    mongodb_data:
  ```

- [ ] Creare `scripts/mongo-init.js`:
  ```javascript
  // Initialize database
  db = db.getSiblingDB('nutrifit');
  
  // Create collections
  db.createCollection('meals');
  db.createCollection('meal_analysis');
  db.createCollection('activity_events');
  db.createCollection('health_totals');
  
  // Create indexes
  db.meals.createIndex({ "user_id": 1, "timestamp": -1 });
  db.meals.createIndex({ "user_id": 1, "created_at": -1 });
  db.meals.createIndex({ "idempotency_key": 1 }, { sparse: true, unique: true });
  db.meals.createIndex({ "analysis_id": 1 }, { sparse: true });
  
  db.meal_analysis.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });
  db.meal_analysis.createIndex({ "user_id": 1, "created_at": -1 });
  db.meal_analysis.createIndex({ "idempotency_key": 1 }, { sparse: true, unique: true });
  
  print('MongoDB initialized successfully');
  ```

#### Task 0.3: Project Structure
- [ ] Creare directory structure completa (vedi sezione File System Architecture)
- [ ] Creare tutti i file `__init__.py`
- [ ] Setup `pytest.ini` e `mypy.ini`

**Deliverable**: Ambiente pronto con MongoDB running e struttura folders

---

### Fase 1: Foundation Layer (5-6 ore)

**Obiettivo**: Domain models, value objects, exceptions

#### Task 1.1: Domain Models

- [ ] **File**: `domain/meal/persistence/models.py`
  ```python
  from dataclasses import dataclass
  from datetime import datetime
  from typing import Optional
  
  @dataclass
  class MealEntry:
      """Domain model per meal entry."""
      user_id: str
      name: str
      quantity_g: float
      timestamp: datetime
      source: str  # PHOTO | BARCODE | DESCRIPTION | MANUAL
      
      # Nutrients (denormalized)
      calories: Optional[int] = None
      protein: Optional[float] = None
      carbs: Optional[float] = None
      fat: Optional[float] = None
      fiber: Optional[float] = None
      sugar: Optional[float] = None
      sodium: Optional[float] = None
      
      # Optional metadata
      id: Optional[str] = None
      barcode: Optional[str] = None
      image_url: Optional[str] = None
      analysis_id: Optional[str] = None
      idempotency_key: Optional[str] = None
      created_at: Optional[datetime] = None
      
      def __post_init__(self):
          if self.created_at is None:
              self.created_at = datetime.utcnow()
          if self.timestamp is None:
              self.timestamp = datetime.utcnow()
  ```

- [ ] **File**: `domain/meal/nutrition/models.py`
  ```python
  from dataclasses import dataclass
  from enum import Enum
  from typing import Optional
  
  class NutrientSource(str, Enum):
      """Source of nutrient data."""
      USDA = "USDA"
      BARCODE_DB = "BARCODE_DB"
      CATEGORY_PROFILE = "CATEGORY_PROFILE"
      AI_ESTIMATE = "AI_ESTIMATE"
  
  @dataclass
  class NutrientProfile:
      """Complete nutrient profile for a food item."""
      # Macronutrients (required)
      calories: int
      protein: float
      carbs: float
      fat: float
      
      # Micronutrients (optional)
      fiber: Optional[float] = None
      sugar: Optional[float] = None
      sodium: Optional[float] = None
      
      # Metadata
      source: NutrientSource = NutrientSource.USDA
      confidence: float = 0.0
      quantity_g: float = 100.0  # Reference quantity
      
      def scale_to_quantity(self, target_g: float) -> 'NutrientProfile':
          """Scale nutrients to target quantity."""
          factor = target_g / self.quantity_g
          
          return NutrientProfile(
              calories=int(self.calories * factor),
              protein=round(self.protein * factor, 1),
              carbs=round(self.carbs * factor, 1),
              fat=round(self.fat * factor, 1),
              fiber=round(self.fiber * factor, 1) if self.fiber else None,
              sugar=round(self.sugar * factor, 1) if self.sugar else None,
              sodium=round(self.sodium * factor, 1) if self.sodium else None,
              source=self.source,
              confidence=self.confidence,
              quantity_g=target_g
          )
  ```

- [ ] **File**: `domain/meal/recognition/models.py`
  ```python
  from dataclasses import dataclass
  from typing import List, Optional
  
  @dataclass
  class RecognizedFoodItem:
      """Single food item recognized from photo/text."""
      label: str           # Machine-readable (es. "pasta")
      display_name: str    # User-friendly (es. "Spaghetti")
      quantity_g: float    # Estimated quantity
      confidence: float    # 0.0 - 1.0
      category: Optional[str] = None  # USDA category
  
  @dataclass
  class FoodRecognitionResult:
      """Complete recognition result."""
      items: List[RecognizedFoodItem]
      dish_name: Optional[str] = None  # Overall dish name
      confidence: float = 0.0          # Average confidence
      processing_time_ms: int = 0
  ```

#### Task 1.2: Shared Value Objects

- [ ] **File**: `domain/shared/value_objects.py`
  ```python
  from dataclasses import dataclass
  from datetime import datetime
  import re
  
  @dataclass(frozen=True)
  class UserId:
      """User ID value object."""
      value: str
      
      def __post_init__(self):
          if not self.value:
              raise ValueError("UserId cannot be empty")
  
  @dataclass(frozen=True)
  class Barcode:
      """Barcode value object with validation."""
      value: str
      
      def __post_init__(self):
          if not re.match(r'^\d{8,13}$', self.value):
              raise ValueError(f"Invalid barcode: {self.value}")
  
  @dataclass(frozen=True)
  class AnalysisId:
      """Analysis ID value object."""
      value: str
      
      @classmethod
      def generate(cls) -> 'AnalysisId':
          import uuid
          return cls(f"analysis_{uuid.uuid4().hex[:12]}")
  ```

#### Task 1.3: Domain Exceptions

- [ ] **File**: `domain/meal/exceptions.py`
  ```python
  class MealDomainError(Exception):
      """Base exception for meal domain."""
      pass
  
  class RecognitionError(MealDomainError):
      """AI recognition failed."""
      pass
  
  class EnrichmentError(MealDomainError):
      """Nutrient enrichment failed."""
      pass
  
  class BarcodeNotFoundError(MealDomainError):
      """Barcode not found in database."""
      pass
  
  class InvalidQuantityError(MealDomainError):
      """Invalid quantity specified."""
      pass
  
  class MealNotFoundError(MealDomainError):
      """Meal not found."""
      pass
  
  class IdempotencyConflictError(MealDomainError):
      """Idempotency key already used."""
      pass
  ```

**Tests**:
- [ ] `tests/unit/domain/meal/test_models.py` (MealEntry, NutrientProfile scaling)
- [ ] `tests/unit/domain/shared/test_value_objects.py` (validation)

**Deliverable**: Domain foundation completo con tests

---

### Fase 2: USDA Integration (8-10 ore)

**Obiettivo**: Complete USDA nutrient enrichment service

#### Task 2.1: USDA Mapper

- [ ] **File**: `domain/meal/nutrition/usda/mapper.py`
  ```python
  from typing import Dict, Any, Optional
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  # USDA nutrient IDs mapping
  NUTRIENT_IDS = {
      "calories": 1008,     # Energy (kcal)
      "protein": 1003,      # Protein (g)
      "carbs": 1005,        # Carbohydrates (g)
      "fat": 1004,          # Total lipid (fat) (g)
      "fiber": 1079,        # Fiber, total dietary (g)
      "sugar": 2000,        # Sugars, total (g)
      "sodium": 1093,       # Sodium (mg)
  }
  
  class USDAMapper:
      """Map USDA API responses to NutrientProfile."""
      
      def map_food_to_profile(
          self,
          usda_food: Dict[str, Any]
      ) -> NutrientProfile:
          """
          Convert USDA food item to NutrientProfile.
          
          Args:
              usda_food: USDA API response (single food item)
              
          Returns:
              NutrientProfile per 100g
          """
          nutrients = usda_food.get("foodNutrients", [])
          
          # Extract nutrients by ID
          def get_nutrient(nutrient_id: int, default: float = 0.0) -> float:
              for nutrient in nutrients:
                  if nutrient.get("nutrientId") == nutrient_id:
                      value = nutrient.get("value", default)
                      return float(value)
              return default
          
          return NutrientProfile(
              calories=int(get_nutrient(NUTRIENT_IDS["calories"])),
              protein=get_nutrient(NUTRIENT_IDS["protein"]),
              carbs=get_nutrient(NUTRIENT_IDS["carbs"]),
              fat=get_nutrient(NUTRIENT_IDS["fat"]),
              fiber=get_nutrient(NUTRIENT_IDS["fiber"]) or None,
              sodium=get_nutrient(NUTRIENT_IDS["sodium"]) or None,
              sugar=get_nutrient(NUTRIENT_IDS["sugar"]) or None,
              source=NutrientSource.USDA,
              confidence=0.9,
              quantity_g=100.0  # USDA sempre per 100g
          )
  ```

**Test**:
- [ ] `tests/unit/domain/meal/nutrition/test_usda_mapper.py`
  ```python
  def test_usda_mapper_extracts_nutrients():
      mapper = USDAMapper()
      
      usda_response = {
          "fdcId": 123456,
          "description": "Pasta, cooked",
          "foodNutrients": [
              {"nutrientId": 1008, "value": 131},  # calories
              {"nutrientId": 1003, "value": 5.0},  # protein
              {"nutrientId": 1005, "value": 25.0}, # carbs
              {"nutrientId": 1004, "value": 1.1},  # fat
          ]
      }
      
      profile = mapper.map_food_to_profile(usda_response)
      
      assert profile.calories == 131
      assert profile.protein == 5.0
      assert profile.carbs == 25.0
      assert profile.fat == 1.1
      assert profile.source == NutrientSource.USDA
      assert profile.confidence == 0.9
  ```

#### Task 2.2: USDA API Client

- [ ] **File**: `infrastructure/external_apis/usda_client.py`
  ```python
  import httpx
  from typing import Optional, Dict, Any
  import structlog
  from datetime import datetime
  import asyncio
  
  logger = structlog.get_logger(__name__)
  
  class RateLimiter:
      """Simple rate limiter for API calls."""
      
      def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
          self.max_requests = max_requests
          self.window = window_seconds
          self._requests: list[datetime] = []
          self._lock = asyncio.Lock()
      
      async def acquire(self) -> None:
          """Wait if rate limit exceeded."""
          async with self._lock:
              now = datetime.utcnow()
              
              # Remove requests outside window
              self._requests = [
                  r for r in self._requests
                  if (now - r).total_seconds() < self.window
              ]
              
              if len(self._requests) >= self.max_requests:
                  # Rate limited, wait
                  oldest = self._requests[0]
                  wait_time = self.window - (now - oldest).total_seconds()
                  logger.warning("usda_rate_limited", wait_seconds=wait_time)
                  await asyncio.sleep(wait_time + 1)
              
              self._requests.append(now)
  
  class USDAApiClient:
      """USDA FoodData Central API client."""
      
      BASE_URL = "https://api.nal.usda.gov/fdc/v1"
      
      def __init__(
          self,
          api_key: str,
          http_client: Optional[httpx.AsyncClient] = None
      ):
          self._api_key = api_key
          self._client = http_client or httpx.AsyncClient()
          self._rate_limiter = RateLimiter(max_requests=100, window_seconds=3600)
      
      async def search_food(
          self,
          query: str,
          page_size: int = 5
      ) -> Optional[Dict[str, Any]]:
          """
          Search food in USDA database.
          
          Args:
              query: Food name to search
              page_size: Number of results to return
              
          Returns:
              First result (best match) or None
              
          Raises:
              USDAApiError: If API call fails
          """
          await self._rate_limiter.acquire()
          
          try:
              response = await self._client.get(
                  f"{self.BASE_URL}/foods/search",
                  params={
                      "query": query,
                      "pageSize": page_size,
                      "api_key": self._api_key
                  },
                  timeout=10.0
              )
              
              response.raise_for_status()
              data = response.json()
              
              foods = data.get("foods", [])
              
              if not foods:
                  logger.info("usda_no_results", query=query)
                  return None
              
              # Return first result (best match)
              first = foods[0]
              
              logger.info(
                  "usda_search_success",
                  query=query,
                  fdc_id=first.get("fdcId"),
                  description=first.get("description")
              )
              
              return first
              
          except httpx.HTTPError as e:
              logger.error("usda_api_error", query=query, error=str(e))
              raise USDAApiError(f"USDA API error: {e}") from e
      
      async def close(self):
          """Close HTTP client."""
          await self._client.aclose()
  
  class USDAApiError(Exception):
      """USDA API call failed."""
      pass
  ```

**Test**:
- [ ] `tests/integration/test_usda_client.py` (with httpx mock)

#### Task 2.3: USDA Cache

- [ ] **File**: `infrastructure/cache/usda_cache.py`
  ```python
  from dataclasses import dataclass
  from datetime import datetime, timedelta
  from typing import Dict, Optional
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  @dataclass
  class CacheEntry:
      """Cache entry with TTL."""
      value: NutrientProfile
      timestamp: datetime
      ttl_seconds: int
  
  class USDACache:
      """
      Multi-level cache for USDA responses.
      
      Level 1: In-memory (production: Redis)
      """
      
      def __init__(self):
          self._memory: Dict[str, CacheEntry] = {}
          self._stats = {"hits": 0, "misses": 0}
      
      async def get(self, key: str) -> Optional[NutrientProfile]:
          """
          Get from cache with TTL check.
          
          Returns:
              None if not found or expired
          """
          if key in self._memory:
              entry = self._memory[key]
              age_seconds = (datetime.utcnow() - entry.timestamp).total_seconds()
              
              if age_seconds < entry.ttl_seconds:
                  self._stats["hits"] += 1
                  logger.debug("cache_hit", key=key)
                  return entry.value
              else:
                  # Expired, remove
                  del self._memory[key]
                  logger.debug("cache_expired", key=key)
          
          self._stats["misses"] += 1
          logger.debug("cache_miss", key=key)
          return None
      
      async def set(
          self,
          key: str,
          value: NutrientProfile,
          ttl: int = 3600
      ) -> None:
          """Set in cache with TTL."""
          self._memory[key] = CacheEntry(
              value=value,
              timestamp=datetime.utcnow(),
              ttl_seconds=ttl
          )
          
          logger.debug("cache_set", key=key, ttl=ttl)
      
      def get_stats(self) -> dict:
          """Cache performance stats."""
          total = self._stats["hits"] + self._stats["misses"]
          hit_rate = self._stats["hits"] / total if total > 0 else 0
          
          return {
              "hits": self._stats["hits"],
              "misses": self._stats["misses"],
              "hit_rate": f"{hit_rate:.2%}",
              "size": len(self._memory)
          }
      
      async def clear(self) -> None:
          """Clear entire cache."""
          self._memory.clear()
          logger.info("cache_cleared")
  ```

#### Task 2.4: Category Profiles (Fallback)

- [ ] **File**: `domain/meal/nutrition/usda/categories.py`
  ```python
  from typing import Dict
  
  # Static category profiles (per 100g)
  CATEGORY_PROFILES_DATA: Dict[str, Dict[str, float]] = {
      "vegetables": {
          "calories": 25,
          "protein": 2.0,
          "carbs": 5.0,
          "fat": 0.3,
          "fiber": 2.0,
      },
      "fruits": {
          "calories": 50,
          "protein": 0.5,
          "carbs": 12.0,
          "fat": 0.2,
          "fiber": 2.0,
          "sugar": 10.0,
      },
      "meat": {
          "calories": 200,
          "protein": 20.0,
          "carbs": 0.0,
          "fat": 12.0,
      },
      "fish": {
          "calories": 150,
          "protein": 22.0,
          "carbs": 0.0,
          "fat": 6.0,
      },
      "dairy": {
          "calories": 100,
          "protein": 8.0,
          "carbs": 5.0,
          "fat": 4.0,
      },
      "grains": {
          "calories": 350,
          "protein": 10.0,
          "carbs": 70.0,
          "fat": 2.0,
          "fiber": 5.0,
      },
  }
  
  class CategoryProfiles:
      """Category-based fallback profiles."""
      
      def get_profile(self, category: str) -> NutrientProfile:
          """
          Get nutrient profile per 100g per category.
          
          Args:
              category: Category name (vegetables, fruits, etc)
              
          Returns:
              NutrientProfile per 100g
          """
          data = CATEGORY_PROFILES_DATA.get(category.lower())
          
          if not data:
              # Default generic profile
              data = {
                  "calories": 100,
                  "protein": 5.0,
                  "carbs": 10.0,
                  "fat": 3.0,
              }
          
          return NutrientProfile(
              calories=int(data.get("calories", 100)),
              protein=data.get("protein", 5.0),
              carbs=data.get("carbs", 10.0),
              fat=data.get("fat", 3.0),
              fiber=data.get("fiber"),
              sodium=data.get("sodium"),
              sugar=data.get("sugar"),
              source=NutrientSource.CATEGORY_PROFILE,
              confidence=0.6,
              quantity_g=100.0
          )
  ```

#### Task 2.5: Nutrition Enrichment Service

- [ ] **File**: `domain/meal/nutrition/service.py`
  ```python
  from typing import Optional
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  class NutritionEnrichmentService:
      """
      Domain service for enriching food items with nutrients.
      
      Cascade strategy:
      1. USDA search (high quality)
      2. Category profile (medium quality)
      3. Generic fallback (low quality)
      """
      
      def __init__(
          self,
          usda_client: USDAApiClient,
          usda_mapper: USDAMapper,
          usda_cache: USDACache,
          category_profiles: CategoryProfiles
      ):
          self._usda_client = usda_client
          self._usda_mapper = usda_mapper
          self._cache = usda_cache
          self._categories = category_profiles
      
      async def enrich(
          self,
          label: str,
          quantity_g: float,
          category: Optional[str] = None
      ) -> NutrientProfile:
          """
          Enrich food label with nutrients.
          
          Args:
              label: Food name (es. "pasta", "chicken")
              quantity_g: Quantity in grams
              category: Optional USDA category for fallback
              
          Returns:
              NutrientProfile scaled to quantity_g
              
          Raises:
              EnrichmentError: If all strategies fail
          """
          # Check cache first
          cache_key = f"usda:{label.lower()}"
          
          cached = await self._cache.get(cache_key)
          if cached:
              logger.debug("usda_cache_hit", label=label)
              return cached.scale_to_quantity(quantity_g)
          
          # Try USDA search
          try:
              usda_food = await self._usda_client.search_food(label)
              
              if usda_food:
                  profile = self._usda_mapper.map_food_to_profile(usda_food)
                  
                  # Cache result (1 hour TTL)
                  await self._cache.set(cache_key, profile, ttl=3600)
                  
                  logger.info(
                      "usda_enrichment_success",
                      label=label,
                      source="USDA"
                  )
                  
                  return profile.scale_to_quantity(quantity_g)
          
          except USDAApiError as e:
              logger.warning("usda_search_failed", label=label, error=str(e))
          
          # Fallback to category profile
          if category:
              logger.info(
                  "using_category_fallback",
                  label=label,
                  category=category
              )
              profile = self._categories.get_profile(category)
              return profile.scale_to_quantity(quantity_g)
          
          # Last resort: generic profile
          logger.warning("using_generic_fallback", label=label)
          profile = self._categories.get_profile("unknown")
          return profile.scale_to_quantity(quantity_g)
  ```

**Tests**:
- [ ] `tests/unit/domain/meal/nutrition/test_enrichment_service.py`
  ```python
  @pytest.mark.asyncio
  async def test_enrichment_uses_cache():
      # Arrange
      mock_cache = USDACache()
      mock_client = Mock(USDAApiClient)
      
      service = NutritionEnrichmentService(
          usda_client=mock_client,
          usda_mapper=USDAMapper(),
          usda_cache=mock_cache,
          category_profiles=CategoryProfiles()
      )
      
      # Pre-populate cache
      cached_profile = NutrientProfile(
          calories=100,
          protein=5.0,
          carbs=10.0,
          fat=2.0,
          source=NutrientSource.USDA,
          confidence=0.9,
          quantity_g=100.0
      )
      await mock_cache.set("usda:pasta", cached_profile)
      
      # Act
      result = await service.enrich("pasta", quantity_g=200)
      
      # Assert
      assert result.calories == 200  # Scaled to 200g
      assert result.protein == 10.0
      mock_client.search_food.assert_not_called()  # Cache hit
  
  @pytest.mark.asyncio
  async def test_enrichment_falls_back_to_category():
      # Arrange
      mock_client = Mock(USDAApiClient)
      mock_client.search_food.return_value = None  # USDA not found
      
      service = NutritionEnrichmentService(
          usda_client=mock_client,
          usda_mapper=USDAMapper(),
          usda_cache=USDACache(),
          category_profiles=CategoryProfiles()
      )
      
      # Act
      result = await service.enrich("tomato", quantity_g=100, category="vegetables")
      
      # Assert
      assert result.source == NutrientSource.CATEGORY_PROFILE
      assert result.calories == 25  # Vegetables category
      assert result.confidence == 0.6
  ```

**Deliverable**: USDA integration completa con fallback strategy + tests

---

### Fase 3: AI Recognition Service (7-9 ore)

**Obiettivo**: OpenAI Vision integration per food recognition

#### Task 3.1: OpenAI Client

- [ ] **File**: `infrastructure/ai/openai_client.py`
  ```python
  from openai import AsyncOpenAI
  from typing import Dict, Any, Optional
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  class OpenAIClient:
      """OpenAI API client wrapper."""
      
      def __init__(self, api_key: str):
          self._client = AsyncOpenAI(api_key=api_key)
      
      async def vision_analyze(
          self,
          image_url: str,
          prompt: str,
          response_format: Optional[Dict] = None,
          model: str = "gpt-4-vision-preview"
      ) -> Dict[str, Any]:
          """
          Analyze image with GPT-4 Vision.
          
          Args:
              image_url: URL to image
              prompt: Analysis prompt
              response_format: Optional JSON schema for structured output
              model: OpenAI model to use
              
          Returns:
              Parsed JSON response
          """
          try:
              messages = [
                  {
                      "role": "user",
                      "content": [
                          {"type": "text", "text": prompt},
                          {"type": "image_url", "image_url": {"url": image_url}}
                      ]
                  }
              ]
              
              kwargs = {
                  "model": model,
                  "messages": messages,
                  "max_tokens": 1000
              }
              
              if response_format:
                  kwargs["response_format"] = {"type": "json_object"}
              
              response = await self._client.chat.completions.create(**kwargs)
              
              content = response.choices[0].message.content
              
              if response_format:
                  import json
                  return json.loads(content)
              
              return {"text": content}
              
          except Exception as e:
              logger.error("openai_vision_error", error=str(e))
              raise OpenAIVisionError(f"OpenAI Vision API error: {e}") from e
      
      async def text_completion(
          self,
          prompt: str,
          response_format: Optional[Dict] = None,
          model: str = "gpt-4-turbo-preview"
      ) -> Dict[str, Any]:
          """
          Get text completion from OpenAI.
          
          Args:
              prompt: Completion prompt
              response_format: Optional JSON schema for structured output
              model: OpenAI model to use
              
          Returns:
              Parsed JSON response
          """
          try:
              kwargs = {
                  "model": model,
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 1000
              }
              
              if response_format:
                  kwargs["response_format"] = {"type": "json_object"}
              
              response = await self._client.chat.completions.create(**kwargs)
              
              content = response.choices[0].message.content
              
              if response_format:
                  import json
                  return json.loads(content)
              
              return {"text": content}
              
          except Exception as e:
              logger.error("openai_completion_error", error=str(e))
              raise OpenAICompletionError(f"OpenAI API error: {e}") from e
  
  class OpenAIVisionError(Exception):
      """OpenAI Vision API error."""
      pass
  
  class OpenAICompletionError(Exception):
      """OpenAI Completion API error."""
      pass
  ```

#### Task 3.2: Recognition Prompts

- [ ] **File**: `domain/meal/recognition/prompts.py`
  ```python
  # Vision recognition prompt
  VISION_RECOGNITION_PROMPT = """Analyze this meal photo and identify all food items visible.

For each food item, provide:
- label: short identifier (e.g., "pasta", "chicken", "salad")
- display_name: user-friendly name (e.g., "Spaghetti", "Grilled Chicken", "Mixed Salad")
- quantity_g: estimated quantity in grams
- confidence: confidence level (0.0 to 1.0)
- category: food category (vegetables, fruits, meat, fish, dairy, grains)

Also provide:
- dish_name: overall dish name if recognizable (e.g., "Spaghetti alla Carbonara")

Return JSON in this exact format:
{
  "dish_name": "string or null",
  "items": [
    {
      "label": "string",
      "display_name": "string",
      "quantity_g": number,
      "confidence": number,
      "category": "string"
    }
  ]
}

Be accurate with quantities. If unsure about quantity, use typical portion sizes.
"""
  
  def build_vision_prompt(hint: Optional[str] = None) -> str:
      """Build vision prompt with optional hint."""
      prompt = VISION_RECOGNITION_PROMPT
      
      if hint:
          prompt += f"\n\nUser hint: {hint}"
          prompt += "\nUse this hint to improve recognition accuracy."
      
      return prompt
  
  # Text extraction prompt
  TEXT_EXTRACTION_PROMPT = """Extract food items from this text description.

For each food item mentioned, provide:
- label: short identifier (e.g., "pizza", "salad")
- display_name: user-friendly name (e.g., "Pizza Margherita", "Green Salad")
- quantity_g: estimated quantity in grams (use typical portions if not specified)
- confidence: confidence level (0.0 to 1.0)
- category: food category (vegetables, fruits, meat, fish, dairy, grains)

Return JSON in this exact format:
{
  "items": [
    {
      "label": "string",
      "display_name": "string",
      "quantity_g": number,
      "confidence": number,
      "category": "string"
    }
  ]
}

Example input: "I ate a pizza margherita and a salad"
Example output:
{
  "items": [
    {
      "label": "pizza",
      "display_name": "Pizza Margherita",
      "quantity_g": 300,
      "confidence": 0.8,
      "category": "grains"
    },
    {
      "label": "salad",
      "display_name": "Mixed Salad",
      "quantity_g": 150,
      "confidence": 0.7,
      "category": "vegetables"
    }
  ]
}
"""
  
  # JSON schema for structured output
  RECOGNITION_JSON_SCHEMA = {
      "type": "object",
      "properties": {
          "dish_name": {"type": ["string", "null"]},
          "items": {
              "type": "array",
              "items": {
                  "type": "object",
                  "properties": {
                      "label": {"type": "string"},
                      "display_name": {"type": "string"},
                      "quantity_g": {"type": "number"},
                      "confidence": {"type": "number"},
                      "category": {"type": "string"}
                  },
                  "required": ["label", "display_name", "quantity_g", "confidence"]
              }
          }
      },
      "required": ["items"]
  }
  ```

#### Task 3.3: Food Recognition Service

- [ ] **File**: `domain/meal/recognition/service.py`
  ```python
  from typing import Optional
  import structlog
  from datetime import datetime
  
  logger = structlog.get_logger(__name__)
  
  class FoodRecognitionService:
      """Domain service for AI-powered food recognition."""
      
      def __init__(self, openai_client: OpenAIClient):
          self._client = openai_client
      
      async def recognize_from_photo(
          self,
          image_url: str,
          hint: Optional[str] = None
      ) -> FoodRecognitionResult:
          """
          Recognize food items from photo.
          
          Args:
              image_url: URL to meal photo
              hint: Optional user hint (e.g., "pasta carbonara")
              
          Returns:
              FoodRecognitionResult with recognized items
              
          Raises:
              RecognitionError: If recognition fails
          """
          start_time = datetime.utcnow()
          
          try:
              prompt = build_vision_prompt(hint)
              
              response = await self._client.vision_analyze(
                  image_url=image_url,
                  prompt=prompt,
                  response_format=RECOGNITION_JSON_SCHEMA
              )
              
              # Parse response
              items = []
              for item_data in response.get("items", []):
                  items.append(
                      RecognizedFoodItem(
                          label=item_data["label"],
                          display_name=item_data["display_name"],
                          quantity_g=float(item_data["quantity_g"]),
                          confidence=float(item_data["confidence"]),
                          category=item_data.get("category")
                      )
                  )
              
              if not items:
                  raise RecognitionError("No food items recognized")
              
              processing_time_ms = int(
                  (datetime.utcnow() - start_time).total_seconds() * 1000
              )
              
              avg_confidence = sum(i.confidence for i in items) / len(items)
              
              result = FoodRecognitionResult(
                  items=items,
                  dish_name=response.get("dish_name"),
                  confidence=avg_confidence,
                  processing_time_ms=processing_time_ms
              )
              
              logger.info(
                  "recognition_success",
                  items_count=len(items),
                  dish_name=result.dish_name,
                  avg_confidence=f"{avg_confidence:.2f}",
                  processing_time_ms=processing_time_ms
              )
              
              return result
              
          except OpenAIVisionError as e:
              logger.error("recognition_failed", error=str(e))
              raise RecognitionError(f"AI recognition failed: {e}") from e
          except Exception as e:
              logger.error("recognition_unexpected_error", error=str(e))
              raise RecognitionError(f"Unexpected error: {e}") from e
  ```

#### Task 3.4: Text Extraction Service

- [ ] **File**: `domain/meal/recognition/text_extractor.py`
  ```python
  from typing import List
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  class TextFoodExtractor:
      """Extract food items from text descriptions."""
      
      def __init__(self, openai_client: OpenAIClient):
          self._client = openai_client
      
      async def extract_from_text(
          self,
          description: str
      ) -> List[RecognizedFoodItem]:
          """
          Extract food items from text.
          
          Args:
              description: Text description (e.g., "I ate pizza and salad")
              
          Returns:
              List of RecognizedFoodItem
              
          Raises:
              RecognitionError: If extraction fails
          """
          try:
              prompt = f"{TEXT_EXTRACTION_PROMPT}\n\nText: {description}"
              
              response = await self._client.text_completion(
                  prompt=prompt,
                  response_format={"type": "json_object"}
              )
              
              items = []
              for item_data in response.get("items", []):
                  items.append(
                      RecognizedFoodItem(
                          label=item_data["label"],
                          display_name=item_data["display_name"],
                          quantity_g=float(item_data["quantity_g"]),
                          confidence=float(item_data["confidence"]),
                          category=item_data.get("category")
                      )
                  )
              
              if not items:
                  raise RecognitionError("No food items extracted from text")
              
              logger.info(
                  "text_extraction_success",
                  description=description[:50],
                  items_count=len(items)
              )
              
              return items
              
          except OpenAICompletionError as e:
              logger.error("text_extraction_failed", error=str(e))
              raise RecognitionError(f"Text extraction failed: {e}") from e
  ```

**Tests**:
- [ ] `tests/unit/domain/meal/recognition/test_recognition_service.py`
- [ ] `tests/unit/domain/meal/recognition/test_text_extractor.py`
- [ ] `tests/integration/test_openai_client.py` (with mocks)

**Deliverable**: AI recognition complete con photo + text extraction

---

### Fase 4: Barcode Service (4-5 ore)

**Obiettivo**: OpenFoodFacts integration

#### Task 4.1: OpenFoodFacts Client

- [ ] **File**: `infrastructure/external_apis/openfoodfacts_client.py`
  ```python
  import httpx
  from typing import Optional, Dict, Any
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  class OpenFoodFactsClient:
      """OpenFoodFacts API client."""
      
      BASE_URL = "https://world.openfoodfacts.org/api/v2"
      
      def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
          self._client = http_client or httpx.AsyncClient()
      
      async def get_product(self, barcode: str) -> Optional[Dict[str, Any]]:
          """
          Get product by barcode.
          
          Args:
              barcode: Product barcode (8-13 digits)
              
          Returns:
              Product data or None if not found
              
          Raises:
              OpenFoodFactsError: If API call fails
          """
          try:
              response = await self._client.get(
                  f"{self.BASE_URL}/product/{barcode}",
                  timeout=10.0
              )
              
              response.raise_for_status()
              data = response.json()
              
              if data.get("status") != 1:
                  logger.info("barcode_not_found", barcode=barcode)
                  return None
              
              product = data.get("product")
              
              logger.info(
                  "barcode_found",
                  barcode=barcode,
                  product_name=product.get("product_name")
              )
              
              return product
              
          except httpx.HTTPError as e:
              logger.error("openfoodfacts_api_error", barcode=barcode, error=str(e))
              raise OpenFoodFactsError(f"OpenFoodFacts API error: {e}") from e
      
      async def close(self):
          """Close HTTP client."""
          await self._client.aclose()
  
  class OpenFoodFactsError(Exception):
      """OpenFoodFacts API error."""
      pass
  ```

#### Task 4.2: OpenFoodFacts Mapper

- [ ] **File**: `domain/meal/barcode/openfoodfacts/mapper.py`
  ```python
  from typing import Dict, Any
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  class OpenFoodFactsMapper:
      """Map OpenFoodFacts responses to domain models."""
      
      def map_to_product(self, off_product: Dict[str, Any]) -> 'Product':
          """
          Convert OpenFoodFacts product to Product model.
          
          Args:
              off_product: OpenFoodFacts API response
              
          Returns:
              Product domain model
          """
          nutriments = off_product.get("nutriments", {})
          
          def get_nutrient(key: str, scale: float = 1.0) -> Optional[float]:
              """Get nutrient value scaled to per 100g."""
              value = nutriments.get(f"{key}_100g")
              if value is None:
                  return None
              return float(value) * scale
          
          return Product(
              barcode=off_product.get("code", ""),
              name=off_product.get("product_name", "Unknown Product"),
              brand=off_product.get("brands"),
              category=off_product.get("categories"),
              # Nutrients per 100g
              calories=int(get_nutrient("energy-kcal") or 0),
              protein=get_nutrient("proteins"),
              carbs=get_nutrient("carbohydrates"),
              fat=get_nutrient("fat"),
              fiber=get_nutrient("fiber"),
              sugar=get_nutrient("sugars"),
              sodium=get_nutrient("sodium", scale=1000),  # mg
              image_url=off_product.get("image_url")
          )
      
      def map_to_nutrient_profile(
          self,
          off_product: Dict[str, Any]
      ) -> NutrientProfile:
          """
          Convert OpenFoodFacts product to NutrientProfile.
          
          Args:
              off_product: OpenFoodFacts API response
              
          Returns:
              NutrientProfile per 100g
          """
          nutriments = off_product.get("nutriments", {})
          
          def get_nutrient(key: str, default: float = 0.0) -> float:
              value = nutriments.get(f"{key}_100g")
              return float(value) if value is not None else default
          
          return NutrientProfile(
              calories=int(get_nutrient("energy-kcal")),
              protein=get_nutrient("proteins"),
              carbs=get_nutrient("carbohydrates"),
              fat=get_nutrient("fat"),
              fiber=get_nutrient("fiber") or None,
              sugar=get_nutrient("sugars") or None,
              sodium=get_nutrient("sodium", default=0.0) * 1000 or None,  # mg
              source=NutrientSource.BARCODE_DB,
              confidence=1.0,  # Barcode = high confidence
              quantity_g=100.0
          )
  ```

#### Task 4.3: Barcode Service

- [ ] **File**: `domain/meal/barcode/service.py`
  ```python
  from typing import Optional
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  class BarcodeService:
      """Domain service for barcode lookups."""
      
      def __init__(
          self,
          off_client: OpenFoodFactsClient,
          off_mapper: OpenFoodFactsMapper
      ):
          self._client = off_client
          self._mapper = off_mapper
      
      async def lookup(self, barcode: str) -> Optional['Product']:
          """
          Lookup product by barcode.
          
          Args:
              barcode: Product barcode
              
          Returns:
              Product or None if not found
              
          Raises:
              BarcodeNotFoundError: If barcode not in database
          """
          try:
              off_product = await self._client.get_product(barcode)
              
              if not off_product:
                  raise BarcodeNotFoundError(f"Barcode {barcode} not found")
              
              product = self._mapper.map_to_product(off_product)
              
              logger.info(
                  "barcode_lookup_success",
                  barcode=barcode,
                  product_name=product.name
              )
              
              return product
              
          except OpenFoodFactsError as e:
              logger.error("barcode_lookup_failed", barcode=barcode, error=str(e))
              raise BarcodeNotFoundError(f"Barcode lookup failed: {e}") from e
      
      async def get_nutrients(
          self,
          barcode: str,
          quantity_g: float
      ) -> NutrientProfile:
          """
          Get nutrient profile for barcode.
          
          Args:
              barcode: Product barcode
              quantity_g: Quantity consumed
              
          Returns:
              NutrientProfile scaled to quantity_g
          """
          off_product = await self._client.get_product(barcode)
          
          if not off_product:
              raise BarcodeNotFoundError(f"Barcode {barcode} not found")
          
          profile = self._mapper.map_to_nutrient_profile(off_product)
          
          return profile.scale_to_quantity(quantity_g)
  ```

**Tests**:
- [ ] `tests/unit/domain/meal/barcode/test_barcode_service.py`
- [ ] `tests/integration/test_openfoodfacts_client.py` (with mocks)

**Deliverable**: Barcode service complete

---

### Fase 5: Orchestration Layer (6-8 ore)

**Obiettivo**: Coordinare servizi atomici per analyze* mutations

#### Task 5.1: Photo Meal Orchestrator

- [ ] **File**: `domain/meal/orchestration/photo_analyzer.py`
  ```python
  from typing import List
  import structlog
  from datetime import datetime
  
  logger = structlog.get_logger(__name__)
  
  class PhotoMealOrchestrator:
      """Orchestrate photo meal analysis workflow."""
      
      def __init__(
          self,
          recognition_service: FoodRecognitionService,
          nutrition_service: NutritionEnrichmentService
      ):
          self._recognition = recognition_service
          self._nutrition = nutrition_service
      
      async def analyze(
          self,
          photo_url: str,
          user_id: str,
          dish_hint: Optional[str] = None
      ) -> 'MealAnalysis':
          """
          Analyze meal from photo.
          
          Workflow:
          1. Recognize food items (AI Vision)
          2. Enrich each item with nutrients (USDA)
          3. Build unified analysis result
          
          Args:
              photo_url: URL to meal photo
              user_id: User ID
              dish_hint: Optional hint for better recognition
              
          Returns:
              MealAnalysis with enriched items
          """
          start_time = datetime.utcnow()
          
          # Step 1: Recognize food items
          logger.info("analyzing_photo", user_id=user_id)
          
          recognition_result = await self._recognition.recognize_from_photo(
              image_url=photo_url,
              hint=dish_hint
          )
          
          # Step 2: Enrich each item with nutrients
          enriched_items = []
          
          for item in recognition_result.items:
              try:
                  nutrients = await self._nutrition.enrich(
                      label=item.label,
                      quantity_g=item.quantity_g,
                      category=item.category
                  )
                  
                  enriched_items.append(
                      EnrichedFoodItem(
                          label=item.label,
                          display_name=item.display_name,
                          quantity_g=item.quantity_g,
                          confidence=item.confidence,
                          nutrients=nutrients
                      )
                  )
                  
              except EnrichmentError as e:
                  logger.warning(
                      "enrichment_failed_for_item",
                      label=item.label,
                      error=str(e)
                  )
                  # Skip item if enrichment fails
                  continue
          
          if not enriched_items:
              raise RecognitionError("No items could be enriched with nutrients")
          
          # Step 3: Calculate totals
          total_calories = sum(item.nutrients.calories for item in enriched_items)
          
          processing_time_ms = int(
              (datetime.utcnow() - start_time).total_seconds() * 1000
          )
          
          analysis = MealAnalysis(
              user_id=user_id,
              source="PHOTO",
              dish_name=recognition_result.dish_name,
              items=enriched_items,
              total_calories=total_calories,
              photo_url=photo_url,
              processing_time_ms=processing_time_ms
          )
          
          logger.info(
              "photo_analysis_complete",
              user_id=user_id,
              items_count=len(enriched_items),
              total_calories=total_calories,
              processing_time_ms=processing_time_ms
          )
          
          return analysis
  ```

#### Task 5.2: Barcode Meal Orchestrator

- [ ] **File**: `domain/meal/orchestration/barcode_analyzer.py`
  ```python
  from typing import List
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  class BarcodeMealOrchestrator:
      """Orchestrate barcode meal analysis workflow."""
      
      def __init__(self, barcode_service: BarcodeService):
          self._barcode = barcode_service
      
      async def analyze(
          self,
          barcode: str,
          user_id: str,
          quantity_g: float
      ) -> 'MealAnalysis':
          """
          Analyze meal from barcode.
          
          Workflow:
          1. Lookup product in OpenFoodFacts
          2. Scale nutrients to quantity
          3. Build analysis result
          
          Args:
              barcode: Product barcode
              user_id: User ID
              quantity_g: Quantity consumed
              
          Returns:
              MealAnalysis with single enriched item
          """
          logger.info("analyzing_barcode", user_id=user_id, barcode=barcode)
          
          # Lookup product
          product = await self._barcode.lookup(barcode)
          
          # Get nutrients scaled to quantity
          nutrients = await self._barcode.get_nutrients(barcode, quantity_g)
          
          # Build single item
          item = EnrichedFoodItem(
              label=product.name.lower().replace(" ", "_"),
              display_name=product.name,
              quantity_g=quantity_g,
              confidence=1.0,  # Barcode = high confidence
              nutrients=nutrients
          )
          
          analysis = MealAnalysis(
              user_id=user_id,
              source="BARCODE",
              dish_name=product.name,
              items=[item],
              total_calories=nutrients.calories,
              processing_time_ms=0
          )
          
          logger.info(
              "barcode_analysis_complete",
              user_id=user_id,
              product_name=product.name,
              calories=nutrients.calories
          )
          
          return analysis
  ```

#### Task 5.3: Text Meal Orchestrator

- [ ] **File**: `domain/meal/orchestration/text_analyzer.py`
  ```python
  from typing import List
  import structlog
  
  logger = structlog.get_logger(__name__)
  
  class TextMealOrchestrator:
      """Orchestrate text description meal analysis workflow."""
      
      def __init__(
          self,
          text_extractor: TextFoodExtractor,
          nutrition_service: NutritionEnrichmentService
      ):
          self._extractor = text_extractor
          self._nutrition = nutrition_service
      
      async def analyze(
          self,
          description: str,
          user_id: str
      ) -> 'MealAnalysis':
          """
          Analyze meal from text description.
          
          Workflow:
          1. Extract food items from text (AI)
          2. Enrich each item with nutrients (USDA)
          3. Build analysis result
          
          Args:
              description: Text description (e.g., "pizza and salad")
              user_id: User ID
              
          Returns:
              MealAnalysis with enriched items
          """
          logger.info("analyzing_text", user_id=user_id)
          
          # Step 1: Extract items from text
          recognized_items = await self._extractor.extract_from_text(description)
          
          # Step 2: Enrich with nutrients
          enriched_items = []
          
          for item in recognized_items:
              try:
                  nutrients = await self._nutrition.enrich(
                      label=item.label,
                      quantity_g=item.quantity_g,
                      category=item.category
                  )
                  
                  enriched_items.append(
                      EnrichedFoodItem(
                          label=item.label,
                          display_name=item.display_name,
                          quantity_g=item.quantity_g,
                          confidence=item.confidence,
                          nutrients=nutrients
                      )
                  )
                  
              except EnrichmentError as e:
                  logger.warning(
                      "enrichment_failed_for_item",
                      label=item.label,
                      error=str(e)
                  )
                  continue
          
          if not enriched_items:
              raise RecognitionError("No items could be extracted and enriched")
          
          # Step 3: Calculate totals
          total_calories = sum(item.nutrients.calories for item in enriched_items)
          
          analysis = MealAnalysis(
              user_id=user_id,
              source="DESCRIPTION",
              items=enriched_items,
              total_calories=total_calories,
              processing_time_ms=0
          )
          
          logger.info(
              "text_analysis_complete",
              user_id=user_id,
              items_count=len(enriched_items),
              total_calories=total_calories
          )
          
          return analysis
  ```

#### Task 5.4: Unified Analysis Models

- [ ] **File**: `domain/meal/orchestration/models.py`
  ```python
  from dataclasses import dataclass
  from typing import List, Optional
  from datetime import datetime
  
  @dataclass
  class EnrichedFoodItem:
      """Food item with nutrients attached."""
      label: str
      display_name: str
      quantity_g: float
      confidence: float
      nutrients: NutrientProfile
  
  @dataclass
  class MealAnalysis:
      """
      Unified meal analysis result.
      
      Used by all analyze* mutations.
      """
      user_id: str
      source: str  # PHOTO | BARCODE | DESCRIPTION
      items: List[EnrichedFoodItem]
      total_calories: int
      
      # Optional fields
      dish_name: Optional[str] = None
      photo_url: Optional[str] = None
      processing_time_ms: int = 0
      
      # Metadata (set by persistence layer)
      id: Optional[str] = None
      created_at: Optional[datetime] = None
      status: str = "PENDING"  # PENDING | COMPLETED | FAILED
      
      def __post_init__(self):
          if self.created_at is None:
              self.created_at = datetime.utcnow()
  ```

**Tests**:
- [ ] `tests/unit/domain/meal/orchestration/test_photo_analyzer.py`
- [ ] `tests/unit/domain/meal/orchestration/test_barcode_analyzer.py`
- [ ] `tests/unit/domain/meal/orchestration/test_text_analyzer.py`

**Deliverable**: Orchestration layer complete

---

### Fase 6: Repository Layer & MongoDB (6-7 ore)

**Obiettivo**: Implementare persistenza MongoDB con repository pattern

*(Già coperto in dettaglio nella sezione MongoDB Schema Design)*

#### Task 6.1: MongoDB Setup
- [ ] Implementare `infrastructure/database/mongodb.py`
- [ ] Creare script `scripts/setup_mongodb.py` per indexes

#### Task 6.2: Meal Repository
- [ ] Implementare `MongoMealRepository`
- [ ] Implementare `AnalysisRepository` per storage temporaneo

#### Task 6.3: Tests
- [ ] `tests/integration/test_mongodb_repository.py`
- [ ] `tests/integration/test_analysis_repository.py`

**Deliverable**: Persistenza MongoDB completa

---

### Fase 7: Application Layer (5-6 ore)

**Obiettivo**: Use cases che coordinano domain + infrastructure

#### Task 7.1: Analyze Use Cases

- [ ] **File**: `application/meal/analyze_photo.py`
  ```python
  class AnalyzeMealPhotoUseCase:
      """Use case: analyze meal from photo."""
      
      def __init__(
          self,
          photo_orchestrator: PhotoMealOrchestrator,
          analysis_repository: AnalysisRepository,
          idempotency_manager: IdempotencyManager
      ):
          self._orchestrator = photo_orchestrator
          self._analysis_repo = analysis_repository
          self._idempotency = idempotency_manager
      
      async def execute(
          self,
          photo_url: str,
          user_id: str,
          dish_hint: Optional[str] = None,
          idempotency_key: Optional[str] = None
      ) -> MealAnalysis:
          """Execute photo analysis."""
          # Check idempotency
          if idempotency_key:
              existing = await self._idempotency.get_result(idempotency_key)
              if existing:
                  return existing
          
          # Orchestrate analysis
          analysis = await self._orchestrator.analyze(
              photo_url=photo_url,
              user_id=user_id,
              dish_hint=dish_hint
          )
          
          # Save to temporary storage
          analysis.id = AnalysisId.generate().value
          await self._analysis_repo.save(analysis)
          
          # Store idempotency
          if idempotency_key:
              await self._idempotency.store(idempotency_key, analysis)
          
          return analysis
  ```

- [ ] Implementare `AnalyzeMealBarcodeUseCase`
- [ ] Implementare `AnalyzeMealDescriptionUseCase`

#### Task 7.2: Confirm Use Case

- [ ] **File**: `application/meal/confirm_meal.py`
  ```python
  class ConfirmMealUseCase:
      """Use case: confirm and persist meal analysis."""
      
      def __init__(
          self,
          analysis_repository: AnalysisRepository,
          meal_repository: IMealRepository,
          idempotency_manager: IdempotencyManager
      ):
          self._analysis_repo = analysis_repository
          self._meal_repo = meal_repository
          self._idempotency = idempotency_manager
      
      async def execute(
          self,
          analysis_id: str,
          accepted_indexes: List[int],
          user_id: str,
          idempotency_key: Optional[str] = None
      ) -> List[MealEntry]:
          """Execute meal confirmation."""
          # Check idempotency
          if idempotency_key:
              existing = await self._idempotency.get_result(idempotency_key)
              if existing:
                  return existing
          
          # Load analysis from temporary storage
          analysis = await self._analysis_repo.get(analysis_id, user_id)
          
          if not analysis:
              raise MealNotFoundError(f"Analysis {analysis_id} not found")
          
          if analysis.status != "PENDING":
              raise ValueError(f"Analysis {analysis_id} already {analysis.status}")
          
          # Create MealEntry for each accepted item
          created_meals = []
          
          for index in accepted_indexes:
              if index >= len(analysis.items):
                  continue
              
              item = analysis.items[index]
              
              meal = MealEntry(
                  user_id=user_id,
                  name=item.display_name,
                  quantity_g=item.quantity_g,
                  timestamp=datetime.utcnow(),
                  source=analysis.source,
                  calories=item.nutrients.calories,
                  protein=item.nutrients.protein,
                  carbs=item.nutrients.carbs,
                  fat=item.nutrients.fat,
                  fiber=item.nutrients.fiber,
                  sugar=item.nutrients.sugar,
                  sodium=item.nutrients.sodium,
                  image_url=analysis.photo_url,
                  analysis_id=analysis_id,
                  idempotency_key=idempotency_key
              )
              
              # Persist to MongoDB
              saved = await self._meal_repo.create(meal)
              created_meals.append(saved)
          
          # Update analysis status
          analysis.status = "COMPLETED"
          await self._analysis_repo.update(analysis)
          
          # Store idempotency
          if idempotency_key:
              await self._idempotency.store(idempotency_key, created_meals)
          
          logger.info(
              "meal_confirmed",
              analysis_id=analysis_id,
              meals_created=len(created_meals)
          )
          
          return created_meals
  ```

#### Task 7.3: CRUD Use Cases

- [ ] Implementare `UpdateMealUseCase`
- [ ] Implementare `DeleteMealUseCase`
- [ ] Implementare `QueryMealsUseCase`

**Tests**:
- [ ] `tests/unit/application/meal/test_analyze_usecase.py`
- [ ] `tests/unit/application/meal/test_confirm_usecase.py`

**Deliverable**: Application layer completo

---

### Fase 8: GraphQL Layer (6-7 ore)

**Obiettivo**: Aggiornare schema GraphQL e resolvers

#### Task 8.1: Update Schema

- [ ] Aggiornare `graphql/schema.graphql` con nuovo schema (vedi sezione Architettura)

#### Task 8.2: Query Resolvers

- [ ] **File**: `graphql/queries/food_recognition.py`
  ```python
  @strawberry.type
  class Query:
      @strawberry.field
      async def recognize_food(
          self,
          info: Info,
          image_url: str,
          hint: Optional[str] = None
      ) -> FoodRecognitionResult:
          """Atomic service: recognize food from image."""
          recognition_service = info.context.get_service(FoodRecognitionService)
          
          result = await recognition_service.recognize_from_photo(
              image_url=image_url,
              hint=hint
          )
          
          return result
  ```

- [ ] Implementare `enrichNutrients` query
- [ ] Rinominare `product` → `searchFoodByBarcode`

#### Task 8.3: Mutation Resolvers

- [ ] **File**: `graphql/mutations/analyze_meal.py`
  ```python
  @strawberry.type
  class Mutation:
      @strawberry.mutation
      async def analyze_meal_photo(
          self,
          info: Info,
          input: AnalyzeMealPhotoInput
      ) -> MealPhotoAnalysis:
          """Orchestration: analyze meal from photo."""
          use_case = info.context.get_use_case(AnalyzeMealPhotoUseCase)
          
          analysis = await use_case.execute(
              photo_url=input.photo_url,
              user_id=input.user_id or info.context.user_id,
              dish_hint=input.dish_hint,
              idempotency_key=input.idempotency_key
          )
          
          return analysis
  ```

- [ ] Implementare `analyzeMealBarcode`
- [ ] Implementare `analyzeMealDescription`
- [ ] Implementare `confirm*` mutations

#### Task 8.4: Remove Deprecated

- [ ] Rimuovere `logMeal` mutation
- [ ] Aggiornare tests GraphQL

**Tests**:
- [ ] `tests/e2e/test_graphql_photo_flow.py`
- [ ] `tests/e2e/test_graphql_barcode_flow.py`
- [ ] `tests/e2e/test_graphql_description_flow.py`

**Deliverable**: GraphQL API completo e funzionante

---

### Fase 9: Dependency Injection & Config (4-5 ore)

**Obiettivo**: Setup DI container e configuration

#### Task 9.1: Settings

- [ ] **File**: `infrastructure/config/settings.py`
  ```python
  from pydantic_settings import BaseSettings
  
  class Settings(BaseSettings):
      """Application settings from environment."""
      
      # Environment
      env: str = "development"
      log_level: str = "INFO"
      
      # API Keys
      openai_api_key: str
      usda_api_key: str
      
      # MongoDB
      mongodb_uri: str = "mongodb://localhost:27017"
      mongodb_database: str = "nutrifit"
      
      # Redis
      redis_uri: str = "redis://localhost:6379"
      redis_enabled: bool = False
      
      # Cache TTL
      usda_cache_ttl: int = 3600  # 1 hour
      
      class Config:
          env_file = ".env"
          case_sensitive = False
  ```

#### Task 9.2: DI Container

- [ ] **File**: `api/dependencies.py`
  ```python
  from functools import lru_cache
  from motor.motor_asyncio import AsyncIOMotorClient
  import httpx
  
  class Container:
      """Dependency injection container."""
      
      def __init__(self, settings: Settings):
          self.settings = settings
          self._setup_infrastructure()
          self._setup_domain_services()
          self._setup_use_cases()
      
      def _setup_infrastructure(self):
          """Setup infrastructure layer."""
          # MongoDB
          self.mongo_client = AsyncIOMotorClient(self.settings.mongodb_uri)
          self.mongo_db = self.mongo_client[self.settings.mongodb_database]
          
          # HTTP clients
          self.http_client = httpx.AsyncClient()
          
          # Repositories
          self.meal_repository = MongoMealRepository(self.mongo_db)
          self.analysis_repository = AnalysisRepository(self.mongo_db)
          
          # External clients
          self.openai_client = OpenAIClient(self.settings.openai_api_key)
          self.usda_client = USDAApiClient(
              api_key=self.settings.usda_api_key,
              http_client=self.http_client
          )
          self.off_client = OpenFoodFactsClient(self.http_client)
          
          # Cache
          self.usda_cache = USDACache()
      
      def _setup_domain_services(self):
          """Setup domain layer services."""
          # Recognition
          self.recognition_service = FoodRecognitionService(self.openai_client)
          self.text_extractor = TextFoodExtractor(self.openai_client)
          
          # Nutrition
          self.usda_mapper = USDAMapper()
          self.category_profiles = CategoryProfiles()
          self.nutrition_service = NutritionEnrichmentService(
              usda_client=self.usda_client,
              usda_mapper=self.usda_mapper,
              usda_cache=self.usda_cache,
              category_profiles=self.category_profiles
          )
          
          # Barcode
          self.off_mapper = OpenFoodFactsMapper()
          self.barcode_service = BarcodeService(
              off_client=self.off_client,
              off_mapper=self.off_mapper
          )
          
          # Orchestrators
          self.photo_orchestrator = PhotoMealOrchestrator(
              recognition_service=self.recognition_service,
              nutrition_service=self.nutrition_service
          )
          self.barcode_orchestrator = BarcodeMealOrchestrator(
              barcode_service=self.barcode_service
          )
          self.text_orchestrator = TextMealOrchestrator(
              text_extractor=self.text_extractor,
              nutrition_service=self.nutrition_service
          )
      
      def _setup_use_cases(self):
          """Setup application layer use cases."""
          self.idempotency_manager = IdempotencyManager()
          
          self.analyze_photo_use_case = AnalyzeMealPhotoUseCase(
              photo_orchestrator=self.photo_orchestrator,
              analysis_repository=self.analysis_repository,
              idempotency_manager=self.idempotency_manager
          )
          # ... other use cases
      
      async def close(self):
          """Cleanup resources."""
          await self.http_client.aclose()
          await self.usda_client.close()
          await self.off_client.close()
          self.mongo_client.close()
  
  @lru_cache()
  def get_container() -> Container:
      """Get singleton container."""
      settings = Settings()
      return Container(settings)
  ```

#### Task 9.3: FastAPI Integration

- [ ] Aggiornare `api/main.py` con nuovo DI

**Deliverable**: DI e config completi

---

### Fase 10: Testing & Quality (8-10 ore)

**Obiettivo**: Test coverage completo + quality checks

#### Task 10.1: Unit Tests
- [ ] Domain layer: 100% coverage
- [ ] Application layer: >90% coverage

#### Task 10.2: Integration Tests
- [ ] MongoDB repository tests
- [ ] External API clients (with mocks)

#### Task 10.3: E2E Tests
- [ ] Complete photo flow
- [ ] Complete barcode flow
- [ ] Complete text flow

#### Task 10.4: Quality Checks
- [ ] MyPy: 0 errors
- [ ] Black: formatting
- [ ] Ruff: linting
- [ ] Test coverage report

**Deliverable**: Test suite completo

---

### Fase 11: Migration & Deployment (4-5 ore)

**Obiettivo**: Migrare dati esistenti e deploy

#### Task 11.1: Data Migration

- [ ] **File**: `scripts/migrate_data.py`
  ```python
  """Migrate existing meals to new schema."""
  
  async def migrate_meals():
      # Load old meals from memory/file
      # Transform to new MealEntry model
      # Save to MongoDB
      pass
  ```

#### Task 11.2: Cleanup

- [ ] Rimuovere codice deprecato
- [ ] Update documentation
- [ ] Update README

#### Task 11.3: Deployment Verification

- [ ] Verify MongoDB running
- [ ] Verify API keys configured
- [ ] Run smoke tests

**Deliverable**: Sistema in produzione

---

## 📊 TESTING STRATEGY

### Unit Tests Structure

```python
# tests/unit/domain/meal/nutrition/test_enrichment_service.py

@pytest.fixture
def mock_usda_client():
    return Mock(spec=USDAApiClient)

@pytest.fixture
def mock_cache():
    return USDACache()

@pytest.fixture
def service(mock_usda_client, mock_cache):
    return NutritionEnrichmentService(
        usda_client=mock_usda_client,
        usda_mapper=USDAMapper(),
        usda_cache=mock_cache,
        category_profiles=CategoryProfiles()
    )

@pytest.mark.asyncio
async def test_enrich_uses_cache_first(service, mock_cache):
    """Test that cache is checked before API call."""
    # Arrange
    cached_profile = NutrientProfile(
        calories=100,
        protein=5.0,
        carbs=10.0,
        fat=2.0,
        source=NutrientSource.USDA,
        confidence=0.9,
        quantity_g=100.0
    )
    await mock_cache.set("usda:pasta", cached_profile)
    
    # Act
    result = await service.enrich("pasta", quantity_g=200)
    
    # Assert
    assert result.calories == 200  # Scaled
    assert result.protein == 10.0
    service._usda_client.search_food.assert_not_called()

@pytest.mark.asyncio
async def test_enrich_falls_back_to_category(service, mock_usda_client):
    """Test fallback to category profile when USDA fails."""
    # Arrange
    mock_usda_client.search_food.return_value = None
    
    # Act
    result = await service.enrich("tomato", quantity_g=100, category="vegetables")
    
    # Assert
    assert result.source == NutrientSource.CATEGORY_PROFILE
    assert result.calories == 25  # Vegetables profile
```

### Integration Tests

```python
# tests/integration/test_mongodb_repository.py

@pytest.fixture
async def mongo_repository():
    """Setup test MongoDB."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.nutrifit_test
    
    repo = MongoMealRepository(db)
    
    yield repo
    
    # Cleanup
    await db.meals.delete_many({})
    client.close()

@pytest.mark.asyncio
async def test_create_and_retrieve_meal(mongo_repository):
    """Test meal persistence."""
    # Arrange
    meal = MealEntry(
        user_id="test_user",
        name="Test Meal",
        quantity_g=100.0,
        timestamp=datetime.utcnow(),
        source="MANUAL",
        calories=100
    )
    
    # Act
    created = await mongo_repository.create(meal)
    retrieved = await mongo_repository.get_by_id(created.id, "test_user")
    
    # Assert
    assert retrieved is not None
    assert retrieved.name == "Test Meal"
    assert retrieved.calories == 100
```

### E2E Tests

```python
# tests/e2e/test_photo_flow.py

@pytest.mark.asyncio
async def test_complete_photo_meal_flow(graphql_client):
    """Test complete photo → analyze → confirm flow."""
    
    # Step 1: Analyze photo
    analyze_result = await graphql_client.execute("""
        mutation {
          analyzeMealPhoto(input: {
            photoUrl: "https://example.com/meal.jpg"
            userId: "test_user"
            dishHint: "pasta"
          }) {
            id
            status
            items {
              label
              calories
            }
            totalCalories
          }
        }
    """)
    
    assert analyze_result["analyzeMealPhoto"]["status"] == "PENDING"
    analysis_id = analyze_result["analyzeMealPhoto"]["id"]
    
    # Step 2: Confirm meal
    confirm_result = await graphql_client.execute(f"""
        mutation {{
          confirmMealPhoto(input: {{
            analysisId: "{analysis_id}"
            acceptedIndexes: [0]
            userId: "test_user"
          }}) {{
            createdMeals {{
              id
              name
              calories
            }}
          }}
        }}
    """)
    
    assert len(confirm_result["confirmMealPhoto"]["createdMeals"]) == 1
    
    # Step 3: Verify meal persisted
    query_result = await graphql_client.execute("""
        query {
          mealEntries(limit: 1, userId: "test_user") {
            id
            name
            calories
          }
        }
    """)
    
    assert len(query_result["mealEntries"]) == 1
```

---

## 🎯 SUCCESS METRICS

### Performance Targets

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **API Latency** | ~2000ms | <1500ms | p95 response time |
| **Cache Hit Rate** | ~60% | >85% | USDA cache hits / total |
| **Recognition Accuracy** | ~75% | >80% | User confirmation rate |
| **Cost per Request** | $0.05 | <$0.035 | OpenAI + USDA costs |

### Quality Targets

| Metric | Target | Verification |
|--------|--------|--------------|
| **Test Coverage** | >90% | pytest-cov |
| **Type Safety** | 100% | mypy --strict |
| **Code Quality** | A grade | ruff + black |
| **Documentation** | 100% public APIs | docstring coverage |

### Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **User Adoption** | >50% use new flow | Analytics tracking |
| **Error Rate** | <2% | Sentry alerts |
| **Support Tickets** | <10/week | Support system |

---

## 📚 DOCUMENTATION DELIVERABLES

### Developer Documentation

1. **Architecture Guide** (`docs/architecture.md`)
   - Layer responsibilities
   - Dependency flow
   - Design patterns used

2. **API Examples** (`docs/api_examples.md`)
   - GraphQL query examples
   - Mutation examples
   - Error handling

3. **Development Guide** (`docs/development.md`)
   - Setup instructions
   - Running tests
   - Debugging tips

### Operational Documentation

1. **Deployment Guide** (`docs/deployment.md`)
   - MongoDB setup
   - Environment variables
   - Monitoring setup

2. **Troubleshooting** (`docs/troubleshooting.md`)
   - Common errors
   - Debug procedures
   - Performance tuning

---

## ⚠️ RISKS & MITIGATION

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **OpenAI API changes** | High | Medium | Version pinning, fallback strategy |
| **USDA rate limits** | Medium | Low | Aggressive caching, fallback profiles |
| **MongoDB scaling** | Medium | Low | Proper indexing, monitoring |
| **Breaking changes** | High | High | Gradual rollout, feature flags |

### Project Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Scope creep** | Medium | Medium | Strict phase gates, no feature adds |
| **Timeline slip** | Medium | Medium | Buffer time in estimates, daily standups |
| **Quality issues** | High | Low | 100% test coverage requirement |

---

## 🚀 ROLLOUT STRATEGY

### Phase 1: Internal Testing (Week 1)
- Deploy to staging
- Internal team testing
- Performance benchmarking

### Phase 2: Beta Users (Week 2)
- 10% user rollout
- Monitor metrics
- Gather feedback

### Phase 3: Full Rollout (Week 3)
- 100% user migration
- Deprecation notices for old API
- Remove old code

---

## 📞 SUPPORT & CONTACTS

**Tech Lead**: [Your Name]  
**Repository**: https://github.com/giamma80/Nutrifit-mobile  
**Documentation**: `/docs` folder  
**Issues**: GitHub Issues  

---

## ✅ CHECKLIST FINALE

Prima del deployment in produzione:

- [ ] Tutti i test passano (unit + integration + e2e)
- [ ] Coverage >90%
- [ ] MyPy 0 errors
- [ ] MongoDB indexes creati
- [ ] Environment variables configurate
- [ ] Documentation aggiornata
- [ ] Breaking changes comunicati
- [ ] Rollback plan definito
- [ ] Monitoring attivo
- [ ] Team training completato

---

**Fine Roadmap** 🎉

Questo documento è la guida completa per il refactoring. Segui le fasi in ordine, testa accuratamente, e mantieni il focus sulla qualità del codice.
