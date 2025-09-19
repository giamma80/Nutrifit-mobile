# Changelog

Tutte le modifiche rilevanti a questo progetto saranno documentate in questo file.

Formato ispirato a [Keep a Changelog](https://keepachangelog.com/it-IT/1.1.0/) e SemVer (fase pre-1.0: API instabili).

## [0.1.0] - 2025-09-18

### Added

- Documentazione architettura mobile (`docs/mobile_architecture_plan.md`).
- Documentazione architettura backend (`docs/backend_architecture_plan.md`).
- Guida nutrizione spostata in `docs/nutrifit_nutrition_guide.md` con pipeline AI, dashboard UX, notifiche.
- Schema GraphQL nutrizione esteso (AIInferenceItem, delta subscription, range summary).
- Servizio fake `food_recognition_service.dart`.
- Prompt AI vision + README pipeline AI (`docs/ai_food_recognition_prompt.md`, `docs/ai_food_pipeline_README.md`).
- README ristrutturato con diagramma, feature matrix e indice.
- CHANGELOG iniziale.

### Removed

- Vecchio file root `nutrifit_nutrition_guide.md` (stub eliminato).

### Internal / Docs

- Roadmap mobile (M0–M9) e backend (B0–B9).
- TODO operativi nelle sezioni AI e notifiche.

## [Unreleased]

### Planned

- Workflow CI (lint, test, schema diff).
- Implementazione meal queue offline.
- Adapter OpenFoodFacts + caching.
- Subscription real-time integration effettiva.
### Added
- Badge pipeline backend (`backend-ci`) nel README backend.
- Badge stato schema GraphQL (placeholder aligned) nel README backend.
- Target `docker-test` per test integrazione container.
- Target `docker-shell` per debug interattivo container.
- Campo GraphQL `health` + test unit dedicato.

### Changed
- README backend aggiornato con sezione cockpit estesa, esempi e differenze run locale vs Docker.
- Dockerfile parametrizzato con `ARG VERSION` propagato a `/version`.

### Chore
- Consolidata toolchain schema (`schema-export`, `schema-check`) + integrazione in CI.
- Script esportazione schema fix path `sys.path`.
- Introduzione script integrazione `scripts/integration_test.sh` eseguito in CI.

### Docs
- Migliorata documentazione comandi versioning (`version-show`, `version-bump`).
- Aggiunta descrizione flusso CI e sezione Health & GraphQL.

