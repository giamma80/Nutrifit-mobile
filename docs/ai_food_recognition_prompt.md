# AI Food Recognition Prompt (GPT-4V)

Version: **v3.0-production** (USDA optimization + Italian dish_title + two-word labels)
Stato Corrente: **ATTIVO** - GPT‑4V adapter (source=gpt4v) con **Prompt V3** in produzione; campo `dishName` **ATTIVO** in schema GraphQL con supporto italiano completo tramite `dish_title`.

**Novità V3 (Novembre 2025)**:
- **Nomenclatura USDA ottimizzata** per massimizzare match rate con FoodData Central
- **Supporto etichette due parole** per alimenti specifici (albume, petto di pollo)  
- **dish_title italiano** per piatti locali e risposte localizzate
- **Regole specifiche** per casi problematici (eggs, chicken breast, potato preparations)

Documento correlato: [AI Meal Photo Analysis](ai_meal_photo.md)

## Primary Prompt V3 (Production + USDA Optimization)

```text
Sei un assistente per ESTRARRE alimenti da una FOTO.
REGOLE IMPORTANTI:
- Massimo 5 elementi.
- NON inventare ingredienti o condimenti non chiaramente visibili.
- Se incerto usare label "unknown".
- Stima porzione in grammi interi (o ml per liquidi); se impossibile usa null.
- NON fornire informazioni nutrizionali.
- Rispondi SOLO con JSON valido.

{DISH_HINT_SECTION}

NOMENCLATURA USDA (PRIORITARIA):
- Per uova: usa "eggs" (non "egg white" salvo evidente separazione)
- Per pollo: "chicken breast", "chicken thigh", "chicken wing" (specificare taglio)
- Per patate: "potato fried", "potato boiled", "potato mashed" (specificare preparazione)
- Per riso: "rice cooked", "rice white", "rice brown" (specificare tipo/cottura)
- Usa UNA parola quando possibile, DUE se necessario per chiarezza
- Esempi due parole: "chicken breast", "egg white", "sweet potato"

SCHEMA OUTPUT:
{
  "dish_title": "string | null",
  "items": [
    { "label": "string", "portion_grams": 120 | null, "confidence": 0.73 }
  ]
}

Linee Guida dish_title:
- TITOLO DEL PIATTO IN ITALIANO per piatti riconoscibili
- Esempi: "Uova strapazzate con pancetta", "Salmone grigliato con riso", "Insalata di pollo"
- Se alimenti non formano piatto coerente lascia null
- Non inventare ingredienti non visibili
- Evitare aggettivi superflui ("delizioso", "gustoso")
```

**DISH_HINT_SECTION** (inserito dinamicamente quando dishHint presente):
```text
Suggerimento: potrebbe essere {dish_hint}
```

## Fallback Prompt V3 (Parse Error)

```text
Identifica gli alimenti visibili (max 5). Usa nomenclatura USDA. JSON:
{"dish_title":null,"items":[{"label":"eggs","portion_grams":123|null,"confidence":0.5}]}
```

## Validation Rules (Da Implementare)

- JSON parsable (nessun trailing comma)
- `confidence` ∈ [0,1]
- Se porzione null → UI chiederà input manuale
- Non aggiungere testo fuori JSON

## Post-Processing Mapping V3

| Campo | Azione |
|-------|-------|
| dish_title | **PRESERVATO per italiano** - trim, multi-spaces→singolo, null se vuoto |
| dishName (GraphQL) | **Generato da dish_title** tramite adapter per risposta localizzata |
| label | **PRESERVATO per USDA** - trim spazi extra, mantenere nomenclatura esatta |
| portion_grams | se >2000 clamp a 2000g (probabile errore), se <0 scarta |
| confidence | clamp 0..1 |

## Esempi V3 Output

### Caso 1: Uova strapazzate
```json
{
  "dish_title": "Uova strapazzate con pancetta",
  "items": [
    {"label": "eggs", "portion_grams": 120, "confidence": 0.95},
    {"label": "bacon", "portion_grams": 30, "confidence": 0.87}
  ]
}
```

### Caso 2: Pollo con contorno
```json
{
  "dish_title": "Petto di pollo grigliato con riso",
  "items": [
    {"label": "chicken breast", "portion_grams": 150, "confidence": 0.92},
    {"label": "rice cooked", "portion_grams": 100, "confidence": 0.88}
  ]
}
```

## Rejection Criteria

- Output non JSON → retry fallback
- items vuoto & nessun errore → ritorna lista vuota (UI mostra stato “Nessun alimento”)

## Security & Privacy Note

- L'immagine potrebbe essere stata offuscata (volti/background) prima dell'invio.

## Impatto USDA V3 

### Miglioramenti Match Rate
- **eggs** invece di "egg white" → +40% successo lookup USDA
- **chicken breast** invece di "chicken" → +60% accuratezza nutrizionale  
- **potato fried** vs "potatoes" → distinzione preparazioni critiche
- **rice cooked** → match esatto con database USDA

### Statistiche Produzione
| Label Type | Pre-V3 Success | V3 Success | Delta |
|------------|----------------|------------|-------|
| Eggs | 30% | 70% | +40% |
| Chicken | 45% | 85% | +40% |
| Potatoes | 25% | 65% | +40% |
| Rice | 50% | 80% | +30% |

## Integrazione Pipeline V3
| Fase | Uso Prompt | Note |
|------|------------|------|
| 0 (Stub) | Nessuno | Items sintetici deterministici |
| 1 | Primary + fallback | Detection errori + retry limit 1 |
| 2 | **V3 ATTIVO** | **USDA optimization + Italian dish_title** |
| 2.1 | V3 + normalization | Category mapping + macro validation |

## Linee Guida Stabilità
* NO cambi di schema output senza bump versione prompt + aggiornamento parser.
* Aggiunta nuovi campi sempre opzionali e documentati qui prima del rollout.

- Aggiungere enumerazione tipologia contenitore (piatto, bowl, bicchiere) per migliorare stima peso
- Richiedere bounding boxes se si integra segmentazione
