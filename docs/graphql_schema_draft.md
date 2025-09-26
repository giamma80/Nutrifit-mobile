# GraphQL Schema Draft – Nutrition, Activity & Recommendations

Versione: 0.1 (Draft evolutivo)
Ultimo aggiornamento: 2025-09-24

<!-- AGGIUNTA: Sezione anticipazione syncHealthTotals (minor 0.5.0) -->
> Nota (design approvato – non ancora runtime): la prossima minor introdurrà `syncHealthTotals` come fonte primaria dei totali attività. Le minute events ingerite via `ingestActivityEvents` rimarranno per analisi granulare ma non alimenteranno più i totali `dailySummary`.

## Stato Runtime Attuale (Slice Implementato)
Al momento il backend espone un sottoinsieme ampliato del draft completo:

Implemented oggi (runtime slice):
```
type Query {
  product(barcode: String!): Product
  mealEntries(after: String, before: String, limit: Int, userId: ID): [MealEntry!]!
  dailySummary(date: Date!, userId: ID): DailySummary!
  cacheStats: CacheStats!
}

type Mutation {
  logMeal(input: LogMealInput!): MealEntry!
  updateMeal(id: ID!, input: LogMealInput!): MealEntry!        # placeholder (non ancora implementato runtime)
  deleteMeal(id: ID!): DeleteMealResult!                       # placeholder (non ancora implementato runtime)
  ingestActivityEvents(input: [ActivityMinuteInput!]!, idempotencyKey: ID, userId: ID): IngestActivityResult!
}

type MealEntry { id: ID! name: String! quantityG: Int! timestamp: DateTime! userId: ID! }
type DailySummary {
  date: Date!
  userId: ID!
  meals: Int!
  calories: Int!
  protein: Float
  carbs: Float
  fat: Float
  fiber: Float
  sugar: Float
  sodium: Float
  activitySteps: Int!
  activityCaloriesOut: Float!
  activityEvents: Int!
  caloriesDeficit: Int!
  caloriesReplenishedPercent: Int!
}
type CacheStats { hits: Int! misses: Int! keys: Int! }

type IngestActivityResult { accepted: Int! duplicates: Int! rejected: [RejectedActivityEvent!]! idempotencyKeyUsed: ID }
type RejectedActivityEvent { index: Int! reason: String! }

input LogMealInput { name: String! quantityG: Int! timestamp: DateTime barcode: String userId: ID }
input ActivityMinuteInput { ts: DateTime! steps: Int caloriesOut: Float hrAvg: Float source: ActivitySource! }
enum ActivitySource { APPLE_HEALTH GOOGLE_FIT MANUAL }
```

Differenze principali vs draft:
- Nessun connection pattern per `mealEntries` (lista semplice + filtri base).
- `dailySummary` ora include anche bilancio energetico (deficit & percentuale reintegro) e metriche attività aggregate ma resta privo di target giornalieri / forecast.
- Assenti tutte le query recommendation / trend / energyBalance avanzata.
- Ingestion attività implementata solo come batch minute → no timeline query granulari.
- CRUD esteso (update/delete) pianificato ma non ancora attivo runtime (placeholder nello slice sopra indicato).
- Cache observability: `cacheStats` per monitoring diagnostico.
- Nutrient constants: centralizzati in `nutrients.py` per coerenza.

Le sezioni successive restano il target evolutivo.

## Query
```graphql
type Query {
  product(barcode: String!): Product
  mealEntries(range: TimeRangeInput!, mealType: MealType, after: String, limit: Int=50): MealEntriesConnection!
  dailySummary(date: Date!): DailyIntakeSummary
  currentIntakeProgress: DailyIntakeSummary
  activityTimeline(range: TimeRangeInput!, granularity: ActivityGranularity!): [ActivityPoint!]!
  energyBalance(range: TimeRangeInput!): [EnergyBalancePoint!]!
  mealTypeTrends(rangeDays: Int=7, mealType: MealType): [MealTypeTrend!]!
  mealQualityInsights(range: TimeRangeInput!): [MealQualityInsight!]!
  recommendations(limit: Int=20, after: String, trigger: RecommendationTrigger): RecommendationConnection!
}
```

## Mutations
```graphql
type Mutation {
  logMeal(input: LogMealInput!, idempotencyKey: ID!): LogMealResult!
  updateMeal(id: ID!, input: LogMealInput!): LogMealResult!
  deleteMeal(id: ID!): DeleteMealResult!
  ingestActivityEvents(input: [ActivityMinuteInput!]!, idempotencyKey: ID!): IngestActivityResult!
  acknowledgeRecommendation(id: ID!): Recommendation!
  refreshDailyForecast: DailyIntakeSummary!
}
```

## Subscriptions (B6+)
```graphql
type Subscription {
  mealAdded: MealEntry!
  activityMinuteTick: ActivityMinuteBatch!
  energyBalanceDelta: EnergyBalancePoint!
  recommendationIssued: Recommendation!
}
```

## Types (Estratto)
```graphql
type MealEntry { id: ID! occurredAt: DateTime! mealType: MealType! energyKcal: Float proteinG: Float carbG: Float sugarsG: Float fatG: Float fiberG: Float sodiumMg: Float completenessScore: Int qualityScore: Int flags: [String!]! }

type DailyIntakeSummary { date: Date! energyKcalTotal: Float energyKcalTarget: Float energyKcalRemaining: Float predictedEveningConsumptionKcal: Float macroSplit: MacroSplit proteinGapG: Float sugarSpike: Boolean flags: [String!]! energyDeficitKcal: Float energyReplenishedPct: Int }

type MealTypeTrend { mealType: MealType! avgEnergyKcal: Float avgProteinG: Float avgCarbG: Float avgSugarsG: Float deltaSugarsPct: Float deltaProteinPct: Float deltaEnergyPct: Float sampleSize: Int }

type MealQualityInsight { flag: String! occurrenceCount: Int suggestion: String }

type Recommendation { id: ID! emittedAt: DateTime! category: RecommendationCategory! triggerType: RecommendationTrigger! message: String! }
```

## Inputs
```graphql
input TimeRangeInput { start: DateTime! end: DateTime! }
input LogMealInput { /* definito nel contratto ingestion */ }
input ActivityMinuteInput { ts: DateTime! steps: Int caloriesOut: Float hrAvg: Float source: ActivitySource! }
```

## Enums
```graphql
enum MealType { BREAKFAST LUNCH DINNER SNACK }
enum ActivityGranularity { MINUTE HOUR }
enum RecommendationTrigger { SUGAR_SPIKE LOW_PROTEIN_PROGRESS EVENING_CALORIE_BUDGET DEFICIT_ADHERENCE HIGH_CARB_LOW_ACTIVITY POST_ACTIVITY_LOW_PROTEIN }
```

## Connection Pattern (Esempio)
```graphql
type MealEntriesConnection { edges: [MealEntryEdge!]! pageInfo: PageInfo! }
type MealEntryEdge { node: MealEntry cursor: String! }
```

## Note Evolutive
- Le subscriptions vengono introdotte solo a B6 quando il bridge realtime è stabile.
- `qualityScore` rimane null fino a milestone B5.
- Il bilancio energetico (runtime: `caloriesDeficit` / `caloriesReplenishedPercent`) verrà evoluto in `DailyIntakeSummary` come `energyDeficitKcal` e `energyReplenishedPct` con possibili campi extra (target, forecast) in milestone C.

## Estensione Pianificata Attività (Draft Additivo)
```graphql
extend type Mutation {
  syncHealthTotals(input: HealthTotalsInput!, idempotencyKey: ID): SyncHealthTotalsResult!
}

input HealthTotalsInput {
  timestamp: DateTime!
  date: Date!
  steps: Int!
  caloriesOut: Float!
  hrAvgSession: Float
  userId: ID
}

type SyncHealthTotalsResult {
  accepted: Boolean!
  duplicate: Boolean!
  reset: Boolean!
  idempotencyKeyUsed: ID!
  idempotencyConflict: Boolean!
  delta: HealthTotalsDelta
}

type HealthTotalsDelta {
  id: ID!
  date: Date!
  timestamp: DateTime!
  stepsDelta: Int!
  caloriesOutDelta: Float!
  stepsTotal: Int!
  caloriesOutTotal: Float!
  hrAvgSession: Float
  userId: ID!
}

extend type Query {
  activityEntries(after: String, before: String, limit: Int=100, userId: ID): [ActivityEntry!]!
  syncEntries(date: Date!, after: String, limit: Int=200, userId: ID): [HealthTotalsDelta!]!
}
```

### Semantica
- Primo snapshot del giorno → delta = valori snapshot, `reset=false`.
- Reset (snapshot con contatori inferiori a precedente) → delta = snapshot, `reset=true`.
- Duplicate (snapshot identico) → `duplicate=true`, nessun nuovo delta.
- Conflitto idempotenza (stessa chiave ma payload differente) → `idempotencyConflict=true`, nessun delta applicato.
- `hrAvgSession` escluso dalla firma idempotenza.

### Impatto su `dailySummary`
| Campo | Prima | Dopo (post 0.5.0) |
|-------|-------|-------------------|
| activitySteps | Somma steps da minute events | Somma `stepsDelta` |
| activityCaloriesOut | Somma calories_out minute events | Somma `caloriesOutDelta` |
| activityEvents | Conteggio minute events | Invariato (solo diagnostico) |

I campi energetici (`caloriesDeficit`, `caloriesReplenishedPercent`) continueranno a usare i totali aggiornati.

### Edge Cases
| Scenario | Effetto |
|----------|---------|
| Nessun snapshot inviato nel giorno | Totali = 0 | 
| Solo snapshot identici ripetuti | Un solo delta (primo), duplication nei successivi |
| Reset dopo mezzanotte mancato (ritardo invio) | Primo snapshot ricevuto vale come reset giorno corrente |

### Migrazione Client
I client devono inviare periodicamente snapshot (polling o push aggregator OS). In assenza di snapshot i totali resteranno 0 → suggerito rollout con feature flag server (facoltativo per MVP interno).
