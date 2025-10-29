# GraphQL API Reference

Documentazione completa delle query e mutation disponibili nell'API GraphQL di Nutrifit dopo il refactor Phase 5.

## Indice

- [Struttura dell'API](#struttura-dellapi)
- [Namespace: Meals](#namespace-meals)
- [Namespace: Activity](#namespace-activity)
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
  atomic: AtomicQueries!        # Query atomiche meal
  meals: AggregateQueries!      # Query aggregate meal
  activity: ActivityQueries!    # Query activity
  
  cacheStats: CacheStats!       # Utility
}

type Mutation {
  meals: MealMutations!         # Mutations meal
  activity: ActivityMutations!  # Mutations activity
  syncHealthTotals(...)         # Mutation root (legacy)
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

### 2. Sincronizzazione attività periodica

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

### 3. Dashboard giornaliero

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

### 4. Dashboard settimanale con trend

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

### 5. Report mensile con confronto

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

### 6. Goal tracking con progress

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
