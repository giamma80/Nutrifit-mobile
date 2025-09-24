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
 <img src="https://img.shields.io/badge/backend_version-0.2.4-green" alt="Backend Version" />
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
8. [Governance & Release Flow](#-governance--release-flow)
9. [Deploy su Render](#-deploy-su-render)
10. [Workflow CI/CD](#-workflow-cicd)
11. [Contributi](#-contributi)
12. [Nerd Corner](#-nerd-corner)
13. [Licenza](#-licenza)

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

Nota evolutiva imminente / stato attuale:
* Runtime slice oggi: `product`, `logMeal`, `mealEntries`, `dailySummary` (versione minimale con calorie/protein placeholder).
* Introdotto: campo `nutrientSnapshotJson` (snapshot nutrizionale opzionale). In arrivo: `idempotencyKey` obbligatorio e arricchimento macro avanzato nel `dailySummary`.

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
| Documentare dailySummary | Esempi e campi futuri (target B3) | Alta |

---

## 📖 Documentazione Principale

| Documento | Link | Descrizione |
|-----------|------|-------------|
| Guida Nutrizione Estesa | [docs/nutrifit_nutrition_guide.md](docs/nutrifit_nutrition_guide.md) | Dominio, formule, UX dashboard, snapshot nutrienti |
| Architettura Mobile | [docs/mobile_architecture_plan.md](docs/mobile_architecture_plan.md) | Roadmap M0–M9, BOM, testing, performance |
| Architettura Backend | [docs/backend_architecture_plan.md](docs/backend_architecture_plan.md) | Roadmap B0–B9 (backend‑centric), SLO, data model |
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

## 🧭 Governance & Release Flow

Il backend adotta un flusso di release centralizzato tramite `backend/make.sh` e versionamento SemVer taggato (`vX.Y.Z`).

| Fase | Comando | Dettaglio |
|------|---------|-----------|
| Preflight | `./make.sh preflight` | format + lint + test + schema-check + commitlint + markdownlint (strict) |
| Guard versione | `./make.sh version-guard` | Impedisce modifiche non autorizzate a `pyproject.toml` |
| Changelog | `./make.sh changelog` | Genera/aggiorna CHANGELOG (conventional commits) |
| Release interattiva | `./make.sh release` | finalize changelog + bump + tag + push |
| Release CI | `./make.sh release-ci` | Non-interattivo (LEVEL=patch/minor/major) per pipeline |
| Release + Deploy | `./make.sh release-deploy` | Release + aggiornamento `APP_VERSION` in `render.yaml` |
| Utilities | `version-show`, `version-bump`, `version-verify` | Strumenti puntuali |

Regole version_guard_logic:
1. Branch feature: vietato cambiare la versione rispetto a merge-base `origin/main`.
2. Branch main: la versione deve avere un tag corrispondente (`vX.Y.Z`).
3. Solo i target di release generano bump + tag.

Esempio release con deploy blueprint:
```bash
cd backend
LEVEL=patch ./make.sh release-deploy
```

### Setup locale rapido (Backend)
Usare sempre `uv` (no pip/poetry):
```bash
cd backend
uv sync                  # installa dipendenze
./make.sh preflight      # lint+test+schema (usa interprete venv attivato dallo script)
./make.sh schema-export  # rigenera SDL runtime
```

Script ausiliario: `backend/scripts/update_app_version_in_render.py` aggiorna `APP_VERSION` nel blueprint.

---

## 🚀 Deploy su Render

Blueprint root: `render.yaml` definisce il servizio `nutrifit-backend-api` (runtime Docker).

Caratteristiche:
* Porta 8000 (healthcheck `/health`).
* Variabili sensibili NON versionate (impostare da dashboard Render).
* Build trigger su modifiche a `backend/**` o al blueprint stesso.
* `APP_VERSION` aggiornato in release-deploy per tracciabilità.

Validazione locale immagine prima del deploy:
```bash
cd backend
docker build -t nutrifit-backend:local --build-arg APP_VERSION=$(./make.sh version-show) .
docker run -p 8000:8000 nutrifit-backend:local
curl -f http://localhost:8000/health
curl -s http://localhost:8000/version
```

Roadmap deploy:
| Evoluzione | Descrizione |
|-----------|-------------|
| Multi-servizi | Aggiunta gateway GraphQL e worker AI |
| Redis opzionale | Cache condivisa per future features |
| Preview PR | Ambienti ephemeral per feature branch |
| Build esterna | Build immagine via CI + deploy da registry |

---

---

## 🔄 Workflow CI/CD

Workflow unificato backend: `.github/workflows/backend-ci.yml` con jobs:

| Job | Scopo |
|-----|-------|
| changes | Path filter: determina se eseguire build docker/integration |
| preflight | Esegue target preflight completo (format, lint, test, schema, markdownlint) |
| docker-integration | Build immagine + run container + test integrazione (GraphQL/health/version) |
| maintenance | Aggiorna changelog + badge schema + versione (solo push main) |

Altri workflow attivi:
* `schema-diff.yml` – verifica drift/mirror schema (estensioni semantiche future).
* `backend-changelog.yml` – aggiornamento changelog opzionale.
* `update-backend-version-badge.yml` – sincronizza badge versione README.
* `release.yml` – orchestrazione release (dispatch) se abilitato.

La precedente frammentazione (preflight separato, schema-status) è stata consolidata.

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

### 🔁 Comportamento Avanzato `schema-sync`

Il target `schema-sync` ora emette un JSON arricchito con il campo booleano `mirror_only_aligned`:

```jsonc
{
  "status": "updated",            // "updated" se almeno un file è stato modificato, altrimenti "unchanged"
  "backend_before": "<hash>",
  "backend_after":  "<hash>",
  "mirror_before":  "<hash>",
  "mirror_after":   "<hash>",
  "hash_export":    "<hash_export_runtime>",
  "mirror_only_aligned": 1,        // 1 se è stato necessario riallineare SOLO il mirror (contenuto identico all'export già presente nel backend)
  "dry_run": 0
}
```

Caso d'uso: a volte il file canonico backend è già aggiornato ma il mirror root diverge (es. differenze newline / whitespace). Prima questo stato non veniva corretto (status restava `unchanged`); ora `schema-sync` forza l'allineamento del mirror e segnala l'evento con `mirror_only_aligned=1` mantenendo `status:"updated"` per rendere evidente la mutazione.

Implicazioni CI:
* `schema-check` in DRY RUN fallisce se `status == updated` (quindi includendo i riallineamenti del solo mirror) evitando drift silenzioso.
* Gli sviluppatori devono committare il mirror riallineato prima del merge.

Nota: il guard (`scripts/schema_guard.py`) continuerà a fallire (exit 4) se i due file differiscono anche solo per whitespace finale.

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
| Schema Diff | `.github/workflows/schema-diff.yml` | Verifica drift e classificazione semantica (additive/breaking) |
| Release Backend | `.github/workflows/backend-github-release.yml` | Tag + pubblicazione release backend |
| Changelog Backend | `.github/workflows/backend-changelog.yml` | Generazione changelog automatizzata |
| Version Badge Update | `.github/workflows/update-backend-version-badge.yml` | Aggiornamento badge versione |
| Commitlint | `.github/workflows/commitlint.yml` | Validazione messaggi commit |

---

## 🤝 Contributi

1. Fork / branch naming: `feature/<slug>` o `fix/<slug>`
2. PR checklist:
  - [ ] Tests pass
  - [ ] Schema GraphQL invariato (o snapshot aggiornato con nota breaking)
  - [ ] Docs aggiornate se necessario
3. Event naming: snake_case, no payload ridondante.

---

## 🧪 Quality Gates (Target)

| Gate | Strumento | Esito Richiesto |
|------|-----------|-----------------|
| Lint | `flutter analyze` | 0 errori |
| Test | `flutter test` | ≥90% critical logic |
| Contract | schema diff | nessun breaking non documentato |
| Performance | dashboard frame time | <16ms frame hot path |

---

## 🧠 Nerd Corner
>
> “All models are wrong, some are useful.” — G.E.P. Box

Snippet pseudo-calcolo adattamento calorie:

```text
delta_pct = clamp((trend_weight - expected)/expected, -0.15, 0.15)
new_cal = round_to_50(old_cal * (1 - delta_pct))
```

Easter Egg Roadmap: quando AI autofill >70% adoption → attivare modalità "Hyper Logging" (UI minimalista).

---

## 🔎 Esempi Query Runtime (Snapshot Attuale)

### Log Meal
```graphql
mutation {
  logMeal(input:{name:"Oatmeal", quantityG:150, timestamp:"2025-09-24T08:15:00Z"}) {
    id
    name
    quantityG
    timestamp
  }
}
```

### Lista Pasti (mealEntries)
```graphql
{
  mealEntries(limit: 5, after: "2025-09-24T00:00:00Z") {
    id
    name
    quantityG
    timestamp
  }
}
```

### Riepilogo Giornaliero (dailySummary)
```graphql
{
  dailySummary(date: "2025-09-24") {
    date
    userId
    meals
    calories
    protein
  }
}
```

Nota: `calories` e `protein` sono placeholder calcolati in modo minimale; verranno sostituiti da aggregazioni nutrienti reali quando introdotti gli snapshot + enrichment completo.

---

## 🗒 Changelog

Vedi [CHANGELOG.md](CHANGELOG.md). Release corrente backend: `v0.2.3` (cockpit script, logging, bump tooling aggiornati).

Quick check versione backend da root (senza entrare in `backend/`):

```bash
cd backend && ./make.sh version-show
```

Altri comandi utili backend:

```bash
./make.sh version-verify   # controlla match tag HEAD vs pyproject
./make.sh schema-export    # genera/aggiorna SDL GraphQL
./make.sh schema-check     # verifica che lo schema versionato sia aggiornato
```

Suggerimento: per utenti junior basta ricordare la sequenza:

```bash
cd backend
make setup   # o ./make.sh setup
make run     # avvia server
make preflight   # prima di fare commit/push
```

Il badge `backend_version` è aggiornato da `update-backend-version-badge.yml` oppure tramite `release-deploy`.

## 📝 Licenza

Da definire. (Per ora nessuna licenza pubblicata; evitare uso in produzione esterna.)

---

## 🧭 Navigazione Rapida

| Se vuoi... | Vai a |
|------------|-------|
| Capire il dominio nutrizionale | [Guida Nutrizione](docs/nutrifit_nutrition_guide.md) |
| Vedere pipeline AI cibo | [Pipeline AI](docs/ai_food_pipeline_README.md) |
| Leggere roadmap mobile | [Arch Mobile](docs/mobile_architecture_plan.md) |
| Leggere roadmap backend | [Arch Backend](docs/backend_architecture_plan.md) |
| Modificare prompt GPT-4V | [Prompt AI](docs/ai_food_recognition_prompt.md) |
