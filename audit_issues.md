# Audit Issues

Separazion| 13 | Low | High | Licenza: README vs pyproject | Badge/README "TBD" vs license Proprietary | Ambiguità legale / contributi | Definita licenza e uniformata doc | DONE | DOC |
| 15 | Low | Medium | Nutrient keys hard‑coded | Lista nutrienti duplicata/dispersa | Errori se si estendono nutrienti | Centralizzare in costante/enum condivisa | DONE |  |
| 16 | Low | Medium | `verify_schema_breaking.py` exit codes | Precedente sempre exit 0 | CI non reagiva | Exit code implementati (0 aligned/additive, 1 breaking/mixed/error) | DONE |  |
| 18 | Low | Low | Assenza `CODEOWNERS` | Review ownership non formalizzata | Merge non revisionati | Aggiunto file CODEOWNERS | DONE | DOC |
| 6 | High | Medium | Cache in-memory | Nessuna metrica hit/miss / dimensione | Difficile tuning & debug performance | Strumentare cache con counters + log / resolver diagnostico | DONE |  |
| 19 | Medium | High | CRUD incompleto | Solo logMeal disponibile, mancano update/delete | Gestione errori utente limitata | Aggiunte mutation updateMeal e deleteMeal con ricalcolo nutrienti | DONE |  |
| 20 | Medium | Medium | Repository pattern limitato | InMemoryMealRepository solo add/list | Estensioni future difficili | Esteso con get/update/delete + test completi | DONE |  |
| 21 | Low | Medium | Docker deploy nutrients.py | ModuleNotFoundError in produzione | Deploy fallito | Aggiunto nutrients.py al COPY nel Dockerfile | DONE |  |ra problemi APERTI (TODO/WIP) e COMPLETATI (DONE) per chiarezza operativa.

## Open Issues

| ID | Severity | Confidence | Scope / Files | Description | Impact | Remediation | Status | Tags |
|----|----------|------------|---------------|-------------|--------|------------|--------|------|
| 5 | High | Medium | CI tooling assente | Mancano scans vulnerabilità | Rischio vulnerabilità non gestite | Aggiungere step security scan (Trivy / pip-audit) | TODO |  |
| 7 | Medium | High | `mobile/`, `web/`, root `pubspec.yaml` | Scaffolding frontend assente / manifest fuori posto | Onboarding confuso, CI parziale | Creare progetti reali e spostare manifest nei path corretti | TODO |  |
| 11 | Medium | Medium | `sync_schema_from_backend.sh` | Script introspection placeholder, copia file senza validazione | Percezione falsa di sync attivo | Semplificare: rimuovere introspection fittizia o usare export formale | TODO |  |
| 14 | Low | Medium | `backend/cache.py` test coverage | TTL/expiry non testati direttamente | Regressioni TTL non rilevate | Aggiungere test su expirazione e purge | TODO |  |
| 17 | Low | Medium | `mobile-ci.yml` path filter | Filtra `lib/**` root (in futuro non corretto) | CI non scatta dopo scaffold mobile | Aggiornare pattern a `mobile/lib/**` + `mobile/pubspec.yaml` | TODO |  |

## Completed Issues

| ID | Severity | Confidence | Scope / Files | Description | Impact | Remediation | Status | Tags |
|----|----------|------------|---------------|-------------|--------|------------|--------|------|
| 1 | Critical | High | `backend/app.py`, docs divergenza | `logMeal` non espone `idempotencyKey` come da piani | Idempotenza fragile futura (dupliche dopo persistenza) | Aggiunto argomento `idempotencyKey` + aggiornate doc contratto | DONE | DOC |
| 2 | Critical | High | Empty workflows (`backend-*`) | Workflow placeholder vuoti danno falsa copertura | Controlli di release potenzialmente mancanti | Popolati placeholder minimi (preflight/changelog/release/schema-status) | DONE |  |
| 3 | High | High | `README.md` badge vs `pyproject.toml` | Version badge 0.1.4 ≠ codice 0.2.0 | Confusione versioni, changelog incoerente | Sincronizzato badge (script CI o update manuale) | DONE | DOC |
| 4 | High | High | `verify_schema_breaking.py`, `schema-diff.yml` | Diff schema solo testuale ora semantica (campi, enum, union, deprecazioni) | Prima breaking non rilevati | Implementato AST diff + classificazione + workflow che fallisce su breaking/mixed | DONE |  |
| 8 | Medium | High | `docs/backend_architecture_plan.md`, pipeline reali | Documentazione pipeline non allineata | Onboarding e governance poco chiari | Aggiornata doc o pipeline coerenti | DONE | DOC |
| 9 | Medium | Medium | Schema futuro vs attuale | Campo `nutrientSnapshotJson` previsto ma assente | Refactor più oneroso futuro | Aggiunto campo opzionale snapshot + doc aggiornate | DONE | DOC |
| 10 | Medium | Medium | Idempotency derivata (timestamp) | Chiave include timestamp server → retry differente | Duplicazioni potenziali post‑DB | Passato a chiave fornita dal client | DONE |  |
| 12 | Medium | Medium | Badge schema status (`README.md`) | Badge statico “synced” non validato | Drift di schema non visibile | Automazione hash (`schema_hash.sh`) + aggiornamento badge CI | DONE | DOC |
| 13 | Low | High | Licenza: README vs pyproject | Badge/README “TBD” vs license Proprietary | Ambiguità legale / contributi | Definita licenza e uniformata doc | DONE | DOC |
| 16 | Low | Medium | `verify_schema_breaking.py` exit codes | Precedente sempre exit 0 | CI non reagiva | Exit code implementati (0 aligned/additive, 1 breaking/mixed/error) | DONE |  |
| 18 | Low | Low | Assenza `CODEOWNERS` | Review ownership non formalizzata | Merge non revisionati | Aggiunto file CODEOWNERS | DONE | DOC |

---
Aggiorna questa lista quando cambia lo stato di un issue. Preferire PR che aggiornano contestualmente questa tabella.
