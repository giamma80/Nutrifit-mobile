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

Oppure usando lo script helper:
```bash
./make.sh setup
./make.sh run
```

## Avvio via Docker

Costruzione immagine (usa `uv` per risolvere dipendenze):
```bash
docker build -t nutrifit-backend:dev backend
docker run -p 8080:8080 nutrifit-backend:dev
```

Oppure:
```bash
./make.sh docker
```

Health: `curl localhost:8080/health`

## Strategia Deployment (Render)

1. Push su `main` → GitHub Actions (`backend-ci`) esegue lint, type-check, test e build Docker (validazione).
2. Render rileva il cambio della directory `backend/` e ricostruisce l'immagine usando il `Dockerfile`.
3. L'immagine avvia `uv run uvicorn app:app --host 0.0.0.0 --port 8080`.
4. (Futuro) Aggiunta variabili d'ambiente per configurazioni (es. SUPABASE_URL, FEATURE_FLAGS, ecc.).

Nessuna pubblicazione su registry esterno: pipeline repository → Render (repo sync).

Nota packaging: la cartella `nutrifit_backend.egg-info/` può essere rigenerata localmente da uv/setuptools ma è ignorata (`.gitignore`). Non è necessaria nel VCS.

## Prossimi Step

- Integrare schema reale Nutrition (porting da file GraphQL)
- Implementare resolver `myNutritionPlan`
- Aggiungere Auth (JWT / API Key dev)
- Observability: logging strutturato + trace
- Rule Engine runtime (valutazione condizioni + throttle)
- Caching OpenFoodFacts (LRU + TTL)

