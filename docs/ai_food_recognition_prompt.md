# AI Food Recognition Prompt (GPT-4V)

Version: v1.0 (Baseline Production Draft)

## Primary Prompt
```
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
```
Identifica gli alimenti visibili (max 5). JSON:
{"items":[{"label":"string","portion_grams":123|null,"confidence":0.5}]}
```

## Validation Rules
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
- Aggiungere enumerazione tipologia contenitore (piatto, bowl, bicchiere) per migliorare stima peso
- Richiedere bounding boxes se si integra segmentazione
