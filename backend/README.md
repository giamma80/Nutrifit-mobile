# Nutrifit Backend Subgraph (Minimal)

Obiettivo: fornire un punto di partenza per il subgraph nutrizionale / AI.

## Endpoints

- `GET /health` → `{status: ok}`
- `GET /version` → `{version: 0.1.0}`
- `POST /graphql` (via Strawberry) – Query disponibili:
  - `hello`: string di test
  - `server_time`: timestamp UTC

## Avvio locale

### Setup con uv (consigliato)

Prerequisiti: Python 3.11 installato, [uv](https://github.com/astral-sh/uv) disponibile nel PATH.

```bash
# Creazione/uso ambiente virtuale isolato (uv lo gestisce automaticamente)
cd backend
uv sync --all-extras --dev

# Avvio server (hot reload)
uv run uvicorn app:app --reload --port 8080
```

### Alternativa (pip)
Se non puoi usare `uv`:
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
```

## Prossimi Step

- Integrare schema reale Nutrition (porting da file GraphQL)
- Implementare resolver `myNutritionPlan`
- Aggiungere Auth (JWT / API Key dev)
- Observability: logging strutturato + trace
- Spostare gestione dipendenze completamente su uv lockfile (rimuovere requirements.txt dopo stabilizzazione)
