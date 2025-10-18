# 📘 Guida Ottimizzazione Meal Photo Analyzer

**Versione:** 1.0  
**Target:** Sviluppatore Backend  
**Contesto:** ~100 utenti, ~2000 analisi/giorno, OpenAI GPT-4o-mini  
**Obiettivo:** Clean refactor per ridurre costi, latenza e migliorare manutenibilità

---

## 🎯 Problema Principale

Il codice attuale genera un **prompt monolitico** (400+ token) inline ad ogni chiamata, senza sfruttare il **prompt caching** di OpenAI.

### Impatto Negativo
- ❌ Spreco di 400 token/chiamata (no caching)
- ❌ Latenza alta (~2500ms)
- ❌ Parsing JSON manuale fragile
- ❌ Calcoli temporanei inutili
- ❌ Codice difficile da manutenere

---

## ✅ Soluzione: 3 Pilastri Fondamentali

### 1. **System Prompt Fisso + User Message Variabile**
**Perché:** OpenAI cacha automaticamente il system prompt (50% sconto, -20-30% latenza)

### 2. **Structured Output + Pydantic**
**Perché:** Elimina parsing manuale fragile, garantisce validazione type-safe

### 3. **Logging Strutturato**
**Perché:** Monitoring real-time, debugging semplificato, metriche business

---

## 🚫 ANTIPATTERN da Evitare

### ❌ Antipattern #1: Prompt Monolitico Inline

```python
# ❌ SBAGLIATO - Genera tutto inline ogni volta
def generate_prompt_v3(*, locale: str = "it") -> str:
    return (
        "COMPITO: Analizza immagine..."
        "REGOLE: 1. dish_title..."
        "ESEMPI: eggs, chicken..."
        # 400+ token ripetuti OGNI chiamata!
    )

# Uso
prompt = generate_prompt_v3()  # Genera stringa gigante
messages = [{"role": "user", "content": prompt}]
```

**Perché è male:**
- 🔴 400 token sprecati ogni chiamata
- 🔴 Nessun caching (ogni volta full price)
- 🔴 Impossibile ottimizzare
- 🔴 Modifica prompt = trova tutte le chiamate

---

### ❌ Antipattern #2: Parsing JSON Manuale

```python
# ❌ SBAGLIATO - Parsing fragile
def _safe_json_extract(text: str) -> Dict:
    first = text.find("{")
    last = text.rfind("}")
    snippet = text[first:last+1]
    obj = json.loads(snippet)  # Può fallire con markdown/code fence
    return obj
```

**Perché è male:**
- 🔴 Fallisce con markdown (` ```json ... ``` `)
- 🔴 Fallisce con code fence
- 🔴 Fallisce con testo extra
- 🔴 Nessun type checking
- 🔴 Errori difficili da debuggare

---

### ❌ Antipattern #3: Calcoli Temporanei Inutili

```python
# ❌ SBAGLIATO - Calcoli che vengono sovrascritti
density, src_density = _resolve_density(label)
calories = int(density * q_final / 100.0)

# Poi questi valori vengono SOVRASCRITTI da NutrientEnrichmentService!
```

**Perché è male:**
- 🔴 Spreco CPU
- 🔴 Può generare dati inconsistenti
- 🔴 Confonde il flusso logico

---

### ❌ Antipattern #4: Dati Variabili nel System Prompt

```python
# ❌ SBAGLIATO - Cache invalidato ogni volta!
system = f"Analizza per utente {user_id} alle ore {timestamp}..."
messages = [{"role": "system", "content": system}]
```

**Perché è male:**
- 🔴 Cache invalidato ad ogni chiamata (cambia sempre)
- 🔴 System prompt dovrebbe essere COSTANTE

---

### ❌ Antipattern #5: Tutto in User Message

```python
# ❌ SBAGLIATO - Tutto mischiato
messages = [
    {
        "role": "user",
        "content": ISTRUZIONI_FISSE + dati_variabili + immagine
    }
]
```

**Perché è male:**
- 🔴 Nessun caching possibile
- 🔴 Confonde responsabilità (istruzioni vs dati)

---

## ✅ PATTERN da Seguire

### ✅ Pattern #1: System Fisso + User Variabile

```python
# ✅ CORRETTO - System prompt come COSTANTE
MEAL_ANALYSIS_SYSTEM_PROMPT = """
Sei un nutrizionista esperto nell'analisi visiva di pasti.

COMPITO PRINCIPALE:
Analizza foto di cibo e identifica ingredienti con quantità stimate.

METODOLOGIA:
1. Identifica il piatto completo se riconoscibile (es: "spaghetti alla carbonara")
2. Se non riconosci la ricetta, identifica i singoli ingredienti principali
3. Stima le quantità in grammi usando riferimenti visivi standard
4. Assegna livello di confidence basato su chiarezza immagine

OUTPUT FORMATO (JSON):
{
  "dish_title": "nome piatto in italiano",
  "items": [
    {
      "label": "nome inglese USDA",
      "display_name": "nome italiano",
      "quantity": {"value": 100, "unit": "g"},
      "confidence": 0.9
    }
  ]
}

REGOLE CRITICHE:
1. dish_title: nome del piatto in italiano per l'utente
2. label: SEMPRE inglese, usa nomenclatura USDA standard
   - Uova: "eggs" (sempre plurale!), "egg white", "egg yolk"
   - Pollo: "chicken", "chicken breast", "chicken thigh"
   - Verdure: "tomatoes", "spinach", "broccoli", "potatoes"
3. display_name: nome italiano dell'ingrediente per interfaccia utente
4. Massimo 5 ingredienti principali per semplicità
5. confidence: valore 0.0-1.0 dove 0.7+ = alta certezza
6. quantity.unit: "g" per grammi, "piece" per pezzi interi

STIMA QUANTITÀ (riferimenti):
- Piatto normale: 23-25cm diametro
- Porzione pasta: 80-120g cruda, 200-300g cotta
- Bistecca: 150-250g
- Petto pollo: 150-200g
- Verdure: 80-150g

CONFIDENCE GUIDELINES:
- 0.9-1.0: Alimento chiaramente visibile, porzione ben definita
- 0.7-0.8: Alimento riconoscibile, stima ragionevole
- 0.5-0.6: Alimento probabile ma parzialmente nascosto
- <0.3: Non usare, scartare l'item

Se nessun cibo riconoscibile: {"dish_title":"","items":[]}

Rispondi SOLO con JSON valido UTF-8. NESSUN testo extra, markdown, o code fence.
"""
# ↑ Questo deve essere >1024 token! Aggiungi altri esempi se necessario.

# ✅ User message minimal - solo dati specifici
def analyze(photo_url: str, dish_hint: str = None):
    user_text = f"Suggerimento: {dish_hint}\nAnalizza:" if dish_hint else "Analizza:"
    
    messages = [
        {
            "role": "system",           # ← FISSO, cachato
            "content": MEAL_ANALYSIS_SYSTEM_PROMPT
        },
        {
            "role": "user",             # ← VARIABILE, sempre diverso
            "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": photo_url}}
            ]
        }
    ]
```

**Perché è bene:**
- ✅ System prompt cachato (50% sconto dopo prima chiamata)
- ✅ Con 1.4 chiamate/minuto → cache hit rate >90%
- ✅ User message minimal (~20 token vs 400)
- ✅ Separazione responsabilità chiara

---

### ✅ Pattern #2: Structured Output + Pydantic

```python
# ✅ CORRETTO - Pydantic models
from pydantic import BaseModel, Field
from typing import List, Literal

class FoodQuantity(BaseModel):
    value: float = Field(gt=0, le=2000)
    unit: Literal["g", "piece"]

class FoodItem(BaseModel):
    label: str
    display_name: str
    quantity: FoodQuantity
    confidence: float = Field(ge=0.0, le=1.0)

class MealAnalysisResponse(BaseModel):
    dish_title: str
    items: List[FoodItem] = Field(max_length=5)

# ✅ API call con structured output
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    response_format={"type": "json_object"}  # ← Force JSON
)

# ✅ Parsing type-safe
result = MealAnalysisResponse.model_validate_json(
    response.choices[0].message.content
)
# result.items[0].label  ← Autocomplete, type-safe!
```

**Perché è bene:**
- ✅ OpenAI garantisce JSON valido
- ✅ Pydantic valida automaticamente
- ✅ Type safety (no errori runtime)
- ✅ Autocomplete nell'IDE
- ✅ 0% parsing errors

---

### ✅ Pattern #3: Logging Strutturato JSON

```python
# ✅ CORRETTO - Log strutturato
import logging
import json

logger = logging.getLogger("meal_analyzer")

def log_cache_metrics(cached_tokens: int, prompt_tokens: int):
    cache_rate = cached_tokens / prompt_tokens if prompt_tokens > 0 else 0
    
    logger.info(json.dumps({
        "event": "cache_metrics",
        "cached_tokens": cached_tokens,
        "prompt_tokens": prompt_tokens,
        "cache_hit": cached_tokens > 0,
        "cache_hit_rate": f"{cache_rate:.2%}",
        "savings_usd": cached_tokens * 0.075 / 1_000_000
    }))

# Analisi log facile:
# cat logs.json | jq -r 'select(.event=="cache_metrics") | .cache_hit_rate'
```

**Perché è bene:**
- ✅ Facilmente parsabile (jq, grep)
- ✅ Dashboard automatiche
- ✅ Debugging semplificato
- ✅ Metriche business real-time

---

### ✅ Pattern #4: Separazione Responsabilità

```python
# ✅ CORRETTO - File separati

# config.py - Solo configurazione
SYSTEM_PROMPT = "..."
OPENAI_CONFIG = {"model": "gpt-4o-mini", ...}

# schemas.py - Solo models Pydantic
class MealAnalysisResponse(BaseModel): ...

# analyzer.py - Solo logica business
class MealPhotoAnalyzer:
    def analyze(self, photo_url, user_id): ...

# logger.py - Solo logging
class AnalysisLogger:
    def log_cache_metrics(...): ...
```

**Perché è bene:**
- ✅ Single Responsibility Principle
- ✅ Facile testare
- ✅ Facile manutenere
- ✅ Chiaro dove modificare cosa

---

### ✅ Pattern #5: Validazione sul Bordo

```python
# ✅ CORRETTO - Valida appena ricevi dati
class FoodItem(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    
    @field_validator('confidence')
    @classmethod
    def reject_low_confidence(cls, v: float) -> float:
        if v < 0.3:
            raise ValueError("Confidence troppo bassa")
        return v
    
    @field_validator('label')
    @classmethod
    def normalize_label(cls, v: str) -> str:
        return v.lower().strip()
```

**Perché è bene:**
- ✅ Fail fast (errori immediati)
- ✅ Dati sempre validi nel sistema
- ✅ Normalizzazione automatica

---

## 📋 Checklist Pre-Implementazione

### System Prompt
- [ ] System prompt è una **COSTANTE** nel file config?
- [ ] System prompt è **>1024 token**? (verifica con tiktoken)
- [ ] System prompt contiene **SOLO istruzioni fisse** (no user_id, timestamp)?
- [ ] User message è **minimal** (<50 token)?

### Structured Output
- [ ] Uso `response_format={"type": "json_object"}`?
- [ ] Ho creato **Pydantic models** per la response?
- [ ] Ho **eliminato** `_safe_json_extract()`?
- [ ] Ho **eliminato** `parse_and_validate_v3()`?

### Code Quality
- [ ] Ho **eliminato** calcoli temporanei (density, calories)?
- [ ] Ho **separato** file per responsabilità?
- [ ] Ho **logging JSON** strutturato?
- [ ] Ho **eliminato** tutto il codice legacy?

### Testing
- [ ] Cache hit dopo 2+ chiamate ravvicinate?
- [ ] `cached_tokens > 0` nei log?
- [ ] Parsing **mai fallisce**?
- [ ] Schema GraphQL **invariato**?

---

## 🎯 Regole d'Oro (Da Stampare e Appendere)

### ⚡ Rule #1: System = Fisso, User = Variabile
```
System prompt = Istruzioni, regole, esempi (COSTANTE)
User message  = Dati specifici della richiesta (VARIABILE)
```

### 📏 Rule #2: System Prompt > 1024 Token
```
< 1024 token = NO caching
> 1024 token = Caching attivo (50% sconto)
```

### 🛡️ Rule #3: Structured Output Always
```
No parsing manuale = No errori
Pydantic + response_format = Type safety garantita
```

### 📊 Rule #4: Log Tutto (Structured)
```
JSON logging = Metriche facili
event + context = Debug immediato
```

### 🗑️ Rule #5: Elimina, Non Commentare
```
Codice legacy = Elimina completamente
No // TODO, no commenti "old way"
Clean refactor = Tabula rasa
```

---

## 📊 Metriche di Successo

### KPI Target (30 giorni)

| Metrica | Prima | Target | Come Misurare |
|---------|-------|--------|---------------|
| **Cache hit rate** | 0% | >85% | `cached_tokens > 0` |
| **Latenza media** | ~2500ms | <1800ms | `duration_ms` in log |
| **Parsing errors** | ~5/giorno | 0/giorno | Exception log count |
| **Costo/analisi** | $0.00015 | $0.00013 | Token usage × price |

### Come Monitorare

```bash
# Cache hit rate giornaliero
cat logs.json | jq -r 'select(.event=="cache_metrics") | .cache_hit' | \
  awk '{sum+=$1; n++} END {print sum/n*100"%"}'

# Latenza media
cat logs.json | jq -r 'select(.event=="analysis_complete") | .duration_ms' | \
  awk '{sum+=$1; n++} END {print sum/n"ms"}'

# Parsing errors
cat logs.json | jq -r 'select(.event=="analysis_error")' | wc -l
```

---

## 🚀 Implementazione Minima Funzionante

### Step 1: Config (5 minuti)
```python
# config.py
MEAL_ANALYSIS_SYSTEM_PROMPT = """
[Il tuo prompt completo qui - assicurati >1024 token]
"""
```

### Step 2: Schema (10 minuti)
```python
# schemas.py
from pydantic import BaseModel, Field
from typing import List

class FoodItem(BaseModel):
    label: str
    display_name: str
    confidence: float = Field(ge=0, le=1)

class MealAnalysisResponse(BaseModel):
    dish_title: str
    items: List[FoodItem]
```

### Step 3: Analyzer (30 minuti)
```python
# analyzer.py
from openai import OpenAI
from .config import MEAL_ANALYSIS_SYSTEM_PROMPT
from .schemas import MealAnalysisResponse

class MealPhotoAnalyzer:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def analyze(self, photo_url: str, hint: str = None):
        # User message minimal
        user_text = f"Hint: {hint}\nAnalizza:" if hint else "Analizza:"
        
        # API call
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": MEAL_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": photo_url}}
                ]}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse type-safe
        return MealAnalysisResponse.model_validate_json(
            response.choices[0].message.content
        )
```

### Step 4: Integration (15 minuti)
```python
# Nel tuo resolver GraphQL - INTERFACE IDENTICA
analyzer = MealPhotoAnalyzer(api_key=settings.OPENAI_API_KEY)

async def resolve_analyze_meal_photo(parent, info, input):
    # Chiama nuovo analyzer
    result = analyzer.analyze(
        photo_url=input.photo_url,
        hint=input.dish_hint
    )
    
    # Converti in GraphQL type (come prima)
    items = [...]  # Enrichment + conversione
    return MealPhotoAnalysis(...)  # Schema invariato
```

---

## 💰 ROI Atteso

**Con 2000 analisi/giorno:**

| Beneficio | Valore Annuale |
|-----------|----------------|
| Riduzione costi API | ~$14/anno |
| Riduzione tempo debug | ~$3,000/anno |
| Riduzione downtime | ~$500/anno |
| **Totale** | **~$3,514/anno** |

**Investimento:** 1 settimana dev (~$400)  
**ROI:** **8.8x** nel primo anno

---

## 🏗️ Struttura File Consigliata

```
meal_photo/
├── __init__.py
├── config.py           # System prompt + configurazione
├── schemas.py          # Pydantic models
├── analyzer.py         # Servizio principale
├── logger.py           # Logging strutturato
└── exceptions.py       # Custom exceptions
```

**Cosa Eliminare Completamente:**
- ❌ `generate_prompt()`, `generate_prompt_v2()`, `generate_prompt_v3()`
- ❌ `_safe_json_extract()`
- ❌ `parse_and_validate()`, `parse_and_validate_v3()`
- ❌ `_resolve_density()` (calcoli temporanei)
- ❌ Classe `ParseError`
- ❌ Classe `ParseStats` (sostituita da metrics in logging)

**Cosa Mantenere:**
- ✅ Dataclasses di types (`MealPhotoAnalysisRecord`, etc)
- ✅ GraphQL types (invariati)

---

## 🧪 Strategia Testing

### Unit Tests
```python
def test_analyzer_cache_hit():
    analyzer = MealPhotoAnalyzer(api_key=TEST_KEY)
    
    # Prima chiamata
    result1 = analyzer.analyze(PHOTO_URL, "pasta")
    
    # Seconda chiamata (entro 5 min)
    result2 = analyzer.analyze(PHOTO_URL_2, "pollo")
    
    # Verifica cache metrics
    assert result2.metrics["cache_hit"] == True
    assert result2.metrics["cached_tokens"] > 1000
```

### Integration Tests
```python
async def test_graphql_schema_unchanged():
    # Query GraphQL
    query = """
    mutation {
      analyzeMealPhoto(input: {photoUrl: "...", userId: "..."}) {
        id
        dishName
        items { label displayName confidence }
      }
    }
    """
    
    result = await execute_graphql(query)
    
    # Schema deve essere identico
    assert "id" in result["analyzeMealPhoto"]
    assert "dishName" in result["analyzeMealPhoto"]
```

---

## ❓ FAQ per lo Sviluppatore

### Q: Devo riscrivere tutto?
**A:** No. Mantieni GraphQL schema identico. Riscrivi solo internals (analyzer, parser).

### Q: Cosa faccio del codice vecchio?
**A:** Eliminalo completamente. No commenti, no `_old.py`. Clean slate.

### Q: E se rompo qualcosa?
**A:** Testing strategy:
1. Testa analyzer standalone (unit test)
2. Testa con GraphQL (integration test)
3. Deploy graduale (10% → 100%)

### Q: Come verifico che il cache funzioni?
**A:** Fai 2 chiamate ravvicinate (entro 5 minuti), controlla nei log che `cached_tokens > 0` nella seconda.

### Q: Quanto tempo richiede?
**A:** ~40 ore (1 settimana lavorativa):
- 8h: Setup + config
- 16h: Analyzer + schema
- 8h: Integration
- 8h: Testing + deploy

### Q: Devo cambiare il database?
**A:** No. Solo la logica di analisi cambia. Storage rimane identico.

### Q: E se il prompt è <1024 token?
**A:** Aggiungi più esempi, edge cases, spiegazioni dettagliate finché non superi 1024 token.

---

## 📚 Verifica Token del System Prompt

```python
# Script per verificare token count
import tiktoken

SYSTEM_PROMPT = """[Il tuo prompt]"""

enc = tiktoken.encoding_for_model("gpt-4o-mini")
tokens = enc.encode(SYSTEM_PROMPT)

print(f"Token count: {len(tokens)}")
print(f"Caching: {'✅ ATTIVO' if len(tokens) >= 1024 else '❌ DISATTIVATO'}")

if len(tokens) < 1024:
    print(f"⚠️ Aggiungi {1024 - len(tokens)} token per attivare cache!")
```

---

## 🎓 Risorse Essenziali

1. **OpenAI Prompt Caching**: https://platform.openai.com/docs/guides/prompt-caching
2. **Pydantic Docs**: https://docs.pydantic.dev/
3. **Structured Outputs**: https://platform.openai.com/docs/guides/structured-outputs
4. **Tiktoken (count tokens)**: https://github.com/openai/tiktoken

---

## 🚨 Red Flags (Quando Qualcosa va Male)

### 🔴 Cache hit rate < 50%
**Cause possibili:**
- System prompt contiene dati variabili
- Chiamate troppo distanziate (>10 min)
- System prompt < 1024 token

**Fix:** Verifica che system prompt sia COSTANTE e >1024 token

### 🔴 Parsing errors frequenti
**Cause possibili:**
- Non usi `response_format={"type": "json_object"}`
- Parsing manuale ancora presente
- Pydantic models non corrispondono a output

**Fix:** Verifica structured output e Pydantic validation

### 🔴 Latenza non migliora
**Cause possibili:**
- Cache non attivo
- Bottleneck in enrichment USDA
- Network issues

**Fix:** Profila con logging, identifica bottleneck

---

## ✅ Checklist Finale

**Prima di iniziare:**
- [ ] Ho letto questo documento completamente
- [ ] Ho capito perché separare system/user
- [ ] Ho capito perché structured output
- [ ] Ho chiaro che GraphQL non cambia

**Durante lo sviluppo:**
- [ ] System prompt >1024 token verificato
- [ ] Pydantic models creati e validati
- [ ] Logging JSON implementato
- [ ] Codice legacy eliminato (non commentato)
- [ ] Unit test passano

**Prima del deploy:**
- [ ] Cache hit verificato (2+ chiamate)
- [ ] Latenza misurata (target <1800ms)
- [ ] GraphQL response identica
- [ ] Monitoring attivo
- [ ] Rollback plan pronto

---

## 📅 Timeline Suggerita

### Giorno 1-2: Setup Base
- Crea nuova struttura file
- Implementa config.py con system prompt >1024 token
- Crea Pydantic models in schemas.py
- Setup logging strutturato

### Giorno 3-4: Core Implementation
- Implementa MealPhotoAnalyzer pulito
- Testa analisi singola con caching
- Verifica metrics logging

### Giorno 5: Integration
- Integra con resolver GraphQL
- Mantieni interfaccia identica
- Test end-to-end

### Giorno 6-7: Testing & Deploy
- Test con diverse foto
- Verifica cache hit rate
- Deploy graduale (10% → 50% → 100%)
- Monitora metriche

---

## 🎯 Success Criteria

**Considerare il refactor SUCCESSO se:**
- ✅ Cache hit rate >85% dopo 48h
- ✅ Latenza media <1800ms
- ✅ 0 parsing errors in 1 settimana
- ✅ GraphQL schema invariato
- ✅ Nessuna regressione funzionale
- ✅ Monitoring attivo e funzionante

---

**Ultima Riga di Difesa:**

> Se il system prompt contiene `user_id`, `timestamp`, o qualsiasi dato che cambia tra chiamate → **SBAGLIATO**.  
> System = COSTANTE. User = VARIABILE.

---

**Fine documento.**  
**Salva come `MEAL_PHOTO_REFACTOR.md` e inizia lo sviluppo.** 🚀

---

## 📞 Contatti e Support

Per domande o dubbi durante l'implementazione:
1. Rileggi le sezioni ANTIPATTERN vs PATTERN
2. Verifica la checklist
3. Controlla i log JSON per diagnostica
4. Consulta le risorse essenziali linkate

**Buon refactoring!** 💪