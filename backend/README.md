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

---

## Panoramica

Subgraph nutrizionale / AI minimale con gestione dipendenze tramite **uv** e deployment container-first.

> Shell compatibility: lo script `make.sh` è scritto per funzionare anche con la bash 3.2 di macOS (niente `${var,,}` ecc.). Colori disattivabili con `NO_COLOR=1`.

### Endpoints (dettaglio)

- `GET /health` → `{status: ok}`
- `GET /version` → `{"version": "0.1.x"}`  (il valore reale è sincronizzato con `pyproject.toml` e il tag `v0.1.x`; evitare hardcode per ridurre aggiornamenti manuali)
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

### Logging locale

La cartella `backend/logs/` contiene `server.log` se avvii in background:

```bash
./make.sh run-bg
./make.sh logs
./make.sh stop
```

I log sono ignorati da git. (Futuro: structlog JSON.)

### Versioning

```bash
./make.sh version-show
./make.sh version-bump LEVEL=patch   # oppure minor / major
./make.sh version-verify
```

#### Version Verify (Workflow Tag)

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

## Typing & Static Analysis Strategy

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
