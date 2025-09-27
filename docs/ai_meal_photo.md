# AI Meal Photo Analysis – Fase 0→1 Evoluzione

Documenti correlati: [Pipeline AI Food Recognition](ai_food_pipeline_README.md) · [Prompt GPT-4V Draft](ai_food_recognition_prompt.md) · [Error Taxonomy](ai_meal_photo_errors.md)

## Obiettivo
Ridurre l'attrito nella registrazione dei pasti offrendo un flusso rapido foto → suggerimenti → conferma, partendo da uno stub deterministico (Fase 0) e introducendo gradualmente euristiche e futura inference remota (Fase 1+).

## Stato Attuale (27-09-2025)
| Aspetto | Fase | Dettagli |
|---------|------|----------|
| Generazione predictions | Stub + Heuristic flaggata | `StubAdapter` default, `HeuristicAdapter` attivabile con env `AI_HEURISTIC_ENABLED=1` |
| Idempotenza analisi | Attiva | Chiave esplicita o auto `user|photoId|photoUrl` (sha256 trunc) – funzione `hash_photo_reference` pronta ma non ancora usata per sostituire la chiave completa user-based |
| Campo `source` schema | Presente | Valori attuali: `stub` o `heuristic` |
| Metriche | Timing wrapper | `time_analysis(phase=adapter.name())` registra latenza per adapter |
| Logging | Parziale | Evento `analysis.created` con adapter e numero items |
| Error Taxonomy | Definita | Non ancora popolata runtime (nessun errore generato nello stub) |

## Flusso Base
1. Client invoca `analyzeMealPhoto` (può passare `photoId` e/o `photoUrl`).
2. Repository verifica idempotenza via `(user, idempotencyKey)`.
3. Se nuova analisi: seleziona adapter attivo → genera lista di item.
4. Ritorna record con `status=COMPLETED`, `source=<adapter>`.
5. `confirmMealPhoto` trasforma indici accettati in `MealEntry` (logica invariata da Fase 0).

## Inference Adapter Layer
File: `backend/inference/adapter.py`

### Protocol
```python
class InferenceAdapter(Protocol):
    def name(self) -> str: ...
    def analyze(self, *, user_id: str, photo_id: Optional[str], photo_url: Optional[str], now_iso: str) -> List[MealPhotoItemPredictionRecord]: ...
```

### Implementazioni
- `StubAdapter`: Restituisce due item statici (insalata, petto di pollo).
- `HeuristicAdapter`: Clona base stub e applica regole:
  * Se ultima cifra `photoId` è pari → aumenta quantità secondo item (+15%) e leggera crescita confidence.
  * Se `photoUrl` contiene "water" → aggiunge item "Acqua" (200g). 

Selezione tramite funzione `get_active_adapter()` che legge `AI_HEURISTIC_ENABLED` (`1|true|on`).

### Hash Foto
Funzione `hash_photo_reference(photo_id, photo_url)` (sha256 trunc 16 chars) predisposta per futura sostituzione della chiave idempotente e caching layer condiviso.

## Repository
File: `backend/repository/ai_meal_photo.py`

Responsabilità chiave:
- Idempotenza: mappa `(user, idempotency_key)` → `analysisId`.
- Generazione record con `source=adapter.name()`.
- Timing metrics attorno a `adapter.analyze` tramite `time_analysis`.
- Logging evento `analysis.created`.

TODO futuri:
- Usare direttamente `hash_photo_reference` come parte della chiave (migrando in modo backward-compatible).
- Aggiungere metriche per cache hit vs new.
- Estendere logging con latenza e dimensione payload.

## Metriche & Telemetria
Attuale: solo latenza per adapter (fase). Pianificato:
| Nome | Tipo | Labels | Descrizione |
|------|------|--------|-------------|
| ai_meal_photo_analysis_latency_seconds | histogram | phase(source) | Latenza analyze per adapter |
| ai_meal_photo_analysis_requests_total | counter | phase | Numero richieste (da estendere) |
| ai_meal_photo_analysis_cache_hits_total | counter | phase | (Futuro) Idempotent reuse |

## Roadmap Aggiornata
| Step | Descrizione | Stato |
|------|-------------|-------|
| Adapter abstraction | Protocol + stub | DONE |
| Heuristic rules | Regole semplici + flag | DONE |
| Source field | Esposto in schema e record | DONE |
| Metrics timing | Wrapper attivo | DONE |
| Hash utility | Funzione pronta | DONE |
| Metrics estensione (cache, errori) | Counters addizionali | TODO |
| Remote model adapter | Chiamata API esterna + fallback | TODO |
| Circuit breaker | Protezione errori provider | TODO |
| Nutrient enrichment | Stima nutrienti per item | TODO |
| Confidence explanation | Dettaglio motivazione | TODO |

## Migrazione Futuro Hash Idempotenza
Piano proposto:
1. Introdurre campo `photoHash` (non usato per lookup) nel record per debug.
2. Raccogliere metriche distribuzione collisioni (attese 0).
3. Abilitare feature flag `AI_IDEMP_HASH_ENABLED` → usa hash come parte della chiave.
4. Rimuovere vecchia chiave dopo periodo di osservazione (7 giorni) mantenendo fallback.

## Estensioni Previste Error Handling
Inserire array `analysisErrors` già nel modello schema (vuoto ora). Regole future:
- Normalizzazione errori in codici (`MealPhotoAnalysisErrorCode`).
- Fallback chain: heuristic → stub se errore remoto o timeout.
- Logging con campo `fallbackApplied`.

## Acceptance Criteria Attuali (Post Heuristic)
1. `source` riflette adapter effettivo (`stub` oppure `heuristic`).
2. Idempotenza invariata rispetto a Fase 0.
3. Nessuna regressione dei test esistenti (repository, idempotenza, metrics base).
4. Heuristic aggiunge al massimo 1 item extra (Acqua) e modifica solo il secondo item di base.

## Dev Notes
- Tutte le modifiche additive: nessun breaking change GraphQL.
- Variabili ambiente centralizzano attivazione feature (nessun toggle runtime via DB ancora).
- Preparare test di integrazione latenza una volta introdotto remote model.

---
Revision: Aggiornato a Fase 1 (heuristic flag) – 2025-09-27.
