# Nutrifit Backend (FastAPI + Strawberry)

Subgraph nutrizionale / AI minimale con gestione dipendenze tramite **uv** e deployment container-first.

## Endpoints

- `GET /health` → `{status: ok}`
- `GET /version` → `{version: 0.1.0}`
- `POST /graphql` (via Strawberry) – Query disponibili:
  - `hello`: string di test
  - `server_time`: timestamp UTC

## Avvio locale

Prerequisiti: Python 3.11, [uv](https://github.com/astral-sh/uv) installato.

```bash
cd backend
uv sync --all-extras --dev
uv run uvicorn app:app --reload --port 8080
```

### Cockpit (script `make.sh`)

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
| `docker-build` | Build immagine locale dev |
| `docker-run` | Run container mappando porta 8080 |
| `docker-stop` | Stop container dev |
| `docker-logs` | Segui log container |
| `docker-restart` | Stop + run |
| `version-bump LEVEL=patch` | Bump versione (patch/minor/major) + commit + tag |
| `release LEVEL=patch` | preflight + bump + tag + push + push tag |
| `status` | Stato rapido (versione, server, container) |
| `clean` | Rimuove .venv, __pycache__, pid |
| `clean-dist` | Pulisce eventuale `dist/` residua |
| `all` | setup + lint + test |
| `logs` | Tail file di log server locale |

Esempi:
```bash
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

## Avvio via Docker

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
```

Health: `curl localhost:8080/health`

## Strategia Deployment (Render)

1. Push su `main` → GitHub Actions (`backend-ci`) esegue lint, type-check, test e build Docker (validazione).
2. Render rileva il cambio della directory `backend/` e ricostruisce l'immagine usando il `Dockerfile`.
3. L'immagine avvia `uv run uvicorn app:app --host 0.0.0.0 --port 8080`.
4. (Futuro) Aggiunta variabili d'ambiente per configurazioni (es. SUPABASE_URL, FEATURE_FLAGS, ecc.).

Nessuna pubblicazione su registry esterno: pipeline repository → Render (repo sync).

Note:
- Packaging Python (wheel/sdist) non usato nel deploy → cartelle `egg-info` e `dist` ignorate.
- Commit governance: conventional commits validati da commitlint (workflow `commitlint.yml`).
- Le versioni sono mantenute in `pyproject.toml` e aggiornabili via `./make.sh version-bump`.

## Prossimi Step

- Integrare schema reale Nutrition (porting da file GraphQL)
- Implementare resolver `myNutritionPlan`
- Aggiungere Auth (JWT / API Key dev)
- Observability: logging strutturato + trace
- Rule Engine runtime (valutazione condizioni + throttle)
- Caching OpenFoodFacts (LRU + TTL)

