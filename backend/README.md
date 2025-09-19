# Backend

![Build Backend](https://github.com/giamma80/Nutrifit-mobile/actions/workflows/backend-ci.yml/badge.svg)
![Schema Status](https://img.shields.io/badge/schema-aligned-brightgreen?label=GraphQL%20SDL)

## Endpoints

- `GET /health`
- `GET /version`
- `POST /graphql`
  - Query:
    - `hello`
    - `serverTime`
    - `health`

## Target principali

| Categoria | Target | Descrizione |
|-----------|--------|-------------|
| Docker | docker-build | Build immagine locale (usa ARG VERSION) |
| Docker | docker-run | Avvia container mappando :8080 |
| Docker | docker-stop | Ferma container |
| Docker | docker-logs | Log in streaming |
| Docker | docker-restart | Restart rapido |
| Docker | docker-shell | Shell interattiva nel container |
| Docker | docker-test | Test integrazione (health/version + GraphQL) |
| GraphQL | schema-export | Esporta SDL in `graphql/schema.graphql` |
| GraphQL | schema-check | Confronta runtime vs SDL versionato |
| Quality | test | Pytest suite |

## Esempi Rapidi

```bash
./make.sh docker-build
./make.sh docker-run
./make.sh docker-test
./make.sh docker-shell
./make.sh schema-export
./make.sh schema-check
```

## Health & GraphQL

```bash
curl localhost:8080/health
curl -s -H 'Content-Type: application/json' -d '{"query":"{ health serverTime }"}' http://localhost:8080/graphql
```

## CI

La pipeline `backend-ci` esegue: lint, type-check, test, export schema, build immagine (con ARG VERSION) e test di integrazione container.
# Nutrifit Backend (FastAPI + Strawberry)

Subgraph nutrizionale / AI minimale con gestione dipendenze tramite **uv** e deployment container-first.

> Shell compatibility: lo script `make.sh` è scritto per funzionare anche con la bash 3.2 di macOS (niente `${var,,}` ecc.). Colori disattivabili con `NO_COLOR=1`.

## Endpoints

- `GET /health` → `{status: ok}`
- `GET /version` → `{version: 0.1.2}`
- `POST /graphql` (via Strawberry) – Query disponibili:
  - `hello`: string di test
  - `server_time`: timestamp UTC
  - `health`: stato (placeholder per future verifiche interne)

## Avvio locale

Prerequisiti: Python 3.11, [uv](https://github.com/astral-sh/uv) installato.

```bash
cd backend
uv sync --all-extras --dev
uv run uvicorn app:app --reload --port 8080
```

### Cockpit (script `make.sh`)

> Per comodità è presente anche un `Makefile`: puoi usare **sia** `./make.sh target` **sia** `make target` (dentro la cartella `backend/`). Se lanci solo `make` senza parametri ottieni lo stesso help.

Tutte le operazioni comuni sono incapsulate in `make.sh` (funziona anche su macOS/Linux):

| Target | Descrizione |
|--------|-------------|
| `setup` | Sync dipendenze (uv) |
| `run` | Avvia server in foreground |
| `run-bg` | Avvia server in background (PID salvato) |
| `stop` | Ferma server background |
| `format` | Esegue Black |
| `lint` | Flake8 + mypy |
| `test` | Pytest |
| `preflight` | format + lint + test + commitlint (range main→HEAD) |
| `commit MSG="..."` | Esegue preflight poi crea commit |
| `push` | Preflight + push ramo |
| `docker-build` | Build immagine locale dev (accetta VERSION=1.2.3) |
| `docker-run` | Run container mappando porta 8080 |
| `docker-stop` | Stop container dev |
| `docker-logs` | Segui log container |
| `docker-restart` | Stop + run |
| `docker-shell` | Shell interattiva dentro il container (bash/sh) |
| `docker-test` | Test integrazione (health/version + GraphQL) |
| `version-bump LEVEL=patch` | Bump versione (patch/minor/major) + commit + tag |
| `version-show` | Mostra versione corrente (solo stdout pulito) |
| `version-verify` | Verifica corrispondenza pyproject vs tag HEAD |
| `schema-export` | Esporta SDL GraphQL in `backend/graphql/schema.graphql` |
| `schema-check` | Confronta schema generato vs file versionato (fail se differente) |
| `release LEVEL=patch` | preflight + bump + tag + push + push tag |
| `status` | Stato rapido (versione, server, container) |
| `clean` | Rimuove .venv, __pycache__, pid |
| `clean-dist` | Pulisce eventuale `dist/` residua |
| `all` | setup + lint + test |
| `logs` | Tail file di log server locale |

Esempi:
```bash
# Primo setup (crea venv e installa dipendenze)
./make.sh setup

# Avvio rapido server (locale hot reload)
./make.sh run

# In alternativa con Makefile
make setup
make run

# Lint, test e controllo schema prima di un commit
./make.sh preflight

# Commit con messaggio conventional commit
./make.sh commit MSG="feat(schema): add meal type"

# Bump versione patch + tag
./make.sh version-bump LEVEL=patch

./make.sh setup
./make.sh run-bg
./make.sh status
./make.sh preflight
./make.sh commit MSG="feat(rules): add evaluator skeleton"
./make.sh push
```

Release veloce (patch):
```bash
./make.sh release LEVEL=patch
```

### Logging locale

Lo script crea (se non esiste) la cartella `backend/logs/` e scrive:

- `logs/server.log` → output cumulativo uvicorn (foreground con tee, background rediretto). Ogni avvio è preceduto da una riga `# <ISO8601> START (fg|bg)` e ogni stop da `# <ISO8601> STOP`.

Comandi utili:
```bash
./make.sh run-bg      # avvia e scrive su logs/server.log
./make.sh logs        # tail -f del file
./make.sh stop        # ferma server e marca STOP
./make.sh status      # mostra anche la dimensione del log
```
I log non sono versionati (ignorati in `.gitignore`). In futuro potremo introdurre structlog / formati JSON.

### Versioning

Per vedere rapidamente la versione senza rumore (utile in script esterni):
```bash
./make.sh version-show
```
Per bump semantico (aggiorna `pyproject.toml`, crea commit e tag):
```bash
./make.sh version-bump LEVEL=patch   # oppure minor / major
```

### Riferimento rapido target (categorie)

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

## Avvio via Docker

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

## Strategia Deployment (Render)

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

## Prossimi Step

- Integrare schema reale Nutrition (porting da file GraphQL)
- Implementare resolver `myNutritionPlan`
- Aggiungere Auth (JWT / API Key dev)
- Observability: logging strutturato + trace
- Rule Engine runtime (valutazione condizioni + throttle)
- Caching OpenFoodFacts (LRU + TTL)

## Roadmap & Progress (Backend)

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

## Changelog & Release Automation

Il file `CHANGELOG.md` (root repo) viene aggiornato automaticamente da uno script che raccoglie i commit in formato **Conventional Commits**.

### Target `changelog`

Genera/aggiorna la sezione `[Unreleased]` raggruppando i commit dalla **ultima tag**:
```bash
./make.sh changelog         # aggiorna CHANGELOG.md (se cambia non committa)
DRY=1 ./make.sh changelog   # anteprima (stampa ma non scrive)
```
Regole parse: `type(scope): subject` dove `type` ∈ `feat|fix|docs|chore|refactor|perf|test|build|ci`.
Le categorie vengono mappate in sezioni: Added, Fixed, Changed, Performance, Docs, Tests, CI, Build, Chore, Other.

Idempotente: se una voce è già presente non viene duplicata.

### Integrazione con `release`

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


