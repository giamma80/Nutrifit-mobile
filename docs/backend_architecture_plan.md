# Backend Platform Architecture & Delivery Plan

Versione: 1.0 (Bozza Iniziale)
Owner: Team Backend
Ultimo aggiornamento: 2025-09-18

## 1. Visione
Costruire una piattaforma modulare che evolve da zero backend → servizi federati scalabili, fornendo API GraphQL unificate (Apollo Federation) per mobile e futura web dashboard, con Supabase come backbone per autenticazione secondaria, storage dati (Postgres), real-time (replication listen), file storage e notifiche (edge functions) dove possibile.

## 2. Principi Architetturali
- Start Simple: prima milestone senza backend (mock client) → riduce time-to-first-value.
- Leverage Managed: usare Supabase per accelerare auth secondaria, Postgres, storage, realtime channel.
- Federated Growth: aggiungere microservizi Python solo per logiche non coperte da Supabase (AI, plan adaptation, analytics derivata).
- Idempotenza & Event Sourcing Light: eventi chiave (meal_logged, plan_updated) salvati in tabella append-only per audit + proiezioni.
- Schema First: GraphQL come contratto stabile + versioning; federation per boundaries.
- Security & Privacy: segmentazione dati sensibili, policy row-level (RLS) Supabase.

## 3. Bill of Materials (BOM)
| Ambito | Tecnologie | Note |
|--------|------------|------|
| DB Primario | Postgres (Supabase) | RLS + row policies |
| Auth Primario | Auth0 (OIDC) | Token exchange → JWT custom claims |
| Auth Secondario | Supabase Auth (fallback) | Usato per canali realtime se necessario |
| API Gateway | Apollo Router/Federation | Compose subgraph Python / supabase-graph |
| Subgraph Core | Strawberry + FastAPI | Nutrition, meals, plan logic |
| AI Service | FastAPI + integrazione GPT-4V | Pipeline inference async |
| Event Bus | Postgres logical decoding / NOTIFY + (futuro) Redpanda/Kafka | Scalare quando volume cresce |
| Cache | Redis (Render) | Session ephemeral, rate limiting |
| Storage Immagini | Supabase Storage Bucket | Policy access controllata |
| CDN | Supabase edge / Cloudflare (futuro) | Distribuzione media |
| Notifications Push | Supabase Edge Functions + FCM/APNs | Orchestrazione iniziale |
| Metrics & Tracing | OpenTelemetry + Prometheus/Grafana (Render) | Dashboard SLO |
| CI/CD | GitHub Actions + Render deploy hooks | Deploy blue/green subservices |
| Infra IaC | Terraform (futuro) | Gestione config prod/staging |

## 4. Evoluzione Incrementale (Milestones Backend)
| Fase | Stato App | Backend Necessario | Output |
|------|-----------|--------------------|--------|
| B0 | Mock totale | Nessuno (client offline) | Guida + schema stub |
| B1 | Log pasto base | Supabase tables + simple REST RPC | Tabelle meal, food |
| B2 | GraphQL base | Subgraph Core (meals, foods) + Apollo gateway | Query/Mutation plan & logging |
| B3 | Storico & Aggregati | Aggiunta materiale daily summaries (SQL views) | Query summary range |
| B4 | Notifiche base | Edge function time-based + event triggers | Reminder colazione/cena |
| B5 | AI Foto baseline | AI microservice + storage bucket + analyzeMealPhoto | Inference pipeline |
| B6 | Real-time delta | Subscription (websocket) + DB trigger publish | dailyNutritionUpdated |
| B7 | Adattamento piano | Job schedulato microservice analytics | plan adjustments |
| B8 | Web Dashboard | Next.js/React app + GraphQL reuse | Visualizzazione storici |
| B9 | Hardening & Scaling | Rate limit, metrics, caching read-heavy | SLO stabilizzati |

## 5. Domain Data Model (Sintesi)
Tabelle principali (Postgres):
- `users` (Auth0 subject mapping)
- `nutrition_plan` (user_id, targets, strategy, updated_at)
- `food_item` (id, name, category, nutrients_json, brand)
- `meal_entry` (id, user_id, food_id, quantity, unit, nutrient_snapshot_json, meal_type, created_at)
- `daily_summary` (user_id, date, nutrient_agg_json, meal_count, adherence)
- `ai_inference` (id, user_id, raw_label, status, confidence, created_at, items_json)
- `event_log` (id, user_id, type, payload_json, created_at)
- `notification_log` (id, user_id, rule_id, channel, delivered_at, tapped_at)

Indice raccomandati:
- meal_entry: (user_id,date(created_at)) partial index, (user_id, meal_type)
- daily_summary: (user_id,date) unique
- ai_inference: (user_id, created_at desc)

## 6. Federation Boundaries (Prima Bozza)
| Subgraph | Responsabilità | Tipi chiave |
|----------|----------------|-------------|
| core-nutrition | meals, foods, plans, inference orchestrazione base | MealEntry, FoodItem, NutritionPlan |
| ai-service | arricchisce AIInferenceResult + mutations analyze/confirm | AIInferenceResult, AIInferenceItem |
| notifications | subscriptions delta + regole reminder | DailyNutritionDelta |
| analytics (futuro) | trend avanzati, adherence storica | TrendSeries |

## 7. Sicurezza & Auth Flow
1. Mobile ottiene token Auth0 (OIDC) con audience API.
2. Backend gateway valida firma JWKS Auth0.
3. Claims custom: `sub` → mapping `users` (on first request provisioning lazy).
4. Row Level Security Supabase: policy `user_id = auth.uid()` (se bridging con Supabase Auth richiede exchange server-side per avere session). In alternativa usare Postgres direttamente con connection pooling e claim user_id passato a livello applicativo.
5. Rate limiting API (Redis token bucket) per mutation sensibili (analyzeMealPhoto, logMeal).

## 8. Real-Time Strategy
- Short term: Postgres LISTEN/NOTIFY -> subscription adapter pubblica su websocket gateway.
- Long term: Event bus (Kafka/Redpanda) → aggregator → push incremental.
- Delta payload: `DailyNutritionDelta` riduce banda rispetto full summary.

## 9. Notifiche
- Trigger base: Cron Edge Function (Supabase) + query su meal coverage.
- Regole avanzate: microservice rule-engine (Python) legge event_log + proiezioni materializzate.
- Delivery: Push (FCM/APNs) + local scheduling (client) per reminder offline.
- Frequency cap enforced in `notification_log` + unique partial indexes (rule_id + timeframe) eventuali.

## 10. AI Service Dettaglio
- Endpoint `/analyze` (uploadId) → job asincrono (coda in memoria / Redis stream BETA, poi sostituire con più robusto).
- GPT-4V call + parse → store ai_inference row.
- Matching nutrienti: query su `food_item` + fallback fetch OFF (cache 24h).
- Confirm → crea meal_entry + produce event (meal_logged, ai_confirmed) + delta.
- Observability: trace id per pipeline (propagation HTTP headers).

## 11. Deployment & CI/CD
### GitHub Actions
Workflows:
- `lint-test` (PR): mypy, pytest, flake8, strawberry schema check.
- `build-push-image` (main): build Docker, push registry (Render auto deploy).
- `contract-check` (PR): estrazione schema federato → diff vs snapshot.

### Environments
- Staging (feature validation + load light)
- Production (scalare replica DB read se necessario)

Deployment Pattern: Rolling (Render) → canary 10% per ai-service prima del full.

## 12. Observability & SLO
| Servizio | SLO | Misura |
|----------|-----|--------|
| core-nutrition Mutation p95 | <300ms | tracing + histogram |
| analyzeMealPhoto end-to-end p90 | <5s | pipeline metric |
| subscription message latency p95 | <1s | diff produce/consume timestamp |

Alerting (Prometheus rules):
- Error rate logMeal >2% 5m
- AI timeout ratio >10% 15m

## 13. Testing Strategy
| Livello | Strumenti | Focus |
|---------|----------|-------|
| Unit | pytest | matching, portion heuristics, rule engine funcs |
| Integration | pytest + ephemeral DB | mutation + RLS policies |
| Contract | federation composition check | schema invariants |
| Load (mirato) | k6 / locust | logMeal throughput, subscription fanout |
| Security | dependency scan (pip-audit) | CVE critiche |

## 14. Migrazioni Dati
- Alembic (Python) per subgraph tabelle custom.
- Convenzione: versioning cartelle `migrations/versions/` + script auto generate + review manuale.
- Supabase SQL migrazioni separate repository (o gestite via CLI).

## 15. Scalabilità & Performance
- Indici parziali meal_entry riducono bloat.
- Partitioning possibile per meal_entry per mese se >10M row.
- Cache calcoli adherence weekly in materialized view rinfrescata (cron 5m) se carico cresce.

## 16. Risk & Mitigation
| Rischio | Mitigazione |
|---------|------------|
| GPT cost escalation | Rate limit + barcode short-circuit |
| Lock contention summary | Incremental update + eventual materialized refresh |
| Subscription overload | Backpressure + message coalescing (aggregate 2s) |
| Federation complexity | Limitare subgraph iniziali (massimo 3) |

## 17. Web Dashboard (Fase B8)
- Stack: Next.js + Apollo Client + shared GraphQL fragments.
- Auth: Auth0 SPA + silent refresh.
- Funzioni: Filtri avanzati (range date custom), esport CSV, grafici trend (d3/Recharts), admin moderation (future).

## 18. Governance & Versioning
- Version bump schema: semantic (MAJOR.breaking.MINOR additive.PATCH fix).
- Changelog automatico generato da diff script.
- Deprecation policy: 2 release minors di preavviso.

## 19. Logging & Auditing
- Structured logs JSON (correlation_id, user_id, operationName, duration_ms, error_code).
- Audit events: CRUD plan, login mapping, AI inference confirm.
- Retention logs: 30gg raw, 180gg aggregati.

## 20. TODO & Backlog
- [ ] Implementare proof-of-concept federation (core + ai-service) in staging
- [ ] Configurare RLS policies meal_entry
- [ ] Implementare subscription adapter LISTEN/NOTIFY
- [ ] Setup tracing OpenTelemetry + exporter
- [ ] Rate limit analyzeMealPhoto (Redis token bucket)
- [ ] Materialized view adherence 7d
- [ ] Edge function reminder colazione

## 21. Appendice: Eventi Principali
| Evento | Descrizione |
|--------|-------------|
| meal_logged | Creazione meal_entry |
| plan_updated | Modifica nutrition_plan |
| ai_inference_confirmed | Inference confermata -> meal_entry |
| daily_summary_recomputed | Rebuild summary giornaliero |
| notification_sent | Notifica emessa |

---
### 22. Deployment Diagram (Federation)
```mermaid
graph LR
	subgraph Client
		APP[Flutter App]
		DASH[Web Dashboard]
	end

	APP --> GATE[GraphQL Gateway]
	DASH --> GATE

	subgraph Federation
		CORE[Core Nutrition Subgraph]\nFastAPI+Strawberry
		AI[AI Service Subgraph]\nFastAPI+Strawberry
		NOTIF[Notifications Subgraph]\n(Phase B5)
	end

	GATE --> CORE
	GATE --> AI
	GATE --> NOTIF

	CORE --> PG[(Postgres/Supabase)]
	AI --> OFF[(OpenFoodFacts)]
	AI --> GPT[GPT-4V API]
	NOTIF --> REDIS[(Redis)]
	CORE --> RLS[(RLS Policies)]
```

### 23. Sequence: analyzeMealPhoto
```mermaid
sequenceDiagram
	participant C as Client (Flutter)
	participant G as Gateway
	participant AI as AI Subgraph
	participant OFF as OpenFoodFacts
	participant GPT as GPT-4V
	participant CORE as Core Nutrition

	C->>G: analyzeMealPhoto(uploadId)
	G->>AI: analyzeMealPhoto(uploadId)
	AI->>GPT: Vision prompt (immagine + contesto utente)
	GPT-->>AI: Candidates (label, portion guesses)
	AI->>OFF: Fetch nutrients (per label/barcode) [parallel]
	AI->>CORE: (opt) Lookup internal food items synonyms
	OFF-->>AI: Nutrient data normalized
	CORE-->>AI: FoodItem match (if found)
	AI->>AI: Merge candidates + nutrient grounding + confidence scoring
	AI-->>G: AIInferenceResult (status=PENDING, items[])
	G-->>C: Result (client mostra lista)
	Note over C: Utente conferma selezioni
	C->>G: confirmInference(id,selections[])
	G->>AI: confirmInference(...)
	AI->>CORE: logMeal mutations (batch)
	CORE-->>AI: MealEntry list
	AI-->>G: MealEntry list
	G-->>C: MealEntries + subscription delta
	CORE-->>G: dailyNutritionUpdated (delta) (async)
	G-->>C: Delta ring aggiornato
```

<!-- Diagrammi aggiunti: deployment federation + sequence analyzeMealPhoto -->
