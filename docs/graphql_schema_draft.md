# GraphQL Schema Draft – Nutrition, Activity & Recommendations

Versione: 0.1 (Draft evolutivo)
Ultimo aggiornamento: 2025-09-20

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

type DailyIntakeSummary { date: Date! energyKcalTotal: Float energyKcalTarget: Float energyKcalRemaining: Float predictedEveningConsumptionKcal: Float macroSplit: MacroSplit proteinGapG: Float sugarSpike: Boolean flags: [String!]! }

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
