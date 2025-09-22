```text
 _   _       _   _  __ _ _ _ _   
| \ | |_   _| |_| |/ _(_) (_) |_ 
|  \| | | | | __| | |_| | | | __|
| |\  | |_| | |_| |  _| | | | |_ 
|_| \_|\__,_|\__|_|_| |_|_|_|\__|
  Nutrition · Fitness · AI
```

<p align="center">
<img src="https://img.shields.io/badge/flutter-ready-blue" alt="Flutter" />
<img src="https://img.shields.io/badge/graphql-modular-purple" alt="GraphQL" />
<img src="https://img.shields.io/badge/ai-food%20vision-orange" alt="AI" />
<img src="https://img.shields.io/badge/license-TBD-lightgrey" alt="License" />
 <img src="https://img.shields.io/badge/backend_version-0.2.0-green" alt="Backend Version" />
 <img src="https://img.shields.io/badge/schema_status-synced-brightgreen" alt="Schema Status" />
<a href="https://github.com/giamma80/Nutrifit-mobile/actions/workflows/backend-ci.yml"><img src="https://github.com/giamma80/Nutrifit-mobile/actions/workflows/backend-ci.yml/badge.svg" alt="Backend CI" /></a>
<a href="https://github.com/giamma80/Nutrifit-mobile/actions/workflows/mobile-ci.yml"><img src="https://img.shields.io/badge/mobile_ci-pending-lightgrey" alt="Mobile CI (stub)" /></a>
</p>

> **Nutrifit** è una piattaforma end-to-end per nutrizione intelligente e fitness: un backend GraphQL centralizzato (backend‑centric) che astrae sorgenti esterne (OpenFoodFacts oggi, Robotoff/AI domani) servendo app Mobile Flutter e un Web Sandbox di validazione, con pipeline AI e automazione nutrizionale coerenti.

## 📚 Indice Rapido

1. [Componenti del Monorepo](#-componenti-del-monorepo)
2. [Documentazione Principale](#-documentazione-principale)
3. [Architettura High-Level](#-architettura-high-level)
4. [Dynamic Recommendations](#-dynamic-recommendations)
5. [Feature Matrix](#-feature-matrix)
6. [Roadmap & Progress](#-roadmap--progress)
7. [Struttura Repository](#-struttura-repository-estratto)
8. [Workflow CI/CD](#-workflow-cicd)
9. [Contributi](#-contributi)
10. [Nerd Corner](#-nerd-corner)
11. [Licenza](#-licenza)

## 🧩 Componenti del Monorepo

Questo repository ospita più superfici applicative (monorepo). Ogni componente mantiene il proprio ciclo di versione, changelog e pipeline.

| Componente | Path | Stato | Versioning | Descrizione Sintetica |
|-----------|------|-------|------------|-----------------------|
| Backend | `backend/` | Attivo | Tag `vX.Y.Z` (SemVer) | API GraphQL (FastAPI + Strawberry), integrazioni nutrizione, caching, enrichment |
| Mobile (Flutter) | `mobile/` | Bootstrap creato | Tag `mobile-vX.Y.Z` | App Flutter consumer GraphQL + offline queue + UI nutrizionale |
| Web Sandbox (React) | `web/` | Bootstrap creato | Tag `web-vX.Y.Z` | Sandbox debug schema, test query/mutation, analisi recommendation |
| Schema Condiviso | `backend/graphql/schema.graphql` (fonte) + `graphql/schema.graphql` (mirror) | Mirror iniziale | Allineato a release backend | Contratto GraphQL centrale consumato da Mobile & Web |

Note operative:
* Il **backend** è già operativo (vedi `backend/README.md` per dettagli completi: endpoints, make targets, release flow).
* Le cartelle `mobile/` e `web/` verranno create nelle prossime milestone; attualmente alcuni file radice (`pubspec.yaml`, `package.json`) sono placeholder storici e saranno spostati.
* Lo schema GraphQL canonicale è esportato dal backend; in fase di standardizzazione potrà essere replicato in una cartella root `graphql/` con history di snapshot per diff automatizzati.
* Ogni PR che modifica il contratto dovrà includere: export aggiornato + nota (additive / breaking / deprecazione) documentata.

### 📦 Policy di Versioning Multi‑Componente

| Tipo Cambiamento | Backend | Mobile | Web | Azione Richiesta |
|------------------|---------|--------|-----|------------------|
| Additive (nuovo campo) | patch/minor | nessuna immediata | nessuna | Documentare in changelog backend |
| Field deprecated | minor | pianificare adeguamento | pianificare | Aggiungere avviso in docs schema |
| Breaking (rimozione/rename) | major | adattare prima del merge | adattare prima del merge | PR marcata `breaking`, sezione MIGRATION |

### 🔄 Distribuzione Schema
1. Backend esporta `schema.graphql` (target `schema-export`).
2. (Futuro) Workflow copia lo schema in `graphql/schema.graphql` (mirror) + genera artifact.
3. Mobile & Web fetch / diff (fallimento se breaking non annunciato).
4. Code generation (quando introdotta) si basa sul mirror versione taggato.

Nota evolutiva imminente:
* Verranno introdotti: argomento `idempotencyKey` in `logMeal` (opzionale) e campo `nutrientSnapshotJson` (opzionale) in `MealEntry` per stabilizzare il contratto prima della persistenza Postgres.

### 🛣 Prossimi Passi Monorepo
| Step | Descrizione | Priorità |
|------|-------------|----------|
| Creazione `mobile/` | Scaffold Flutter + script fetch schema | Alta |
| Creazione `web/` | Scaffold React/Vite + Apollo Client | Alta |
| Mirror schema root | Stabilire cartella `graphql/` + diff tool | Media |
| Workflow schema-diff | Azione GitHub diff & classification (additive/breaking) | Media |
| Commitlint per componente | Prefisso commit (`backend:`, `mobile:`, `web:`) | Media |
| Codegen (mobile) | ferry / graphql_flutter + fragments condivisi | Media |
| Sandbox query catalog | Collezione query e mutation di test | Medio |

---

## 📖 Documentazione Principale

| Documento | Link | Descrizione |
|-----------|------|-------------|
| Guida Nutrizione Estesa | [docs/nutrifit_nutrition_guide.md](docs/nutrifit_nutrition_guide.md) | Dominio, formule, UX dashboard, snapshot nutrienti |
| Architettura Mobile | [docs/mobile_architecture_plan.md](docs/mobile_architecture_plan.md) | Roadmap M0–M9, BOM, testing, performance |
| Architettura Backend | [docs/backend_architecture_plan.md](docs/backend_architettura_plan.md) | Roadmap B0–B9 (backend‑centric), SLO, data model |
| Policy Contratto Schema | [docs/schema_contract_policy.md](docs/schema_contract_policy.md) | Regole evoluzione schema, deprecation, label PR |
| Diff Semantico Schema | [docs/schema_diff.md](docs/schema_diff.md) | Classificazione aligned/additive/breaking, output JSON, roadmap |
| Contratto Ingestion Dati | (coming soon) [docs/data_ingestion_contract.md](docs/data_ingestion_contract.md) | Evento `logMeal`, idempotenza, validazioni |
| Sprint Plan | (coming soon) [docs/sprint_plan.md](docs/sprint_plan.md) | Sequenza milestone tecniche & deliverables |
| Pipeline AI Food Recognition | [docs/ai_food_pipeline_README.md](docs/ai_food_pipeline_README.md) | Flusso inference + enrichment futuro |
| Prompt AI Vision | [docs/ai_food_recognition_prompt.md](docs/ai_food_recognition_prompt.md) | Prompt primario e fallback GPT-4V |
| Changelog Versioni | [CHANGELOG.md](CHANGELOG.md) | Cronologia modifiche & release semver |

## 🏗 Architettura High-Level (Backend‑Centric)

```mermaid
graph TD
  subgraph Client
    A[Flutter Mobile App]
    W[Web Sandbox (React)]
  end
  A -->|HTTPS GraphQL| B[Backend API (FastAPI + Strawberry)]
  W -->|HTTPS GraphQL| B
  B --> OFF[(OpenFoodFacts API)]
  B --> R[Robotoff (future enrichment)]
  B --> VAI[Vision AI Pipeline (future)]
  B --> DB[(Persistence / Nutrient Snapshots)]
  A --> Local[Offline Queue / Local Cache]
```

Caratteristiche chiave del modello backend‑centric:

1. ASTRAZIONE DATI: tutte le sorgenti esterne (OFF oggi, Robotoff, AI proprietaria domani) vengono normalizzate lato server → contratto GraphQL stabile per i client.
2. CONSISTENZA NUTRIENTI: il backend produce uno snapshot immutabile dei nutrienti al momento del log per evitare drift se l'origine cambia.
3. EVOLUZIONE SICURA: nuove capability (es. enrichment AI, ranking prodotti) si aggiungono dietro lo stesso endpoint senza aggiornare simultaneamente tutti i client.
4. PERFORMANCE: caching & TTL barcode lato server → riduzione latenza e consumo batteria.
5. OSSERVABILITÀ: metriche di hit/miss cache, errori OFF e tempi medio risposta centralizzati.

La precedente ipotesi di federazione multi‑subgraph è rimandata; verrà rivalutata quando il dominio crescerà (es. micro‑team dedicati o carichi eterogenei).

---

## ⚡ Dynamic Recommendations

Il motore di raccomandazioni elabora in tempo quasi reale i trend nutrizionali e di attività per suggerire micro-azioni contestuali (es: spike zuccheri → cardio leggero, proteine basse → snack proteico, budget cena disponibile). Basato su:

| Input | Fonte | Frequenza |
|-------|-------|-----------|
| Meal log | `meal_entry` snapshot | Evento (mutation) |
| Activity minute | `activity_event_minute` | Batch 1–5 min |
| Rolling baselines | `rolling_intake_window` | Job giornaliero |

Trigger iniziali (MVP evolutivo): `SUGAR_SPIKE`, `LOW_PROTEIN_PROGRESS`, `HIGH_CARB_LOW_ACTIVITY`, `EVENING_CALORIE_BUDGET`, `POST_ACTIVITY_LOW_PROTEIN`, `DEFICIT_ADHERENCE`.

Ogni raccomandazione è persistita (`recommendations`) con payload diagnostico e pubblicabile via subscription (`recommendationIssued`). Dettagli completi in `docs/recommendation_engine.md`.

---

---

## ✅ Feature Matrix

| Area | MVP | v1 | v1.2 | Futuro |
|------|-----|----|------|--------|
| Logging Manuale | ✔ | ✔ | ✔ | Refinements |
| Barcode | ✔ | ✔ | ✔ | Cache avanzata |
| Foto AI | ✖ | ✔ (baseline) | ✔ (autofill) | Segmentazione on-device |
| Dashboard Giornaliera | ✔ | ✔ | ✔ | Custom layout |
| Storico Settimanale | ✖ | ✔ | ✔ | Analisi avanzate |
| Notifiche | ✖ | ✔ base | ✔ smart | Rule engine evoluto |
| Adattamento Piano | ✖ | ✖ | ✔ | ML personalization |
| Web Dashboard | ✖ | ✖ | ✔ | Admin / Analitiche |

Legenda: ✔ disponibile · ✖ non ancora · (noti) evoluzioni.

---

## 📈 Roadmap & Progress

```text
Mobile   M0 ████░░░░ (20%)   → M1 → M2 → M3 ...
Backend  B0 ████░░░░ (20%)   → B1 → B2 → B3 ...
AI       POC ███░░░░ (15%)   → Baseline → Autofill
```

Dettagli granulari nelle rispettive roadmap dei documenti.

---

## 🗂 Struttura Repository (Estratto)

nutrifit_nutrition_guide.md  # Stub redirect

```text
docs/                # Documentazione architettura & guide
lib/
  graphql/           # Schema, fragments, queries
  services/          # Servizi (es. food_recognition_service.dart)
  ... (future features)
```

---

## 🔄 Workflow CI/CD

Planned:

- GitHub Actions: lint, analyze, schema diff, unit tests.
- Codemagic: build store (iOS/Android) + distribuzione canali.
- Backend: build Docker microservizi + deploy Render (rolling / canary AI service).

TODO: aggiungere workflow YAML (lint + schema snapshot) in `/ .github/workflows`.

### Workflow Schema Diff (Nuovo)

Il workflow `schema-diff` (pull_request) verifica che il mirror `graphql/schema.graphql` sia sincronizzato rispetto alla fonte `backend/graphql/schema.graphql`.

Pipeline attuale (baseline):
1. Confronto file (`diff -u`).
2. Classificazione placeholder (`aligned` / `needs-review`).
3. Fallisce la PR se il backend è cambiato senza aggiornare il mirror.

Estensioni pianificate:
| Fase | Miglioria | Stato |
|------|-----------|-------|
| 1 | Analisi semantica script `verify_schema_breaking.py` | TODO |
| 2 | Classificazione additive / deprecation / breaking | TODO |
| 3 | Commento automatico PR con elenco cambi | TODO |
| 4 | Badge freshness (hash schema) in README | TODO |
| 5 | Exit codes granulari (needs-review/breaking) | TODO |

Workflows placeholder ancora presenti verranno rimossi o completati: `backend-preflight.yml`, `backend-changelog.yml`, `backend-github-release.yml`, `backend-schema-status.yml`.

Inviare PR schema: eseguire `make schema-export` nel backend, aggiornare mirror (`scripts/sync_schema_from_backend.sh`), commit e aprire PR.

### 🔍 Semantic GraphQL Schema Diff (Sintesi)

Per i dettagli completi ora utilizzare `docs/schema_diff.md`. Di seguito la sintesi operativa:

```bash
cd backend
uv run python scripts/verify_schema_breaking.py | jq
```

Categorie: `aligned`, `additive`, `breaking`. Exit code 1 solo in caso di `breaking`.

---

## 🛠 Utility Schema
Strumenti per sincronizzazione e verifica contratto GraphQL.

| Script | Path | Scopo |
|--------|------|-------|
| Export SDL | `backend/scripts/export_schema.py` | Genera `backend/graphql/schema.graphql` dal runtime Strawberry |
| Sync Mirror (bash) | `scripts/sync_schema_from_backend.sh` | Copia SDL backend nel mirror root `graphql/` |
| Sync Mirror (py) | `scripts/sync_schema_from_backend.py` | Variante Python al Bash sync |
| Calcolo Hash | `scripts/schema_hash.sh` | Produce hash per badge freshness (future) |
| Diff Semantico | `backend/scripts/verify_schema_breaking.py` | Classifica aligned/additive/breaking |

Esecuzione rapida:
```bash
cd backend
uv run python scripts/export_schema.py
cd ..
./scripts/sync_schema_from_backend.sh
cd backend
uv run python scripts/verify_schema_breaking.py | jq
```

---

## 🤖 Workflow CI Attivi (Estratto)
| Workflow | File | Funzione Sintetica |
|----------|------|--------------------|
| Backend CI | `.github/workflows/backend-ci.yml` | Lint, type-check, test, export schema |
| Schema Diff | `.github/workflows/schema-diff.yml` | (Planned) Verifica drift e classificazione semantica |
| Release Backend | `.github/workflows/backend-github-release.yml` | Tag + pubblicazione release backend |
| Changelog Backend | `.github/workflows/backend-changelog.yml` | Generazione changelog automatizzata |
| Version Badge Update | `.github/workflows/update-backend-version-badge.yml` | Aggiornamento badge versione |
| Commitlint | `.github/workflows/commitlint.yml` | Validazione messaggi commit |