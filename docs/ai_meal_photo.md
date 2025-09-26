# AI Meal Photo Analysis – Fase 0 Stub

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
