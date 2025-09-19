# AI Food Recognition Pipeline

Questa README descrive il flusso tecnico end-to-end del riconoscimento alimenti basato su GPT-4V + OpenFoodFacts + dizionario interno.

## Obiettivi

- Time-to-value rapido senza modello custom iniziale.
- Grounding deterministico nutrienti (mai fidarsi di stime LLM dirette).
- Cost & Latency Control con early-exit (barcode-first) e caching profili.

## Flusso Sintetico

1. Upload immagine → ottieni `uploadId` (fuori scope qui).
2. Mutation `analyzeMealPhoto(uploadId)` → avvia pipeline.
3. Backend:
   - Estrae eventuale barcode (ZXing) → se trovato skip GPT.
   - Altrimenti pre-process (resize 1024, strip EXIF, optional blur volti).
   - Prompt GPT-4V (vedi `ai_food_recognition_prompt.md`).
   - Parsing JSON + normalizzazione label.
   - Matching (fuzzy + embeddings) contro:
     1. Dizionario interno (preferito)
     2. OpenFoodFacts (nome + synonyms)
     3. Fallback generico
   - Calcolo uncertainty band.
   - Costruzione `AIInferenceResult` con `items`.
4. Client mostra UI conferma (auto-fill se condizioni soddisfatte).
5. Mutation `confirmInference` con `selections` (uno o più item). Restituisce lista `MealEntry`.
6. Subscription `dailyNutritionUpdated` notifica delta nutrienti per aggiornare ring.

## Schema Esteso

Vedi `lib/graphql/schema_nutrition.graphql` (tipi: `AIInferenceItem`, `UncertaintyBand`, `InferenceSource`, `DailyNutritionDelta`).

## Matching Details

- Fuzzy ratio (es. token set) + embedding cosine (>=0.62 soglia safe).
- Normalizzazione heuristica: rimozione aggettivi marketing, plurali → singolare base.
- Caricamento dizionario custom (alimentazione utente) come primo livello.

## Confidence Composition

```text
final_conf = match_confidence * portion_confidence * source_weight
```

Policy auto-fill: final_conf ≥ 0.70 AND items ≤2 AND kcal_totali_stimati < 800.

## Caching

- Profili nutrienti OFF (chiave: product code) TTL 24h.
- LRU 256 voci, frequenza alimenti utente → pre-warm.

## Metriche Chiave

| Nome | Descrizione |
|------|-------------|
| ai_inference_latency_ms | end-to-end analyzeMealPhoto |
| ai_inference_low_confidence_ratio | % inferenze che richiedono editing |
| ai_portion_adjustment_ratio | % item con porzione rivista utente |
| ai_autofill_accept_rate | % auto-fill confermati senza modifica |

## Error Handling

| Caso | Azione |
|------|--------|
| Timeout GPT | fallback UI manuale immediato |
| JSON invalido | retry 1 prompt fallback |
| Zero items | UI stato empty |
| Confidenza bassa | richiesta selezione manuale |

## Evoluzione Futura

- Segmentazione multi-item on-device, bounding boxes.
- Distillazione modello per ridurre costo GPT.
- Depth-based volume per piatti.

## TODO

- [ ] Implementare embedding index (alimentazione utente + global foods)
- [ ] Logging structured tracing (traceId per pipeline)
- [ ] Rate limiting GPT per utente (abuso foto)

---
