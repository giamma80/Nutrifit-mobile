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
8. GPT-4V Vision Client & Mocking

---
## 1. Architettura & Adapter Pattern

`get_active_adapter()` seleziona dinamicamente l'implementazione in base alle variabili d'ambiente (lette ad ogni chiamata):

Priorità: GPT-4V (via AI_MEAL_PHOTO_MODE) > Remote > Heuristic > Stub

| Adapter | Nome (`adapter.name()`) | Attivazione | Funzione | Stato | Fallback |
|---------|------------------------|------------|----------|-------|----------|
| Gpt4vAdapter | `gpt4v` | `AI_MEAL_PHOTO_MODE=gpt4v` (+ opzionali: `AI_GPT4V_REAL_ENABLED=1` & `OPENAI_API_KEY`) | Chiamata reale OpenAI Vision o simulazione deterministica | sperimentale | simulazione → stub (solo su parse hard fail) |
| RemoteModelAdapter | `remote` | `AI_REMOTE_ENABLED=1` (se `AI_MEAL_PHOTO_MODE` non impostata) | Simula chiamata remota con latenza / timeout | sperimentale | heuristic → stub |
| HeuristicAdapter | `heuristic` | `AI_HEURISTIC_ENABLED=1` (se sopra non attivi) | Genera pseudo‑item via hash | stabile | stub |
| StubAdapter | `stub` | default | Ritorna lista fissa di 2 item | stabile | N/A |

### Struttura item & dishHint Support
Ogni adapter restituisce lista di dict con chiavi minime (es. `label`, `confidence`, `quantityG`). L'arricchimento macro/micro nutrienti è best‑effort.

**Nuovo**: tutti gli adapter supportano il parametro opzionale `dish_hint` che viene incluso nel prompt di analisi per migliorare l'accuratezza. Il suggerimento viene incorporato con formato: `"Suggerimento: potrebbe essere {dish_hint}"`

### Nota Optionalità Metrics
Il modulo `metrics.ai_meal_photo` è opzionale: se non importabile le funzioni (`time_analysis`, `record_error`, `record_fallback`, ecc.) sono sostituite da no‑op con stessa firma. Questo garantisce che build/container possano escludere dipendenze di osservabilità senza rompere il flusso runtime. Documentare sempre la differenza “metriche disattivate” quando si analizzano latenze.

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
| `AI_MEAL_PHOTO_MODE` | string | (vuoto) | {`gpt4v`,`heuristic`,`model`,`stub`} | Se presente forza adapter specifico (nuova priorità) |
| `AI_GPT4V_REAL_ENABLED` | bool/int | 0 | {0,1} | Abilita path reale vision nel Gpt4vAdapter (altrimenti simulazione) |
| `OPENAI_API_KEY` | string | (vuoto) | — | Necessaria per path reale GPT‑4V |
| `OPENAI_VISION_MODEL` | string | `gpt-4o-mini` | nome modello valido | Override modello vision |
| `AI_HEURISTIC_ENABLED` | bool/int | 0 | {0,1} | Abilita heuristic (legacy path) |
| `AI_REMOTE_ENABLED` | bool/int | 0 | {0,1} | Abilita remote (legacy path) |
| `REMOTE_TIMEOUT_MS` | int | 1200 | >0 | Timeout simulato |
| `REMOTE_LATENCY_MS` | int | 900 | >=0 | Latenza base |
| `REMOTE_JITTER_MS` | int | 300 | >=0 | Jitter random max |
| `REMOTE_FAIL_RATE` | float | 0.0 | 0–1 | Probabilità raise Exception |

Note:
- Flags riletti ad ogni invocazione → test possono monkeypatchare l'ambiente live.
- In produzione usare override per rollout graduale.

---
## 4. Metriche Dettagliate

### Elenco (Design Attuale)
| Nome | Tipo | Labels | Descrizione |
|------|------|--------|-------------|
| `ai_meal_photo_requests_total` | counter | `phase`, `status`, `source?` | Incrementato a fine fase (o fail) |
| `ai_meal_photo_latency_ms` | histogram | `source?` | Durata fase principale |
| `ai_meal_photo_fallback_total` | counter | `reason`, `source?` | Conteggio fallback (adapter superiore non disponibile o errore) |
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
- Dimensioni aggiuntive: `timeout=bool`, `model=real|sim`
- Cause fallback estese (timeout, rate limit, HTTP_* codes)

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
## 6. Estensioni & Fallback (Aggiornato)
- Circuit breaker (trip se timeout consecutivi > soglia).
- Persistenza analisi (DB) + TTL cache warmup.
- Normalizzazione/standard schema items (macronutrienti, bounding boxes, ecc.).
- Integrazione risultato analisi nel meal enrichment pipeline.

### Cause Fallback Attuali (label `reason`)
| Codice | Significato |
|--------|-------------|
| `REAL_DISABLED` | Flag real GPT‑4V non attivo (`AI_GPT4V_REAL_ENABLED`=0) |
| `MISSING_API_KEY` | Assente variabile `OPENAI_API_KEY` per path reale |
| `TIMEOUT:<detail>` | Timeout chiamata vision reale (esaurito budget tempo) |
| `TRANSIENT:<detail>` | Errore transiente recuperabile (rate limit, 5xx, network) |
| `CALL_ERR:<detail>` | Errore generico non classificato nella chiamata vision |
| `PARSE_<CODE>` | Errore parsing output modello (es. `PARSE_NO_JSON_OBJECT`) |

Nel caso `PARSE_*` viene incrementato anche `ai_meal_photo_errors_total{code=...}`.
Percorso successo: solo `ai_meal_photo_requests_total{status=completed}` + latenza.

#### Mapping Fallback → Metriche (riepilogo operativo)
| Evento | Counter incrementati | Note |
|--------|----------------------|------|
| Success path (output valido) | `requests_total{phase=gpt4v,status=completed}` + latency hist | Nessun fallback/error |
| REAL_DISABLED / MISSING_API_KEY | `fallback_total{reason=...}` + success request (simulazione) | Non è un errore funzionale |
| TIMEOUT:* | `fallback_total{reason=TIMEOUT:*}` + success request | Non incrementa errors_total |
| TRANSIENT:* | `fallback_total{reason=TRANSIENT:*}` + success request | Possibile futuro retry |
| CALL_ERR:* | `fallback_total{reason=CALL_ERR:*}` + success request | Classifica generica; da specializzare |
| PARSE_* (JSON/validazione) | `fallback_total{reason=PARSE_*}` + `errors_total{code=PARSE_*}` + success request (stub) | Fallback finale a StubAdapter |

> Nota: "success request" indica comunque l'incremento di `ai_meal_photo_requests_total{status=completed}` perché l'analisi produce un output valido (anche se degradato) per la UX. Attualmente (Fase 1) la catena multi‑adapter (gpt4v→model→heuristic→stub) non è implementata: alcuni fallback reason vengono prodotti solo in simulazione / test.

### Error Code Table (Runtime & Planned)
| Code | Terminale | Categoria | Descrizione breve |
|------|-----------|-----------|-------------------|
| INVALID_IMAGE | yes | input | File non decodificabile |
| UNSUPPORTED_FORMAT | yes | input | Formato non supportato |
| IMAGE_TOO_LARGE | yes | input | Dimensione supera limite |
| BARCODE_DETECTION_FAILED | no | detection | Barcode non trovato (warning) |
| PARSE_EMPTY | yes | parse | Nessun contenuto strutturato dal modello |
| PORTION_INFERENCE_FAILED | no | portion | Stima quantità fallita (usa default) |
| RATE_LIMITED | yes | platform | Rate limit provider vision |
| INTERNAL_ERROR | yes | system | Errore generico inatteso |

Mapping metriche:
* Terminale → `ai_meal_photo_errors_total{code}` + request con `status=failed`.
* Non terminale → solo `ai_meal_photo_errors_total{code}` (status=completed) (se implementato nel layer); oggi alcuni warning possono non essere ancora contati.

---
## 7. AI Meal Photo V3 Enhancements (Novembre 2025)

### Sistema 3-Tier Enrichment
Il sistema di arricchimento è stato potenziato da un semplice fallback heuristic→default a un sistema a 3 livelli:

```
ParsedItem[] → NutrientEnrichmentService → EnrichmentResult[]
                     ↓
              1. USDA FoodData Central API (70% successo)
                     ↓ (fallback)
              2. Category Profile Mapping 
                     ↓ (fallback)
              3. Default Values
```

### Nuove Metriche V3
| Metrica | Tipo | Etichette | Descrizione |
|---------|------|-----------|-------------|
| `ai_meal_photo_enrichment_success_total` | Counter | `source` (usda\|category_profile\|default) | Successi enrichment per fonte |
| `ai_meal_photo_usda_lookup_total` | Counter | `status` (success\|failure) | Chiamate USDA API |
| `ai_meal_photo_enrichment_latency_ms` | Histogram | `source` | Latenza enrichment incluso USDA |
| `ai_meal_photo_macro_fill_ratio` | Histogram | - | Percentuale campi macro popolati |

### USDA Client Integration
- **Client completo** `usda_client.py` per FoodData Central API
- **Caching** e rate limiting automatico
- **Normalizzazione** label per massimizzare match rate
- **Fallback chain** USDA → category → default

### Prompt V3 USDA Optimization
- **Nomenclatura standardizzata**: `eggs` (non "egg white"), `chicken breast`, `rice cooked`
- **Supporto due parole** per alimenti specifici: `chicken breast`, `egg white`, `sweet potato`
- **Match rate migliorato**: +40% per eggs, chicken, potatoes

### dishName Italiano
- Campo `dish_title` dal GPT-4V per piatti locali
- Esempi: "Uova strapazzate con pancetta", "Salmone grigliato con riso"
- Campo `dishName` GraphQL popolato automaticamente

### enrichmentSource Tracking
Ogni item ora include `enrichmentSource` per trasparenza:
- `usda`: Dati da USDA FoodData Central
- `category_profile`: Profilo categoria specifica
- `default`: Valori fallback generici

---
## 8. FAQ / Troubleshooting

| Problema | Sintomo | Soluzione |
|----------|---------|-----------|
| Metriche sporcano altri test | Counter > atteso al primo assert | Verifica fixture attiva (nome corretto `conftest.py`), esegui singolo test per confermare |
| Flag non applicato | Adapter non cambia | Assicurarsi di aver impostato variabile PRIMA della chiamata a `create_or_get()` |
| Latenza test flakey | Sleep random jitter | Ridurre `REMOTE_LATENCY_MS` / `REMOTE_JITTER_MS` via monkeypatch env nel test |
| Idempotenza non funziona | Nuovo ID generato | Verifica valori input (photo_id / photo_url / user) identici e chiave non forzata |

---
## 8. GPT-4V Vision Client & Mocking (Aggiornato)

### Obiettivi del layer `vision_client`
Separare la logica di orchestrazione (adapter) dalla chiamata raw al modello vision per:
1. Rendere il test deterministico (monkeypatch su singolo simbolo).
2. Introdurre in futuro retry/backoff senza toccare l'adapter.
3. Mappare errori esterni → eccezioni semantiche (`VisionTimeoutError`, `VisionTransientError`, `VisionCallError`).

### Bridge sync → async (fase transitoria)
L'adapter oggi è sincrono e usa `asyncio.run(call_openai_vision(...))`. Limiti:
* Non invocabile da un event loop già attivo (si è risolto rendendo i test sincroni).
* Penalizza performance se chiamato molte volte in parallelo.

Prossimo step naturale: rendere `Gpt4vAdapter.analyze` async ed evitare `asyncio.run`, quindi i test potranno tornare async.

### Strategia di mocking nei test
I test patchano direttamente `inference.adapter.call_openai_vision` (non il modulo `vision_client`) perché l'import avviene a livello modulo. Questo evita che il simbolo già referenziato nell'adapter continui a puntare all'implementazione reale/skeleton.

Esempio snippet (semplificato):
```python
import inference.adapter as adapter_mod

async def _fake_call(*, image_url, prompt, timeout_s=12.0):
    return '{"items":[{"label":"x","quantity":{"value":50,"unit":"g"},"confidence":0.9}]}'

monkeypatch.setattr(adapter_mod, "call_openai_vision", _fake_call)
```

### Implementazione Reale (fase corrente)

Il file `inference/vision_client.py` ora contiene una implementazione reale della funzione
`call_openai_vision` che:

1. Valida presenza di `OPENAI_API_KEY` e `image_url`.
2. Costruisce un singolo messaggio utente multi‑part (testo prompt + image_url) per il modello
    (default `gpt-4o-mini`, override via `OPENAI_VISION_MODEL`).
3. Esegue la chiamata sincrona del client OpenAI in un executor per non bloccare l'event loop.
4. Applica un timeout hard (`asyncio.wait_for`) con default 12s (parametro `timeout_s`).
5. Mappa eccezioni → gerarchia semantica:
    - Timeout di rete / client (`ConnectTimeout`, `ReadTimeout`, `APITimeoutError`, scadenza `wait_for`) → `VisionTimeoutError`.
    - Rate limit / HTTP 5xx → `VisionTransientError`.
    - Qualsiasi altro errore API / risposta priva di contenuto → `VisionCallError`.
6. Logga sempre (anche in errore) un evento strutturato `vision.call` con campi:
    - `elapsed_ms`: durata
    - `has_image`: bool presenza URL
    - `timeout_s`: budget richiesto

Il parsing dell'output rimane responsabilità dell'adapter GPT-4V (`parse_and_validate`).

#### Variabili d'Ambiente Aggiuntive
| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `OPENAI_VISION_MODEL` | `gpt-4o-mini` | Nome modello vision usato nella chiamata |
| `OPENAI_API_KEY` | — | Chiave API necessaria per abilitare path reale |

> Nota: il flag effettivo che abilita la parte reale rimane `AI_GPT4V_REAL_ENABLED=1` (controllato nell'adapter). Senza flag o chiave viene attivato fallback simulato con reason `REAL_DISABLED` o `MISSING_API_KEY`.

#### Contratto di Errore Vision Client → Adapter
| Eccezione vision_client | Adapter fallback reason | Effetto metriche |
|-------------------------|-------------------------|------------------|
| `VisionTimeoutError` | `TIMEOUT:<detail>` | + `fallback_total` (no `errors_total`) |
| `VisionTransientError` | `TRANSIENT:<detail>` | + `fallback_total` |
| `VisionCallError` | `CALL_ERR:<detail>` | + `fallback_total` |
| Output parse‑invalid (a valle) | `PARSE_<CODE>` | + `fallback_total` + `errors_total` |

#### Logging
Esempio (formato semplificato):
```
INFO ai.vision vision.call elapsed_ms=842 has_image=True timeout_s=12.0
```
Consente di correlare outliers di latenza senza dover guardare ogni singola metrica.

### Estensioni pianificate vision_client
| Feature | Descrizione | Impatto metriche |
|---------|-------------|------------------|
| Timeout configurabile | Parametro env `AI_GPT4V_TIMEOUT_S` | Tag add-on (timeout=true) futuro |
| Retry con backoff | Retry N volte su `VisionTransientError` | Counter aggiuntivo `ai_meal_photo_retries_total` |
| Telemetria tokens | Calcolo tokens in/out (se API lo espone) | Nuovi counter/hist `ai_meal_photo_tokens_total` |
| Circuit breaker | Aprire dopo X TIMEOUT/TRANSIENT consecutivi | Fallback reason dedicato es: `CB_OPEN` |

### Linee guida future di robustezza
Integrazioni previste: retry/backoff esponendo contatori `ai_meal_photo_retries_total`, aggiunta `ai_meal_photo_tokens_total` se l'SDK espone usage, circuit breaker (raggruppato con metriche fallback cause `CB_OPEN`).


## Riferimenti Codice

## Changelog
| Versione | Modifica |
|----------|----------|
| v1 | Documento iniziale metriche + adapter pattern |
| v2 | Aggiunta tabella fallback reasons e vision client real impl |
| v3 | Nota optionalità metrics + tabella error codes completa (ott 2025) |

## Cross-link
Per il flusso completo (flusso two‑step, error taxonomy dettagliata, roadmap) fare riferimento a `../../docs/ai_meal_photo.md` (documento canonicale).
