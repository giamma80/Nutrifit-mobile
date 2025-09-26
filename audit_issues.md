## Audit Issues (Consolidated)

Questo file sostituisce `ussues.md` (rimandare qui e rimuovere duplicazioni). Struttura tabellare unica per tracciamento stato.

| ID | Severity | Confidence | Scope / Files | Description | Impact | Remediation | Status | Tags |
|----|----------|------------|---------------|-------------|--------|------------|--------|------|
| 1 | Critical | High | backend/app.py, docs | `logMeal` non esponeva `idempotencyKey` | Idempotenza fragile / duplicati | Aggiunta chiave + doc aggiornata | DONE | DOC |
| 2 | Critical | High | workflows backend-* | Workflow placeholder vuoti | Copertura CI falsa | Popolati pipeline minime | DONE |  |
| 3 | High | High | README badge vs pyproject | Version mismatch | Confusione versioni | Sincronizzazione badge automatica | DONE | DOC |
| 4 | High | High | verify_schema_breaking.py | Diff non semantico | Breaking non rilevati | AST diff + exit codes | DONE |  |
| 5 | High | Medium | CI security | Nessun vulnerability scan | Rischio CVE latenti | Integrare Trivy + pip-audit | TODO | SEC |
| 6 | High | Medium | cache.py | Nessuna metrica iniziale | Difficile tuning | Aggiunta stats + resolver cacheStats | DONE |  |
| 7 | Medium | High | mobile/, web/ | Mancato scaffolding | Onboarding lento | Creare scaffold reali | TODO |  |
| 8 | Medium | High | backend_architecture_plan.md | Doc pipeline non allineata | Governance confusa | Allineata doc | DONE | DOC |
| 9 | Medium | Medium | Schema runtime | Mancanza nutrientSnapshotJson | Refactor futuro oneroso | Campo opzionale introdotto | DONE | DOC |
| 10 | Medium | Medium | Idempotency derivata | Timestamp nella firma | Duplicati potenziali | Escluso timestamp server | DONE |  |
| 11 | Medium | Medium | sync_schema_from_backend.sh | Script placeholder | Falsa percezione sync | Rimuovere o sostituire con schema-sync | TODO |  |
| 12 | Medium | Medium | Badge schema status | Statico non validato | Drift invisibile | Hash + check workflow | DONE | DOC |
| 13 | Low | High | Licenza | Incongruenza README/pyproject | Ambiguità legale | Uniformata licenza Proprietary | DONE | DOC |
| 14 | Low | Medium | cache TTL tests | Expiry non testato | Regressioni TTL invisibili | Aggiungere test scadenze | TODO | TEST |
| 15 | Low | Medium | Nutrient keys | Hard-coded duplicati | Incoerenze estensioni | Centralizzate in constants | DONE |  |
| 16 | Low | Medium | exit codes diff | exit sempre 0 | CI non reagiva | Exit codes implementati | DONE |  |
| 17 | Low | Medium | mobile-ci.yml pattern | Filtri generici root | CI skip dopo scaffold | Aggiornare pattern path | TODO | CI |
| 18 | Low | Low | CODEOWNERS assente | Ownership informale | Review mancanti | Aggiunto CODEOWNERS | DONE | DOC |
| 19 | Medium | High | CRUD pasti | Mancavano update/delete | Funzioni incomplete | Aggiunte mutation CRUD | DONE |  |
| 20 | Medium | Medium | Meal repo pattern | Solo add/list | Estensione complessa | Estesi metodi + test | DONE |  |
| 21 | Low | Medium | Dockerfile copy nutrients.py | File escluso build | Errore runtime | Aggiunto al COPY | DONE |  |
| 22 | Medium | High | Attività totalizzazione | Totali da minute events | Drift / incompletezza | Introdotto syncHealthTotals delta source | DONE | ARCH |
| 23 | Medium | Medium | Idempotency conflitti attività | Approccio differenziato ingest vs sync | Incoerenza flag | Unificata semantica flag (duplicate/conflict/reset) | DONE | ARCH |

Legenda Tags: DOC=documentazione, SEC=sicurezza, ARCH=architettura, TEST=test coverage, CI=continuous integration.

Indicazioni aggiornamento: ogni PR che chiude o crea un finding aggiorna questa tabella nello stesso commit.
