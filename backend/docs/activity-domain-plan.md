# Activity Domain Plan (Phase 1)

Stato: draft iniziale implementato (modelli base) — feature flag non ancora attivo.

## Obiettivi

1. Unificare le due sorgenti dati correnti:
   * Minute events (`repository.activities`)
   * Cumulative snapshots + deltas (`repository.health_totals`)
2. Fornire un linguaggio ubiquo (Value Objects) per servizi di calcolo e sync
3. Abilitare rollout incrementale tramite feature flag `ACTIVITY_DOMAIN_V2`
4. Preservare retro-compatibilità GraphQL (nessuna breaking change su tipi attuali)

## Modelli (implementati)

| Model | Descrizione |
|-------|-------------|
| `ActivityEvent` | Evento a granularità minuto (o normalizzato a minuto) |
| `HealthSnapshot` | Snapshot cumulativo (steps, calories_out) per `user_id`+`date` |
| `ActivityDelta` | Delta derivato da snapshot precedente con flag `reset`/`duplicate` |
| `DailyActivitySummary` | Riepilogo giornaliero consolidato (totali + events count diagnostico) |

## Layer Previsti

1. `ports/` — Interfacce astratte verso storage esistente (events & snapshots)
2. `adapters/` — Implementazioni che delegano ai repository in-memory correnti
3. `application/` — Servizi:
   * `ActivitySyncService` — idempotenza, detection reset/duplicate, orchestrazione snapshot->delta
   * `ActivityAggregationService` — costruzione `DailyActivitySummary`
   * `ActivityCalculationService` — (futuro) metriche derivate (es. intensità, moving averages)
4. `integration.py` — Feature flag + bridging verso GraphQL (`dailySummary`, `ingestActivityEvents`, `syncHealthTotals`)

## Fasi

| Fase | Contenuto | Stato |
|------|-----------|-------|
| 1 | Modelli + plan (questo commit) | In corso |
| 2 | Ports + adapters bridging repos esistenti | TODO |
| 3 | Servizi Sync & Aggregation + test unitari | TODO |
| 4 | Equivalence tests vs implementazione legacy (pytest) | TODO |
| 5 | Integrazione feature flag (read-only) | TODO |
| 6 | Attivazione progressiva + metriche osservabilità | TODO |

## Considerazioni Reset & Duplicate

Logica attuale (legacy) in `health_totals_repo`:
* `duplicate`: snapshot identico a precedente → delta (0,0) non persistito
* `reset`: almeno un contatore diminuisce → delta = valori snapshot (nuovo baseline)

Il dominio manterrà semantica identica per equivalence; successivamente potremo
estendere per gestione multi-sessione.

## Prossimi Passi Immediati

1. Definizione delle interfacce `ActivityEventsPort` e `ActivitySnapshotsPort`
2. Implementazione adapters minimi (in-memory → repository esistenti)
3. Servizio di aggregazione daily (produce `DailyActivitySummary`)
4. Prime unit test per normalizzazione timestamp e aggregazione.

---

Autogenerato da Copilot Assistant — revisione manuale consigliata prima di merge.
