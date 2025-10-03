# AI Food Recognition Pipeline (Fase 2 Attiva)

**Stato Attuale (Ottobre 2025)**: Pipeline completa GPT-4V + Nutrient Enrichment attiva. Le mutation `analyzeMealPhoto` e `confirmMealPhoto` eseguono inference reale con arricchimento automatico macronutrienti e fallback robusto.

Obiettivo Fase 0: definire boundary chiari e semantica campi (`source=STUB`) per permettere sviluppo parallelo mobile mentre la pipeline AI reale è in design.

## Obiettivi (Generali)

- Time-to-value rapido senza modello custom iniziale.
- Grounding deterministico nutrienti (mai fidarsi di stime LLM dirette) via adapter OFF centralizzato.
- Cost & Latency Control con early-exit (barcode-first) e caching profili centralizzata lato server.

## Flusso Sintetico (Oggi vs Futuro)

| Step | Fase 0 (Runtime) | Fase 1 (Baseline Vision) | Fase 2 (Enrichment & Matching) |
|------|------------------|--------------------------|--------------------------------|
| 1 | Upload immagine (placeholder) | Upload + basic validation | Upload + on-device preprocessing |
| 2 | `analyzeMealPhoto` restituisce lista stub (1–2 item fissi) | Barcode detect + GPT-4V prompt | Vision model custom + fallback GPT |
| 3 | Items hanno campi minimi (name, quantityGuess=null, confidence=1.0, source=STUB) | JSON GPT normalizzato | Fuzzy + embedding matching OFF + dizionario |
| 4 | **✅ Nutrient enrichment heuristic + default** | **✅ Macronutrienti automatici (protein, carbs, fat, fiber)** | Portion refinement + volume heuristics |
| 5 | `confirmMealPhoto` crea MealEntry con `name` & `quantityG` passata | **✅ idem + macronutrienti arricchiti** | idem + nutrient inference fallback |
| 6 | — | Metriche base | Metriche avanzate + quality scoring |

Subscription non ancora implementata (roadmap B6).

## **✅ Phase 2 Architecture (Attiva - Ottobre 2025)**

### Nutrient Enrichment Pipeline

```
GPT-4V Response → ParsedItem[] → NutrientEnrichmentService → EnrichmentResult[] → MealPhotoItemPredictionRecord[]
```

**Strategia Fallback**:
1. **Heuristic Lookup**: Dizionario statico `HEURISTIC_NUTRIENTS` per alimenti comuni
2. **Default Values**: Valori nutrizionali generici se item non trovato

**Dati Integrati**:
- `pollo`: 25.0g protein, 0.0g carbs, 4.0g fat, 0.0g fiber (per 100g)
- `riso`: 3.0g protein, 78.0g carbs, 0.5g fat, 1.0g fiber (per 100g)  
- `verdure`: 2.0g protein, 6.0g carbs, 0.3g fat, 3.0g fiber (per 100g)
- **Default**: 2.0g protein, 10.0g carbs, 1.0g fat, 1.0g fiber (per 100g)

**Metriche Attive**:
- `ai_meal_photo_enrichment_success_total`: Counter batch enrichment
- `ai_meal_photo_enrichment_latency_ms`: Histogram tempo processing
- `ai_meal_photo_macro_fill_ratio`: Coverage campi popolati

**Test Coverage**: 
- Unit tests: `test_nutrient_enrichment.py` (7 test cases)
- Integration tests: `test_gpt4v_adapter_enrichment.py` (end-to-end)

Riferimenti correlati: [AI Meal Photo Analysis](ai_meal_photo.md) · [Prompt Draft GPT-4V](ai_food_recognition_prompt.md) · [Error Taxonomy](ai_meal_photo_errors.md)

## Schema (Stub Attuale – Estratto)

```graphql
type AnalyzedMealItem {
   label: String!
   confidence: Float!
   source: String!   # STUB per fase 0
}

type AnalyzeMealPhotoResult {
   id: ID!
   items: [AnalyzedMealItem!]!
   source: String!   # STUB
}

type Mutation {
   analyzeMealPhoto(uploadId: String!): AnalyzeMealPhotoResult!
   confirmMealPhoto(id: ID!, selection: Int!, quantityG: Float!): MealEntry!
}
```

## Differenze vs Design Finale

| Aspetto | Stub | Futuro |
|---------|------|--------|
| Confidence | Fisso 1.0 | Calcolo composito (vision * matching * portion) |
| Fonte | 'STUB' | Enum (`BARCODE_DETECT`,`VISION_MODEL`,`LLM_FALLBACK`) |
| Matching | Nessuno | Fuzzy + embedding + ranking |
| Porzione | Non stimata | Heuristics + ML volume |
| Nutrienti | Non arricchiti | Snapshot via OFF / inference AI | 
| Multi-item reale | Limitato (placeholder) | Supporto 1..5 item con ranking |

## Roadmap Confidence (Indicativa)
`final_conf = vision_conf * match_conf * portion_conf * source_weight` (clamp 0..1) — implementazione Fase 2.

## Caching

- Profili nutrienti OFF (chiave: product code) TTL 24h (fase B1/B4: in-memory + SWR; eventuale Redis se eviction > soglia).
- LRU 256 voci (target iniziale) con metriche hit/miss → decisione scaling.

## Metriche (Previste)

| Nome | Descrizione |
|------|-------------|
| ai_inference_latency_ms | end-to-end analyzeMealPhoto |
| ai_inference_low_confidence_ratio | % inferenze che richiedono editing |
| ai_portion_adjustment_ratio | % item con porzione rivista utente |
| ai_autofill_accept_rate | % auto-fill confermati senza modifica |

## Error Handling (Fase 0)
Tutti i percorsi stub sono deterministici; principali errori futuri saranno introdotti in Fase 1 (timeout model, parsing JSON). Manteniamo già un punto di estensione per differenziare `source`.

| Caso | Azione |
|------|--------|
| Timeout GPT | fallback UI manuale immediato |
| JSON invalido | retry 1 prompt fallback |
| Zero items | UI stato empty |
| Confidenza bassa | richiesta selezione manuale |

## Evoluzione Futura

- Segmentazione multi-item on-device, bounding boxes (post federazione eventuale).
- Distillazione modello per ridurre costo GPT.
- Depth-based volume per piatti.
- Enrichment Robotoff (fronte etichette/barcode) prima di GPT se barcode mancante.
 - Source Chain Tracking: ogni inferenza confermata arricchisce `meal_entry.source_chain` (lista step: barcode→OFF normalization→AI match→portion adjust) per audit.
 - Quality Score Late Update: se enrichment tardivo modifica macro >5% ricalcolo `quality_score` (non mutiamo snapshot nutrienti originale, append step al source_chain).

## TODO (Aggiornato)

- [ ] Integrare barcode detect reale (ZXing) prima di GPT
- [ ] Prompt GPT-4V operativo + parser robusto
- [ ] Embedding index (utente + global foods)
- [ ] Portion heuristics (stima baseline) + feedback loop
- [ ] Structured tracing (traceId) end-to-end
- [ ] Rate limiting foto per utente
- [ ] Enum source definitivo e rimozione stringa libera
- [ ] Subscription aggiornamenti nutrizionali post conferma

---
