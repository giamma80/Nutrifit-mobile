# AI Meal Photo Analysis – Fase 0 Stub

Documenti correlati: [Pipeline AI Food Recognition](ai_food_pipeline_README.md) · [Prompt GPT-4V Draft](ai_food_recognition_prompt.md) · [Error Taxonomy](ai_meal_photo_errors.md)

## Obiettivo
Ridurre l'attrito nella registrazione dei pasti offrendo un flusso rapido foto → suggerimenti → conferma, iniziando con uno stub deterministico (nessuna AI esterna) per validare UX, schema e idempotenza.

## Flusso Fase 0
1. Client acquisisce foto (non caricata realmente – `photoId` opzionale).
2. Mutation `analyzeMealPhoto` genera sempre due item statici:
   - Insalata mista (150g)
   - Petto di pollo (120g)
3. Utente seleziona item (uno o più) → `confirmMealPhoto` → crea `MealEntry`.
4. Idempotenza:
   - `analyzeMealPhoto`: chiave esplicita o auto da (user|photoId|photoUrl) → stesso `analysisId`.
   - `confirmMealPhoto`: idempotency interna tramite chiave meal `ai:<analysis_id>:<index>`.

## Schema (estratto)
```
mutation analyzeMealPhoto(input: AnalyzeMealPhotoInput!): MealPhotoAnalysis
mutation confirmMealPhoto(input: ConfirmMealPhotoInput!): ConfirmMealPhotoResult
```
Status possibili (future fasi): `PENDING|COMPLETED|FAILED` (ora solo COMPLETED).

## Repository Stub
File: `backend/repository/ai_meal_photo.py`
Memorizza in-memory:
* Analisi: `(user, analysis_id)` → record
* Idempotenza: `(user, idempotency_key)` → analysis_id
Predictions generate staticamente (estendibile a pipeline reale).

## Evoluzione Pianificata
| Fase | Descrizione | Output | Dipendenze |
|------|-------------|--------|-----------|
| 0 | Stub deterministico | 2 item statici | Nessuna |
| 1 | Heuristic / rule-based (es. parse testo utente) | Lista item dinamica limitata | Parser regole |
| 2 | Inference remoto (Vision API / GPT-4o / custom) | Items + nutrienti stimati | Adapter esterno, rate limit |
| 3 | Post-processing nutrizionale | Normalizzazione nutrienti + fonti dati | Mapping ingredienti, DB prodotti |
| 4 | Feedback loop / correzione utente | Retraining / ranking | Storage feedback |

## KPI Iniziali (Fase 0→1)
| KPI | Target Iniziale | Note |
|-----|-----------------|------|
| Adoption feature (utenti che provano almeno 1 foto) | >25% early adopters | Misurare su base giornaliera |
| Conversione foto → conferma (almeno 1 item) | >60% | Segnale utilità |
| Tempo medio conferma (s) | <10s | Proxy rapidità UX |
| Errori invalid index | <1% chiamate confirm | Indica problemi UI |

## Acceptance Criteria Fase 0
1. Mutation disponibili nello schema e additive (nessun breaking change).
2. Idempotenza `analyzeMealPhoto`: stessa chiave → stesso `analysisId`, stesse predictions.
3. Conferma ripetuta di stessi indici non crea duplicati pasti.
4. Invalid index restituisce errore `INVALID_INDEX`.
5. Test automatici coprono: analyze base, analyze idempotente, confirm (creazione 2 pasti), confirm idempotente, invalid index.
6. Nessun impatto sulle mutation esistenti (regressioni test esistenti = 0).

## Rischi & Mitigazioni
| Rischio | Impatto | Mitigazione |
|---------|---------|-------------|
| Aspettativa “vera AI” da parte utente | Delusione | Etichettare come beta / anticipare roadmap |
| Crescita rapida complessità prima di validare UX | Over-engineering | Iterare stub → heuristic → AI con metriche gating |
| Drift schema quando passeremo a PENDING asincrono | Client break | Aggiungere campi nuovi (es. `processingProgress`) in modo backward-compatible |
| Duplice creazione pasti in edge case race | Dati duplicati | Idempotency meal key già in place + lock futura persistenza |
| Costi inference futuri elevati | Margini | Budget cap + fallback heuristic |

## Next Steps (per Fase 1)
1. Aggiungere attributo opzionale `confidenceExplanation` agli item (additivo).
2. Introdurre un adapter base `inference_adapter.py` con interfaccia + stub corrente.
3. Implementare semplice normalizzazione nome → canonical form (lowercase, trimming, rimozione aggettivi). 
4. Logging strutturato per analyze/confirm (tempo, items, idempotency) → base per metriche.
5. Definire eventi analitici (analyze.request, analyze.cached, confirm.accepted, confirm.duplicateMeal).

## Metriche Raccolta (telemetry futura)
| Evento | Campi |
|--------|-------|
| analyze.request | userId, photoId|url hash, predictions_count |
| analyze.cached | userId, analysisId |
| confirm.accepted | userId, analysisId, accepted_count |
| confirm.duplicateMeal | userId, mealKey |
| confirm.error.INVALID_INDEX | userId, analysisId |

## Nota Persistenza
Quando si introdurrà Postgres:
* Tabella `meal_photo_analysis` (status, raw_json, created_at, idem_key)
* Tabella `meal_photo_prediction` (fk analysis, nutrienti opzionali)
* Migrazione semplice grazie a interfaccia repository già isolata.

---
Revision: Fase 0 (stub) – data iniziale merge.

## Analisi Costi & Rischi (Fasi 1→2)
Questa sezione dettaglia ipotesi economiche e tecniche per passare da stub a inference remota.

### Ipotesi Volume (mese 1 post lancio AI vera)
- Utenti attivi feature: 2.000
- Foto/giorno per utente attivo: 1.2 (media)
- Foto totali mese: ~72.000

### Modelli di Costo (esempi)
| Voce | Ipotesi | Costo unitario | Costo mensile stimato | Note |
|------|---------|----------------|-----------------------|------|
| Vision API (label + nutrition heuristic) | 72k chiamate | $0.0025 | ~$180 | Prezzo indicativo low-end |
| GPT multimodale (prompt breve) | 20% richieste escalate (14.4k) | $0.01 | ~$144 | Escalation solo casi Low Confidence |
| Storage immagini (media 250KB) | 72k * 0.25MB = 18GB | $0.02/GB | ~$0.36 | Se conserviamo 30 giorni |
| Telemetry / Logging | 72k eventi | $0.0001 | ~$7 | Se log strutturato esterno |
| Totale stimato |  |  | ~$331 | Margine ±30% |

### Sensibilità
- Se adozione raddoppia (4.000 utenti) ⇒ costo ~ +85% (economia di scala solo logging).
- Se confidenza bassa porta escalation 50% ⇒ GPT costo ~ $360 (+$216 delta).

### Rischi Economici
| Rischio | Trigger | Mitigazione | Soglia Action |
|---------|--------|-------------|---------------|
| Escalation eccessiva | Confidence < threshold spesso | Dynamic threshold + caching embed | Escalation >35% per 3 giorni |
| Chiamate duplicate | Retry client | Idempotency per photo hash | Dup call rate >3% |
| Foto non confermate (spreco) | UX bassa | Misurare conversione foto→confirm | Conversione <40% |

### Rischi Tecnici Addizionali
| Rischio | Impatto | Mitigazione Tecnica |
|---------|---------|--------------------|
| Latenza >3s media | Drop utilizzo | Pipeline parallela + prefetch nutrienti |
| Formato output modello instabile | Error parsing | JSON schema enforced + validatore |
| Saturazione rate limit provider | Fail hard UX | Circuit breaker + fallback heuristic |
| Drift reputazione calorie | Fiducia bassa | Ricalibrazione con dataset validato periodico |

## Piano Rollout Incrementale
| Fase | Ambiente | Gate Metriche | % Utenti | Azioni se Fallisce |
|------|----------|---------------|----------|--------------------|
| 0 (Stub) | Prod | Test tutti verdi | 100% | Rollback rapido (feature innocua) |
| 1 (Heuristic) | Prod (feature flag) | Conversione foto→confirm ≥55%, Errori index <1% | 10% → 50% | Se <55%: iterazione regole, copy UX |
| 2 (Remote Inference) | Prod (flag separato) | Latenza p95 <2500ms, Escalation <35% | 5% → 30% | Se p95 >2500ms: caching / batching |
| 3 (Post-processing nutrizionale) | Prod | Accuratezza stima kcal ±25% vs manuale | Subset 10% | Se >25% errore: retrain mapping |
| 4 (Feedback loop) | Prod | Retention feature +5pp | Graduale | Se neutra: rivalutare costo loop |

### Gating Operativo
- Promozione Fase 1 → 2 solo dopo 7 giorni di metriche stabili.
- Ogni aumento percentuale utenti avviene in step (10pp) con verifica 24h.

## Acceptance Criteria Estesi (Fasi Future)
### Fase 1 (Heuristic)
1. Items generati dinamicamente da regole (≥3 classi alimenti).
2. Campi opzionali: `confidence` variabile, `confidenceExplanation` presente se confidence <0.7.
3. Degradazione: se parsing fallisce ritorna fallback 2 item statici + flag `fallbackUsed`.
4. Metriche loggate: analyze.request, analyze.cached, confirm.accepted con latenza.

### Fase 2 (Remote Inference)
1. Adapter con timeout configurabile (default 2.5s) e fallback heuristico.
2. Circuit breaker (apre dopo 5 errori consecutivi per 60s).
3. Normalizzazione nutrienti: calorie stimate sempre presenti, macro se fornite.
4. Logging differenzia source: `source: heuristic|model|fallback`.
5. Tests coprono: timeout fallback, breaker open, caching per stesso hash foto.

## Raccomandazioni Operative Immediate
Priorità (prossimi 2-3 giorni):
1. Instrumentazione: aggiungere logging strutturato analyze/confirm (user, analysisId, duration, fallbackUsed).
2. Definire interfaccia `InferenceAdapter` + implementazione `StubAdapter` (attuale) per ridurre refactor futuro.
3. Aggiungere hashing foto (placeholder funzione) per preparare dedup + caching.
4. Preparare feature flag semplice environment variable per Fase 1 (enable heuristic).
5. Dashboard metriche basilare (esportare in log → successivo ingest su console / BigQuery). 

### Checklist Tecnica
- [ ] Creare modulo `inference/adapter.py` con Protocol.
- [ ] Spostare logica static predictions nell'adapter.
- [ ] Aggiungere wrapper timing.
- [ ] Introdurre funzione `hash_photo_reference(photoId, photoUrl)`.
- [ ] Estendere schema con campo `source` (additivo).

## Aggiornamento Revision
Revision: Fase 0 (stub) – aggiornato con piano strategico (data: 2025-09-27).
