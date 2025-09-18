# Nutrifit Backend Subgraph (Minimal)

Obiettivo: fornire un punto di partenza per il subgraph nutrizionale / AI.

## Endpoints
- `GET /health` → `{status: ok}`
- `GET /version` → `{version: 0.1.0}`
- `POST /graphql` (via Strawberry) – Query disponibili:
  - `hello`: string di test
  - `server_time`: timestamp UTC

## Avvio locale
```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
```

## Prossimi Step
- Integrare schema reale Nutrition (porting da file GraphQL)
- Implementare resolver `myNutritionPlan`
- Aggiungere Auth (JWT / API Key dev)
- Observability: logging strutturato + trace
