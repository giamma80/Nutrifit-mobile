#   Backend

![Build Backend](https://github.com/giamma80/Nutrifit-mobile/actions/workflows/backend-ci.yml/badge.svg)
![Schema Status](https://img.shields.io/badge/schema-aligned-brightgreen?label=GraphQL%20SDL)
![Release](https://github.com/giamma80/Nutrifit-mobile/actions/workflows/release.yml/badge.svg)

##   Endpoints

- `GET /health`
- `GET /version`
- `POST /graphql`
  - Query:
    - `hello`
    - `serverTime`
    - `health`
    - `product(barcode: String!)`
    - `mealEntries(limit: Int = 20, after: String, before: String, userId: String): [MealEntry!]!`
    - `dailySummary(date: String!, userId: String): DailySummary!`
    - `activityEntries(limit: Int = 100, after: String, before: String, userId: String): [ActivityEvent!]!` (diagnostica minute events)
    - `syncEntries(date: String!, userId: String, after: String, limit: Int = 200): [HealthTotalsDelta!]!` (delta health totals per giorno)
    - `cacheStats: CacheStats!`
  - Mutation:
    - `logMeal(input: LogMealInput!): MealEntry!`
    - `updateMeal(input: UpdateMealInput!): MealEntry!`
    - `deleteMeal(id: String!): Boolean!`
    - `ingestActivityEvents(input: [ActivityMinuteInput!]!, idempotencyKey: String, userId: String): IngestActivityResult!`
    - `syncHealthTotals(input: HealthTotalsInput!, idempotencyKey: String, userId: String): SyncHealthTotalsResult!`

##   Tipi GraphQL Principali

```graphql
# Estratto sintetico (schema runtime attuale – vedere `backend/graphql/schema.graphql` per versione completa)

type Product { barcode name brand category calories protein carbs fat fiber sugar sodium }

type MealEntry {
  id: ID!
  userId: String!
  name: String!
  quantityG: Float!
  timestamp: String!
  barcode: String
  idempotencyKey: String
  nutrientSnapshotJson: String
  calories: Int
  protein: Float
  carbs: Float
  fat: Float
  fiber: Float
  sugar: Float
  sodium: Float
}

input LogMealInput { name: String! quantityG: Float! timestamp: String barcode: String idempotencyKey: String userId: String }
input UpdateMealInput { id: String! name: String quantityG: Float timestamp: String barcode: String userId: String }

type ActivityEvent { userId: String! ts: String! steps: Int caloriesOut: Float hrAvg: Float source: ActivitySource! }
input ActivityMinuteInput { ts: String! steps: Int=0 caloriesOut: Float hrAvg: Float hrAvg: Float source: ActivitySource! = MANUAL }
enum ActivitySource { APPLE_HEALTH GOOGLE_FIT MANUAL }

input HealthTotalsInput { timestamp: String! date: String! steps: Int! caloriesOut: Float! hrAvgSession: Float userId: String }
type HealthTotalsDelta {
  id: String!
  userId: String!
  date: String!
  timestamp: String!
  stepsDelta: Int!
  caloriesOutDelta: Float!
  stepsTotal: Int!
  caloriesOutTotal: Float!
  hrAvgSession: Float
}
type SyncHealthTotalsResult {
  accepted: Boolean!
  duplicate: Boolean!
  reset: Boolean!
  idempotencyKeyUsed: String
  idempotencyConflict: Boolean!
  delta: HealthTotalsDelta
}

type DailySummary {
  date: String!
  userId: String!
  meals: Int!
  calories: Int!
  protein: Float
  carbs: Float
  fat: Float
  fiber: Float
  sugar: Float
  sodium: Float
  activitySteps: Int!
  activityCaloriesOut: Float!
  activityEvents: Int!          # solo diagnostico (minute events ingestati)
  caloriesDeficit: Int!
  caloriesReplenishedPercent: Int!
}

type Query {
  product(barcode: String!): Product
  mealEntries(limit: Int=20, after: String, before: String, userId: String): [MealEntry!]!
  dailySummary(date: String!, userId: String): DailySummary!
  activityEntries(limit: Int=100, after: String, before: String, userId: String): [ActivityEvent!]!
  syncEntries(date: String!, userId: String, after: String, limit: Int=200): [HealthTotalsDelta!]!
  cacheStats: CacheStats!
}

type Mutation {
  logMeal(input: LogMealInput!): MealEntry!
  updateMeal(input: UpdateMealInput!): MealEntry!
  deleteMeal(id: String!): Boolean!
  ingestActivityEvents(input: [ActivityMinuteInput!]!, idempotencyKey: String, userId: String): IngestActivityResult!
  syncHealthTotals(input: HealthTotalsInput!, idempotencyKey: String, userId: String): SyncHealthTotalsResult!
}
```

###   Esempi Query / Mutation

Fetch prodotto (cache TTL di default 10 minuti):

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"query":"{ product(barcode: \"8000500310427\") { name calories protein } }"}' \
  http://localhost:8080/graphql | jq
```

Log di un pasto senza barcode:

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"query":"mutation { logMeal(input:{name: \"Mela\", quantityG:150}) { id name quantityG calories } }"}' \
  http://localhost:8080/graphql | jq
```

Log con enrichment nutrienti via barcode (scaling per quantità /100g):

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"query":"mutation { logMeal(input:{name: \"Bar\", quantityG:50, barcode: \"123456\"}) { id name quantityG calories protein } }"}' \
  http://localhost:8080/graphql | jq
```

Daily summary (con nuovi campi energetici):

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"query":"{ dailySummary(date: \"2025-09-26\") { date meals calories activitySteps activityCaloriesOut caloriesDeficit caloriesReplenishedPercent } }"}' \
  http://localhost:8080/graphql | jq
```

Esempio risposta (valori indicativi):

```jsonc
{
  "data": {
    "dailySummary": {
      "date": "2025-09-26",
      "meals": 3,
      "calories": 1450,
      "activitySteps": 7200,
      "activityCaloriesOut": 510.5,
      "caloriesDeficit": -939,                // surplus (hai introdotto più di quanto speso)
      "caloriesReplenishedPercent": 284       // >100% indica surplus; clamp non attivato (<999)
    }
  }
}
```

Idempotenza: la chiave è calcolata così (se non fornisci `idempotencyKey` esplicito):

```
lower(name) | round(quantityG,3) | (timestamp se fornito al client altrimenti "") | barcode | userId
```

Note:

- Se NON passi `timestamp`, il server ne genera uno ma NON lo include nella chiave ⇒ due chiamate identiche senza timestamp condividono la stessa chiave (comportamento idempotente più robusto lato client).
- Se passi tu un `timestamp` allora entra nella chiave e due richieste con timestamp diversi producono record diversi.
- Puoi sempre passare un tuo `idempotencyKey` custom per controllare la deduplicazione.

Errori comuni:

- Quantità <= 0 → `INVALID_QUANTITY`
- Barcode non trovato → logMeal ignora enrichment ma registra comunque il pasto.

Nota camelCase: Strawberry (v0.211.1) converte automaticamente i campi (es.
`quantity_g` → `quantityG`). Usare sempre i nomi camelCase nelle richieste.

###   nutrientSnapshotJson (Snapshot Nutrienti)

Il campo `nutrientSnapshotJson` (se disponibile) contiene una stringa JSON con i nutrienti calcolati al momento del log, derivati dal prodotto (barcode) e scalati per `quantityG`:

```jsonc
{
  "calories": 180,
  "protein": 6.4,
  "carbs": 22.5,
  "fat": 5.1,
  "fiber": 3.2,
  "sugar": 12.0,
  "sodium": 150
}
```

Regole attuali:
1. Se il barcode è fornito e il prodotto viene trovato nella cache o via OpenFoodFacts → snapshot popolato.
2. Se il prodotto non è trovato o non è fornito `barcode` → snapshot `null` (verrà popolato in futuro da enrichment AI / risoluzione differita).
3. Il contenuto è stabile (immutabile); futuri cambi di nutrienti a sorgente non retro-modificano lo snapshot.
4. Serializzazione ordinata (`sort_keys=True`) per consentire confronti deterministici nei test futuri.

###   Idempotenza (Dettaglio Aggiornato)

Chiave generata (fallback) se non passi `idempotencyKey`:
```
lower(name) | round(quantityG,3) | (timestamp se fornito) | barcode | userId
```
Differenze chiave rispetto al passato: se il timestamp NON è fornito dal client non viene incluso → due chiamate identiche senza timestamp condividono la chiave (evita duplicati accidentali quando il client non genera un timestamp deterministico).
Se passi un `idempotencyKey` esplicito, qualunque differenza nel payload (es. quantity) viene ignorata e il primo record rimane autorevole.

###   Attività: Minute Ingestion vs Health Totals Sync

La piattaforma espone DUE modalità complementari:

1. `ingestActivityEvents` (batch minute events) – scopo diagnostico / granularità timeline
2. `syncHealthTotals` (snapshot cumulativi) – fonte AUTORITATIVA per i totali di `dailySummary`

Razionale migrazione: i provider OS espongono contatori cumulativi affidabili; ricostruire i totali da minute events soffre di drift (eventi mancanti, ordine, duplicati). Per questo i campi `activitySteps` e `activityCaloriesOut` ora sommano i delta derivati dai snapshot registrati (HealthTotalsRepository).

Tabella confronto rapida:

| Caratteristica | ingestActivityEvents | syncHealthTotals |
|----------------|----------------------|------------------|
| Fonte Totali dailySummary | (DEPRECATA) | ✅ primaria |
| Idempotenza | Firma batch SHA256 eventi normalizzati | Chiave esplicita o firma (date|steps|caloriesOut|user) |
| Duplicate detection | Per evento minuto identico | Snapshot identico (stessi contatori) |
| Conflict semantic | Evento minuto diverso stesso minuto → rejected | Stessa chiave diversa payload → `idempotencyConflict=true` |
| Reset handling | N/A (eventi monotoni richiesti) | `reset=true` se contatori scendono |
| Uso consigliato | Debug / timeline dettagliata | Totali affidabili / recupero dopo offline |

Edge cases sync:
* Primo snapshot giorno: delta = snapshot
* Duplicate: nessun nuovo delta, `duplicate=true`
* Reset (contatori diminuiscono): delta = snapshot, `reset=true`
* Conflitto chiave: nessun delta, `idempotencyConflict=true`

NOTA: `activityEvents` nel `DailySummary` rimane il conteggio degli eventi minuto ingestati (diagnostica), non più correlato ai totali.

Guida completa (algoritmo, state machine, edge cases estesi): vedi `docs/health_totals_sync.md` dalla root oppure [../../docs/health_totals_sync.md](../../docs/health_totals_sync.md).

La mutation (forma sintetica):

```graphql
mutation {
  ingestActivityEvents(
    userId: "u1"
    idempotencyKey: String
    input: [ActivityEventInput!]!
  ): ActivityIngestResult!
}
```

Concetti chiave:
1. Normalizzazione minuto: tutti i timestamp vengono ridotti al minuto (secondi/millisecondi ignorati) per definire un bucket logico.
2. Firma batch: eventi (normalizzati) vengono ordinati e serializzati in modo deterministico → SHA256 → primi 16 char → `auto-<hash>` se non fornisci `idempotencyKey`.
3. Replay idempotente: stesso batch (stesso set eventi dopo normalizzazione) → stessa chiave auto e stesso risultato (accepted/duplicates/rejected) dal cache idempotency.
4. Mutazione batch: se cambi anche un solo campo di un evento, la firma cambia → nuova chiave auto generata.
5. Conflitti: se un evento punta ad un minuto già esistente con dati diversi (es. `steps` diverso) viene rifiutato con `reason = CONFLICT_DIFFERENT_DATA` (NON è duplicate).
6. Duplicati: evento identico (stesso minuto + stessi dati) già persistito → conteggiato in `duplicates`.

Esempio evolutivo (semplificato):

1. Primo batch (10 passi @ 07:00, 5 passi @ 07:01) → `accepted=2`, `duplicates=0`, `rejected=[]`, chiave `auto-aaaa...`.
2. Secondo batch identico → stessa chiave `auto-aaaa...`, risultato identico via cache (replay idempotente, non reinserisce dati).
3. Terzo batch modifica passi del primo evento a 11 → nuova chiave `auto-bbbb...`, `accepted=0`, `duplicates=1` (secondo evento identico), `rejected=[CONFLICT_DIFFERENT_DATA]` per il primo evento.

Motivazione: mantenere evento minuto immutabile dopo la prima accettazione, separando chiaramente (a) retry identici (cache) da (b) tentativi di modifica (conflitto esplicito) evitando overwrite silenziosi.

Suggerimenti client:
- Consolidare i conteggi per minuto prima di inviare il batch.
- Evitare di usare la mutation come meccanismo di update: introdurre in futuro un endpoint di correzione esplicito.
- Loggare la chiave `idempotencyKeyUsed` per correlare eventuali retry.

Codici `reason` principali (parziale): `CONFLICT_DIFFERENT_DATA`, `NEGATIVE_VALUE`.



###   DailySummary – Calorie Deficit, Percentuale Refill & Fonte Attività

Nuovi campi (additivi, retro‑compatibili):

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `caloriesDeficit` | `Int!` | `activityCaloriesOut - calories`. Valore > 0 indica ancora deficit (non hai reintegrato tutte le calorie consumate). Valore < 0 indica surplus (hai introdotto più calorie di quante ne hai speso). |
| `caloriesReplenishedPercent` | `Int!` | Percentuale (approssimata a intero) di calorie reintegrate: `(calories / activityCaloriesOut) * 100`. Se `activityCaloriesOut == 0` ⇒ 0. Clamp massimo 999 per evitare outlier estremi (es. errori di import). Può superare 100 in caso di surplus. |

Formula e logica:
```
caloriesDeficit = activityCaloriesOut - calories
if activityCaloriesOut <= 0:
  caloriesReplenishedPercent = 0
else:
  pct = round((calories / activityCaloriesOut) * 100)
  caloriesReplenishedPercent = min(max(pct, 0), 999)
```

Esempi rapidi:
```
activityCaloriesOut=500, calories=400  -> deficit=100,  percent=80
activityCaloriesOut=500, calories=500  -> deficit=0,    percent=100
activityCaloriesOut=500, calories=650  -> deficit=-150, percent=130 (surplus)
activityCaloriesOut=200, calories=1200 -> deficit=-1000,percent=600 (<999 nessun clamp)
activityCaloriesOut=50,  calories=6000 -> raw percent=12000 -> clamp a 999
```

Uso suggerito lato client:
* Evidenziare `caloriesDeficit > 0` come progress bar verso 0 (target di refill energetico).
* `caloriesDeficit == 0`: stato “neutral” (equilibrio energetico giornaliero).
* `caloriesDeficit < 0`: segnalare surplus (badge o colore differente) senza considerarlo errore.
* `caloriesReplenishedPercent == 999`: mostrare indicatore di valore fuori scala (es. `> 999%`).

Fonte attività attuale:
* `activitySteps` = somma `stepsDelta` dei delta health totals del giorno
* `activityCaloriesOut` = somma `caloriesOutDelta`
* Se nessun snapshot inviato → entrambi 0 (anche se minute events esistono)

Backward compatibility: i client precedenti che non richiedono i nuovi campi non subiscono rotture (schema solo esteso). Tuttavia per vedere valori attività > 0 devono implementare la chiamata `syncHealthTotals`.

###   Stato attuale vs Schema Draft (Aggiornato)

Il file `docs/graphql_schema_draft.md` contiene una versione estesa per milestone future. Stato implementazione runtime aggiornato:

| Funzione Draft | Stato Runtime | Note |
|----------------|--------------|------|
| `product` | ✅ | Fetch + cache TTL |
| `logMeal` | ✅ | Idempotenza fallback + snapshot nutrienti |
| `updateMeal` | ✅ | Ricalcolo nutrienti se cambia barcode/quantity |
| `deleteMeal` | ✅ | Rimozione entry (ritorna Boolean) |
| `mealEntries` | ✅ | Lista semplice + cursori after/before |
| `dailySummary` | ✅ | Usa delta health totals + calorie balance |
| `ingestActivityEvents` | ✅ | Minute events diagnostici (non più fonte totali) |
| `syncHealthTotals` | ✅ | Fonte primaria totali passi / calorie out |
| `activityTimeline` | ❌ | Pianificato (deriverà da minute events) |
| `recommendations` | ❌ | Engine non ancora attivo |
| Subscriptions | ❌ | Milestone B6 |

---

##   Esempi Rapidi

```bash
./make.sh docker-build
./make.sh docker-run
./make.sh docker-test
./make.sh docker-shell
./make.sh schema-export
./make.sh schema-check
```

##   Health & GraphQL

```bash
curl localhost:8080/health
curl -s -H 'Content-Type: application/json' -d '{"query":"{ health serverTime }"}' http://localhost:8080/graphql
```

##   CI

La pipeline `backend-ci` esegue: lint, type-check, test, export schema, build immagine (con ARG VERSION) e test di integrazione container.

---

##   Panoramica

Subgraph nutrizionale / AI minimale con gestione dipendenze tramite **uv** e deployment container-first.

> Shell compatibility: lo script `make.sh` è scritto per funzionare anche con la bash 3.2 di macOS (niente `${var,,}` ecc.). Colori disattivabili con `NO_COLOR=1`.

###   Endpoints (dettaglio)

- `GET /health` → `{status: ok}`
- `GET /version` → `{"version": "0.1.x"}`  (il valore reale è sincronizzato con `pyproject.toml` e il tag `v0.1.x`; evitare hardcode per ridurre aggiornamenti manuali)
- `POST /graphql` (via Strawberry) – Query disponibili:
  - `hello`: string di test
  - `server_time`: timestamp UTC
  - `health`: stato (placeholder per future verifiche interne)
  - `product(barcode: String!)`
  - Mutation: `logMeal`

##   Avvio locale

Prerequisiti: Python 3.11, [uv](https://github.com/astral-sh/uv) installato.

```bash
cd backend
uv sync --all-extras --dev
uv run uvicorn app:app --reload --port 8080
```

###   Cockpit (script `make.sh`)

> C'è anche un `Makefile`: puoi usare sia `./make.sh <target>` sia `make <target>` da `backend/`.

Tabella principali target:

| Target | Descrizione |
|--------|-------------|
| `setup` | Sync dipendenze (uv) |
| `run` | Avvia server in foreground |
| `run-bg` | Avvia server in background (PID salvato) |
| `stop` | Ferma server background |
| `format` | Esegue Black |
| `lint` | Flake8 + mypy |
| `test` | Pytest |
| `preflight` | format + lint + test + schema-check + commitlint (soft) |
| `commit MSG="..."` | Preflight + commit |
| `push` | Preflight + push ramo |
| `docker-build` | Build immagine locale dev (VERSION opzionale) |
| `docker-run` | Run container (porta 8080) |
| `docker-test` | Test integrazione container |
| `schema-export` | Esporta SDL GraphQL |
| `schema-check` | Verifica drift SDL |
| `version-show` | Mostra versione corrente |
| `version-bump LEVEL=patch` | Bump versione + tag |
| `version-verify` | Confronta pyproject vs tag HEAD |
| `release LEVEL=patch` | Preflight + finalize changelog + tag + push |
| `status` | Info rapide (server/container/versione) |
| `logs` | Tail file log locale |
| `clean` | Rimuove artefatti (venv, cache, pid) |
| `clean-dist` | Pulisce `dist/` |

Esempi rapidi:

```bash
# Setup iniziale
./make.sh setup

# Avvio server (hot reload)
./make.sh run

# Preflight completo prima di commit
./make.sh preflight

# Commit conventional + push
./make.sh commit MSG="feat(schema): add meal type"
./make.sh push

# Bump versione patch + release
./make.sh release LEVEL=patch

# Docker quick path
./make.sh docker-build && ./make.sh docker-run
./make.sh docker-test
```

###   Logging locale

La cartella `backend/logs/` contiene `server.log` se avvii in background:

```bash
./make.sh run-bg
./make.sh logs
./make.sh stop
```

I log sono ignorati da git. (Futuro: structlog JSON.)

###   Versioning

```bash
./make.sh version-show
./make.sh version-bump LEVEL=patch   # oppure minor / major
./make.sh version-verify
```

####   Version Verify (Workflow Tag)

Ogni push di un tag `vX.Y.Z` attiva il workflow GitHub Actions `Backend Version Verify` che:

1. Esegue il checkout del repository.
2. Estrae la versione dal tag (rimuovendo il prefisso `v`).
3. Legge il campo `version` in `backend/pyproject.toml`.
4. Fallisce se i due valori non coincidono.

Uso pratico:

```bash
./make.sh release LEVEL=patch   # genera tag vX.Y.(Z+1)
# push automatico esegue il workflow di verifica
```

Benefici: previene disallineamenti tra codice distribuito e metadati backend, riducendo sorprese in ambienti containerizzati / CI.

> Nota: il workflow GitHub Release richiede `permissions: contents: write`; è stato aggiunto per evitare l'errore 403 "Resource not accessible by integration".

###   Riferimento rapido target (categorie)

| Categoria | Target | Scopo sintetico |
|-----------|--------|-----------------|
| Base | setup | Installa/aggiorna dipendenze |
| Base | run / run-bg / stop / logs | Gestione server locale |
| Qualità | format / lint / test | Code style + static analysis + tests |
| GraphQL | schema-export / schema-check | Aggiorna e verifica SDL versionato (include campo health) |
| Preflight | preflight | Tutte le verifiche (incluso schema) |
| Versioning | version-show / version-verify / version-bump | Gestione versione semver |
| Release | release | Pipeline bump + tag + push |
| Git | commit / push | Helper con preflight automatico |
| Docker | docker-build / docker-run / docker-logs / docker-stop | Container locale |
| Utility | status / clean / clean-dist / all | Info e pulizia |

##   Avvio via Docker

Differenza rapida:

| Metodo | Comando | Caratteristiche |
|--------|---------|-----------------|
| Locale (uv) | `./make.sh run` / `uv run uvicorn ...` | Hot reload, dipendenze in `.venv` |
| Docker | `./make.sh docker-run` | Ambiente isolato immagine, no auto-reload (usa rebuild) |

Costruzione immagine (usa `uv` per risolvere dipendenze):

```bash
docker build -t nutrifit-backend:dev backend
docker run -p 8080:8080 nutrifit-backend:dev
```

Oppure via cockpit:

```bash
./make.sh docker-build
./make.sh docker-run
./make.sh docker-logs
./make.sh docker-test    # integrazione rapida
./make.sh docker-shell   # entra nel container
```

Health: `curl localhost:8080/health`  |  GraphQL health:

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"query":"{ health serverTime }"}' \
  http://localhost:8080/graphql
```

##   Strategia Deployment (Render)

1. Push su `main` → GitHub Actions (`backend-ci`) esegue lint, type-check, test, export schema e build Docker + integration test.
2. Render rileva il cambio della directory `backend/` e ricostruisce l'immagine usando il `Dockerfile`.
3. L'immagine avvia `uv run uvicorn app:app --host 0.0.0.0 --port 8080`.
4. (Futuro) Aggiunta variabili d'ambiente per configurazioni (es. SUPABASE_URL, FEATURE_FLAGS, ecc.).

Nessuna pubblicazione su registry esterno: pipeline repository → Render (repo sync).

Note:

- Packaging Python (wheel/sdist) non usato nel deploy → cartelle `egg-info` e `dist` ignorate.
- Commit governance: conventional commits validati da commitlint (workflow `commitlint.yml`).
- Le versioni sono mantenute in `pyproject.toml` e aggiornabili via `./make.sh version-bump`.
- Il check schema drift è incluso in `preflight` (`schema-check`). Se fallisce: `./make.sh schema-export` e commit.

##   Prossimi Step

- Integrare schema reale Nutrition (porting da file GraphQL)
- Implementare resolver `myNutritionPlan`
- Aggiungere Auth (JWT / API Key dev)
- Observability: logging strutturato + trace
- Rule Engine runtime (valutazione condizioni + throttle)
- Caching OpenFoodFacts (LRU + TTL)

##   Roadmap & Progress (Backend)

| Area | Stato Attuale | Prossimo Obiettivo | Note |
|------|---------------|--------------------|------|
| Core API (health/version) | ✅ | Estendere endpoints nutrizione | Base stabile |
| GraphQL Schema | 🟡 Minimal demo | Porting schema nutrition reale | Drift guard attivo (`schema-check`) |
| OpenFoodFacts Adapter | ✅ Prototype | Cache + normalizzazione avanzata | Integrazione futura in resolver |
| Rule Engine DSL | 🟡 Draft parser | Eseguire engine runtime | Dipende da eventi & notifiche |
| Logging | ✅ File semplice | Logging strutturato JSON | Collegare tracing successivamente |
| Versioning Tooling | ✅ bump/verify | Automazione changelog | Badge dinamico già attivo |
| Release Pipeline | 🟡 Manuale script | CI release gating | Agganciare workflow semver |
| Auth | ❌ | Token dev / API key | Necessario prima di features sensibili |
| Caching | ❌ | OFF basic caching | Riduce latenza / rate-limit risk |
| Observability | ❌ | Strutturare log | Aggiungere tracing & metrics |

Legenda: ✅ completato base · 🟡 in progresso/parziale · ❌ non avviato.

##   Changelog & Release Automation

Il file `CHANGELOG.md` (root repo) viene aggiornato automaticamente da uno script che raccoglie i commit in formato **Conventional Commits**.

###   Target `changelog`

Genera/aggiorna la sezione `[Unreleased]` raggruppando i commit dalla **ultima tag**:

```bash
./make.sh changelog         # aggiorna CHANGELOG.md (se cambia non committa)
DRY=1 ./make.sh changelog   # anteprima (stampa ma non scrive)
```

Regole parse: `type(scope): subject` dove `type` ∈ `feat|fix|docs|chore|refactor|perf|test|build|ci`.
Le categorie vengono mappate in sezioni: Added, Fixed, Changed, Performance, Docs, Tests, CI, Build, Chore, Other.

Idempotente: se una voce è già presente non viene duplicata.

###   Integrazione con `release`

Il target `release` ora effettua un ciclo completo con finalize automatico:

1. `preflight` (qualità + schema-check + commitlint)
2. Anteprima changelog (`DRY=1 ./make.sh changelog`) mostrata prima della conferma
3. Conferma utente
4. Finalizzazione: sposta il contenuto di `[Unreleased]` in una nuova sezione `## [vX.Y.Z] - YYYY-MM-DD`
5. Rigenerazione (se servisse) e bump versione (`pyproject.toml`)
6. Commit unico contenente `pyproject.toml` + `CHANGELOG.md`
7. Creazione tag `vX.Y.Z` e push (tag incluso)

Esempio release minor:

```bash
./make.sh release LEVEL=minor
```

Solo anteprima modifiche prima di rilasciare:

```bash
DRY=1 ./make.sh changelog
```

Sezione `[Unreleased]` rimane vuota (o pronta per i futuri commit) dopo il finalize.

Il workflow GitHub `backend-changelog.yml` continua ad aggiornare la parte `[Unreleased]` su push a `main` (evita drift locale → remoto).

##   Typing & Static Analysis Strategy

Adottiamo una strategia di typing incrementale ma portata a stato fully‑typed (0 errori mypy) con configurazione strict.

Principi:

- Tutte le nuove funzioni devono avere annotazioni (parametri + return). Nei test sempre `-> None` esplicito.
- Nessun uso di `type: ignore` salvo casi documentati; ignore rimossi appena non necessari.
- Preferenza per `dict[str, Any]` solo ai confini (I/O, parsing YAML/JSON); all'interno normalizzare in strutture tipizzate (dataclass / TypedDict) quando la stabilità del formato è consolidata.
- Evitare over-engineering: se un wrapper ha due key dinamiche non creare dataclass troppo rigide finché il dominio non si stabilizza.
- Uso di `GraphQLRouter[Any, Any]` come fallback generico per evitare warning di tipo finché non introduciamo un context tipizzato per i resolver.

Tooling:

- `./make.sh lint` esegue Flake8 + mypy (full project)
- `./make.sh typecheck` disponibile per solo static type pass (utile in CI o durante refactor massivi)
- Preflight (`./make.sh preflight`) include già mypy, quindi prima di ogni commit si garantisce lo zero-error.

Pattern adottati:

- Adapter esterni (es. OpenFoodFacts) trasformano input non tipizzato → `ProductDTO` (dataclass `slots=True`) con `NutrientsDict` (TypedDict opzionale) per i campi normalizzati; calcoli su numerici avvengono solo dopo guard non-null.
- Parser DSL (`rules/parser.py`) produce dataclass validate() con responsabilità chiara e insiemi per deduplicazione.
- Script di tooling (`scripts/generate_changelog.py`) tipizzato con ritorni espliciti e parsing commit robusto.

Futuro:

- Estendere uso TypedDict per porzioni di schema GraphQL se iniziamo a generare parte del codice dai resolver.
- Aggiungere plugin mypy (es. strawberry) se utile a validare schema vs resolver signatures.
- Integrare un badge di stato type-check (workflow dedicato) se la pipeline cresce.

Comandi rapidi:

```bash
./make.sh typecheck    # solo mypy
./make.sh lint         # lint + typecheck
./make.sh preflight    # full quality gate
```

##   Metrics & AI Meal Photo Adapters

###   Adapter Pattern

Pipeline analisi foto pasto (stato attuale):

1. `StubAdapter` (default) – restituisce sempre una lista fissa di item simulati.
2. `HeuristicAdapter` (abilitato con `AI_HEURISTIC_ENABLED=1`) – genera item pseudo‑deterministici a partire da hash di photoId / photoUrl.
3. `RemoteModelAdapter` (scheletro; abilitato con `AI_REMOTE_ENABLED=1`) – simula chiamata remota con latenza, jitter e timeout configurabili; in caso di timeout/failure (placeholder) ricade su heuristic o stub.

Se più flag sono attivi vale la precedenza: Remote > Heuristic > Stub.

###   Variabili d'Ambiente (Flag)

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `AI_HEURISTIC_ENABLED` | 0 | Abilita HeuristicAdapter |
| `AI_REMOTE_ENABLED` | 0 | Abilita RemoteModelAdapter |
| `REMOTE_TIMEOUT_MS` | 1200 | Timeout simulato remoto |
| `REMOTE_LATENCY_MS` | 900 | Latenza media simulata |
| `REMOTE_JITTER_MS` | 300 | Jitter massima additiva |
| `REMOTE_FAIL_RATE` | 0.0 | Probabilità simulata di failure (0–1) |

I flag vengono letti a ogni invocazione (`get_active_adapter()`), quindi i test possono modificarli a runtime senza ricostruire il modulo.

###   Metriche Disponibili

Tutte le metriche supportano il label opzionale `source` (adapter attivo) e, ove rilevante, `phase` o codici errore:

| Nome | Tipo | Labels | Significato |
|------|------|--------|-------------|
| `ai_meal_photo_requests_total` | counter | `phase`, `status`, `source?` | Conteggio invocazioni e outcome (completed/failed) |
| `ai_meal_photo_latency_ms` | histogram | `source?` | Latenza end‑to‑end per fase principale |
| `ai_meal_photo_fallback_total` | counter | `reason`, `source?` | (Futuro) conteggi fallback remoto → heuristic/stub |
| `ai_meal_photo_errors_total` | counter | `code`, `source?` | Errori granulari (singoli item) |
| `ai_meal_photo_failed_total` | counter | `code`, `source?` | Failure finale bloccante |

Per ora `phase == source` (unica fase). L'infrastruttura consente di introdurre sotto‑fasi (es. pre‑processing / model / post‑processing) senza cambiare il contratto esistente.

###   Timing e Conteggio

Il context manager `time_analysis(phase, source=...)` incapsula:

1. Start timer (perf_counter)
2. Esecuzione adapter
3. Incremento `requests_total{status=...}` (completed se nessuna eccezione)
4. Osservazione latenza sull'histogram

In caso di eccezione: `status=failed` e l'eccezione è rilanciata.

###   Reset Metriche nei Test

File `tests/conftest.py` definisce fixture autouse `metrics_reset` che invoca `metrics.ai_meal_photo.reset_all()` prima e dopo ogni test per garantire isolamento (evitare dipendenza dall'ordine dei test). Questo ha permesso di eliminare chiamate manuali a `reset_all()` dentro i singoli test.

###   Idempotenza Analisi

Chiave auto‑generata: `auto-<sha256(user|photoId|photoUrl)[:16]>` se non viene passato `idempotency_key` esplicito. Un'analisi identica (stessi parametri) ritorna il record esistente senza ricrearlo / ricontare metriche.

###   Fallback (Roadmap)

Il `RemoteModelAdapter` in futuro registrerà:

* `ai_meal_photo_fallback_total{reason=timeout|error,source=remote}` quando ricade su heuristic/stub.
* Etichette distinte di fase (`remote_call`, `heuristic_fallback`) se introdurremo multi‑fase.

###   Estensioni Future

* Circuit breaker per fallimenti remoti
* Cache risultati per photo hash
* Persistenza store analisi (oggi in‑memory)
* Arricchimento nutrizionale derivato da detection items

###   Debug Rapido Metriche

Nei test: `from metrics.ai_meal_photo import snapshot; print(snapshot())`.

Output snapshot (esempio sintetico):
```python
RegistrySnapshot(counters={'ai_meal_photo_requests_total': {('phase=stub','status=completed'): 1}}, histograms={...})
```

---

##   Schema Diff (Semantic Quick Reference)

Lo script `scripts/verify_schema_breaking.py` confronta lo SDL runtime (`backend/graphql/schema.graphql`) con il mirror root (`graphql/schema.graphql`). Classificazioni:

| classification | Significato | Exit |
|----------------|-------------|------|
| aligned | Nessun cambiamento semantico | 0 |
| additive | Aggiunta campi / enum values | 0 |
| breaking | Rimozioni o violazioni interfacce | 1 |

Esecuzione manuale:
```bash
pwd  # deve essere la root repo o backend/
cd backend
uv run python scripts/verify_schema_breaking.py | jq
```

Output JSON include: `added_fields`, `removed_fields`, `added_enum_values`, `interface_breaks`, `tool_version`.

Dettagli completi e roadmap: consultare `../../docs/schema_diff.md` (dal path di questo README) oppure `docs/schema_diff.md` dalla root.

###   Utility Schema (Sync)
| Script | Scopo |
|--------|-------|
| `scripts/export_schema.py` | Esporta SDL runtime in `backend/graphql/schema.graphql` |
| `../scripts/sync_schema_from_backend.sh` | Copia SDL nel mirror root `graphql/schema.graphql` |
| `../scripts/schema_hash.sh` | Calcola hash (future freshness badge) |

Flusso manuale:
```bash
cd backend
uv run python scripts/export_schema.py
cd ..
./scripts/sync_schema_from_backend.sh
cd backend
uv run python scripts/verify_schema_breaking.py | jq
```
