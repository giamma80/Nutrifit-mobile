# Changelog

Tutte le modifiche rilevanti a questo progetto saranno documentate in questo file.

Formato ispirato a [Keep a Changelog](https://keepachangelog.com/it-IT/1.1.0/) e SemVer (fase pre-1.0: API instabili).

## [Unreleased]

### Chore
 
- align backend-changelog workflow (python setup + uv install)
- cleanup backend README and add markdownlint gate
- fix schema badge push & pip cache; build(changelog): uniform version headers
- normalize changelog headings + fix lint config

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

Added: Documentazione architettura mobile (`docs/mobile_architecture_plan.md`); documentazione architettura backend (`docs/backend_architecture_plan.md`); guida nutrizione spostata in `docs/nutrifit_nutrition_guide.md` con pipeline AI, dashboard UX, notifiche; schema GraphQL nutrizione esteso (AIInferenceItem, delta subscription, range summary); servizio fake `food_recognition_service.dart`; prompt AI vision + README pipeline AI (`docs/ai_food_recognition_prompt.md`, `docs/ai_food_pipeline_README.md`); README ristrutturato con diagramma, feature matrix e indice; CHANGELOG iniziale.

Removed: Vecchio file root `nutrifit_nutrition_guide.md` (stub eliminato).

Docs: Roadmap mobile (M0–M9) e backend (B0–B9); TODO operativi nelle sezioni AI e notifiche.
