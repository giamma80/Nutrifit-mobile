# Data Ingestion Contract – Meal & Activity (Stato Runtime v0.4.x)

Versione documento: 0.2
Ultimo aggiornamento: 2025-09-27

Questo documento riflette lo STATO IMPLEMENTATO nel backend attuale (in‑memory persistence) e distingue chiaramente ciò che è già runtime da ciò che è pianificato.

## 1. Obiettivi

| Obiettivo | Stato | Note |
|-----------|-------|------|
| Idempotenza meal log | ✅ Implementata (fallback key) | Chiave derivata se non fornita esplicitamente |
| Snapshot nutrienti immutabile | ✅ | Campo `nutrientSnapshotJson` opzionale |
| CRUD pasti completo | ✅ | `logMeal`, `updateMeal`, `deleteMeal` |
| Idempotenza activity minute | ✅ | Hash batch deterministico |
| Health totals snapshot (fonte primaria) | ✅ | `syncHealthTotals` produce delta consumati da `dailySummary` |
| Raccomandazioni inline nel log | ❌ | Pianificato, engine non attivo |

## 2. Mutations Runtime (Estratto SDL Attuale)

```graphql
input LogMealInput {
  name: String!
  quantityG: Float!
  timestamp: String
  barcode: String
  idempotencyKey: String
  userId: String
}
input UpdateMealInput {
  id: String!
  name: String
  quantityG: Float
  timestamp: String
  barcode: String
  userId: String
}

type MealEntry {
  id: ID!
  userId: String!
  name: String!
  quantityG: Float!
  timestamp: String!
  barcode: String
  idempotencyKey: String
  nutrientSnapshotJson: String
  calories: Int
  protein: Float
  carbs: Float
  fat: Float
  fiber: Float
  sugar: Float
  sodium: Float
}

type Mutation {
  logMeal(input: LogMealInput!): MealEntry!
  updateMeal(input: UpdateMealInput!): MealEntry!
  deleteMeal(id: String!): Boolean!
  ingestActivityEvents(input: [ActivityMinuteInput!]!, idempotencyKey: String, userId: String): IngestActivityResult!
  syncHealthTotals(input: HealthTotalsInput!, idempotencyKey: String, userId: String): SyncHealthTotalsResult!
}
```

## 3. Idempotenza Meal Logging

Fallback key (se `idempotencyKey` non passata):
```
lower(name) | round(quantityG,3) | (timestamp se fornito) | barcode | userId
```
Caratteristiche:
* Se il client NON fornisce timestamp → non entra nella chiave → due log identici senza timestamp sono deduplicati.
* Se il client fornisce un timestamp diverso → produce chiavi distinte (scelta intenzionale per consentire log retroattivi).
* Il campo `idempotencyKey` risultante viene restituito nel `MealEntry` per correlare replay.

Conflitto: se viene passata una chiave esplicita già usata con payload diverso → il backend (attuale implementazione stub) accetterà la prima e ignorerà successivi log (future: response con flag conflitto).

## 4. nutrientSnapshotJson

Popolato quando disponibile un prodotto barcode normalizzato (OpenFoodFacts adapter in cache). Struttura attuale (esempio):
```jsonc
{
  "calories": 180,
  "protein": 6.4,
  "carbs": 22.5,
  "fat": 5.1,
  "fiber": 3.2,
  "sugar": 12.0,
  "sodium": 150
}
```
Regole:
1. Scala per `quantityG` rispetto a 100g origine.
2. Immutabile dopo il log (future enrichment non muta lo snapshot originale; potrà generare record supplementari o campi derivati).
3. Chiavi ordinate (serializzazione deterministica) per consentire confronti test.
4. Se prodotto non trovato → `null` (potrà essere popolato da pipeline AI futura).

## 5. Update & Delete

`updateMeal` ricalcola lo snapshot nutrienti se cambia `barcode` o `quantityG`. Campi opzionali non passati rimangono invariati. `deleteMeal` restituisce Boolean (`true` se la entry esisteva ed è stata rimossa). Non esiste oggi ricalcolo retroattivo del `dailySummary` memorizzato (summary calcolato on-demand), quindi il consumo successivo rifletterà lo stato aggiornato.

## 6. Activity Ingestion (Diagnostico)

`ingestActivityEvents` accetta minute events per scopi di debug / timeline; NON alimenta più i totali di `dailySummary` (sostituiti dal flusso Health Totals Sync). Idempotenza: firma batch deterministica su eventi normalizzati (timestamp ridotto al minuto) → replay ritorna stesso risultato senza reinserimento. Eventi confliggenti (stesso minuto dati diversi) scartati con reason (es. `CONFLICT_DIFFERENT_DATA`).

## 7. Health Totals Sync (Autoritativo)

La mutation `syncHealthTotals` converte snapshot cumulativi (steps/caloriesOut/hrAvgSession opzionale) in delta robusti con gestione `duplicate`, `reset`, `idempotencyConflict`. I delta alimentano `dailySummary.activitySteps` e `dailySummary.activityCaloriesOut`. Dettagli completi: vedere `health_totals_sync.md`.

## 8. Errori & Validazioni (Stato Attuale)

Implementazione corrente esegue validazioni basilari:
| Categoria | Regola | Stato |
|-----------|--------|-------|
| quantityG | > 0 | Enforced |
| barcode | Lunghezza ragionevole (basic) | Parziale |
| timestamp | ISO8601 se presente | Enforced superficiale |
| idempotenza | Chiave generata / rispettata | Enforced |

Roadmap (non ancora): controlli range macro, error taxonomy standardizzata, rate limiting.

## 9. Estensioni Pianificate (Non Runtime)

| Feature | Tipo | Note |
|---------|------|------|
| meal batching | additive | Input lista di LogMealInput |> ritorno lista entries |
| micronutrients avanzati | additive | Aggiunta altri campi nello snapshot |
| recommendation embedding | additive | Campo recommendations in risposta logMeal |
| conflict flag responses | additive | Response arricchita con `idempotencyConflict` per chiave riusata |

## 10. Testing Contractuale (Guidelines)

Minimo set da mantenere:
1. Log idempotente senza timestamp (2 richieste → 1 record).
2. Log con timestamp diversi → 2 record.
3. Update modifica quantity → calorie cambiano coerentemente (scaling lineare).
4. Delete rimuove entry e seconda delete ritorna `False` (o rimane senza effetto) – comportamento attuale Boolean semplice.
5. syncHealthTotals duplicate → nessun nuovo delta.
6. syncHealthTotals reset detection → delta = snapshot.

## 11. Open Questions

* Introdurre subito conflict flag su idempotenza esplicita? (basso costo)
* Normalizzazione nome meal per dedup più aggressivo (rimuovere stop‑words)?
* Retention idempotency keys (attualmente in-memory – definire TTL persistente in futuro DB).

---
Feedback: creare issue con prefisso `contract:` per proporre estensioni o segnalare edge case non coperti.
