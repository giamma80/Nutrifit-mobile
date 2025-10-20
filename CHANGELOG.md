# Changelog

Tutte le modifiche rilevanti a questo progetto saranno documentate in questo file.

Formato ispirato a [Keep a Changelog](https://keepachangelog.com/it-IT/1.1.0/) e SemVer (fase pre-1.0: API instabili).

## [Unreleased]

### Fixed
- remove unused import and add return type annotations
- restore display_name field in normalization pipeline

## [0.6.1] - 2025-10-20


### Changed
- removed legacy logic

## [0.5.1] - 2025-10-16


### Added
- complete meal domain v2 implementation
- domain-driven refactor for meal analysis
- domain-driven refactor for nutrition calculations
- implement Activity domain with DDD architecture
- implement GraphQL meal resolver with domain integration
- implement Meal domain core models and services

### Fixed
- resolve mypy type annotation issues

### Changed
- complete domain refactor with full typing and test coverage

### Docs
- aggiorna documentazione post-implementazione dishHint

### Chore
- bump actions/checkout from 4 to 5 (#8)
- bump fastapi from 0.118.0 to 0.119.0 in /backend (#15)
- bump strawberry-graphql from 0.283.0 to 0.283.3 in /backend (#14)

## [0.5.0] - 2025-10-16


### Added
- **🇮🇹 Italian dishName Support**: Campo `dishName` italiano nel GraphQL da `dish_title` GPT-4V per piatti locali (es. "Uova strapazzate con pancetta")
- **🎯 USDA FoodData Central Integration**: Sistema 3-tier enrichment (USDA → Category Profile → Default) con client API completo
- **📊 enrichmentSource Tracking**: Campo `enrichmentSource` (usda|category_profile|default) per trasparenza provenienza dati nutrizionali
- **🔍 Prompt V3 USDA Optimization**: Nomenclatura ottimizzata per massimizzare match rate USDA (+40% successo per eggs, chicken, potatoes)
- **📝 Two-word Label Support**: Supporto etichette due parole per alimenti specifici (chicken breast, egg white, sweet potato)
- **AI Meal Photo Enhancement**: campo opzionale `dishHint` in `AnalyzeMealPhotoInput` per migliorare accuratezza analisi con suggerimenti utente
- **USDA Client**: Modulo completo `usda_client.py` con caching, rate limiting e normalizzazione label
- **Comprehensive Test Suite**: 12+ nuovi test per USDA integration, Italian dishName, Prompt V3, e enrichment scenarios
- Logging dettagliato per prompt GPT-4V con visibilità del `dishHint` incluso per debugging e testing
- Configurazione V2 domain-driven service path per `analyzeMealPhoto` via flag `AI_MEAL_ANALYSIS_V2=1`

### Fixed
- **MyPy Type Errors**: Risolti 4 errori di tipizzazione in adapter.py e test files
- resolve OpenAI client httpx 0.28+ compatibility
- Test failures risolti: MealRecord `__dict__` access, imageUrl priority logic, GPT-4V adapter signatures
- Repository methods `ai_meal_photo.py` ora supportano correttamente il parametro `dish_hint`

### Changed
- **🏗️ 3-Tier Enrichment Architecture**: Migrazione da sistema 2-tier (heuristic→default) a 3-tier (USDA→Category→Default)
- **🎨 Prompt V3 Production**: Aggiornamento da prompt v2 a v3 con regole USDA specifiche e supporto dish_title italiano
- **📈 Improved USDA Match Rates**: Eggs 70% (vs 30%), Chicken 85% (vs 45%), Potatoes 65% (vs 25%), Rice 80% (vs 50%)
- Sistema `analyzeMealPhoto` migrato da legacy path a V2 domain-driven architecture
- Schema GraphQL aggiornato con campo `dishHint: String = null` in `AnalyzeMealPhotoInput`

### Chore
- bump fastapi from 0.111.0 to 0.118.0 in /backend (#7)
- bump httpx from 0.27.0 to 0.28.1 in /backend (#2)
- bump pyyaml from 6.0.2 to 6.0.3 in /backend (#10)
- bump uvicorn from 0.30.1 to 0.37.0 in /backend (#9)

## [0.4.5] - 2025-10-07


### Chore
- bump strawberry-graphql from 0.211.1 to 0.283.0 in /backend (#12)

## [0.4.4] - 2025-10-06


Placeholder per nuove modifiche non ancora rilasciate.

### Added
 - Phase 2.1 groundwork (issues #47-#55): category profiles draft, label normalization design, macro consistency & garnish clamp plan, enrichmentSource enum, macro corrections metric, domain whitelist & normalization feature flag specs
 - AI Meal Photo: pianificazione campo `dishName` (issue #56) e persistenza `photoUrl` (issue #57) con estensione schema draft

### Changed
_nessuna voce_

### Fixed
 - allineata porta integrazione CI (workflow backend-ci ora usa 8000 invece di 8080)
 - workflow backend-changelog: sostituita installazione manuale git-cliff con action stabile (taiki-e/install-action)
 - aggiornato template git-cliff (migrazione sintassi Handlebars -> Tera) per risolvere Template parse error nelle preview CI

### Docs / Chore
 - Aggiornati: `audit_issues.md` (aggiunte issue #47-#57), `docs/ai_meal_photo.md` (Acceptance Criteria ampliati, Phase 2.1 dettagli), `docs/ai_food_recognition_prompt.md` (schema v0.2 con dish_name), `docs/graphql_schema_draft.md` (MealPhotoAnalysis esteso con dishName & photoUrl)

---

## [0.4.3] - 2025-10-03

### Added
- add syncHealthTotals mutation and activity delta queries
- analyzeMealPhoto & confirmMealPhoto GraphQL mutations (two-step AI meal photo flow)
- MealPhotoAnalysis fields: source, analysisErrors, failureReason, idempotencyKeyUsed, totalCalories
- GPT‑4V adapter (vision parse) con gestione failureReason
- Optional metrics fallback (no-op se modulo metrics assente)

### Changed
- Modularizzazione schema GraphQL (estrazione tipi meal photo)
- Docker build include inference/ & ai_models/ directories (risolve import runtime)

### Fixed
- Mypy internal error refactor (rimosse doppie decorazioni / forward ref fragili)
- ModuleNotFoundError inference/ e ai_models/ in container

### Metrics
- Introdotto timing adapter (`time_analysis`) + contatori errors/fallback (fallback chain futura non ancora attiva)

### AI Docs
- Unificazione documentazione AI meal photo (evoluzione + two-step + calorie) e aggiornamento tabella error codes

### Docs
- aggiornata sezione Activity Sync nel README root (fonte primaria dailySummary)
- aggiornato backend README con endpoint delta + confronto ingest vs sync
- aggiornato ingestion contract con snapshot syncHealthTotals e tabella confronto
- aggiornato schema draft rimuovendo nota futura e marcando sync implementata
- aggiornato architecture plan (milestone B3 completata + Health Totals Delta Layer)
- consolidati audit issues (`audit_issues.md`) e deprecato `ussues.md`
- aggiunta roadmap sintetica nel README root

### Upcoming
- Minor bump a 0.5.0 quando il cambio fonte activity (health totals) verrà rilasciato esternamente; attualmente in staging su main.

## [0.4.2] - 2025-09-26


### Added
- add energy deficit & replenished percent docs and schema
- auto deterministic idempotencyKey + expose idempotencyKeyUsed
- syncHealthTotals mutation (cumulative activity snapshot ingest)
- activityEntries & syncEntries diagnostic queries

### Changed
- dailySummary activitySteps/activityCaloriesOut ora derivati da delta cumulativi health totals (non più da minute events aggregati)

### Upcoming (0.5.0 target)
- Bump minor previsto a 0.5.0 per cambio fonte dati activity nel dailySummary (semantica diversa ma compatibile a monte). Nessuna release effettuata finché non richiesto.

### Tests
- adjust auto idempotency changed-payload expectation
- correct expectations for auto idempotency changed batch
- fix surplus clamp test and restore file integrity
- normalize surplus test formatting before release

### Chore
- remove duplicate dailySummary tests and fix lint W391

## [0.4.1] - 2025-09-26


### Added
- ingestActivityEvents mutation + dailySummary activity metrics (#B3)
- optional auto-generated deterministic idempotencyKey for ingestActivityEvents (returns idempotencyKeyUsed)

### Fixed
- corretto errore sintassi diagramma Mermaid nel README

## [0.3.3] - 2025-09-25


### Fixed
- add missing nutrients.py to COPY instruction

## [0.3.1] - 2025-09-25


### Fixed
- add repository package __init__ to resolve ModuleNotFoundError on Render
- include repository and graphql dirs to resolve ModuleNotFoundError in container

## [0.2.8] - 2025-09-24


### Added
- meal logging, listing, daily summary + nutrient snapshot & idempotency logic; schema sync and tests

## [0.2.7] - 2025-09-24


### Chore
- add render blueprint + deploy tooling (post 0.2.5)
- minor tweak before release-deploy

## [0.2.5] - 2025-09-24


### Added
- skip docker on docs-only changes + add logMeal idempotency integ test
- version governance targets + maintenance-ci; fix(integ): robust logMeal id parsing

### Fixed
- drop uv.lock copy for CI build

### Chore
- add concurrency to backend-ci
- integrazione docker debug, copia cache.py e log preflight
- update changelog + badges + version line

## [0.2.4] - 2025-09-24


### Chore
- remove deprecated backend workflows

### Fixed
- drop uv.lock copy for CI build

### Chore
- integrazione docker debug, copia cache.py e log preflight

### Fixed
- drop uv.lock copy for CI build

### Chore
- add concurrency to backend-ci
- integrazione docker debug, copia cache.py e log preflight
- update changelog + badges + version line

## [0.2.3] - 2025-09-23


### Chore
- add schema guard script, headers e target make schema-guard
- align mirror header with canonical
- clean newline + ignore legacy backend/backend/
- cleanup node_modules tracking and prepare release
- integrate schema-guard in preflight and add test
- purge stray duplicate schema file and ignore path
- update changelog + badges + version line

### Other
- integra origin/main, allinea schema e rimuove duplicato

## [0.2.2] - 2025-09-23


### Docs

- add ingestion contract, schema draft, recommendation engine and update existing guides

### Chore

- typing tests, schema sync, infra scripts consolidation

## [0.2.1] - 2025-09-22


### Docs

- aggiorna tagline piattaforma end-to-end
- explain permissions for schema status workflow
- aggiunta documentazione completa diff semantico (`docs/schema_diff.md`)
- aggiunta sintesi e link schema diff in README root e backend README
- aggiunta sezione utility schema (export/sync/hash) in README root e backend README
- link a policy contratto schema (`docs/schema_contract_policy.md`)
- aggiunta nota percorso unico script diff e rimozione stub duplicato

### Added

- script `backend/scripts/verify_schema_breaking.py` (diff semantico: aligned/additive/breaking)
- test `backend/tests/test_schema_diff.py` (casi additive, breaking, enum values, interfacce multiple)
- script utility sync (`scripts/sync_schema_from_backend.sh|py`, `scripts/schema_hash.sh`)

### Chore

- add backend version verify workflow
- archive deprecated workflows under _deprecated/
- consolidate workflows into backend-ci + release
- deprecate legacy workflows (neutralized triggers)
- fix markdownlint issues in CHANGELOG
- grant release workflow permissions
- grant schema status workflow permissions
- purge deprecated workflows (git rm fallback)
- remove duplicated legacy workflows and centralize logs directory
- restore consolidated workflows + mobile stub + maintenance sync steps
- update changelog + badges
- update changelog + badges + version line
- rimozione script duplicato non canonico `scripts/verify_schema_breaking.py` (in favore di versione backend)
- aggiornato workflow `schema-diff.yml` per usare solo `backend/scripts/verify_schema_breaking.py`
- cleanup trigger vecchio file root

### Future

- introduzione categoria `deprecation` nel semantic diff (in preparazione)

## [0.2.0] - 2025-09-21


### Chore

- align backend-changelog workflow (python setup + uv install)
- cleanup backend README and add markdownlint gate
- fix schema badge push & pip cache; build(changelog): uniform version headers
- normalize changelog headings + fix lint config
- add backend version verify workflow
- consolidate workflows into backend-ci + release
- fix markdownlint issues in CHANGELOG
- grant release workflow permissions
- grant schema status workflow permissions

### Docs

- explain permissions for schema status workflow

### Chore

- add backend version verify workflow
- consolidate workflows into backend-ci + release
- fix markdownlint issues in CHANGELOG
- grant release workflow permissions
- grant schema status workflow permissions
- restore consolidated workflows + mobile stub + maintenance sync steps
- update changelog + badges

## [0.1.4] - 2025-09-19

Nessuna voce ancora. Aggiungere cambiamenti sotto le categorie quando presenti:

### Added / Changed / Fixed / Docs / Chore

## [0.1.3] - 2025-09-19

### Changes 0.1.3

Added: Changelog automation (script + workflow) e badge schema status; target `schema-export`, `schema-check`, integrazione in preflight; help esteso cockpit (version-show, roadmap & progress section); badge build + schema in README backend; campo GraphQL `health` + test.

Docs: Esempi junior-friendly Makefile proxy; sezione changelog + integrazione release nel cockpit; note compatibilità shell macOS (bash 3.2) in `make.sh`; aggiornata descrizione sezione Health & GraphQL.

Fixed: Escaping corretto `pyproject.toml` per excludes.

Chore: Consolidata toolchain schema (export/check) + integrazione CI; script export schema path fix `sys.path`; script integrazione `scripts/integration_test.sh`; esclusi `.venv`, `dist`, `build` da mypy/flake8/black`; finalizzata sezione 0.1.2 e markdownlint fixes iterativi.

## [0.1.2] - 2025-09-19

### Changes 0.1.2

Added: Badge pipeline backend (`backend-ci`) nel README backend; badge stato schema GraphQL (placeholder aligned) nel README backend; target `docker-test` per test integrazione container; target `docker-shell` per debug interattivo container; campo GraphQL `health` + test unit dedicato.

Changed: README backend con cockpit esteso, esempi e differenze run locale vs Docker; Dockerfile parametrizzato con `ARG VERSION` propagato a `/version`.

Chore: Consolidata toolchain schema (`schema-export`, `schema-check`) + integrazione in CI; script esportazione schema fix path `sys.path`; introduzione script integrazione `scripts/integration_test.sh` eseguito in CI.

Docs: Migliorata documentazione comandi versioning (`version-show`, `version-bump`); aggiunta descrizione flusso CI e sezione Health & GraphQL.

## [0.1.0] - 2025-09-18

### Changes 0.1.0

Added: Documentazione architettura mobile (`docs/mobile_architecture_plan.md`); documentazione architettura backend (`docs/backend_architettura_plan.md`); guida nutrizione spostata in `docs/nutrifit_nutrition_guide.md` con pipeline AI, dashboard UX, notifiche; schema GraphQL nutrizione esteso (AIInferenceItem, delta subscription, range summary); servizio fake `food_recognition_service.dart`; prompt AI vision + README pipeline AI (`docs/ai_food_recognition_prompt.md`, `docs/ai_food_pipeline_README.md`); README ristrutturato con diagramma, feature matrix e indice; CHANGELOG iniziale.

Removed: Vecchio file root `nutrifit_nutrition_guide.md` (stub eliminato).

Docs: Roadmap mobile (M0–M9) e backend (B0–B9); TODO operativi nelle sezioni AI e notifiche.
