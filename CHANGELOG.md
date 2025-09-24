# Changelog

Tutte le modifiche rilevanti a questo progetto saranno documentate in questo file.

Formato ispirato a [Keep a Changelog](https://keepachangelog.com/it-IT/1.1.0/) e SemVer (fase pre-1.0: API instabili).

## [Unreleased]

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
