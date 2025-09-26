## Audit Issues (Deprecated File)

Questo file è stato consolidato in `audit_issues.md` nella root del repository.

Usare SOLO `audit_issues.md` per aggiornare o aggiungere nuovi finding.

Motivo: eliminare duplicazioni e desync tra liste. Questo file rimane temporaneamente per compatibilità con link storici e verrà rimosso in una futura minor.

Redirect manuale: vedere `audit_issues.md`.

---
Contenuto precedente rimosso.

Legenda colonne:
- ID: identificatore finding
- Severity: Critical | High | Medium | Low
- Confidence: livello di confidenza sulla classificazione
- Scope / Files: file o aree coinvolte (sintesi)
- Description: descrizione concisa del problema
- Impact: effetto pratico / rischio
- Remediation: azione raccomandata principale (high‑level)
- Status: stato remediation (TODO = non iniziato, WIP = in corso, DONE = completato)
- Tags: DOC se intervento primario è aggiornare documentazione / README / badge / policy, altrimenti vuoto (più tag separati da virgola se necessario)

| ID | Severity | Confidence | Scope / Files | Description | Impact | Remediation | Status | Tags |
|----|----------|------------|---------------|-------------|--------|------------|--------|------|
| 1 | Critical | High | `backend/app.py`, docs divergenza | `logMeal` non espone `idempotencyKey` come da piani | Idempotenza fragile futura (dupliche dopo persistenza) | Aggiungere argomento `idempotencyKey` opzionale + aggiornare doc contratto | DONE | DOC |
| 2 | Critical | High | Empty workflows (`backend-*`) | Workflow placeholder vuoti danno falsa copertura | Controlli di release potenzialmente mancanti | Popolati placeholder minimi (preflight/changelog/release/schema-status) | DONE |  |
| 3 | High | High | `README.md` badge vs `pyproject.toml` | Version badge 0.1.4 ≠ codice 0.2.0 | Confusione versioni, changelog incoerente | Sincronizzare badge (script CI o update manuale) | DONE | DOC |
| 4 | High | High | `verify_schema_breaking.py`, `schema-diff.yml` | Diff schema era solo testuale, ora semantica (campi, enum, union, deprecazioni) | Prima breaking non rilevati correttamente | Implementato AST diff + classificazione + workflow che fallisce su breaking/mixed | DONE |  |
| 5 | High | Medium | CI tooling assente | Mancano scans vulnerabilità | Rischio vulnerabilità non gestite | Aggiungere step security scan (Trivy / pip-audit) | TODO |  |
| 6 | High | Medium | Cache in-memory | Nessuna metrica hit/miss / dimensione | Difficile tuning & debug performance | Strumentare cache con counters + log / resolver diagnostico | TODO |  |
| 7 | Medium | High | `mobile/`, `web/`, root `pubspec.yaml` | Scaffolding frontend assente / manifest fuori posto | Onboarding confuso, CI parziale | Creare progetti reali e spostare manifest nei path corretti | TODO |  |
| 8 | Medium | High | `docs/backend_architecture_plan.md`, pipeline reali | Documentazione pipeline non allineata alla realtà | Onboarding e governance poco chiari | Aggiornare doc oppure rifattorizzare pipeline coerenti | DONE | DOC |
| 9 | Medium | Medium | Schema futuro vs attuale | Campo `nutrientSnapshotJson` previsto ma assente | Refactor più oneroso quando si introduce persistenza | Aggiungere campo opzionale snapshot + doc aggiornate | DONE | DOC |
| 10 | Medium | Medium | Idempotency derivata (timestamp) | Chiave include timestamp server → retry differente | Duplicazioni potenziali post‑DB | Passare a chiave fornita dal client (vedi ID 1) | DONE |  |
| 11 | Medium | Medium | `sync_schema_from_backend.sh` | Script introspection placeholder, copia file senza validazione | Percezione falsa di sync attivo | Semplificare: rimuovere introspection fittizia o usare export formale | TODO |  |
| 12 | Medium | Medium | Badge schema status (`README.md`) | Badge statico “synced” non validato | Drift di schema non visibile | Automazione hash (`schema_hash.sh`) + aggiornamento badge CI | DONE | DOC |
| 13 | Low | High | Licenza: README vs pyproject | Badge/README “TBD” vs license Proprietary | Ambiguità legale / contributi | Definire licenza e uniformare doc | DONE | DOC |
| 14 | Low | Medium | `backend/cache.py` test coverage | TTL/expiry non testati direttamente | Regressioni TTL non rilevate | Aggiungere test su expirazione e purge | TODO |  |
| 15 | Low | Medium | Nutrient keys hard‑coded | Lista nutrienti duplicata/dispersa | Errori se si estendono nutrienti | Centralizzare in costante/enum condivisa | TODO |  |
| 16 | Low | Medium | `verify_schema_breaking.py` exit codes | Precedente sempre exit 0 | CI non poteva reagire granularmente | Exit code implementati (0 aligned/additive, 1 breaking/mixed/error) | DONE |  |
| 17 | Low | Medium | `mobile-ci.yml` path filter | Filtra `lib/**` root (in futuro non corretto) | CI non scatta dopo scaffold mobile | Aggiornare pattern a `mobile/lib/**` + `mobile/pubspec.yaml` | TODO |  |
| 18 | Low | Low | Assenza `CODEOWNERS` | Review ownership non formalizzata | Merge non revisionati | Aggiungere file CODEOWNERS documentato | DONE | DOC |

### Note Tag DOC
È stato marcato come DOC ogni finding in cui la remediation primaria o necessaria in parallelo consiste in aggiornamento di documentazione / badge / policy esplicita. Alcuni item (es. #1, #9) includono anche cambi codice ma richiedono revisione immediata della documentazione contrattuale.

### Priorità Suggerita (macro)
1. Sicurezza & Qualità: 5,6,14 (aggiungere anche scans), 15
2. Roadmap Schema & Tooling: 11 (script sync), eventuali estensioni diff (interface, input validation)
3. Frontend Bootstrap: 7,17
4. Persistenza & Snapshot: (NUOVO) DB MealEntry + nutrientSnapshotJson popolato (DEFERRED)
5. Policy & Governance: residui minori post aggiornamenti

### Nota Deferimento Persistenza
La persistenza DB per MealEntry e popolamento reale di `nutrientSnapshotJson` è rinviata (DEFERRED): richiede scelta storage (Postgres / Lite) + migrazioni + strategia snapshot (copia nutrienti arricchiti) e verrà trattata in milestone successiva.
