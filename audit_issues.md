## Audit Issues (Consolidated)

Questo file sostituisce `ussues.md` (rimandare qui e rimuovere duplicazioni). Struttura tabellare unica per tracciamento stato.

| ID | Severity | Confidence | Scope / Files | Description | Impact | Remediation | Status | Tags |
|----|----------|------------|---------------|-------------|--------|------------|--------|------|
| 1 | Critical | High | backend/app.py, docs | `logMeal` non esponeva `idempotencyKey` | Idempotenza fragile / duplicati | Aggiunta chiave + doc aggiornata | DONE | DOC |
| 2 | Critical | High | workflows backend-* | Workflow placeholder vuoti | Copertura CI falsa | Popolati pipeline minime | DONE |  |
| 3 | High | High | README badge vs pyproject | Version mismatch | Confusione versioni | Sincronizzazione badge automatica | DONE | DOC |
| 4 | High | High | verify_schema_breaking.py | Diff non semantico | Breaking non rilevati | AST diff + exit codes | DONE |  |
| 5 | High | Medium | CI security | Nessun vulnerability scan | Rischio CVE latenti | Integrare Trivy + pip-audit | TODO | SEC |
| 6 | High | Medium | cache.py | Nessuna metrica iniziale | Difficile tuning | Aggiunta stats + resolver cacheStats | DONE |  |
| 7 | Medium | High | mobile/, web/ | Mancato scaffolding | Onboarding lento | Creare scaffold reali | TODO |  |
| 8 | Medium | High | backend_architecture_plan.md | Doc pipeline non allineata | Governance confusa | Allineata doc | DONE | DOC |
| 9 | Medium | Medium | Schema runtime | Mancanza nutrientSnapshotJson | Refactor futuro oneroso | Campo opzionale introdotto | DONE | DOC |
| 10 | Medium | Medium | Idempotency derivata | Timestamp nella firma | Duplicati potenziali | Escluso timestamp server | DONE |  |
| 11 | Medium | Medium | sync_schema_from_backend.sh | Script placeholder | Falsa percezione sync | Rimuovere o sostituire con schema-sync | TODO |  |
| 12 | Medium | Medium | Badge schema status | Statico non validato | Drift invisibile | Hash + check workflow | DONE | DOC |
| 13 | Low | High | Licenza | Incongruenza README/pyproject | Ambiguità legale | Uniformata licenza Proprietary | DONE | DOC |
| 14 | Low | Medium | cache TTL tests | Expiry non testato | Regressioni TTL invisibili | Aggiungere test scadenze | TODO | TEST |
| 15 | Low | Medium | Nutrient keys | Hard-coded duplicati | Incoerenze estensioni | Centralizzate in constants | DONE |  |
| 16 | Low | Medium | exit codes diff | exit sempre 0 | CI non reagiva | Exit codes implementati | DONE |  |
| 17 | Low | Medium | mobile-ci.yml pattern | Filtri generici root | CI skip dopo scaffold | Aggiornare pattern path | TODO | CI |
| 18 | Low | Low | CODEOWNERS assente | Ownership informale | Review mancanti | Aggiunto CODEOWNERS | DONE | DOC |
| 19 | Medium | High | CRUD pasti | Mancavano update/delete | Funzioni incomplete | Aggiunte mutation CRUD | DONE |  |
| 20 | Medium | Medium | Meal repo pattern | Solo add/list | Estensione complessa | Estesi metodi + test | DONE |  |
| 21 | Low | Medium | Dockerfile copy nutrients.py | File escluso build | Errore runtime | Aggiunto al COPY | DONE |  |
| 22 | Medium | High | Attività totalizzazione | Totali da minute events | Drift / incompletezza | Introdotto syncHealthTotals delta source | DONE | ARCH |
| 23 | Medium | Medium | Idempotency conflitti attività | Approccio differenziato ingest vs sync | Incoerenza flag | Unificata semantica flag (duplicate/conflict/reset) | DONE | ARCH |
| 24 | Medium | High | backend/graphql analyzeMealPhoto+confirmMealPhoto, docs/ai_meal_photo.md | Introdotto stub AI Meal Photo (source=STUB) | Riduce coupling futuro, definisce boundary pipeline | Endpoint e doc allineati | DONE | ARCH |
| 25 | Medium | High | docs/health_totals_sync.md, README.md | Estratta doc Health Totals Sync dedicata | Migliora governance e riduce drift | Doc separata con link nel README | DONE | DOC |
| 26 | Medium | Medium | docs/data_ingestion_contract.md | Contratto ingest aggiornato (nutrientSnapshotJson + fallback idempotency) | Evita refactor futuri e duplicati | SDL + sezione idempotenza aggiornate | DONE | DOC |
| 27 | Low | Medium | docs/ai_* cross-link | Mancavano cross-link tra docs AI (pipeline, prompt, stub) | Navigazione scarsa | Aggiunti link reciproci | DONE | DOC |
| 28 | Low | Medium | docs/recommendation_engine.md | Draft non marcato "non-runtime" | Potenziale confusione stato feature | Stato esplicitato (non runtime) | DONE | DOC |
| 29 | Medium | Medium | AI pipeline observability | Assenza tracing strutturato & metriche (latency, fallback usage) | Difficile tuning e debug fasi successive | Introdurre logging strutturato + OpenTelemetry + counters | TODO | ARCH |
| 30 | High | Medium | Futuro modello visione | Mancano rate limiting & cost guard | Rischio costi / abuso | Implementare rate limit per utente/IP + budget giornaliero | TODO | SEC |
| 31 | Medium | Medium | Meal idempotency logging | Nessun evento esplicito su dedupe pasti | Diagnosi dedupe difficile | Log evento con reason=IDEMPOTENT_DUPLICATE | TODO | OBS |
| 32 | Medium | Medium | health_totals_delta storage | Stato solo in-memory | Perdita dati su restart | Persistenza (es. tabella Postgres) + migrazione | TODO | ARCH |
| 33 | Low | Low | AI error taxonomy | Codici errore non definiti (INVALID_IMAGE, PARSE_FALLBACK_USED) | Gestione client incoerente | Definire enum e surface nel payload GraphQL | TODO | DOC |

Legenda Tags: DOC=documentazione, SEC=sicurezza, ARCH=architettura, TEST=test coverage, CI=continuous integration, OBS=observability.

Indicazioni aggiornamento: ogni PR che chiude o crea un finding aggiorna questa tabella nello stesso commit.

### Piano Prossimi Passi – AI Food Recognition Phase 1 (Heuristic)

Obiettivo Phase 1: passare da stub (source=STUB) a pipeline heuristica/barcode-first senza modelli visione costosi, mantenendo costi ~0 e introducendo osservabilità.

Deliverable principali:
1. Feature Flag `aiMealPhotoPhase1` (default off) + gating per utente.
2. Adapter `InferenceAdapter` con implementazioni: `StubAdapter` (attuale), `HeuristicAdapter` (nuovo) – strategy pattern plug-in futura VisionAdapter.
3. Barcode-first branch: se codice a barre rilevato (libreria mobile / metadata) recupero nutrienti da catalogo locale (TODO dataset) prima di parsing testo.
4. Heuristic parsing: estrazione alimenti e quantità con regex + mapping dizionario sinonimi → nutrient snapshot aggregation.
5. Portion estimation euristica (grammi default, moltiplicatori per parole chiave: “piatto”, “cucchiaio”, “bicchiere”).
6. Error taxonomy introdotta (Issue 33) + surface nel campo `analysisErrors`.
7. Observability (Issue 29): counters (requests, fallbackUsed), histogram latenza, sampling logging per mismatch conferma utente.
8. Rate limiting placeholder integrato (Issue 30) – contatore locale in-memory + TODO estensione Redis.
9. Metrics definizione SLO: p95 < 800ms (heuristic), fallback rate < 15%.
10. Documentazione: aggiornare `docs/ai_food_pipeline_README.md` sezione Phase 1 + changelog tabella fasi.

Checklist esecuzione (da creare come issues separati collegati a ID audit corrispondenti):
- [ ] Flag configurazione + toggle runtime
- [ ] Interfaccia Adapter + wiring DI
- [ ] Implementazione HeuristicAdapter
- [ ] Barcode detection hook (stub se mobile non pronto)
- [ ] Dizionario sinonimi + nutrient mapping seed
- [ ] Portion heuristics + test unitari
- [ ] Error enum + schema GraphQL update (Issue 33)
- [ ] Structured logging + metrics (Issue 29)
- [ ] Rate limit baseline (Issue 30)
- [ ] Aggiornamento documentazione e prompt note
- [ ] Test end-to-end analyze→confirm con branch heuristico

Rischi & Mitigazioni:
- Qualità parsing bassa → A/B gating + metric fallbackUsed.
- Dizionario incompleto → schema per aggiunte rapide + script rigenerazione.
- Overfitting heuristico → limitare regole e misurare coverage alimenti reali.

Go/No-Go Criteria per rollout flag ON al 5%: p95 sotto target per 3 giorni, fallback < 20%, nessun errore critico (500) > 0.5% richieste.
