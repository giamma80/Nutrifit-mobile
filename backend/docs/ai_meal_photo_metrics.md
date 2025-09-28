# AI Meal Photo – Adapters & Metrics Deep Dive

## Obiettivo
Fornire una base osservabile e idempotente per l'analisi (placeholder) di foto pasto, evolvibile verso inference reale remota con fallback resiliente.

## Sommario
1. Architettura & Adapter Pattern
2. Lifecyle Analisi & Idempotenza
3. Variabili d'Ambiente / Feature Flags
4. Metriche Dettagliate
5. Fixture di Test & Isolamento
6. Estensioni Pianificate
7. FAQ / Troubleshooting

---
## 1. Architettura & Adapter Pattern

`get_active_adapter()` seleziona dinamicamente l'implementazione in base alle variabili d'ambiente (lette ad ogni chiamata):

Priorità: Remote > Heuristic > Stub

| Adapter | Nome (`adapter.name()`) | Attivazione | Funzione | Stato | Fallback |
|---------|------------------------|------------|----------|-------|----------|
| StubAdapter | `stub` | default | Ritorna lista fissa di 2 item | stabile | N/A |
| HeuristicAdapter | `heuristic` | `AI_HEURISTIC_ENABLED=1` | Genera pseudo‑item via hash | stabile | verso stub se disattivato |
| RemoteModelAdapter | `remote` | `AI_REMOTE_ENABLED=1` | Simula chiamata remota con latenza / timeout | sperimentale | verso heuristic → stub |

### Struttura item (placeholder)
Ogni adapter restituisce lista di dict con chiavi minime (es. `label`, `confidence`, `quantityG`). Nessuna validazione rigida finché lo schema di output non è stabilizzato.

---
## 2. Lifecycle Analisi & Idempotenza

Entry point repository: `InMemoryMealPhotoAnalysisRepository.create_or_get()`:
1. Calcolo/derivazione chiave idempotenza (`auto-<sha256(user|photoId|photoUrl)[:16]>` se non fornita).
2. Cache lookup: se esiste, ritorna record esistente (no nuove metriche, no nuovo ID).
3. Se nuovo: selezione adapter → context `time_analysis()` → esecuzione → creazione record COMPLETED.
4. Log evento `analysis.created` con campi diagnostici.

Stato univoco attuale: `COMPLETED`. Futuro: `PENDING`, `FAILED`, `CANCELLED`.

---
## 3. Variabili d'Ambiente / Feature Flags

| Variabile | Tipo | Default | Range | Uso |
|-----------|------|---------|-------|-----|
| `AI_HEURISTIC_ENABLED` | bool/int | 0 | {0,1} | Abilita heuristic |
| `AI_REMOTE_ENABLED` | bool/int | 0 | {0,1} | Abilita remote |
| `REMOTE_TIMEOUT_MS` | int | 1200 | >0 | Timeout simulato |
| `REMOTE_LATENCY_MS` | int | 900 | >=0 | Latenza base |
| `REMOTE_JITTER_MS` | int | 300 | >=0 | Jitter random max |
| `REMOTE_FAIL_RATE` | float | 0.0 | 0–1 | Probabilità raise Exception |

Note:
- Flags riletti ad ogni invocazione → test possono monkeypatchare l'ambiente live.
- In produzione usare override per rollout graduale.

---
## 4. Metriche Dettagliate

### Elenco
| Nome | Tipo | Labels | Descrizione |
|------|------|--------|-------------|
| `ai_meal_photo_requests_total` | counter | `phase`, `status`, `source?` | Incrementato a fine fase (o fail) |
| `ai_meal_photo_latency_ms` | histogram | `source?` | Durata fase principale |
| `ai_meal_photo_fallback_total` | counter | `reason`, `source?` | (TODO) conteggio fallback remoti |
| `ai_meal_photo_errors_total` | counter | `code`, `source?` | Errori granulari (non fatal) |
| `ai_meal_photo_failed_total` | counter | `code`, `source?` | Failure finale bloccante |

### Semantica Labels
- `phase`: granularità temporale (oggi = adapter.name()). In futuro: `remote_call`, `heuristic_fallback`, ecc.
- `source`: adapter primario che ha servito la richiesta.
- `status`: `completed` | `failed` (da eccezioni).

### Context Manager `time_analysis()`
Pseudo‑flow:
```python
with time_analysis(phase=adapter.name(), source=adapter.name()):
    items = adapter.analyze(...)
```
Registra: counter requests + histogram latency. Se un'eccezione emerge → `status=failed`.

### Reset & Snapshot
- `reset_all()` pulisce counters/histograms (solo test).
- `snapshot()` ritorna `RegistrySnapshot` (dict counters + dict histograms) usabile per assert deterministici.

### Estensioni Pianificate
- Bucketizzazione esplicita histogram (oggi naive, in‑memory)
- Export Prometheus (converter → /metrics)
- Dimensioni aggiuntive: `fallback=bool`, `timeout=bool`

---
## 5. Fixture di Test & Isolamento

`tests/conftest.py` definisce fixture autouse `metrics_reset`:
```python
@pytest.fixture(autouse=True)
def metrics_reset():
    from metrics.ai_meal_photo import reset_all
    reset_all(); yield; reset_all()
```
Motivo: prevenire accumulo contatori tra test ed eliminare dipendenze dall'ordine.

Se un test richiede di ispezionare valori cumulativi multi‑step, deve farlo entro i propri confini (non rely su stato precedente). Per disabilitare temporaneamente il reset finale si può copiare la logica interna (sconsigliato se non strettamente necessario).

---
## 6. Estensioni Pianificate
- Fallback metrics: `ai_meal_photo_fallback_total` popolato in `RemoteModelAdapter`.
- Circuit breaker (trip se timeout consecutivi > soglia).
- Persistenza analisi (DB) + TTL cache warmup.
- Normalizzazione/standard schema items (macronutrienti, bounding boxes, ecc.).
- Integrazione risultato analisi nel meal enrichment pipeline.

---
## 7. FAQ / Troubleshooting

| Problema | Sintomo | Soluzione |
|----------|---------|-----------|
| Metriche sporcano altri test | Counter > atteso al primo assert | Verifica fixture attiva (nome corretto `conftest.py`), esegui singolo test per confermare |
| Flag non applicato | Adapter non cambia | Assicurarsi di aver impostato variabile PRIMA della chiamata a `create_or_get()` |
| Latenza test flakey | Sleep random jitter | Ridurre `REMOTE_LATENCY_MS` / `REMOTE_JITTER_MS` via monkeypatch env nel test |
| Idempotenza non funziona | Nuovo ID generato | Verifica valori input (photo_id / photo_url / user) identici e chiave non forzata |

---
## Riferimenti Codice
- Repository: `repository/ai_meal_photo.py`
- Metriche helpers: `metrics/ai_meal_photo.py`
- Adapter: `inference/adapter.py`
- Test metriche: `tests/test_metrics_source_label.py`, `tests/test_metrics_ai_meal_photo.py`

---
## Changelog
- v0: Introduzione stub + metriche base + reset fixture.
- v1 (planned): Remote fallback counters + multi-phase timing.
