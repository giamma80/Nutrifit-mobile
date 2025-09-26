# Data Ingestion Contract – logMeal & Related Events

Versione: 0.1 (Draft)
Ultimo aggiornamento: 2025-09-20

## 1. Scopo

Definire il contratto stabile per l’ingestione di pasti nel backend Nutrifit, garantendo:

- Idempotenza per richieste ripetute (retry client / condizioni offline)
- Snapshot nutrienti immutabile al momento del log
- Validazioni coerenti tra canali (manuale, barcode, AI)
- Estensibilità futura (nuovi campi, enrichment AI, portion heuristics) senza breaking changes

## 2. Mutation Principale

### 2.1 Create: logMeal

```graphql
mutation logMeal($input: LogMealInput!, $idempotencyKey: ID!) {
  logMeal(input: $input, idempotencyKey: $idempotencyKey) {
    mealEntryId
    createdAt
    snapshot {
      energyKcal
      proteinG
      carbsG
      fatG
      ... future nutrient fields
    }
  }
}
```

### 2.2 Update: updateMeal

```graphql
mutation updateMeal($id: ID!, $input: LogMealInput!) {
  updateMeal(id: $id, input: $input) {
    mealEntryId
    updatedAt
    snapshot {
      energyKcal
      proteinG
      carbsG
      fatG
      fiberG
      sugarG
      sodiumMg
    }
  }
}
```

### 2.3 Delete: deleteMeal

```graphql
mutation deleteMeal($id: ID!) {
  deleteMeal(id: $id) {
    success
    deletedAt
    recalculatedStats {
      energyKcal
      fatG
      sugarG
      sodiumMg
    }
  }
}
```

### 2.1 Input Structure (Logical)

| Campo | Tipo | Obbligatorio | Descrizione |
|-------|------|--------------|-------------|
| `foodRef` | union (`ProductBarcodeRef` / `ManualEntryRef` / `AIInferenceRef`) | sì | Origine del cibo loggato |
| `quantity` | Float > 0 | sì | Quantità numerica |
| `unit` | Enum (`g`,`ml`,`piece`,`serving`) | sì | Unità di misura |
| `mealType` | Enum (`breakfast`,`lunch`,`dinner`,`snack`) | sì | Categoria pasto |
| `userNote` | String(<=300) | no | Nota libera opzionale |
| `portionOverride` | Float >0 | no | Override porzione se diversa da standard |

`foodRef` varianti:

```graphql
type ProductBarcodeRef { barcode: String! }
type ManualEntryRef { name: String!, nutrients: ManualNutrientsInput! }
type AIInferenceRef { inferenceId: ID!, itemId: ID! }
```
`ManualNutrientsInput` campi minimi: `energyKcal`, `proteinG`, `carbsG`, `fatG` (opzionali micronutrienti estensibili).

### 2.2 Idempotency Key

- Campo header o variabile GraphQL `idempotencyKey` (UUID v4 consigliato)
- Finestra retention chiavi: 24h (configurabile)
- Se richiesta identica (stesso hash normalizzato) → restituisce stessa risposta (HTTP 200, no duplicato)
- Se conflitto (chiave riusata con payload differente) → errore `IdempotencyConflict`

Hash normalizzato include: user_id, foodRef (serializzato), quantity, unit, mealType, portionOverride (se presente).

## 3. Snapshot Nutrienti

Al log, il backend produce `nutrient_snapshot_json` con almeno:

```json
{
  "schema_version": 1,
  "source": "OFF|MANUAL|AI",
  "source_ref": "barcode|manual|inference:<id>",
  "energy_kcal": 210.0,
  "protein_g": 12.5,
  "carbs_g": 18.0,
  "fat_g": 8.4,
  "raw": { /* payload originale ridotto */ }
}
```

Regole:

- Conversione kJ→kcal se necessario (fattore 0.239006)
- Se sale presente e sodio assente → `sodium_mg = salt_g * 400`
- Valori negativi o > range plausibile (es. protein > 150g per porzione standard) → rifiuto input

## 4. Validazioni

| Categoria | Regola | Azione |
|-----------|--------|--------|
| Quantità | `quantity > 0` e `<= 5000` | Errore `InvalidQuantity` |
| Unit | Enum valido | Errore `InvalidUnit` |
| Meal Type | Enum valido | Errore `InvalidMealType` |
| Barcode | Regex EAN13/8 | Errore `InvalidBarcode` |
| AI Ref | Inference esiste & `status=CONFIRMED_PENDING` | Errore `InvalidAIReference` |
| Macro | kcal derivabile se macro presenti | Autocalcolo se mancante |

## 5. Errori Standard (GraphQL Codes)

| Codice | Descrizione | HTTP | Operazioni |
|--------|-------------|------|------------|
| `IdempotencyConflict` | Chiave riusata con payload diverso | 409 | logMeal |
| `InvalidQuantity` | Quantità fuori range | 400 | logMeal, updateMeal |
| `InvalidBarcode` | Barcode non valido | 400 | logMeal, updateMeal |
| `ProductNotFound` | OFF non ritorna prodotto / mismatch | 404 | logMeal, updateMeal |
| `AIItemMismatch` | Item inference non appartiene a utente | 400 | logMeal, updateMeal |
| `MealNotFound` | ID pasto non esiste o non appartiene a utente | 404 | updateMeal, deleteMeal |
| `MealAlreadyDeleted` | Tentativo operazione su pasto già eliminato | 410 | updateMeal, deleteMeal |
| `RateLimited` | Superato rate limite mutation | 429 | Tutte |
| `ServerError` | Errore interno generico | 500 | Tutte |

## 6. Estensioni Future (Backward Compatible)

- Campo opzionale `micronutrients` nel snapshot.
- Aggiunta `mealContext` (es. preWorkout, postWorkout) come enum.
- Supporto multi-item batching (input lista) mantenendo mutazione singola attuale.

## 7. Eventi Derivati

Event Log (append-only) genererà eventi:

| Evento | Payload Principale |
|--------|--------------------|
| `meal_logged` | meal_entry_id, user_id, meal_type, energy_kcal |
| `daily_summary_recomputed` | user_id, date, deltas |

## 8. Rate Limiting (Indicativo)

| Azione | Limite | Finestra |
|--------|--------|----------|
| `logMeal` | 120 | 1h per utente |
| `logMeal` | 600 | 24h per utente |
| `updateMeal` | 60 | 1h per utente |
| `updateMeal` | 300 | 24h per utente |
| `deleteMeal` | 30 | 1h per utente |
| `deleteMeal` | 150 | 24h per utente |

Superamento produce errore `RateLimited` con header `Retry-After`.

## 9. Test Contractuali

### 9.1 Test CRUD Operations
- **Create (logMeal)**: Test idempotenza: ripetere stessa mutation 2 volte → una sola row
- **Create Conflict**: Test conflitto: stessa chiave con macro diverse → errore
- **Update**: Test update di pasto esistente → snapshot nutrients aggiornato correttamente
- **Update Not Found**: Test update di pasto inesistente → errore `MealNotFound`
- **Delete**: Test delete di pasto esistente → success=true e stats ricalcolate
- **Delete Not Found**: Test delete di pasto inesistente → errore `MealNotFound`
- **Delete Idempotence**: Test delete ripetuto → errore `MealAlreadyDeleted`

### 9.2 Schema Validation
- Snapshot SDL GraphQL aggiornato per ogni aggiunta di campo
- Retrocompatibilità: campi aggiunti sempre opzionali
- Response structure: updateMeal e deleteMeal mantengono struttura coerente

## 10. Open Questions

- Batching multi-pasto: vale la pena per ridurre roundtrip o complessità > beneficio iniziale?
- Micronutrienti dinamici: introdurre dizionario centralizzato validi vs free-form JSON?

---

## 11. Activity Ingestion (Nuova)

Mutation (batch minute events):

```graphql
mutation ingestActivityEvents($input: [ActivityMinuteInput!]!, $idempotencyKey: ID!) {
  ingestActivityEvents(input: $input, idempotencyKey: $idempotencyKey) {
    accepted
    duplicates
    rejected { index reason }
  }
}
```

`ActivityMinuteInput`:
| Campo | Tipo | Note |
|-------|------|------|
| ts | DateTime (min precision) | Normalizzato a minuto UTC |
| steps | Int >=0 | opzionale, default 0 |
| caloriesOut | Float >=0 | opzionale |
| hrAvg | Float >=0 | opzionale |
| source | Enum (`APPLE_HEALTH`,`GOOGLE_FIT`,`MANUAL`) | required |

Idempotenza: hash batch = sha256(sorted(ts,user_id,steps,caloriesOut,hrAvg)). Tentativo ripetuto con stessa chiave → risposta cached.

Conflitto: stessa chiave con payload diverso → `IdempotencyConflict`.

## 12. logMeal Response Estesa

Estensione (additiva) per includere raccomandazioni appena emesse:

```graphql
type LogMealResult {
  mealEntryId: ID!
  createdAt: DateTime!
  snapshot: MealSnapshot!
  recommendations: [Recommendation!]!
}
```

Se nessuna generata → lista vuota.

## 13. Recommendation Object (Estratto)

```graphql
type Recommendation {
  id: ID!
  emittedAt: DateTime!
  category: RecommendationCategory!
  triggerType: RecommendationTrigger!
  message: String!
}
```

Codici trigger definiti in `docs/recommendation_engine.md`.

Feedback: aprire issue `contract:` con suggerimenti / edge case.
