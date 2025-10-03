# AI Food Recognition Prompt (GPT-4V)

Version: v0.1-spec (Allineato al design – non attivo runtime)
Stato Corrente: la pipeline runtime usa uno STUB (`source=STUB`) e NON invoca ancora GPT-4V. Questo documento definisce il prompt previsto per la Fase 1.

Documento correlato (stub corrente): [AI Meal Photo Analysis](ai_meal_photo.md)

## Primary Prompt (Draft)

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
  "items": [
    { "label": "string", "portion_grams": 120 | null, "confidence": 0.73 }
  ]
}
```

## Fallback Prompt (Parse Error)

```text
Identifica gli alimenti visibili (max 5). JSON:
{"items":[{"label":"string","portion_grams":123|null,"confidence":0.5}]}
```

## Validation Rules (Da Implementare)

- JSON parsable (nessun trailing comma)
- `confidence` ∈ [0,1]
- Se porzione null → UI chiederà input manuale
- Non aggiungere testo fuori JSON

## Post-Processing Mapping

| Campo | Azione |
|-------|-------|
| label | lowercase, trim, remove adjectives superflui |
| portion_grams | se >2000 scarta (probabile errore) |
| confidence | clamp 0..1 |

## Rejection Criteria

- Output non JSON → retry fallback
- items vuoto & nessun errore → ritorna lista vuota (UI mostra stato “Nessun alimento”)

## Security & Privacy Note

- L'immagine potrebbe essere stata offuscata (volti/background) prima dell'invio.

## Evoluzioni Future (Note)
- Aggiungere bounding boxes SOLO quando disponibile segmentazione per sfruttare portion heuristics (riduce prompt size).
- Introdurre campi opzionali `container_type`, `is_mixed_dish` per modulare stima porzioni.

## Integrazione Pipeline
| Fase | Uso Prompt | Note |
|------|------------|------|
| 0 (Stub) | Nessuno | Items sintetici deterministici |
| 1 | Primary + fallback | Introduzione detection errori + retry limit 1 |
| 2 | Primary adattivo | Prompt modulato da risultati barcode / dizionario locale |

## Linee Guida Stabilità
* NO cambi di schema output senza bump versione prompt + aggiornamento parser.
* Aggiunta nuovi campi sempre opzionali e documentati qui prima del rollout.

- Aggiungere enumerazione tipologia contenitore (piatto, bowl, bicchiere) per migliorare stima peso
- Richiedere bounding boxes se si integra segmentazione
