# AI Food Recognition Prompt (GPT-4V)

Version: v0.2-spec (dish_name draft, normalization prep)
Stato Corrente: runtime attuale usa GPT‑4V adapter (source=gpt4v) con prompt v2 in valutazione A/B; il campo `dishName` (issue #56) non è ancora esposto nello schema GraphQL (PLANNED). Questo documento definisce lo schema target imminente.

Documento correlato (stub corrente): [AI Meal Photo Analysis](ai_meal_photo.md)

## Primary Prompt (Draft v0.2)

```text
Sei un assistente per ESTRARRE alimenti da una FOTO.
REGOLE IMPORTANTI:
- Massimo 5 elementi.
- NON inventare ingredienti o condimenti non chiaramente visibili.
- Se incerto usare label "unknown".
- Stima porzione in grammi interi (o ml per liquidi); se impossibile usa null.
- NON fornire informazioni nutrizionali.
- Rispondi SOLO con JSON valido.
SCHEMA OUTPUT:
{
  "dish_name": "string | null",
  "items": [
    { "label": "string", "portion_grams": 120 | null, "confidence": 0.73 }
  ]
}

Linee Guida dish_name:
- Rappresenta il piatto complessivo (es: "grilled salmon with rice", "chicken salad").
- Se gli alimenti non formano un piatto coerente lascia null.
- Non inventare ingredienti non visibili. Evitare aggettivi superflui ("delicious", "tasty").
```

## Fallback Prompt (Parse Error)

```text
Identifica gli alimenti visibili (max 5). JSON:
{"dish_name":null,"items":[{"label":"string","portion_grams":123|null,"confidence":0.5}]}
```

## Validation Rules (Da Implementare)

- JSON parsable (nessun trailing comma)
- `confidence` ∈ [0,1]
- Se porzione null → UI chiederà input manuale
- Non aggiungere testo fuori JSON

## Post-Processing Mapping

| Campo | Azione |
|-------|-------|
| dish_name | lowercase, trim, multi-spaces→singolo, null se stringa vuota |
| label | lowercase, trim, remove adjectives superflui |
| portion_grams | se >2000 scarta (probabile errore) |
| confidence | clamp 0..1 |

## Rejection Criteria

- Output non JSON → retry fallback
- items vuoto & nessun errore → ritorna lista vuota (UI mostra stato “Nessun alimento”)

## Security & Privacy Note

- L'immagine potrebbe essere stata offuscata (volti/background) prima dell'invio.

## Evoluzioni Future (Note)
- Bounding boxes quando disponibile segmentazione per portion heuristics.
- Campi opzionali `container_type`, `is_mixed_dish` per modulare stima porzioni.
- Integrazione Phase 2.1: category hints (NON richieste al modello, derivano da normalizzazione server-side).

## Integrazione Pipeline
| Fase | Uso Prompt | Note |
|------|------------|------|
| 0 (Stub) | Nessuno | Items sintetici deterministici |
| 1 | Primary + fallback | Introduzione detection errori + retry limit 1 |
| 2 | Primary adattivo | Prompt modulato da risultati barcode / dizionario locale |
| 2.1 | Primary v0.2 | dish_name estratto; normalization server (dry-run) |

## Linee Guida Stabilità
* NO cambi di schema output senza bump versione prompt + aggiornamento parser.
* Aggiunta nuovi campi sempre opzionali e documentati qui prima del rollout.

- Aggiungere enumerazione tipologia contenitore (piatto, bowl, bicchiere) per migliorare stima peso
- Richiedere bounding boxes se si integra segmentazione
