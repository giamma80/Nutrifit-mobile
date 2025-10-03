## AI Meal Photo – Error Taxonomy (Draft)

Stato: DRAFT (non ancora esposto nello schema GraphQL) – riferito all'Issue 33 in `audit_issues.md`.

Obiettivi:
* Fornire enum stabile e versionabile per gli errori dell'analisi foto pasto.
* Separare errori "blocking" (status→FAILED) da avvisi / fallback (status può restare COMPLETED ma con degradazione qualità).
* Permettere al client di adattare UX: retry, messaggi, degradazione silenziosa.

### Enum Proposta

```graphql
# NON ancora nel runtime SDL.
enum MealPhotoAnalysisErrorCode {
  # Input / validazione immagine
  INVALID_IMAGE            # Dati non decodificabili / non immagine
  UNSUPPORTED_FORMAT       # Formato non supportato (es: HEIC se non convertito)
  IMAGE_TOO_LARGE          # Supera limiti byte/pixel (config)

  # Pipeline heuristica / estrazione
  BARCODE_DETECTION_FAILED # Atteso barcode-first path ma non trovato (warning)
  PARSE_EMPTY              # Parser non ha estratto alcun item (blocking: status FAILED)
  PORTION_INFERENCE_FAILED # Quantità non determinabile → default utilizzato

  # Controlli di sicurezza / limiti
  RATE_LIMITED             # Rate limit superato (blocking)

  # Sistema
  INTERNAL_ERROR           # Eccezione non mappata
}
```

### Tipo Error Dettagliato

```graphql
type MealPhotoAnalysisError {
  code: MealPhotoAnalysisErrorCode!
  message: String!              # Localizzabile lato client, stringa server = fallback
  severity: MealPhotoErrorSeverity! # ERROR | WARNING
  debugId: String               # Correlazione log (solo in env non-prod?)
  fallbackApplied: Boolean      # true se il sistema ha degradato (es: default quantity)
}

enum MealPhotoErrorSeverity { ERROR WARNING }
```

### Superficie nel GraphQL (Incrementale)
1. Fase 1: Aggiungere campo opzionale `analysisErrors: [MealPhotoAnalysisError!]!` a `MealPhotoAnalysis`.
   * Backward compat: nuovo campo non rompe client esistenti.
   * Lista vuota = nessun errore/avviso.
2. Fase 2: Possibile aggiunta `failureReason: MealPhotoAnalysisErrorCode` quando `status=FAILED` (solo errori blocking).

### Mappatura Semantica
| Scenario | status | errors[] | Note UX |
|----------|--------|----------|---------|
| Immagine corrotta | FAILED | [INVALID_IMAGE] | Mostrare retry immediato |
| Formato non supportato | FAILED | [UNSUPPORTED_FORMAT] | Suggerire conversione / scatto nuovo |
| Rate limit superato | FAILED | [RATE_LIMITED] | Messaggio attesa / upgrade |
| Parser vuoto (nessun alimento riconosciuto) | FAILED | [PARSE_EMPTY] | Suggerire nuovo scatto o inserimento manuale |
| Barcode assente | COMPLETED | [BARCODE_DETECTION_FAILED] | Silenzioso o info icon |
| Portion inference fallita | COMPLETED | [PORTION_INFERENCE_FAILED] | Mostrare quantità editabile evidenziata |
| Eccezione generica | FAILED | [INTERNAL_ERROR] | Messaggio generico + debugId se support |

### Regole di Severità
* severity=ERROR → può portare a status=FAILED (blocking) oppure (se recupero parziale) status COMPLETED ma con qualità ridotta (caso raro – da evitare per semplicità iniziale).
* severity=WARNING → status resta COMPLETED.

### Logging & Metrics (collegato a Issue 29)
Per ogni errore:
* Counter `ai_meal_photo_errors_total{code, severity}`
* Se severity=ERROR → incrementare anche `ai_meal_photo_failed_total{code}`

### Backward Compatibility & Evoluzione
* Aggiunta di nuovi `code` è backward compatibile.
* Rimozione o change semantico di `code` richiede MAJOR nel changelog API.
* Introduzione di severity aggiuntive (INFO) post-Fase 1 è safe (client ignoreranno valori ignoti se gestito correttamente).

### Requisiti Implementativi (Fase 1)
1. Implementare enum + tipi.
2. Aggiungere lista `analysisErrors` sempre valorizzata (almeno []).
3. Stub attuale restituisce lista vuota.
4. Heuristic adapter popola codici PARSE_EMPTY, BARCODE_DETECTION_FAILED, PORTION_INFERENCE_FAILED quando applicabile.
5. Mappare eccezioni generiche a INTERNAL_ERROR con debugId (uuid4 short) solo se non ambiente prod (config?).

### Test di Accettazione
* analyzeMealPhoto senza problemi → `analysisErrors=[]`.
* Forzare scenario parser vuoto (input artificiale) → `errors[0].code=PARSE_EMPTY`, status FAILED.
* Simulare invalid image (mock adapter) → status FAILED + `INVALID_IMAGE`.

---
Versione documento: 0.1 (draft)
