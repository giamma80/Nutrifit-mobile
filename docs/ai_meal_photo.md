# AI Meal Photo – Evoluzione, Flusso Two‑Step & Calorie

Documenti correlati: 
- [Pipeline AI Food Recognition](ai_food_pipeline_README.md)
- [Prompt GPT-4V Draft](ai_food_recognition_prompt.md)
- [Error Taxonomy](ai_meal_photo_errors.md)
- [Metriche & Fallback](../backend/docs/ai_meal_photo_metrics.md)

## Obiettivo
Ridurre l'attrito nella registrazione dei pasti offrendo un flusso rapido foto → suggerimenti → conferma, partendo da uno stub deterministico (Fase 0) e introducendo gradualmente euristiche, GPT‑4V simulato e futura inference remota.

## Sommario
1. Stato Attuale sintetico
2. Flusso Two‑Step (Analyze → Confirm)
3. Idempotenza
4. Adapter Layer & Selezione
5. Calorie: modello e aggregazione
6. Sequence Diagram (analysis) + Sequence Calorie
7. Errori & Fallback
8. Acceptance Criteria
9. Roadmap & Migrazioni
10. Cross‑link

---
## 1. Stato Attuale (Fase 1 – 2025-10)
| Aspetto | Stato | Note |
|---------|-------|------|
| Adapter attivo | GPT‑4V (source=gpt4v) | Chiamata reale o simulata; fallback chain non ancora implementata |
| Adapter alternativi | stub (test), heuristic (PLANNED) | Se GPT non configurato si usa stub diretto |
| Idempotenza analyze | Attiva | Chiave esplicita o auto sha256 trunc user|photo refs (idempotencyKeyUsed) |
| Conferma | Idempotente per analysisId | Nessun duplicato createdMeals |
| Calorie item | Calcolate server | Somma coerente totalCalories |
| Error handling | failureReason + analysisErrors[] | failureReason solo se status=FAILED |
| Metriche | Opzionali (no-op fallback) | time_analysis + record_error/fallback (fallback non usato) |
| Error taxonomy | Definita (vedi tabella) | RATE_LIMITED, INTERNAL_ERROR inclusi |
| Status supportati | COMPLETED / FAILED | PENDING riservato futuro async |

---
## 2. Flusso Two‑Step
Vedi anche documento metriche per dettagli di osservabilità.

Step:
1. `analyzeMealPhoto` genera analisi COMPLETED (sempre today) con items proposti.
2. UI mostra items, utente seleziona subset.
3. `confirmMealPhoto` crea `MealEntry` (o riusa se già confermato).

Motivazioni divisione: UX iterativa, future streaming, prevenzione side‑effects se inference lenta/fallisce.

---
## 3. Idempotenza
`analyzeMealPhoto`:
- Usa chiave esplicita oppure genera `auto-<sha256(user|photoId|photoUrl)[:16]>`.
- Ritorno cached non rigenera metriche né tocca adapter.
`confirmMealPhoto`:
- Idempotente per `(analysisId, acceptedIndexes)` → nessuna duplicazione MealEntry.

Migrazione futura: feature flag `AI_IDEMP_HASH_ENABLED` per sostituire progressivamente chiave completa con `photoHash` dedicato.

---
## 4. Adapter Layer
File chiave: `backend/inference/adapter.py`.

Implementazioni:
- GPT‑4V Adapter (attivo): prompt + vision call + parse JSON;
  - In caso di parse/vision error oggi l'analisi può risultare FAILED (nessuna catena multi‑fallback ancora costruita).
- Stub Adapter: risposta deterministica per test/dev.
- Heuristic Adapter (PLANNED): regole quantitative + detection acqua.
- Remote Model Adapter (PLANNED): modello proprietario / API esterna.

Selezione (priorità attuale): `AI_MEAL_PHOTO_MODE` (gpt4v|stub) > fallback stub.
Logica futura: gpt4v → model → heuristic → stub.

Instrumentation: `time_analysis()` (latency), `record_error(code, source)`, `record_fallback(reason, source)` (quest'ultimo oggi non invocato).

---
## 5. Calorie: Modello e Aggregazione
Per ogni item: densità kcal/100g risolta con catena di priorità (DB → tabella statica → euristica categoria → fallback 100).
Formula: `calories = round(quantity_g * kcal_100g / 100, 1)` → clamp negativo a 0.
`totalCalories = sum(item.calories)` (o 0 se lista vuota).
Telemetria proposta aggiuntiva: `ai_meal_photo_density_fallback_total` + `ai_meal_photo_calories_compute_seconds`.

Outlier handling: quantità > 2000g clampata a 2000g (flag interno). Unità non‑gram convertite prima con peso medio.

---
## 6. Sequence Diagram (Analyze → Confirm)
```mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant G as GraphQL API
  participant R as Analysis Repo
  participant A as Adapter
  participant M as Meal Repo

  C->>G: analyzeMealPhoto(input)
  G->>R: create_or_get(key,input)
  alt Cache Hit
    R-->>G: existing analysis
  else New
    R->>A: analyze_async
    A-->>R: items (+calories prelim)
    R-->>G: analysis COMPLETED
  end
  G-->>C: MealPhotoAnalysis

  C->>G: confirmMealPhoto(analysisId, indexes)
  G->>R: load analysis
  alt Indici validi
    G->>M: create/find MealEntry
    M-->>G: createdMeals
    G-->>C: ConfirmMealPhotoResult
  else Invalid
    G-->>C: GraphQL error INVALID_INDEX
  end
```

### Sequence (Foto → Calorie → LogMeal Dettagliata)
```mermaid
sequenceDiagram
  autonumber
  participant C as Client
  participant API as GraphQL
  participant Repo as AnalysisRepo
  participant Sel as AdapterSelector
  participant A as Adapter
  participant Parse as Parser
  participant Nut as NutrientSvc
  participant Agg as CalorieAgg
  participant Meals as MealRepo

  C->>API: analyzeMealPhoto(photoId?, photoUrl?)
  API->>Repo: checkIdempotency
  alt Hit
    Repo-->>API: existing (items+calories)
  else Miss
    API->>Sel: get_active_adapter
    Sel-->>API: adapter
    API->>A: analyze_async
    A-->>Parse: raw predictions
    Parse->>Nut: resolve kcal/100g
    Nut-->>Parse: enriched items
    Parse->>Agg: normalized items
    Agg-->>API: items + totalCalories
    API->>Repo: persist
    Repo-->>API: analysisId
  end
  API-->>C: analysis payload
  C->>API: confirmMealPhoto(analysisId, indices)
  API->>Repo: load
  API->>Meals: create MealEntries
  Meals-->>API: createdMeals
  API-->>C: result
```

---
## 7. Errori & Fallback
L'implementazione corrente distingue:
* `analysisErrors[]`: lista (WARNING o ERROR non terminali)
* `failureReason`: singolo codice terminale → `status=FAILED` (items ignorati lato conferma)

Fallback chain multi‑adapter NON ancora implementata: un errore terminale oggi porta direttamente a FAILED (nessun downgrade automatico a stub in runtime produzione – previsto).

### Tabella Codici Errori (MealPhotoAnalysisErrorCode)
| Codice | Categoria | Terminale | Descrizione Sintetica |
|--------|-----------|----------|-----------------------|
| INVALID_IMAGE | INPUT | Sì | Immagine non valida / corrotta |
| UNSUPPORTED_FORMAT | INPUT | Sì | Formato non supportato |
| IMAGE_TOO_LARGE | INPUT | Sì | Dimensioni oltre limite consentito |
| BARCODE_DETECTION_FAILED | DETECTION | No | Impossibile estrarre barcode (warning) |
| PARSE_EMPTY | PARSE | Sì | Nessun JSON / struttura vuota dal modello |
| PORTION_INFERENCE_FAILED | PORTION | No | Stima quantità fallita (usa default) |
| RATE_LIMITED | PLATFORM | Sì | Rate limit provider vision raggiunto |
| INTERNAL_ERROR | SYSTEM | Sì | Errore generico non classificato |

Severity (non mostrata nella tabella): `ERROR` per terminali, `WARNING` per non terminali.

### Metriche correlate
| Evento | Metrica | Note |
|--------|---------|------|
| Analisi riuscita | requests_total + latency | status=completed |
| Errore terminale | requests_total(status=failed) + errors_total{code} | failureReason presente |
| Fallback (futuro) | fallback_total{reason} | Non ancora attivo |

### Campi diagnostici payload
| Campo | Tipo | Popolamento |
|-------|------|-------------|
| source | String! | Adapter usato (gpt4v, stub) |
| analysisErrors | [MealPhotoAnalysisError!]! | Warnings e errori non terminali |
| failureReason | MealPhotoAnalysisErrorCode | Solo se status=FAILED |
| idempotencyKeyUsed | String | Se analisi servita da cache idempotente |

---
## 8. Acceptance Criteria (aggiornati)
1. Idempotenza: analisi ripetuta con stessa chiave non reinvoca adapter.
2. Conferma: nessun duplicato MealEntry per stesso `(analysisId, indexes)`.
3. Nutrizione: ogni item (se presente) ha `calories >= 0`; `totalCalories` coerente.
4. Error Handling: errori terminali impostano `failureReason` e `status=FAILED`.
5. Warnings: errori non terminali finiscono in `analysisErrors[]` senza interrompere UX.
6. Metriche (se modulo presente): latency + requests + errors; nessun crash se assente (no-op).
7. `source` aderisce all'adapter scelto.
8. Parse error (PARSE_EMPTY) non genera eccezione non gestita (risposta coerente FAILED). 
9. IdempotencyKeyUsed presente quando cache reused.

---
## 9. Roadmap & Migrazioni
| Step | Descrizione | Stato |
|------|-------------|-------|
| Adapter abstraction | Protocol + stub | DONE |
| GPT‑4V adapter | Vision + parse | DONE |
| Calorie base | Densità + aggregation | DONE |
| Error taxonomy estesa | Codici + severity | DONE |
| Heuristic adapter | Regole locali quantità/acqua | PLANNED |
| Fallback chain multi‑adapter | gpt4v→model→heuristic→stub | PLANNED |
| Hash idempotenza dedicato | Flag + migrazione | PLANNED |
| Remote model adapter | Chiamata modello proprietario | PLANNED |
| Circuit breaker | Protezione error burst provider | PLANNED |
| Portion refinement | Stima porzioni avanzata | PLANNED |
| Nutrient enrichment avanzato | Macro + micro nutrienti | PLANNED |

Migrazione hash: introdurre `photoHash` osservabile → flag → switch definitivo → rimozione chiave legacy.

---
## 10. Cross‑link
- Metriche: `backend/docs/ai_meal_photo_metrics.md`
- Prompt & pipeline: `ai_food_recognition_prompt.md`, `ai_food_pipeline_README.md`
- Errori dettagliati: `ai_meal_photo_errors.md`
- Contratto ingestione: `data_ingestion_contract.md`

---
## Changelog
- v3: Aggiornamento per adapter GPT‑4V attivo, tabella errori completa, criteri aggiornati (ott 2025)
- v2: Unificazione doc evoluzione + flusso two‑step + calorie (ott 2025)
- v1: Documento iniziale evoluzione (sett 2025)
