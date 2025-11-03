# GraphQL API Reference

Documentazione completa delle query e mutation disponibili nell'API GraphQL di Nutrifit dopo il refactor Phase 5.

## Indice

- [Struttura dell'API](#struttura-dellapi)
- [Namespace: Meals](#namespace-meals)
- [Namespace: Activity](#namespace-activity)
- [Namespace: Nutritional Profile](#namespace-nutritional-profile)
- [Root Mutations](#root-mutations)
- [Utilities](#utilities)

---

## Struttura dell'API

L'API GraphQL è organizzata in **namespace** per dominio:

```graphql
type Query {
  serverTime: String!
  health: String!
  
  # Namespace domains
  atomic: AtomicQueries!                    # Query atomiche meal
  meals: AggregateQueries!                  # Query aggregate meal
  activity: ActivityQueries!                # Query activity
  nutritionalProfile: NutritionalProfileQueries!  # Query profilo nutrizionale
  
  cacheStats: CacheStats!                   # Utility
}

type Mutation {
  meals: MealMutations!                     # Mutations meal
  activity: ActivityMutations!              # Mutations activity
  nutritionalProfile: NutritionalProfileMutations!  # Mutations profilo
  syncHealthTotals(...)                     # Mutation root (legacy)
}
```

---

## Namespace: Meals

### Query: `atomic`

Query atomiche per operazioni singole sui meal.

#### `atomic.searchFoodByBarcode`

Cerca un prodotto per barcode nell'enrichment service.

**Uso**:
```graphql
query {
  atomic {
    searchFoodByBarcode(barcode: "8001505005707") {
      barcode
      name
      brand
      nutrients {
        calories
        protein
        carbs
        fat
        fiber
        sugar
        sodium
        quantityG
      }
      servingSizeG
      imageUrl
    }
  }
}
```

**Parametri**:
- `barcode` (String!): Codice a barre del prodotto

**Ritorna**: `BarcodeProduct` o `null` se non trovato

---

#### `atomic.recognizeFood`

Riconosce cibi da foto o testo con AI vision.

**Uso**:
```graphql
query {
  atomic {
    recognizeFood(
      photoUrl: "https://..."
      dishHint: "pasta"
    ) {
      items {
        label
        displayName
        quantityG
        confidence
      }
      averageConfidence
    }
  }
}
```

**Parametri**:
- `photoUrl` (String, opzionale): URL immagine
- `text` (String, opzionale): Descrizione testuale
- `dishHint` (String, opzionale): Suggerimento sul piatto

**Ritorna**: `FoodRecognitionResult` con lista cibi riconosciuti

---

#### `atomic.enrichNutrients`

Arricchisce un cibo con dati nutrizionali da USDA.

**Uso**:
```graphql
query {
  atomic {
    enrichNutrients(label: "chicken breast", quantityG: 150) {
      calories
      protein
      carbs
      fat
      fiber
      sugar
      sodium
      quantityG
    }
  }
}
```

**Parametri**:
- `label` (String!): Nome del cibo
- `quantityG` (Float!): Quantità in grammi

**Ritorna**: `NutrientProfile` o `null` se non trovato

---

### Query: `meals`

Query aggregate per operazioni complesse sui meal.

#### `meals.meal`

Recupera un singolo meal per ID.

**Uso**:
```graphql
query {
  meals {
    meal(mealId: "550e8400-e29b-41d4-a716-446655440000", userId: "user123") {
      id
      userId
      timestamp
      mealType
      dishName
      imageUrl
      source
      confidence
      entries {
        id
        name
        displayName
        quantityG
        calories
        protein
        carbs
        fat
        fiber
        sugar
        sodium
        confidence
        barcode
      }
      totalCalories
      totalProtein
      totalCarbs
      totalFat
      totalFiber
      totalSugar
      totalSodium
      createdAt
      updatedAt
    }
  }
}
```

**Parametri**:
- `mealId` (String!): UUID del meal
- `userId` (String!): ID utente (autorizzazione)

**Ritorna**: `Meal` o `null` se non trovato/non autorizzato

---

#### `meals.mealHistory`

Recupera storico meal con filtri e paginazione.

**Uso**:
```graphql
query {
  meals {
    mealHistory(
      userId: "user123"
      startDate: "2025-10-01T00:00:00Z"
      endDate: "2025-10-28T23:59:59Z"
      mealType: "BREAKFAST"
      limit: 20
      offset: 0
    ) {
      meals {
        id
        timestamp
        mealType
        dishName
        totalCalories
        totalProtein
        entries {
          name
          calories
        }
      }
      totalCount
      hasMore
    }
  }
}
```

**Parametri**:
- `userId` (String!): ID utente
- `startDate` (DateTime, opzionale): Data inizio filtro
- `endDate` (DateTime, opzionale): Data fine filtro
- `mealType` (String, opzionale): Tipo meal ("BREAKFAST", "LUNCH", "DINNER", "SNACK")
- `limit` (Int, default: 20): Risultati per pagina
- `offset` (Int, default: 0): Offset paginazione

**Ritorna**: `MealHistoryResult` con lista meals, conteggio totale e flag hasMore

---

#### `meals.search`

Ricerca full-text nei meal (entries e notes).

**Uso**:
```graphql
query {
  meals {
    search(
      userId: "user123"
      queryText: "chicken pasta"
      limit: 20
      offset: 0
    ) {
      meals {
        id
        timestamp
        dishName
        entries {
          name
          displayName
          calories
        }
        totalCalories
      }
      totalCount
    }
  }
}
```

**Parametri**:
- `userId` (String!): ID utente
- `queryText` (String!): Testo di ricerca
- `limit` (Int, default: 20): Risultati per pagina
- `offset` (Int, default: 0): Offset paginazione

**Ritorna**: `MealSearchResult` con lista meals e conteggio

---

#### `meals.dailySummary`

Riepilogo nutrizionale giornaliero aggregato dai meal.

**Uso**:
```graphql
query {
  meals {
    dailySummary(userId: "user123", date: "2025-10-28T00:00:00Z") {
      date
      totalCalories
      totalProtein
      totalCarbs
      totalFat
      totalFiber
      totalSugar
      totalSodium
      mealCount
      breakdownByType  # JSON string con breakdown per tipo meal
      hasMeals
    }
  }
}
```

**Parametri**:
- `userId` (String!): ID utente
- `date` (DateTime!): Data per il summary

**Ritorna**: `DailySummary` con totali nutrizionali e breakdown per tipo meal

**Note**: Aggrega solo dati meal, non include dati activity (activitySteps, caloriesDeficit, ecc.)

**Differenze con altre query meals**:
- **vs `summaryRange`**: `dailySummary` ritorna dati per UN SOLO giorno, mentre `summaryRange` permette di aggregare su intervalli multi-giorno con grouping flessibile (DAY/WEEK/MONTH)
- **vs `mealHistory`**: `dailySummary` ritorna solo AGGREGATI (totali nutrizionali), mentre `mealHistory` ritorna lista dettagliata di singoli meal
- **Caso d'uso**: Dashboard giornaliero, widget "Today's Nutrition", notifiche fine giornata

---

#### `meals.summaryRange`

Riepilogo nutrizionale per intervalli di date con grouping flessibile (DAY/WEEK/MONTH).

**Uso**:
```graphql
query {
  meals {
    summaryRange(
      userId: "user123"
      startDate: "2025-10-21T00:00:00Z"
      endDate: "2025-10-27T23:59:59Z"
      groupBy: WEEK
    ) {
      periods {
        period          # "2025-W43"
        startDate
        endDate
        totalCalories
        totalProtein
        totalCarbs
        totalFat
        totalFiber
        totalSugar
        totalSodium
        mealCount
        breakdownByType  # JSON: {"BREAKFAST": 450, "LUNCH": 650, ...}
      }
      total {
        period          # "TOTAL"
        totalCalories   # Somma di tutti i periods
        totalProtein
        totalCarbs
        totalFat
        totalFiber
        totalSugar
        totalSodium
        mealCount
        breakdownByType
      }
    }
  }
}
```

**Parametri**:
- `userId` (String!): ID utente
- `startDate` (DateTime!): Inizio range (inclusivo)
- `endDate` (DateTime!): Fine range (inclusivo)
- `groupBy` (GroupByPeriod!): Raggruppa per DAY, WEEK o MONTH

**Ritorna**: `RangeSummaryResult`
- `periods`: Array di `PeriodSummary`, uno per ogni periodo (giorno/settimana/mese) nel range
- `total`: `PeriodSummary` aggregato con somma di tutti i periods

**Formato period label**:
- `DAY`: "2025-10-28" (ISO date)
- `WEEK`: "2025-W43" (ISO week)
- `MONTH`: "2025-10" (anno-mese)

**Differenze con altre query meals**:
- **vs `dailySummary`**: `summaryRange` supporta intervalli MULTI-GIORNO con grouping flessibile (giorno/settimana/mese), mentre `dailySummary` è limitato a UN SOLO giorno
- **vs `mealHistory`**: `summaryRange` ritorna solo AGGREGATI per periodo, mentre `mealHistory` ritorna lista dettagliata dei singoli meal
- **Vantaggio chiave**: Ritorna sia breakdown per periodo CHE totale aggregato in una sola query, evitando N+1 queries per dashboard settimanali/mensili

**Casi d'uso**:
- Dashboard settimanale: "Nutrition this week" con grafico giornaliero
- Report mensile: "October summary" con breakdown per settimana
- Trend analysis: Ultimi 30 giorni raggruppati per settimana
- Confronto periodi: "Questa settimana vs settimana scorsa"

**Esempio pratico - Dashboard settimanale**:
```graphql
query WeeklyDashboard {
  meals {
    # Ultimi 7 giorni con breakdown giornaliero
    summaryRange(
      userId: "user123"
      startDate: "2025-10-22T00:00:00Z"
      endDate: "2025-10-28T23:59:59Z"
      groupBy: DAY
    ) {
      periods {
        period          # "2025-10-22", "2025-10-23", ...
        totalCalories
        mealCount
      }
      total {
        totalCalories   # Totale settimana
        mealCount       # Totale meals settimana
      }
    }
  }
}
```

**Esempio pratico - Report mensile**:
```graphql
query MonthlyReport {
  meals {
    # Ottobre raggruppato per settimana
    summaryRange(
      userId: "user123"
      startDate: "2025-10-01T00:00:00Z"
      endDate: "2025-10-31T23:59:59Z"
      groupBy: WEEK
    ) {
      periods {
        period          # "2025-W40", "2025-W41", ...
        totalCalories
        breakdownByType
      }
      total {
        totalCalories   # Totale mese
      }
    }
  }
}
```

---

### Mutations: `meals`

#### `meals.analyzeMealPhoto`

Analizza una foto di cibo con AI per riconoscimento e arricchimento nutrizionale.

**Uso**:
```graphql
mutation {
  meals {
    analyzeMealPhoto(
      input: {
        userId: "user123"
        photoUrl: "https://example.com/meal.jpg"
        timestamp: "2025-10-28T12:30:00Z"
        mealType: LUNCH
        dishHint: "Pranzo in ufficio"
      }
    ) {
      ... on MealAnalysisSuccess {
        analysisId
        meal {
          id
          dishName
          confidence
          entries {
            name
            quantityG
            calories
            protein
            carbs
            fat
          }
          totalCalories
          totalProtein
        }
      }
      ... on MealAnalysisError {
        code
        message
      }
    }
  }
}
```

**Parametri**:
- `input.userId` (String!): ID utente
- `input.photoUrl` (String!): URL immagine meal
- `input.dishHint` (String, opzionale): Suggerimento sul nome del piatto
- `input.timestamp` (DateTime!): Timestamp del meal
- `input.mealType` (MealType!): Tipo meal (BREAKFAST, LUNCH, DINNER, SNACK)
- `input.idempotencyKey` (String, opzionale): Chiave per deduplicazione

**Ritorna**: Union type `MealAnalysisSuccessMealAnalysisError`
- `MealAnalysisSuccess`: Analisi completata con successo
- `MealAnalysisError`: Errore durante l'analisi

**Note**: Il meal viene creato in stato PENDING, richiede conferma con `confirmMealAnalysis`

---

#### `meals.confirmMealAnalysis`

Conferma un'analisi meal creata da photo/barcode, rendendola definitiva.

**Uso**:
```graphql
mutation {
  meals {
    confirmMealAnalysis(
      input: {
        mealId: "meal-uuid-123"
        userId: "user123"
        confirmedEntryIds: ["entry-1", "entry-2", "entry-3"]
      }
    ) {
      ... on ConfirmAnalysisSuccess {
        meal {
          id
          dishName
          entries { name calories }
          totalCalories
        }
        confirmedCount
        rejectedCount
      }
      ... on ConfirmAnalysisError {
        code
        message
      }
    }
  }
}
```

**Parametri**:
- `input.mealId` (String!): ID del meal da confermare
- `input.userId` (String!): ID utente (autorizzazione)
- `input.confirmedEntryIds` ([String!]!): Lista ID degli entry da confermare

**Ritorna**: Union type `ConfirmAnalysisSuccessConfirmAnalysisError`

---

#### `meals.analyzeMealBarcode`

Analizza un meal da barcode con arricchimento nutrizionale.

**Uso**:
```graphql
mutation {
  meals {
    analyzeMealBarcode(
      input: {
        userId: "user123"
        barcode: "8001505005707"
        quantityG: 100
        timestamp: "2025-10-28T12:30:00Z"
        mealType: SNACK
      }
    ) {
      ... on MealAnalysisSuccess {
        analysisId
        meal {
          id
          dishName
          entries {
            name
            barcode
            quantityG
            calories
            protein
          }
          totalCalories
        }
      }
      ... on MealAnalysisError {
        code
        message
      }
    }
  }
}
```

**Parametri**:
- `input.userId` (String!): ID utente
- `input.barcode` (String!): Codice a barre prodotto
- `input.quantityG` (Float!): Quantità in grammi
- `input.timestamp` (DateTime!): Timestamp del meal
- `input.mealType` (MealType!): Tipo meal

**Ritorna**: Union type `MealAnalysisSuccessMealAnalysisError`

---

#### `meals.analyzeMealText`

Analizza un meal da descrizione testuale con AI per riconoscimento e arricchimento nutrizionale.

**Uso**:
```graphql
mutation {
  meals {
    analyzeMealText(
      input: {
        userId: "user123"
        textDescription: "150g di pasta al pomodoro con basilico"
        timestamp: "2025-10-28T12:30:00Z"
        mealType: LUNCH
        idempotencyKey: "meal-text-001"
      }
    ) {
      ... on MealAnalysisSuccess {
        analysisId
        meal {
          id
          dishName
          confidence
          entries {
            name
            displayName
            quantityG
            calories
            protein
            carbs
            fat
          }
          totalCalories
          totalProtein
          source  # "DESCRIPTION"
        }
      }
      ... on MealAnalysisError {
        code
        message
      }
    }
  }
}
```

**Parametri**:
- `input.userId` (String!): ID utente
- `input.textDescription` (String!): Descrizione testuale del meal (es. "2 uova strapazzate con toast")
- `input.timestamp` (DateTime!): Timestamp del meal
- `input.mealType` (MealType!): Tipo meal (BREAKFAST, LUNCH, DINNER, SNACK)
- `input.idempotencyKey` (String, opzionale): Chiave per deduplicazione

**Ritorna**: Union type `MealAnalysisSuccess | MealAnalysisError`
- `MealAnalysisSuccess`: Analisi completata con successo
- `MealAnalysisError`: Errore durante l'analisi

**Comportamento**:
1. **Riconoscimento AI**: Usa GPT-4o per identificare cibi e quantità dalla descrizione testuale
2. **Arricchimento nutrizionale**: Per ogni cibo riconosciuto, recupera dati nutrizionali da USDA
3. **Creazione meal**: Crea meal con source="DESCRIPTION" in stato PENDING
4. **Idempotenza**: Cache di 1 ora per evitare rianalisi duplicate

**Source value**: Il campo `source` del meal sarà impostato a `"DESCRIPTION"` (non "TEXT")

**Note**: 
- Il meal viene creato in stato PENDING, richiede conferma con `confirmMealAnalysis`
- L'AI può stimare quantità se non specificate (es. "una mela" → ~182g)
- Supporta descrizioni complesse con più ingredienti (es. "pasta con pomodoro e basilico" → 3 entries)
- Idempotency key opzionale: se omessa, viene auto-generata da payload

**Esempi di input supportati**:
```text
# Con quantità esplicite
"150g di pasta al pomodoro con basilico"
→ Pasta (150g), Sugo di pomodoro (80g), Basilico (5g)

# Con quantità implicite
"2 uova strapazzate con 2 fette di pane tostato"
→ Uova (100g, 2 large), Pane tostato (60g, 2 slices)

# Descrizione minima
"una mela"
→ Mela (182g, 1 medium apple)

# Meal complessi
"risotto ai funghi porcini con grana padano"
→ Riso arborio (80g), Funghi porcini (50g), Grana Padano (20g), Brodo (200ml)
```

**Differenze con altre analyze mutations**:
- **vs `analyzeMealPhoto`**: `analyzeMealText` non richiede immagine, usa solo descrizione testuale
- **vs `analyzeMealBarcode`**: `analyzeMealText` riconosce più alimenti da testo libero, non singolo prodotto
- **Vantaggio chiave**: Veloce e conveniente per meal semplici o quando non è possibile scattare foto

**Casi d'uso**:
- Quick logging di meal semplici ("colazione standard: latte e cereali")
- Retroactive logging di meal passati
- Meal consumati fuori casa dove fotografare è scomodo
- Import da diario alimentare scritto
- Voice-to-text integration (utente detta meal, app converte e analizza)

**Workflow tipico**:
```graphql
# Step 1: Analizza testo
mutation {
  meals {
    analyzeMealText(
      input: {
        userId: "user123"
        textDescription: "colazione con 2 uova strapazzate e 2 fette di pane tostato"
        timestamp: "2025-10-28T08:00:00Z"
        mealType: BREAKFAST
      }
    ) {
      ... on MealAnalysisSuccess {
        meal {
          id
          entries {
            id
            name
            quantityG
            calories
          }
          totalCalories
        }
      }
    }
  }
}

# Step 2: Review entries (UI mostra preview)
# User può accettare/rifiutare singoli entries

# Step 3: Conferma meal
mutation {
  meals {
    confirmMealAnalysis(
      input: {
        mealId: "..."
        userId: "user123"
        confirmedEntryIds: ["entry-1", "entry-2"]  # Esclude "butter" se non desiderato
      }
    ) {
      ... on ConfirmAnalysisSuccess {
        meal { id totalCalories }
      }
    }
  }
}
```

---

#### `meals.updateMeal`

Aggiorna un meal esistente (tipo, timestamp, note).

**Uso**:
```graphql
mutation {
  meals {
    updateMeal(
      input: {
        mealId: "meal-uuid-123"
        userId: "user123"
        notes: "Porzione abbondante"
        mealType: DINNER
        timestamp: "2025-10-28T19:30:00Z"
      }
    ) {
      ... on UpdateMealSuccess {
        meal {
          id
          mealType
          timestamp
          notes
          totalCalories
        }
      }
      ... on UpdateMealError {
        code
        message
      }
    }
  }
}
```

**Parametri**:
- `input.mealId` (String!): UUID del meal da aggiornare
- `input.userId` (String!): ID utente (autorizzazione)
- `input.mealType` (MealType, opzionale): Nuovo tipo meal
- `input.timestamp` (DateTime, opzionale): Nuovo timestamp
- `input.notes` (String, opzionale): Nuove note

**Ritorna**: Union type `UpdateMealSuccessUpdateMealError`

**Note**: Non è possibile modificare gli entries con questa mutation. Per modificare gli entries, eliminare il meal e crearne uno nuovo.

---

#### `meals.deleteMeal`

Elimina un meal.

**Uso**:
```graphql
mutation {
  meals {
    deleteMeal(mealId: "meal-uuid-123", userId: "user123") {
      ... on DeleteMealSuccess {
        mealId
        message
      }
      ... on DeleteMealError {
        code
        message
      }
    }
  }
}
```

**Parametri**:
- `mealId` (String!): UUID del meal da eliminare
- `userId` (String!): ID utente (autorizzazione)

**Ritorna**: Union type `DeleteMealSuccessDeleteMealError`

---

## Namespace: Activity

### Query: `activity`

#### `activity.entries`

Lista eventi di attività minute-by-minute.

**Uso**:
```graphql
query {
  activity {
    entries(
      userId: "user123"
      limit: 100
      after: "2025-10-28T10:00:00Z"
      before: "2025-10-28T11:00:00Z"
    ) {
      userId
      ts
      source
      steps
      caloriesOut
      hrAvg
    }
  }
}
```

**Parametri**:
- `userId` (String, opzionale): ID utente (default: "default")
- `limit` (Int, default: 100, max: 500): Numero risultati
- `after` (String, opzionale): Timestamp inizio periodo (ISO 8601)
- `before` (String, opzionale): Timestamp fine periodo (ISO 8601)

**Ritorna**: Lista di `ActivityEvent`
- `userId` (String!): ID utente
- `ts` (String!): Timestamp evento (ISO 8601)
- `steps` (Int): Passi nel minuto
- `caloriesOut` (Float): Calorie bruciate
- `hrAvg` (Float): Frequenza cardiaca media
- `source` (ActivitySource!): Fonte dati

**Quando usarla**:
- Per visualizzare dati granulari dell'attività
- Per costruire grafici temporali
- Per analizzare pattern di movimento durante la giornata

---

#### `activity.syncEntries`

Lista delta di sincronizzazione dei totali giornalieri.

**Uso**:
```graphql
query {
  activity {
    syncEntries(
      date: "2025-10-28"
      userId: "user123"
      after: "2025-10-28T08:00:00Z"
      limit: 200
    ) {
      timestamp
      steps
      caloriesOut
      hrAvgSession
    }
  }
}
```

**Parametri**:
- `date` (String!): Data in formato YYYY-MM-DD
- `userId` (String, opzionale): ID utente (default: "default")
- `after` (String, opzionale): After timestamp (ISO 8601)
- `limit` (Int, default: 200, max: 500): Numero risultati

**Ritorna**: Lista di `HealthTotalsDelta`
- `timestamp` (String!): Timestamp della sync
- `steps` (Int!): Incremento passi
- `caloriesOut` (Float!): Incremento calorie
- `hrAvgSession` (Float): Frequenza cardiaca media sessione

**Differenze con altre query activity**:
- **vs `aggregateRange`**: `syncEntries` ritorna DELTA incrementali delle sincronizzazioni (snapshot progressivi), mentre `aggregateRange` aggrega eventi minute-by-minute con grouping flessibile
- **vs `entries`**: `syncEntries` ritorna snapshot di sincronizzazione cumulative, mentre `entries` ritorna eventi granulari minute-by-minute
- **Caso d'uso**: Debugging sync issues, visualizzazione timeline sincronizzazioni, audit trail

---

#### `activity.aggregateRange`

Aggregati di attività per intervalli di date con grouping flessibile (DAY/WEEK/MONTH).

**Uso**:
```graphql
query {
  activity {
    aggregateRange(
      userId: "user123"
      startDate: "2025-10-21T00:00:00Z"
      endDate: "2025-10-27T23:59:59Z"
      groupBy: WEEK
    ) {
      periods {
        period          # "2025-W43"
        startDate
        endDate
        totalSteps
        totalCaloriesOut
        avgHeartRate
        eventCount
        activeMinutes
      }
      total {
        period          # "TOTAL"
        totalSteps      # Somma di tutti i periods
        totalCaloriesOut
        avgHeartRate
        eventCount
        activeMinutes
      }
    }
  }
}
```

**Parametri**:
- `userId` (String!): ID utente
- `startDate` (String!): Inizio range in formato ISO 8601 (inclusivo)
- `endDate` (String!): Fine range in formato ISO 8601 (inclusivo)
- `groupBy` (GroupByPeriod!): Raggruppa per DAY, WEEK o MONTH

**Ritorna**: `ActivityRangeResult`
- `periods`: Array di `ActivityPeriodSummary`, uno per ogni periodo nel range
- `total`: `ActivityPeriodSummary` aggregato con somma/media di tutti i periods

**Formato period label**:
- `DAY`: "2025-10-28" (ISO date)
- `WEEK`: "2025-W43" (ISO week)
- `MONTH`: "2025-10" (anno-mese)

**Differenze con altre query activity**:
- **vs `entries`**: `aggregateRange` ritorna AGGREGATI per periodo (totali/medie), mentre `entries` ritorna eventi GRANULARI minute-by-minute
- **vs `syncEntries`**: `aggregateRange` aggrega eventi activity reali, mentre `syncEntries` ritorna delta delle sincronizzazioni (snapshot cumulativi)
- **Vantaggio chiave**: Ritorna sia breakdown per periodo CHE totale aggregato in una sola query, ottimizzato per dashboard multi-giorno

**Casi d'uso**:
- Dashboard settimanale: "Activity this week" con grafico giornaliero passi/calorie
- Report mensile: "October activity" con breakdown per settimana
- Trend analysis: Ultimi 30 giorni raggruppati per settimana
- Confronto periodi: "Questa settimana vs settimana scorsa"
- Progress tracking: Goal settimanali/mensili con visualizzazione progresso

**Esempio pratico - Dashboard settimanale**:
```graphql
query WeeklyActivity {
  activity {
    # Ultimi 7 giorni con breakdown giornaliero
    aggregateRange(
      userId: "user123"
      startDate: "2025-10-22T00:00:00Z"
      endDate: "2025-10-28T23:59:59Z"
      groupBy: DAY
    ) {
      periods {
        period          # "2025-10-22", "2025-10-23", ...
        totalSteps
        totalCaloriesOut
        avgHeartRate
        activeMinutes
      }
      total {
        totalSteps      # Totale settimana
        totalCaloriesOut
        avgHeartRate
        activeMinutes
      }
    }
  }
}
```

**Esempio pratico - Report mensile**:
```graphql
query MonthlyActivity {
  activity {
    # Ottobre raggruppato per settimana
    aggregateRange(
      userId: "user123"
      startDate: "2025-10-01T00:00:00Z"
      endDate: "2025-10-31T23:59:59Z"
      groupBy: WEEK
    ) {
      periods {
        period          # "2025-W40", "2025-W41", ...
        totalSteps
        totalCaloriesOut
        activeMinutes
      }
      total {
        totalSteps      # Totale mese
        totalCaloriesOut
      }
    }
  }
}
```

**Esempio pratico - Confronto periodi**:
```graphql
query CompareWeeks {
  thisWeek: activity {
    aggregateRange(
      userId: "user123"
      startDate: "2025-10-21T00:00:00Z"
      endDate: "2025-10-27T23:59:59Z"
      groupBy: WEEK
    ) {
      total { totalSteps totalCaloriesOut }
    }
  }
  
  lastWeek: activity {
    aggregateRange(
      userId: "user123"
      startDate: "2025-10-14T00:00:00Z"
      endDate: "2025-10-20T23:59:59Z"
      groupBy: WEEK
    ) {
      total { totalSteps totalCaloriesOut }
    }
  }
}
```

---

### Mutations: `activity`

#### `activity.syncActivityEvents`

Sincronizza batch di eventi attività minute-by-minute con idempotenza.

**Uso**:
```graphql
mutation {
  activity {
    syncActivityEvents(
      input: [
        {
          ts: "2025-10-28T10:00:00Z"
          steps: 50
          caloriesOut: 5.2
          hrAvg: 75.0
          source: APPLE_HEALTH
        }
        {
          ts: "2025-10-28T10:01:00Z"
          steps: 48
          caloriesOut: 5.0
          source: APPLE_HEALTH
        }
      ]
      userId: "user123"
      idempotencyKey: "sync-batch-001"
    ) {
      accepted
      duplicates
      rejected {
        index
        reason
      }
      idempotencyKeyUsed
    }
  }
}
```

**Parametri**:
- `input` (List[ActivityMinuteInput]!): Lista eventi da sincronizzare
  - `ts` (String!): Timestamp evento in formato ISO 8601
  - `steps` (Int, default: 0): Passi in quel minuto
  - `caloriesOut` (Float, opzionale): Calorie bruciate
  - `hrAvg` (Float, opzionale): Frequenza cardiaca media
  - `source` (ActivitySource, default: MANUAL): Fonte dati (APPLE_HEALTH, GOOGLE_FIT, MANUAL)
- `userId` (String, opzionale): ID utente (default: "default")
- `idempotencyKey` (String, opzionale): Chiave per deduplicazione

**Ritorna**: `IngestActivityResult`
- `accepted`: Numero eventi accettati
- `duplicates`: Numero eventi duplicati (già presenti con stesso timestamp)
- `rejected`: Lista eventi rifiutati con motivo
- `idempotencyKeyUsed`: Chiave usata (auto-generata se non fornita)

**Idempotenza**:
- Se non fornisci `idempotencyKey`, viene auto-generata da payload (esclusi timestamp)
- Formato auto-key: `auto-{hash16}`
- **Deduplicazione primaria** su `(user_id, timestamp)`: eventi con stesso timestamp vengono sempre contati come `duplicates`
- **Idempotency key** serve per retry sicuri: stessa key con stesso payload → ritorna risultato cached
- Conflict detection se stessa key con payload diverso

**Note**:
- Gli eventi vengono sempre deduplicated su `(userId, timestamp)` indipendentemente dall'idempotency key
- L'idempotency key serve per garantire che un retry di invio (es. per errore di rete) non causi effetti collaterali
- Se invii gli stessi eventi con chiave diversa, verranno comunque deduplicated come `duplicates` ma la mutation sarà accettata

**Quando usarla**:
- Per sincronizzare dati granulari da wearable
- Quando hai dettagli minute-by-minute
- Per analisi dettagliate dell'attività

---

## Namespace: Nutritional Profile

### Query: `nutritionalProfile`

Query per gestione profilo nutrizionale, calcoli BMR/TDEE e tracking progresso.

#### `nutritionalProfile.nutritionalProfile`

Recupera il profilo nutrizionale di un utente.

**Uso**:
```graphql
query {
  nutritionalProfile {
    nutritionalProfile(userId: "user123") {
      profileId
      userId
      goal
      userData {
        weight
        height
        age
        sex
        activityLevel
      }
      bmr {
        value
      }
      tdee {
        value
        activityLevel
      }
      caloriesTarget
      macroSplit {
        proteinG
        carbsG
        fatG
      }
      progressHistory {
        date
        weight
        consumedCalories
        consumedProteinG
        consumedCarbsG
        consumedFatG
        caloriesBurnedBmr
        caloriesBurnedActive
        notes
      }
      createdAt
      updatedAt
    }
  }
}
```

**Parametri**:
- `profileId` (String, opzionale): ID del profilo
- `userId` (String, opzionale): ID utente

**Nota**: Deve essere fornito `profileId` O `userId` (almeno uno dei due)

**Ritorna**: `NutritionalProfileType` o `null` se non trovato

**Campi Ritornati**:
- `profileId`: UUID del profilo
- `userId`: ID utente proprietario
- `goal`: Obiettivo (CUT, MAINTAIN, BULK)
- `userData`: Dati biometrici e attività
  - `weight`: Peso in kg
  - `height`: Altezza in cm
  - `age`: Età in anni
  - `sex`: Sesso biologico (M/F)
  - `activityLevel`: Livello attività (SEDENTARY, LIGHT, MODERATE, ACTIVE, VERY_ACTIVE)
- `bmr`: Metabolismo Basale (kcal/giorno a riposo)
- `tdee`: Dispendio Energetico Totale Giornaliero (kcal/giorno con attività)
- `caloriesTarget`: Calorie target giornaliere (aggiustate per obiettivo)
- `macroSplit`: Distribuzione macronutrienti in grammi
  - `proteinG`: Proteine giornaliere target
  - `carbsG`: Carboidrati giornalieri target
  - `fatG`: Grassi giornalieri target
- `progressHistory`: Storico registrazioni progresso
- `createdAt`: Data creazione profilo
- `updatedAt`: Data ultimo aggiornamento

**Calcoli Automatici**:
- **BMR** (Basal Metabolic Rate): Calcolato con formula Mifflin-St Jeor
  - Maschi: `10 * weight + 6.25 * height - 5 * age + 5`
  - Femmine: `10 * weight + 6.25 * height - 5 * age - 161`
- **TDEE** (Total Daily Energy Expenditure): `BMR * activity_multiplier`
  - SEDENTARY: 1.2
  - LIGHT: 1.375
  - MODERATE: 1.55
  - ACTIVE: 1.725
  - VERY_ACTIVE: 1.9
- **Calorie Target**: Aggiustato per obiettivo
  - CUT: `TDEE - 500` (deficit per perdita peso)
  - MAINTAIN: `TDEE` (mantenimento)
  - BULK: `TDEE + 300` (surplus per massa muscolare)
- **Macro Split**: Personalizzato per obiettivo
  - CUT: Alto proteine (2.2g/kg), carboidrati moderati, grassi bassi
  - MAINTAIN: Proteine moderate (1.8g/kg), carboidrati alti, grassi moderati
  - BULK: Proteine alte (2.0g/kg), carboidrati molto alti, grassi moderati

**Quando usarla**:
- Dashboard profilo utente
- Visualizzazione obiettivi nutrizionali
- Tracking progresso giornaliero
- Ricalcolo metriche dopo aggiornamenti

---

#### `nutritionalProfile.progressScore`

Calcola statistiche di progresso su un intervallo di date.

**Uso**:
```graphql
query {
  nutritionalProfile {
    progressScore(
      userId: "user123"
      startDate: "2025-10-21"
      endDate: "2025-10-27"
    ) {
      startDate
      endDate
      weightDelta
      avgDailyCalories
      avgCaloriesBurned
      avgDeficit
      daysDeficitOnTrack
      daysMacrosOnTrack
      totalDays
      adherenceRate
    }
  }
}
```

**Parametri**:
- `userId` (String!): ID utente
- `startDate` (Date!): Data inizio periodo (formato: YYYY-MM-DD)
- `endDate` (Date!): Data fine periodo (formato: YYYY-MM-DD)

**Ritorna**: `ProgressStatisticsType` o `null` se profilo non trovato

**Campi Ritornati**:
- `startDate`: Data inizio analisi
- `endDate`: Data fine analisi
- `weightDelta`: Variazione peso in kg (negativo = perdita, positivo = aumento)
- `avgDailyCalories`: Media calorie consumate giornaliere
- `avgCaloriesBurned`: Media calorie bruciate giornaliere (BMR + attività)
- `avgDeficit`: Media deficit/surplus calorico giornaliero (negativo = deficit)
- `daysDeficitOnTrack`: Giorni in cui deficit/surplus era nel range target (±200 kcal)
- `daysMacrosOnTrack`: Giorni con macro aderenti al target (±10g per macro)
- `totalDays`: Giorni totali con dati registrati nel periodo
- `adherenceRate`: Percentuale aderenza complessiva (0.0-1.0)

**Calcoli**:
- **Weight Delta**: `peso_finale - peso_iniziale` (dai progressHistory nel periodo)
- **Avg Daily Calories**: Media delle `consumedCalories` registrate
- **Avg Deficit**: Media di `(consumedCalories - (caloriesBurnedBmr + caloriesBurnedActive))`
- **Days On Track**: Conta giorni dove il deficit effettivo è entro ±200 kcal dal target
- **Macros On Track**: Conta giorni dove P/C/F sono entro ±10g dai target
- **Adherence Rate**: `min(daysDeficitOnTrack, daysMacrosOnTrack) / totalDays`

**Casi d'uso**:
- Report settimanale progressi
- Calcolo aderenza a piano nutrizionale
- Validazione efficacia strategia (deficit reale vs atteso)
- Dashboard "This Week" con metriche aggregate

**Differenze con altre query**:
- **vs `nutritionalProfile`**: Questa query ritorna AGGREGATI su range, mentre `nutritionalProfile` ritorna dati grezzi completi
- **vs `meals.summaryRange`**: `progressScore` include anche dati peso/deficit/aderenza, non solo nutrizione
- **Vantaggio**: Combina dati profilo + progress tracking + validazione aderenza in una query

**Esempio pratico - Report settimanale**:
```graphql
query WeeklyProgress {
  nutritionalProfile {
    progressScore(
      userId: "user123"
      startDate: "2025-10-21"
      endDate: "2025-10-27"
    ) {
      weightDelta          # "Lost 0.8 kg this week"
      avgDailyCalories     # "Avg: 1,850 kcal/day"
      avgDeficit           # "Avg deficit: -450 kcal/day"
      adherenceRate        # "Adherence: 85%"
      daysDeficitOnTrack   # "6/7 days on track"
    }
  }
}
```

---

#### `nutritionalProfile.forecastWeight` 🤖 ML-POWERED

Genera previsioni di peso future usando modelli di machine learning su serie temporali.

**Uso**:
```graphql
query {
  nutritionalProfile {
    forecastWeight(
      profileId: "279ed963-39b3-477a-a12c-cd4703d8464c"
      daysAhead: 30
      confidenceLevel: 0.95
    ) {
      profileId
      generatedAt
      modelUsed
      confidenceLevel
      dataPointsUsed
      trendDirection
      trendMagnitude
      predictions {
        date
        predictedWeight
        lowerBound
        upperBound
      }
    }
  }
}
```

**Parametri**:
- `profileId` (String!): ID del profilo nutrizionale
- `daysAhead` (Int, opzionale, default: 30): Giorni futuri da prevedere (1-90)
- `confidenceLevel` (Float, opzionale, default: 0.95): Livello confidenza intervalli (0.68, 0.95, 0.99)

**Ritorna**: `WeightForecastType` con previsioni e metadati

**Campi Ritornati**:
- `profileId`: ID profilo utilizzato
- `generatedAt`: Timestamp generazione forecast
- `modelUsed`: Modello ML utilizzato (SimpleTrend, LinearRegression, ExponentialSmoothing, ARIMA)
- `confidenceLevel`: Livello confidenza intervalli (es: 0.95 = 95%)
- `dataPointsUsed`: Numero record progresso utilizzati per training
- `trendDirection`: Direzione trend previsto ("decreasing", "increasing", "stable")
- `trendMagnitude`: Magnitudine variazione prevista in kg (negativo = perdita, positivo = aumento)
- `predictions`: Array di previsioni giornaliere
  - `date`: Data previsione
  - `predictedWeight`: Peso previsto in kg
  - `lowerBound`: Limite inferiore intervallo confidenza
  - `upperBound`: Limite superiore intervallo confidenza

**Selezione Automatica Modello** (data-driven):
- **SimpleTrend** (<7 data points): Estrapolazione lineare con intervalli espansi
- **LinearRegression** (7-13 points): Regressione lineare OLS con intervalli predizione
- **ExponentialSmoothing** (14-29 points): Holt's method per trend + stagionalità
- **ARIMA(1,1,1)** (30+ points): Modello time series completo con fallback

**Trend Analysis** 🎯:
- **Stable** (`|magnitude| < 0.5 kg`): Plateau rilevato
  - Insight: Considera aggiustare calorie per rompere plateau
- **Decreasing** (`magnitude < -0.5 kg`): Perdita peso prevista
  - Insight: Trend coerente con obiettivo CUT
- **Increasing** (`magnitude > 0.5 kg`): Aumento peso previsto
  - Insight: Trend coerente con obiettivo BULK o verifica deficit

**Requisiti Minimi**:
- Almeno 2 record di progresso nel profilo
- Record ordinati cronologicamente
- Peso sempre positivo

**Validazione**:
- `daysAhead` deve essere tra 1 e 90
- `confidenceLevel` deve essere 0.68, 0.95 o 0.99
- Se dati insufficienti → errore esplicativo

**Confidenza Intervalli**:
- **95%**: Intervallo standard, 95% probabilità peso reale sia nell'intervallo
- **68%**: Intervallo stretto, ~1 deviazione standard
- **99%**: Intervallo largo, massima confidenza

**Performance**:
- Response time tipico: 30-170ms
- Cache: Non implementata (calcoli veloci)
- Background job: Nessuno (on-demand)

**Casi d'uso**:
- Dashboard "Goal Prediction": "You'll reach 75kg by 2025-12-15"
- Motivazione utente: Visualizzare progresso futuro
- Validazione piano: "At current rate, you'll lose 5kg in 60 days"
- Plateau detection: "Weight stable for 14 days, consider calorie adjustment"

**Esempio pratico - Previsione 2 settimane**:
```graphql
query ShortTermForecast {
  nutritionalProfile {
    forecastWeight(
      profileId: "abc-123"
      daysAhead: 14
      confidenceLevel: 0.95
    ) {
      modelUsed              # "ExponentialSmoothing"
      trendDirection         # "decreasing"
      trendMagnitude         # -0.8 (kg)
      predictions {
        date                 # "2025-11-17"
        predictedWeight      # 82.3
        lowerBound           # 81.5
        upperBound           # 83.1
      }
    }
  }
}
```

**Esempio pratico - Plateau Detection**:
```graphql
query CheckPlateau {
  nutritionalProfile {
    forecastWeight(profileId: "abc-123", daysAhead: 7) {
      trendDirection         # "stable"
      trendMagnitude         # 0.2 (kg, within threshold)
      # UI: Show "⚠️ Weight plateau detected. Consider adjusting calories."
    }
  }
}
```

**Differenze con altre query**:
- **vs `progressScore`**: `forecastWeight` prevede FUTURO, `progressScore` analizza PASSATO
- **vs `nutritionalProfile`**: `forecastWeight` usa ML per predizioni, `nutritionalProfile` mostra dati attuali
- **Vantaggio**: Predizioni scientifiche con intervalli confidenza, non semplici trend lineari

**Note ML**:
- ARIMA può fallire convergenza → graceful fallback a ExponentialSmoothing
- Intervalli confidenza si espandono nel tempo (maggiore incertezza)
- Peso costante → SimpleTrend con previsioni stabili
- Trend Detection considera solo primo e ultimo giorno previsioni (robust to noise)

---

### Mutations: `nutritionalProfile`

#### `nutritionalProfile.createNutritionalProfile`

Crea un nuovo profilo nutrizionale per un utente.

**Uso**:
```graphql
mutation {
  nutritionalProfile {
    createNutritionalProfile(
      input: {
        userId: "user123"
        userData: {
          weight: 85.0
          height: 180.0
          age: 30
          sex: M
          activityLevel: MODERATE
        }
        goal: CUT
        initialWeight: 85.0
        initialDate: "2025-10-28"
      }
    ) {
      profileId
      userId
      goal
      bmr { value }
      tdee { value }
      caloriesTarget
      macroSplit {
        proteinG
        carbsG
        fatG
      }
      progressHistory {
        date
        weight
      }
    }
  }
}
```

**Parametri**:
- `input.userId` (String!): ID utente
- `input.userData` (UserDataInput!): Dati biometrici e attività
  - `weight` (Float!): Peso attuale in kg (range: 30-300)
  - `height` (Float!): Altezza in cm (range: 100-250)
  - `age` (Int!): Età in anni (range: 18-120)
  - `sex` (SexEnum!): Sesso biologico (M o F)
  - `activityLevel` (ActivityLevelEnum!): Livello attività fisica
- `input.goal` (GoalEnum!): Obiettivo nutrizionale (CUT, MAINTAIN, BULK)
- `input.initialWeight` (Float!): Peso iniziale per tracking progresso
- `input.initialDate` (Date, opzionale): Data inizio tracking (default: oggi)

**Ritorna**: `NutritionalProfileType` - Profilo completo con calcoli BMR/TDEE/macros

**Validazioni**:
- Un utente può avere solo un profilo attivo (vincolo unicità su `user_id`)
- Se esiste già un profilo, la mutation fallisce
- Tutti i valori biometrici devono essere nei range consentiti

**Comportamento**:
1. Calcola BMR con formula Mifflin-St Jeor
2. Calcola TDEE moltiplicando BMR per activity multiplier
3. Calcola calorie target aggiustando TDEE per goal
4. Calcola macro split ottimale per goal
5. Crea primo record in progressHistory con peso iniziale
6. Ritorna profilo completo

**Quando usarla**:
- Onboarding nuovo utente
- Setup iniziale profilo fitness
- Prima configurazione obiettivi nutrizionali

---

#### `nutritionalProfile.updateNutritionalProfile`

Aggiorna un profilo esistente (goal o dati biometrici).

**Uso**:
```graphql
mutation {
  nutritionalProfile {
    updateNutritionalProfile(
      input: {
        profileId: "profile-uuid-123"
        goal: MAINTAIN
      }
    ) {
      profileId
      goal
      caloriesTarget
      macroSplit {
        proteinG
        carbsG
        fatG
      }
      updatedAt
    }
  }
}
```

**Parametri**:
- `input.profileId` (String!): UUID del profilo da aggiornare
- `input.userData` (UserDataInput, opzionale): Nuovi dati biometrici
  - Se fornito, ricalcola BMR/TDEE/target con nuovi valori
- `input.goal` (GoalEnum, opzionale): Nuovo obiettivo (CUT, MAINTAIN, BULK)
  - Se cambiato, ricalcola calorie target e macro split

**Ritorna**: `NutritionalProfileType` - Profilo aggiornato con nuovi calcoli

**Comportamento**:
- Se cambi `goal`: Ricalcola `caloriesTarget` e `macroSplit` mantenendo stesso BMR/TDEE
- Se cambi `userData`: Ricalcola BMR, TDEE, caloriesTarget e macroSplit da zero
- Se cambi entrambi: Ricalcola tutto con nuovi dati
- Aggiorna `updatedAt` timestamp

**Quando usarla**:
- Cambio obiettivo (da cut a maintain, da bulk a cut, ecc.)
- Aggiornamento peso dopo periodo di tracking
- Modifica livello attività (es. inizio nuovo programma allenamento)
- Ricalcolo dopo milestone raggiunta

**Esempio pratico - Cambio goal dopo target raggiunto**:
```graphql
mutation SwitchToMaintenance {
  nutritionalProfile {
    updateNutritionalProfile(
      input: {
        profileId: "abc-123"
        userData: {
          weight: 78.0      # Nuovo peso dopo cut
          height: 180.0
          age: 30
          sex: M
          activityLevel: MODERATE
        }
        goal: MAINTAIN      # Passa da CUT a MAINTAIN
      }
    ) {
      caloriesTarget      # Aumentato da 2100 a 2600 (esempio)
      macroSplit {
        proteinG          # Ridotto da 190g a 150g
        carbsG            # Aumentato da 220g a 320g
        fatG              # Aumentato da 60g a 80g
      }
    }
  }
}
```

---

#### `nutritionalProfile.recordProgress`

Registra progresso giornaliero (peso, calorie, macros).

**Uso**:
```graphql
mutation {
  nutritionalProfile {
    recordProgress(
      input: {
        profileId: "profile-uuid-123"
        date: "2025-10-28"
        weight: 84.5
        consumedCalories: 2100
        consumedProteinG: 180
        consumedCarbsG: 230
        consumedFatG: 65
        caloriesBurnedActive: 450
        notes: "Allenamento intenso"
      }
    ) {
      date
      weight
      consumedCalories
      consumedProteinG
      consumedCarbsG
      consumedFatG
      caloriesBurnedBmr
      caloriesBurnedActive
      notes
    }
  }
}
```

**Parametri**:
- `input.profileId` (String!): UUID del profilo
- `input.date` (Date!): Data registrazione (formato: YYYY-MM-DD)
- `input.weight` (Float!): Peso del giorno in kg
- `input.consumedCalories` (Float, opzionale): Calorie totali consumate
- `input.consumedProteinG` (Float, opzionale): Proteine consumate in grammi
- `input.consumedCarbsG` (Float, opzionale): Carboidrati consumati in grammi
- `input.consumedFatG` (Float, opzionale): Grassi consumati in grammi
- `input.caloriesBurnedBmr` (Float, opzionale): Calorie bruciate a riposo (auto-filled se null)
- `input.caloriesBurnedActive` (Float, opzionale): Calorie bruciate da attività
- `input.notes` (String, opzionale): Note giornata

**Ritorna**: `ProgressRecordType` - Record registrato

**Comportamento**:
- Se esiste già un record per stessa data: **UPDATE** (sovrascrive)
- Se `caloriesBurnedBmr` è null: Usa automaticamente BMR del profilo
- Tutti i campi nutrizionali sono opzionali (permette tracking parziale)
- Record viene aggiunto a `progressHistory` del profilo

**Validazioni**:
- `date` deve essere una data valida (non futura)
- `weight` deve essere ragionevole (30-300 kg)
- Valori nutrizionali devono essere non negativi se forniti

**Quando usarla**:
- Check-in giornaliero peso
- Log dati nutrizionali fine giornata
- Registrazione calorie attività da wearable
- Tracking aderenza piano

**Workflow tipico**:
```graphql
# Ogni mattina: registra peso
mutation MorningWeighIn {
  nutritionalProfile {
    recordProgress(
      input: {
        profileId: "abc-123"
        date: "2025-10-28"
        weight: 84.5
      }
    ) {
      date
      weight
    }
  }
}

# Fine giornata: aggiungi dati nutrizionali
mutation EveningUpdate {
  nutritionalProfile {
    recordProgress(
      input: {
        profileId: "abc-123"
        date: "2025-10-28"
        weight: 84.5
        consumedCalories: 2100
        consumedProteinG: 180
        consumedCarbsG: 230
        consumedFatG: 65
        caloriesBurnedActive: 450
      }
    ) {
      date
      weight
      consumedCalories
    }
  }
}
```

**Integrazione cross-domain**:
```typescript
// Esempio: Popola automaticamente da meal domain
const dailySummary = await meals.dailySummary({ userId, date });

await nutritionalProfile.recordProgress({
  profileId,
  date,
  weight: userInput.weight,
  consumedCalories: dailySummary.totalCalories,
  consumedProteinG: dailySummary.totalProtein,
  consumedCarbsG: dailySummary.totalCarbs,
  consumedFatG: dailySummary.totalFat,
  caloriesBurnedActive: activityData.totalCaloriesOut
});
```

---

## Root Mutations

### `syncHealthTotals`

Sincronizza snapshot cumulativi giornalieri di attività.

**Uso**:
```graphql
mutation {
  syncHealthTotals(
    input: {
      date: "2025-10-28"
      timestamp: "2025-10-28T15:00:00Z"
      steps: 8000
      caloriesOut: 450.5
      hrAvgSession: 75
    }
    userId: "user123"
    idempotencyKey: "sync-15h"
  ) {
    accepted
    duplicate
    reset
    idempotencyKeyUsed
    idempotencyConflict
    delta {
      timestamp
      steps
      caloriesOut
      hrAvgSession
    }
  }
}
```

**Parametri**:
- `input.date` (String!): Data in formato YYYY-MM-DD
- `input.timestamp` (DateTime!): Timestamp della sync
- `input.steps` (Int!): **Totale cumulativo** passi della giornata
- `input.caloriesOut` (Float!): **Totale cumulativo** calorie bruciate
- `input.hrAvgSession` (Int, opzionale): Frequenza cardiaca media sessione
- `userId` (String, opzionale): ID utente
- `idempotencyKey` (String, opzionale): Chiave per deduplicazione

**Ritorna**: `SyncHealthTotalsResult`
- `accepted`: true se accettato
- `duplicate`: true se già processato (stessa idempotency key)
- `reset`: true se totale è MINORE del precedente (reset device)
- `delta`: Incremento calcolato rispetto all'ultima sync

**Idempotenza**:
- L'`idempotencyKey` è **obbligatoria** per funzionamento corretto
- Stessa key con stesso payload → `duplicate: true`, ritorna risultato cached
- Key diversa con stesso timestamp/dati → viene accettata come nuova sync (il sistema calcola i delta)
- L'idempotency key ha TTL di 24 ore

**Differenza con `activity.syncActivityEvents`**:
- Questa mutation accetta **totali cumulativi** della giornata
- Il sistema calcola automaticamente i **delta** rispetto alla sync precedente
- Ideale per sincronizzazioni periodiche da app (ogni ora, ogni apertura)

**Quando usarla**:
- Quando hai totali giornalieri progressivi da Fitbit/Apple Health/Google Fit
- Per sync periodiche (ogni ora, ogni apertura app)
- NON quando hai dati minute-by-minute (usa `activity.syncActivityEvents`)

---

## Utilities

### `serverTime`

Ritorna timestamp corrente del server.

**Uso**:
```graphql
query {
  serverTime
}
```

**Ritorna**: String ISO timestamp

---

### `health`

Health check endpoint.

**Uso**:
```graphql
query {
  health
}
```

**Ritorna**: "OK" se server attivo

---

### `cacheStats`

Statistiche della cache prodotti.

**Uso**:
```graphql
query {
  cacheStats {
    size
    hits
    misses
    hitRate
  }
}
```

**Ritorna**: `CacheStats` con metriche cache

---

## Best Practices

### Scelta della Query Giusta

#### Namespace Nutritional Profile - Quando usare quale query?

| Query | Scopo | Ritorna | Caso d'uso tipico |
|-------|-------|---------|-------------------|
| `nutritionalProfile` | Profilo completo con dati grezzi | Profilo + progressHistory | Dashboard profilo, edit settings, view history |
| `progressScore` | Statistiche aggregate su range | Metriche aderenza + peso | Report settimanale, validazione piano, trend analysis |

**Regola pratica**:
- Serve **dati completi** del profilo? → `nutritionalProfile` (settings, targets, history raw)
- Serve **report aggregato** con aderenza? → `progressScore` (weekly stats, compliance)

**Workflow consigliato**:
```typescript
// Dashboard profilo: Usa nutritionalProfile per dati completi
const profile = await query.nutritionalProfile.nutritionalProfile({ userId });
// Display: goal, targets, BMR/TDEE, macro split, raw history

// Report settimanale: Usa progressScore per aggregati
const weeklyStats = await query.nutritionalProfile.progressScore({
  userId,
  startDate: startOfWeek(),
  endDate: endOfWeek()
});
// Display: weight delta, avg calories, adherence rate

// Combined dashboard: 1 query con entrambi
query WeeklyDashboard {
  profile: nutritionalProfile { nutritionalProfile(userId: "user123") {...} }
  stats: nutritionalProfile { progressScore(userId: "user123", ...) {...} }
}
```

**Integrazione cross-domain**:
```typescript
// Pattern: Popola automaticamente progressRecord da altri domini
async function dailyCheckIn(userId: string, weight: number, date: string) {
  // 1. Fetch meal totals
  const meals = await query.meals.dailySummary({ userId, date });
  
  // 2. Fetch activity totals
  const activity = await query.activity.aggregateRange({
    userId,
    startDate: date,
    endDate: date,
    groupBy: 'DAY'
  });
  
  // 3. Record in profile (single source of truth)
  await mutation.nutritionalProfile.recordProgress({
    profileId,
    date,
    weight,
    consumedCalories: meals.totalCalories,
    consumedProteinG: meals.totalProtein,
    consumedCarbsG: meals.totalCarbs,
    consumedFatG: meals.totalFat,
    caloriesBurnedActive: activity.total.totalCaloriesOut
  });
}
```

---

#### Namespace Meals - Quando usare quale query?

| Query | Scopo | Granularità | Ritorna | Caso d'uso tipico |
|-------|-------|-------------|---------|-------------------|
| `meal` | Singolo meal per ID | 1 meal | Meal completo con entries | Dettaglio meal, modifica, visualizzazione singola |
| `mealHistory` | Lista meals con filtri | N meals | Array di Meal | Lista cronologica, scroll infinito, filtri |
| `search` | Ricerca full-text | N meals | Array di Meal | Barra di ricerca, "Trova meal con pollo" |
| `dailySummary` | Aggregato 1 giorno | 1 giorno | Totali nutrizionali + breakdown | Dashboard "Today", widget giornaliero |
| `summaryRange` | Aggregati multi-giorno | N giorni/settimane/mesi | Periods + Total | Dashboard settimanale/mensile, grafici trend |

**Regola pratica**:
- Serve **dettagli** di meal singoli? → `meal` / `mealHistory` / `search`
- Serve **aggregati** nutrizionali? → `dailySummary` (1 giorno) o `summaryRange` (range)
- Hai un **range di date**? → Sempre `summaryRange` (evita loop di N `dailySummary`)

**Esempio anti-pattern** ❌:
```typescript
// SBAGLIATO: Loop di 7 query per dashboard settimanale
for (let i = 0; i < 7; i++) {
  const date = addDays(today, -i);
  const summary = await client.query.meals.dailySummary({
    userId, date
  });
  // ... processa singolo giorno
}
```

**Esempio corretto** ✅:
```typescript
// GIUSTO: 1 query per dashboard settimanale
const weeklySummary = await client.query.meals.summaryRange({
  userId,
  startDate: subDays(today, 6),
  endDate: today,
  groupBy: 'DAY'
});
// periods[] ha già tutti i 7 giorni + total aggregato
```

---

#### Namespace Activity - Quando usare quale query?

| Query | Scopo | Granularità | Ritorna | Caso d'uso tipico |
|-------|-------|-------------|---------|-------------------|
| `entries` | Eventi minute-by-minute | Minuti | Array ActivityEvent | Grafico intraday dettagliato, analisi pattern |
| `syncEntries` | Delta sincronizzazioni | Sync snapshots | Array HealthTotalsDelta | Debugging sync, audit trail |
| `aggregateRange` | Aggregati multi-giorno | N giorni/settimane/mesi | Periods + Total | Dashboard settimanale/mensile, goal tracking |

**Regola pratica**:
- Serve **granularità minuto-per-minuto**? → `entries` (grafici intraday)
- Serve **debugging sync**? → `syncEntries` (delta timeline)
- Serve **aggregati per dashboard**? → `aggregateRange` (totali/medie per periodo)

**Esempio anti-pattern** ❌:
```typescript
// SBAGLIATO: Fetch tutti gli eventi e aggrega lato client
const events = await client.query.activity.entries({
  userId,
  after: startOfWeek,
  before: endOfWeek,
  limit: 10000  // Troppi dati!
});
// Aggrega lato client (lento, inefficiente)
const totalSteps = events.reduce((sum, e) => sum + e.steps, 0);
```

**Esempio corretto** ✅:
```typescript
// GIUSTO: Usa aggregateRange per totali pre-calcolati
const weeklyActivity = await client.query.activity.aggregateRange({
  userId,
  startDate: startOfWeek,
  endDate: endOfWeek,
  groupBy: 'DAY'
});
// total.totalSteps è già calcolato lato server
```

---

### Idempotenza

**Mutations idempotenti**:
- `activity.syncActivityEvents`
- `syncHealthTotals`

**Come funziona**:
1. Fornisci una `idempotencyKey` univoca per richiesta
2. Se omessa, viene auto-generata da payload (esclusi timestamp)
3. Stessa key con stesso payload → ritorna risultato cached
4. Stessa key con payload diverso → errore IdempotencyConflict

**Esempio**:
```graphql
mutation {
  activity {
    syncActivityEvents(
      input: [{ts: "2025-10-28T10:00:00Z", steps: 50}]
      idempotencyKey: "sync-batch-morning-001"  # ← chiave client-defined
    ) {
      accepted
      idempotencyKeyUsed
    }
  }
}
```

---

### Paginazione

**Query con paginazione**:
- `meals.mealHistory`
- `meals.search`
- `activity.entries`
- `activity.syncEntries`

**Pattern**:
```graphql
query {
  meals {
    mealHistory(userId: "user123", limit: 20, offset: 0) {
      meals { id timestamp }
      totalCount
      hasMore  # ← true se ci sono altri risultati
    }
  }
}

# Pagina successiva
query {
  meals {
    mealHistory(userId: "user123", limit: 20, offset: 20) {
      meals { id timestamp }
      totalCount
      hasMore
    }
  }
}
```

---

### Error Handling

**Union types per errori**:
```graphql
mutation {
  meals {
    analyzeMealPhoto(input: {...}) {
      ... on MealPhotoSuccess {
        meal { id dishName }
      }
      ... on MealPhotoError {
        code     # ← es. "ANALYSIS_FAILED", "INVALID_IMAGE"
        message  # ← messaggio descrittivo
      }
    }
  }
}
```

**Gestione in client**:
```typescript
const result = await client.mutation.meals.analyzeMealPhoto({...});

if (result.__typename === 'MealPhotoSuccess') {
  console.log('Meal:', result.meal);
} else if (result.__typename === 'MealPhotoError') {
  console.error('Error:', result.code, result.message);
}
```

---

## Workflow Tipici

### 1. Analisi meal da foto

```graphql
# Step 1: Analizza foto
mutation {
  meals {
    analyzeMealPhoto(input: {
      userId: "user123"
      photoUrl: "https://..."
      timestamp: "2025-10-28T12:30:00Z"
      mealType: LUNCH
      dishHint: "Pranzo in ufficio"
    }) {
      ... on MealAnalysisSuccess {
        analysisId
        meal {
          id
          dishName
          entries { id name quantityG calories }
          totalCalories
        }
      }
    }
  }
}

# Step 2: Conferma analisi (rende il meal definitivo)
mutation {
  meals {
    confirmMealAnalysis(input: {
      mealId: "..."
      userId: "user123"
      confirmedEntryIds: ["entry-1", "entry-2"]
    }) {
      ... on ConfirmAnalysisSuccess {
        meal { id }
        confirmedCount
      }
    }
  }
}
```

---

### 2. Analisi meal da testo

```graphql
# Step 1: Analizza descrizione testuale
mutation {
  meals {
    analyzeMealText(input: {
      userId: "user123"
      textDescription: "150g di pasta al pomodoro con basilico"
      timestamp: "2025-10-28T12:30:00Z"
      mealType: LUNCH
      idempotencyKey: "lunch-oct28"
    }) {
      ... on MealAnalysisSuccess {
        analysisId
        meal {
          id
          dishName
          entries {
            id
            name
            displayName
            quantityG
            calories
            protein
          }
          totalCalories
          source  # "DESCRIPTION"
        }
      }
      ... on MealAnalysisError {
        code
        message
      }
    }
  }
}

# Step 2: Conferma analisi (opzionale: rifiuta alcuni entries)
mutation {
  meals {
    confirmMealAnalysis(input: {
      mealId: "..."
      userId: "user123"
      confirmedEntryIds: ["entry-1", "entry-2"]  # Esclude entry-3 se non desiderato
    }) {
      ... on ConfirmAnalysisSuccess {
        meal {
          id
          totalCalories  # Ricalcolato senza entry rifiutato
        }
        confirmedCount
        rejectedCount
      }
    }
  }
}
```

**Esempi di descrizioni supportate**:
```text
# Con quantità esplicite
"150g di pasta al pomodoro con basilico"
→ 3 entries: Pasta (150g), Sugo (80g), Basilico (5g)

# Con quantità implicite
"2 uova strapazzate con toast"
→ 3 entries: Eggs (100g), Toast (30g), Butter (5g)

# Descrizione minima
"una mela"
→ 1 entry: Apple (182g, AI estimated)

# Meal complessi
"colazione con yogurt greco, muesli e frutti di bosco"
→ 4 entries: Greek yogurt (150g), Muesli (40g), Blueberries (50g), Strawberries (50g)
```

---

### 3. Analisi meal da barcode

```graphql
# Step 1: Analizza prodotto da barcode
mutation {
  meals {
    analyzeMealBarcode(input: {
      userId: "user123"
      barcode: "8001505005707"
      quantityG: 100
      timestamp: "2025-10-28T15:00:00Z"
      mealType: SNACK
    }) {
      ... on MealAnalysisSuccess {
        analysisId
        meal {
          id
          dishName
          entries {
            name
            barcode
            quantityG
            calories
            protein
          }
          totalCalories
        }
      }
    }
  }
}

# Step 2: Conferma analisi
mutation {
  meals {
    confirmMealAnalysis(input: {
      mealId: "..."
      userId: "user123"
      confirmedEntryIds: ["entry-1"]
    }) {
      ... on ConfirmAnalysisSuccess {
        meal { id totalCalories }
      }
    }
  }
}
```

---

### 4. Sincronizzazione attività periodica

```graphql
# Ogni ora, invia totale cumulativo
mutation {
  syncHealthTotals(
    input: {
      date: "2025-10-28"
      timestamp: "2025-10-28T15:00:00Z"
      steps: 8000        # ← totale fino alle 15:00
      caloriesOut: 450
    }
    userId: "user123"
    idempotencyKey: "sync-15h"  # ← evita duplicati
  ) {
    delta {
      steps           # ← incremento rispetto a sync precedente
    }
  }
}
```

---

### 5. Dashboard giornaliero

```graphql
query {
  # Riepilogo nutrizionale
  meals {
    dailySummary(userId: "user123", date: "2025-10-28T00:00:00Z") {
      totalCalories
      totalProtein
      mealCount
      breakdownByType
    }
  }
  
  # Ultimi meal
  meals {
    mealHistory(userId: "user123", limit: 5, offset: 0) {
      meals {
        id
        timestamp
        mealType
        dishName
        totalCalories
      }
    }
  }
  
  # Attività recente
  activity {
    entries(userId: "user123", limit: 60) {
      timestamp
      steps
      caloriesOut
    }
  }
}
```

---

### 6. Dashboard settimanale con trend

```graphql
query WeeklyDashboard {
  # Nutrition trend ultimi 7 giorni
  meals {
    summaryRange(
      userId: "user123"
      startDate: "2025-10-22T00:00:00Z"
      endDate: "2025-10-28T23:59:59Z"
      groupBy: DAY
    ) {
      periods {
        period          # Per grafico: asse X
        totalCalories   # Per grafico: asse Y
        totalProtein
        mealCount
        breakdownByType
      }
      total {
        totalCalories   # "Week total: 12,450 kcal"
        totalProtein    # "Week total: 420g protein"
        mealCount       # "21 meals this week"
      }
    }
  }
  
  # Activity trend ultimi 7 giorni
  activity {
    aggregateRange(
      userId: "user123"
      startDate: "2025-10-22T00:00:00Z"
      endDate: "2025-10-28T23:59:59Z"
      groupBy: DAY
    ) {
      periods {
        period          # Per grafico: asse X
        totalSteps      # Per grafico: asse Y
        totalCaloriesOut
        avgHeartRate
      }
      total {
        totalSteps      # "Week total: 65,432 steps"
        totalCaloriesOut # "Week total: 3,250 kcal burned"
      }
    }
  }
}
```

**Implementazione UI**:
```typescript
// Component: WeeklyDashboard.tsx
const { data } = useQuery(WEEKLY_DASHBOARD_QUERY);

// Grafico nutrition (Chart.js / Recharts)
const nutritionChartData = data.meals.summaryRange.periods.map(p => ({
  date: p.period,
  calories: p.totalCalories,
  protein: p.totalProtein
}));

// Grafico activity
const activityChartData = data.activity.aggregateRange.periods.map(p => ({
  date: p.period,
  steps: p.totalSteps,
  caloriesOut: p.totalCaloriesOut
}));

// Cards riepilogo
<Card>
  <Title>This Week</Title>
  <Stat label="Total Calories" value={data.meals.summaryRange.total.totalCalories} />
  <Stat label="Total Steps" value={data.activity.aggregateRange.total.totalSteps} />
  <Stat label="Meals Logged" value={data.meals.summaryRange.total.mealCount} />
</Card>
```

---

### 7. Report mensile con confronto

```graphql
query MonthlyReport {
  # Questo mese (raggruppato per settimana)
  thisMonth: meals {
    summaryRange(
      userId: "user123"
      startDate: "2025-10-01T00:00:00Z"
      endDate: "2025-10-31T23:59:59Z"
      groupBy: WEEK
    ) {
      periods {
        period          # "2025-W40", "2025-W41", ...
        totalCalories
        mealCount
      }
      total {
        totalCalories
        totalProtein
        mealCount
      }
    }
  }
  
  # Mese scorso (per confronto)
  lastMonth: meals {
    summaryRange(
      userId: "user123"
      startDate: "2025-09-01T00:00:00Z"
      endDate: "2025-09-30T23:59:59Z"
      groupBy: WEEK
    ) {
      total {
        totalCalories
        totalProtein
        mealCount
      }
    }
  }
  
  # Activity questo mese
  activityThisMonth: activity {
    aggregateRange(
      userId: "user123"
      startDate: "2025-10-01T00:00:00Z"
      endDate: "2025-10-31T23:59:59Z"
      groupBy: WEEK
    ) {
      periods {
        period
        totalSteps
        totalCaloriesOut
      }
      total {
        totalSteps
        totalCaloriesOut
        avgHeartRate
      }
    }
  }
}
```

**Implementazione UI**:
```typescript
// Component: MonthlyReport.tsx
const { data } = useQuery(MONTHLY_REPORT_QUERY);

// Confronto month-over-month
const caloriesDiff = data.thisMonth.total.totalCalories - 
                     data.lastMonth.total.totalCalories;
const percentChange = (caloriesDiff / data.lastMonth.total.totalCalories) * 100;

<ComparisonCard>
  <Month>October 2025</Month>
  <Metric value={data.thisMonth.total.totalCalories} unit="kcal" />
  <Trend value={percentChange} />  {/* +8.5% vs September */}
</ComparisonCard>

// Grafico trend settimanale
const weeklyTrend = data.thisMonth.periods.map(p => ({
  week: p.period,      // "W40", "W41", ...
  calories: p.totalCalories,
  meals: p.mealCount
}));
```

---

### 8. Goal tracking con progress

```graphql
query GoalTracking {
  # Goal settimanale: 50,000 steps
  weeklySteps: activity {
    aggregateRange(
      userId: "user123"
      startDate: "2025-10-27T00:00:00Z"  # Monday
      endDate: "2025-11-02T23:59:59Z"    # Sunday
      groupBy: DAY
    ) {
      periods {
        period
        totalSteps
      }
      total {
        totalSteps      # Progress verso goal
      }
    }
  }
  
  # Goal nutrizionale: 1800 kcal/giorno media
  weeklyNutrition: meals {
    summaryRange(
      userId: "user123"
      startDate: "2025-10-27T00:00:00Z"
      endDate: "2025-11-02T23:59:59Z"
      groupBy: DAY
    ) {
      periods {
        period
        totalCalories
      }
      total {
        totalCalories
        mealCount
      }
    }
  }
}
```

**Implementazione UI**:
```typescript
// Component: GoalsWidget.tsx
const { data } = useQuery(GOAL_TRACKING_QUERY);

// Steps goal progress
const WEEKLY_STEPS_GOAL = 50000;
const currentSteps = data.weeklySteps.total.totalSteps;
const stepsProgress = (currentSteps / WEEKLY_STEPS_GOAL) * 100;

<ProgressBar 
  label="Weekly Steps Goal"
  current={currentSteps}
  goal={WEEKLY_STEPS_GOAL}
  progress={stepsProgress}
/>

// Calories goal progress (daily average)
const DAILY_CALORIES_TARGET = 1800;
const daysInWeek = data.weeklyNutrition.periods.length;
const avgDailyCalories = data.weeklyNutrition.total.totalCalories / daysInWeek;
const caloriesProgress = (avgDailyCalories / DAILY_CALORIES_TARGET) * 100;

<ProgressBar 
  label="Daily Calories Target (avg)"
  current={Math.round(avgDailyCalories)}
  goal={DAILY_CALORIES_TARGET}
  progress={caloriesProgress}
/>

// Mini chart: daily breakdown
<MiniChart 
  data={data.weeklySteps.periods}
  xKey="period"
  yKey="totalSteps"
  type="bar"
/>
```

---

### 9. Setup e tracking profilo nutrizionale completo

```graphql
# Step 1: Onboarding - Crea profilo iniziale
mutation CreateProfile {
  nutritionalProfile {
    createNutritionalProfile(
      input: {
        userId: "user123"
        userData: {
          weight: 85.0
          height: 180.0
          age: 30
          sex: M
          activityLevel: MODERATE
        }
        goal: CUT
        initialWeight: 85.0
        initialDate: "2025-10-21"
      }
    ) {
      profileId
      bmr { value }          # 1830 kcal/day
      tdee { value }         # 2836 kcal/day
      caloriesTarget         # 2336 kcal/day (deficit 500)
      macroSplit {
        proteinG             # 187g (high protein for cut)
        carbsG               # 251g
        fatG                 # 65g
      }
    }
  }
}

# Step 2: Check-in giornaliero (mattina)
mutation DailyWeighIn {
  nutritionalProfile {
    recordProgress(
      input: {
        profileId: "abc-123"
        date: "2025-10-28"
        weight: 84.2
      }
    ) {
      date
      weight
    }
  }
}

# Step 3: Fine giornata - Log dati completi
mutation EndOfDayLog {
  # Prima: ottieni totali dal meal domain
  meals {
    dailySummary(userId: "user123", date: "2025-10-28T00:00:00Z") {
      totalCalories
      totalProtein
      totalCarbs
      totalFat
    }
  }
  
  # Poi: registra nel profilo con dati activity
  nutritionalProfile {
    recordProgress(
      input: {
        profileId: "abc-123"
        date: "2025-10-28"
        weight: 84.2
        consumedCalories: 2100        # Da meals.dailySummary
        consumedProteinG: 180
        consumedCarbsG: 230
        consumedFatG: 65
        caloriesBurnedActive: 450     # Da activity domain
        notes: "Great training session"
      }
    ) {
      date
      weight
      consumedCalories
    }
  }
}

# Step 4: Report settimanale con aderenza
query WeeklyProgressReport {
  nutritionalProfile {
    # Profilo attuale
    nutritionalProfile(userId: "user123") {
      goal
      caloriesTarget
      macroSplit {
        proteinG
        carbsG
        fatG
      }
      progressHistory {
        date
        weight
        consumedCalories
      }
    }
    
    # Statistiche settimana
    progressScore(
      userId: "user123"
      startDate: "2025-10-21"
      endDate: "2025-10-27"
    ) {
      weightDelta           # -0.8 kg (good progress)
      avgDailyCalories      # 2150 kcal (vs target 2336)
      avgDeficit            # -450 kcal (vs target -500)
      daysDeficitOnTrack    # 6/7 days within ±200 kcal
      daysMacrosOnTrack     # 5/7 days with macros ±10g
      adherenceRate         # 0.71 (71% adherence)
    }
  }
}

# Step 5: Cambio goal dopo milestone
mutation SwitchToMaintain {
  nutritionalProfile {
    updateNutritionalProfile(
      input: {
        profileId: "abc-123"
        userData: {
          weight: 80.0        # Nuovo peso raggiunto
          height: 180.0
          age: 30
          sex: M
          activityLevel: MODERATE
        }
        goal: MAINTAIN        # Da CUT a MAINTAIN
      }
    ) {
      goal
      caloriesTarget        # Aumentato a 2750 (da 2300)
      macroSplit {
        proteinG            # 150g (ridotto da 187g)
        carbsG              # 330g (aumentato da 251g)
        fatG                # 90g (aumentato da 65g)
      }
    }
  }
}
```

**Implementazione UI - Dashboard Profilo**:
```typescript
// Component: NutritionProfileDashboard.tsx
const { data } = useQuery(NUTRITION_PROFILE_QUERY);

const profile = data.nutritionalProfile.nutritionalProfile;
const weeklyStats = data.nutritionalProfile.progressScore;

<ProfileCard>
  <Section title="Current Goal">
    <GoalBadge goal={profile.goal} />  {/* CUT */}
    <Stat label="Daily Target" value={`${profile.caloriesTarget} kcal`} />
  </Section>
  
  <Section title="Macro Targets">
    <MacroRing 
      protein={profile.macroSplit.proteinG}
      carbs={profile.macroSplit.carbsG}
      fat={profile.macroSplit.fatG}
    />
  </Section>
  
  <Section title="This Week">
    <Stat 
      label="Weight Change" 
      value={`${weeklyStats.weightDelta.toFixed(1)} kg`}
      trend={weeklyStats.weightDelta < 0 ? 'down' : 'up'}
    />
    <Stat 
      label="Adherence" 
      value={`${(weeklyStats.adherenceRate * 100).toFixed(0)}%`}
      status={weeklyStats.adherenceRate > 0.7 ? 'good' : 'warning'}
    />
    <Stat 
      label="Days On Track" 
      value={`${weeklyStats.daysDeficitOnTrack}/${weeklyStats.totalDays}`}
    />
  </Section>
  
  <Section title="Progress Chart">
    <WeightChart data={profile.progressHistory} />
  </Section>
</ProfileCard>

// Daily check-in flow
const handleDailyCheckIn = async (weight: number) => {
  // 1. Record weight
  await recordProgress({
    profileId: profile.profileId,
    date: today,
    weight
  });
  
  // 2. Fetch meal totals
  const mealData = await getDailySummary({ userId, date: today });
  
  // 3. Fetch activity totals
  const activityData = await getActivityAggregate({ 
    userId, 
    startDate: today, 
    endDate: today 
  });
  
  // 4. Update with full data
  await recordProgress({
    profileId: profile.profileId,
    date: today,
    weight,
    consumedCalories: mealData.totalCalories,
    consumedProteinG: mealData.totalProtein,
    consumedCarbsG: mealData.totalCarbs,
    consumedFatG: mealData.totalFat,
    caloriesBurnedActive: activityData.total.totalCaloriesOut
  });
};
```

---

## Note Architetturali

### Namespace Organization

L'API è organizzata per **domain** secondo CQRS:

- **`atomic`**: Query atomiche single-entity (product lookup)
- **`meals`**: Aggregate queries e mutations per meal domain
- **`activity`**: Queries e mutations per activity domain

### Meal Analysis Workflow

I meal creati da foto/barcode sono inizialmente in stato **PENDING**:

1. `analyzeMealPhoto` → crea meal PENDING
2. Client può visualizzare/modificare
3. `confirmMealAnalysis` → rende definitivo

Questo permette editing prima della conferma finale.

### Activity Data Models

Due modelli per dati activity:

1. **ActivityEvent** (minute-by-minute): Granularità massima, source-specific
2. **HealthTotalsDelta** (sync snapshots): Aggregati progressivi giornalieri

Scegli in base alla granularità disponibile dai tuoi device/API.

---

## Changelog

- **2025-11-02**: Nuova API per analisi meal da testo
  - ✨ Aggiunta mutation `meals.analyzeMealText`: Analizza meal da descrizione testuale con AI
  - 🤖 Riconoscimento AI con GPT-4o per identificare cibi e quantità da testo libero
  - 🍝 Supporto descrizioni complesse con più ingredienti (es. "pasta al pomodoro con basilico" → 3 entries)
  - 📏 Stima automatica quantità se non specificate (es. "una mela" → ~182g)
  - 🔄 Idempotenza con cache 1 ora (chiave opzionale, auto-generata da payload)
  - 📊 Source value: "DESCRIPTION" (consistente con domain event MealAnalyzed)
  - 🎯 Casi d'uso: Quick logging, retroactive logging, meal fuori casa, voice-to-text
  - 📝 Workflow completo: Analizza → Review entries → Conferma (come photo/barcode)
  - ✅ 13 unit tests passing (command handler + orchestrator + backward compatibility)
  - ✅ E2E test integrato in `test_meal_persistence.sh`
  - ✅ API validata manualmente: descrizioni semplici/complesse, idempotenza, confirmation workflow

- **2025-10-31**: Dominio Nutritional Profile completato (Phase 9.6)
  - ✨ Aggiunto namespace `nutritionalProfile` con queries e mutations complete
  - 📊 Query `nutritionalProfile`: Recupera profilo con BMR/TDEE/macro/progress history
  - 📈 Query `progressScore`: Statistiche aggregate con aderenza su range date
  - 🔧 Mutation `createNutritionalProfile`: Setup profilo con calcoli automatici BMR/TDEE
  - 🔄 Mutation `updateNutritionalProfile`: Aggiorna goal o dati biometrici con ricalcolo
  - 📝 Mutation `recordProgress`: Tracking giornaliero peso/calorie/macros
  - 🧮 Calcoli automatici: Mifflin-St Jeor BMR, TDEE con activity multipliers, macro split per goal
  - 🎯 Supporto 3 goals: CUT (deficit 500), MAINTAIN (TDEE), BULK (surplus 300)
  - 📊 Progress tracking: Weight delta, avg deficit, aderenza calorie/macros
  - 🔗 Integrazione cross-domain con meal e activity per calcolo deficit completo
  - 📝 Documentazione completa con workflow e best practices

- **2025-10-29**: Nuove query aggregate range
  - ✨ Aggiunta `meals.summaryRange`: Aggregati nutrizionali multi-giorno con grouping DAY/WEEK/MONTH
  - ✨ Aggiunta `activity.aggregateRange`: Aggregati activity multi-giorno con grouping DAY/WEEK/MONTH
  - 📊 Entrambe ritornano wrapper type con `periods` (breakdown per periodo) e `total` (aggregato totale)
  - 🎯 Ottimizzate per dashboard settimanali/mensili: 1 query invece di N loop
  - 🔧 Fix timezone handling in meal repository per comparazioni date corrette
  - 📝 Documentazione completa con tabelle comparative e workflow pratici
  
- **2025-10-28**: Refactor Phase 5 completato
  - Spostato `dailySummary` da root a `meals` namespace
  - Rinominato `ingestActivityEvents` → `activity.syncActivityEvents`
  - Organizzazione namespace per domain (meals, activity)
  - Idempotenza con auto-generation di keys
