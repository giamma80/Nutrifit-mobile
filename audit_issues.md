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
| 24 | Medium | High | backend/graphql analyzeMealPhoto+confirmMealPhoto, docs/ai_meal_photo.md | Introdotto stub AI Meal Photo (source=STUB) → evoluto a GPT (source=gpt4v) | Boundary definito ora con adapter reale | DONE | ARCH |
| 25 | Medium | High | docs/health_totals_sync.md, README.md | Estratta doc Health Totals Sync dedicata | Migliora governance e riduce drift | Doc separata con link nel README | DONE | DOC |
| 26 | Medium | Medium | docs/data_ingestion_contract.md | Contratto ingest aggiornato (nutrientSnapshotJson + fallback idempotency) | Evita refactor futuri e duplicati | SDL + sezione idempotenza aggiornate | DONE | DOC |
| 27 | Low | Medium | docs/ai_* cross-link | Mancavano cross-link tra docs AI (pipeline, prompt, stub) | Navigazione scarsa | Aggiunti link reciproci | DONE | DOC |
| 28 | Low | Medium | docs/recommendation_engine.md | Draft non marcato "non-runtime" | Potenziale confusione stato feature | Stato esplicitato (non runtime) | DONE | DOC |
| 29 | Medium | Medium | AI pipeline observability | Assenza tracing strutturato & metriche (latency, fallback usage) | Difficile tuning e debug fasi successive | Introdurre logging strutturato + OpenTelemetry + counters | TODO | ARCH |
| 30 | High | Medium | Futuro modello visione | Mancano rate limiting & cost guard | Rischio costi / abuso | Implementare rate limit per utente/IP + budget giornaliero | TODO | SEC |
| 31 | Medium | Medium | Meal idempotency logging | Nessun evento esplicito su dedupe pasti | Diagnosi dedupe difficile | Log evento con reason=IDEMPOTENT_DUPLICATE | TODO | OBS |
| 32 | Medium | Medium | health_totals_delta storage | Stato solo in-memory | Perdita dati su restart | Persistenza (es. tabella Postgres) + migrazione | TODO | ARCH |
| 33 | Low | Low | AI error taxonomy | Codici errore non definiti (INVALID_IMAGE, PARSE_FALLBACK_USED) | Gestione client incoerente | Enum definito + campi analysisErrors/failureReason esposti + metrics base | DONE | DOC |
| 34 | Medium | Medium | AI meal photo fallback chain | Assente catena multi-adapter (gpt4v→stub) | Mancato degrad graceful | Implementare decision tree + metriche fallback | TODO | ARCH,OBS |
| 35 | High | Medium | GPT rate limiting | Assenza throttling per utente/IP | Rischio costi e abuso | Introdurre token bucket + quota giornaliera | TODO | SEC |
| 36 | Medium | Medium | Portion inference | Stima quantità rudimentale | Nutrienti potenzialmente errati | Introdurre heuristics + test copertura | TODO | ARCH |
| 37 | Medium | Medium | Persistence MealPhotoAnalysis | In-memory volatile | Perdita analisi / audit gap | Persistenza tabellare + migrazione retrocompatibile | TODO | ARCH |
| 38 | Medium | Medium | Metrics optional clarity | Mancata nota optionalità in docs storiche | Interpretazioni fuorvianti | Doc aggiornata + flag stato raccolta | DONE | DOC |
| 39 | Low | Medium | Docs drift roadmap adapter | Roadmap non riflette GPT già attivo | Disallineamento stakeholder | Aggiornata sezione stato corrente | DONE | DOC |
| 40 | Medium | Medium | Error warnings counting | Warning non sempre contati come metriche | Osservabilità parziale | Aggiungere counter dedicato warnings_total | TODO | OBS |
| 41 | Medium | High | GPT-4V prompt formato | Prompt minimale non impone enum unit e struttura rigida | Parse fallimenti potenziali / hallucination | Introdurre prompt v2 con sezione MUST/DO NOT + schema rigido | **DONE (V3)** | ARCH,OBS |
| 42 | High | High | Parser JSON robustezza | Assenza gestione dettagliata errori (missing keys, tipi) | PARSE_EMPTY frequente → fallback e UX peggiorata | Implementare parser con validazioni granulari + error taxonomy mapping | TODO | ARCH |
| 43 | Medium | Medium | Quantity clamp enforcement | Clamp implementato ma non metricato | Assenza visibilità input anomali | Aggiungere counters quantity_clamped_total + log debugId | TODO | OBS |
| 44 | Medium | Medium | Macro fill ratio logging | Nessun tracciamento copertura macro calcolate | Difficile valutare enrichment futuro | Calcolare macro_fill_ratio e log/metric histogram | TODO | OBS |
| 45 | Medium | Medium | Parse success rate metric | Mancano parse_success_total / parse_failed_total | Non misurabile miglioramento Fase 1 | Aggiungere counters + percentuale derivata in dashboard | TODO | OBS |
| 46 | Low | Medium | Prompt versioning | Nessun campo version nel payload | Difficoltà correlare regressioni | Aggiungere promptVersion in raw_json o analysisErrors debugId | TODO | DOC,OBS |
| 47 | Medium | High | backend/nutrient_enrichment/, docs/ai_meal_photo.md | Category profiles assenti (lean_fish, poultry, pasta_cooked, ecc.) | Macro incoerenti e impossibile normalizzare nutrienti | Introdurre modulo category_profiles.py con ≥10 profili documentati | TODO | ARCH,OBS |
| 48 | Medium | High | backend/nutrient_enrichment/, docs/ai_meal_photo.md | Label normalization mancante (regex/token) | Bassa hit rate profili categoria | Implementare normalize_label + test coverage edge cases | TODO | ARCH,TEST |
| 49 | Medium | Medium | backend/nutrient_enrichment/ | Garnish quantity non normalizzata (lemon slice, parsley) | Calorie gonfiate da garnish | Range fisso 5–10g + clamp e metric garnish_clamped_total | TODO | ARCH,OBS |
| 50 | Medium | Medium | backend/nutrient_enrichment/ | Hard constraints macro mancanti (carbs>0 per pesce) | Macro implausibili propagate | Regole categoria: lean_fish & poultry carbs=0 se >2g | TODO | ARCH |
| 51 | Medium | Medium | backend/inference/adapter.py | Macro/calorie consistency check assente | Calories divergenti dai macro → trust errato | Recompute calories se delta>15% + flag calorieCorrected | TODO | ARCH,OBS |
| 52 | Low | Medium | backend/nutrient_enrichment/ | Mancanza campo enrichmentSource | Audit difficile provenienza nutrienti | Aggiungere enum enrichmentSource (heuristic|default|category_profile) | **DONE (usda|category_profile|default)** | ARCH,DOC |
| 53 | Medium | Medium | backend/metrics/, docs/ai_meal_photo_metrics.md | Metriche correzioni macro inesistenti | Impossibile misurare efficacia normalization | Aggiungere ai_meal_photo_macro_corrections_total{reason} | TODO | OBS |
| 54 | High | Medium | backend/inference/adapter.py | Nessun whitelist dominio photoUrl | Rischio SSRF / abuse GPT-4V | Validare photoUrl dominio (es. firebase storage) + error code INVALID_IMAGE | TODO | SEC,ARCH |
| 55 | Medium | Medium | feature flags config | Assente feature flag rollout (dry_run→enforce) per normalization | Rollout rischio regressioni | Introdurre flag AI_NORMALIZATION_MODE (off|dry_run|enforce) | TODO | ARCH,OPS |
| 56 | Medium | High | backend/inference/adapter.py, schema GraphQL | Mancanza dishName aggregato | UX meno leggibile / niente label piatto | Estrarre high-level dishName via prompt + esporre campo | **DONE** | ARCH,UX |
| 57 | Medium | High | backend/inference/adapter.py, persistence repo | photoUrl non persistita in analysis & confirm | Perdita tracciabilità immagine | Aggiungere storage e campo photoUrl in MealPhotoAnalysis | TODO | ARCH,DOC |
| 58 | High | High | docs/nutrifit_nutrition_guide.md | Sezione "Fonti nutrienti e priorità" assente | Governance sorgenti nutrienti non formalizzata | Aggiungere sezione con gerarchia (user_override > off_barcode > usda_generic > ciqual > category_profile > heuristic > gpt_guess) | TODO | DOC,ARCH |
| 59 | Critical | High | enrichment pipeline, new module usda_adapter.py | Assenza integrazione USDA (FoodData Central) per alimenti generici | Macro/calorie meno accurate per alimenti non confezionati | Implementare lookup FDC (ricerca descrizione → fdc_id, normalizzazione per 100g, caching, tagging source=usda_generic/usda_exact) | **DONE** | ARCH,DATA |
| 60 | Medium | High | GraphQL analyzeMealPhoto, domain V2, adapter layer | Campo dishHint per migliorare accuratezza AI meal analysis | UX migliorata con suggerimenti utente | Implementato campo opzionale dishHint in schema + domain service + adapter layer con logging completo | DONE | ARCH,UX |

Legenda Tags: DOC=documentazione, SEC=sicurezza, ARCH=architettura, TEST=test coverage, CI=continuous integration, OBS=observability, UX=user experience.

Indicazioni aggiornamento: ogni PR che chiude o crea un finding aggiorna questa tabella nello stesso commit.

### Note Evolutive
La precedente sezione "Phase 1 (Heuristic)" è stata rimossa in favore del nuovo Piano Operativo nel documento `docs/ai_meal_photo.md`. Le issue 41–46 tracciano gli obiettivi attuali della Fase 1 (Prompt rigoroso, Parser robusto, Metriche parse, Clamp visibile, Macro fill ratio, Versioning prompt). Le fasi successive restano mappate su issue esistenti (29, 34, 36, 35).
