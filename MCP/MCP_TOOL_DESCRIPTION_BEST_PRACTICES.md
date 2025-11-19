# MCP Tool Description Best Practices

Guida per scrivere descrizioni tool MCP efficaci per LLM (Large Language Models).

## 📋 Indice

1. [Principi Fondamentali](#principi-fondamentali)
2. [Le 7 Regole d'Oro](#le-7-regole-doro)
3. [Template Riutilizzabile](#template-riutilizzabile)
4. [Esempi Comparativi](#esempi-comparativi)
5. [Checklist di Validazione](#checklist-di-validazione)

---

## Principi Fondamentali

### Perché le Descrizioni sono Critiche

Gli LLM selezionano i tool basandosi SOLO sulle descrizioni. Una descrizione debole = tool ignorato o usato male.

**Obiettivi:**
- ✅ LLM capisce QUANDO usare il tool
- ✅ LLM sa COME chiamarlo correttamente
- ✅ LLM prevede COSA aspettarsi come output
- ✅ LLM evita errori comuni (missing params, wrong enum values)

### Context Window Optimization

Gli LLM leggono descrizioni in ordine sequenziale. Priorità:

```
1. 🔝 HOOK (emoji + critical info)
2. 📝 WHAT (cosa fa in 1 frase)
3. ⏰ WHEN (quando usarlo vs alternative)
4. 🔄 HOW (workflow se multi-step)
5. 📊 ARGS (input dettagliati)
6. 📦 RETURNS (output structure)
7. 💡 EXAMPLES (codice reale)
8. ⚠️ EDGE CASES (errori, performance)
```

---

## Le 7 Regole d'Oro

### 1. Visual Anchors (Emoji Strategici)

**Perché:** LLM hanno attention bias verso simboli visivi.

```python
# ❌ MALE
"""Get user profile."""

# ✅ BENE
"""🔐 Get authenticated user profile."""
```

**Emoji Consigliati:**
- 🔐 Autenticazione
- 👤 User profile
- 📊 Query/Read
- ✏️ Update/Mutation
- 🗑️ Delete
- ⬆️ Upload/Sync
- 🔄 Sync/Refresh
- 📈 Analytics/Stats
- 🍽️ Meal/Food
- 🏃 Activity
- 🔮 ML/Forecast
- ⚠️ Warning critico
- ✅ Confirmation

### 2. Imperativi Chiari

**Pattern:**
- `MUST` = Requisito bloccante
- `REQUIRED` = Input obbligatorio
- `BEFORE/AFTER` = Ordine temporale
- `Optional` = Flessibilità
- `IDEMPOTENT` = Safe retry

```python
"""⚠️ REQUIRED FIRST STEP when user provides image file!

MUST be called BEFORE analyze_meal_photo if user shares image directly.
"""
```

### 3. Workflow Sequenziali

Per tool che fanno parte di un processo multi-step:

```python
"""Workflow:
1. User shares image → upload_meal_image (get URL)
2. Use returned URL → analyze_meal_photo(photo_url=url)
3. Confirm analysis → confirm_meal_analysis

Critical: DO NOT skip step 1 if user provides file attachment!
"""
```

**Pattern Decision-Tree:**

```python
"""When to use:
- Have photo URL? → Use photo_url parameter
- Have text description? → Use text parameter
- Both? → Use both for better accuracy
- Want to refine? → Add dish_hint parameter
"""
```

### 4. Args Dettagliati (Non Astrazioni)

❌ **MALE:**
```python
"""Args:
    input: User preferences
"""
```

✅ **BENE:**
```python
"""Args:
    input: Preferences to update (all optional)
        - language: ISO 639-1 code (e.g., "it", "en", "es")
        - theme: UI theme → "light" | "dark" | "auto"
        - notifications: Enable push → true | false
"""
```

**Convenzioni:**
- `→` = "must be one of"
- `|` = OR logico per enum
- `(e.g., ...)` = Esempi concreti
- `(default: X)` = Valore di default
- `(required)` / `(optional)` = Obbligatorietà
- `Range: X-Y` = Vincoli numerici

### 5. Return Values Specifici

❌ **MALE:**
```python
"""Returns:
    User object
"""
```

✅ **BENE:**
```python
"""Returns:
    Complete user profile:
    - id: User UUID
    - auth0Sub: Auth0 identifier
    - email, name: Basic info
    - language, theme, notificationsEnabled: Preferences
    - isActive, createdAt, updatedAt: Metadata
"""
```

**Per return complessi:**
```python
"""Returns:
    Paginated activity events:
    - edges: Array of activity nodes
        * id, userId, timestamp, source
        * steps, caloriesOut, hrAvg (optional fields)
    - pageInfo: {hasNextPage, hasPreviousPage}
"""
```

### 6. Esempi Concreti

Sempre includere almeno UN esempio con valori reali:

```python
"""Example:
    # Weekly summary for last 30 days
    summary = await aggregate_activity_range(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        start_date="2025-10-18",
        end_date="2025-11-17",
        group_by="WEEK"
    )
"""
```

**Per workflow complessi:**
```python
"""Example workflow:
    # Step 1: Upload image
    upload = await upload_meal_image(
        user_id="uuid",
        image_data=base64_from_attachment,
        filename="lunch.jpg"
    )
    
    # Step 2: Analyze
    meal = await analyze_meal_photo(
        user_id="uuid",
        photo_url=upload["url"],
        meal_type="LUNCH"
    )
    
    # Step 3: Confirm
    confirmed = await confirm_meal_analysis(
        meal_id=meal["id"],
        user_id="uuid",
        confirmed_entry_ids=[meal["entries"][0]["id"]]
    )
"""
```

### 7. Edge Cases e Performance

Documentare:
- Errori comuni
- Idempotency
- Performance notes
- Limitazioni

```python
"""Raises:
    Exception: If user_id not found or JWT invalid

Performance: Pre-aggregated data → fast queries even for large ranges.

Idempotency:
- Same idempotency_key → skips duplicate events
- Safe to retry on network failure
"""
```

---

## Template Riutilizzabile

```python
@mcp.tool()
async def {action}_{entity}(input: {Entity}Input) -> dict:
    """{🔥 EMOJI} {Azione chiara in 1 frase}.
    
    {⚠️ WARNING se critico (REQUIRED/MUST/BEFORE)}.
    
    {Contesto: quando usarlo vs alternative}.
    {Effetti collaterali/stato post-operazione}.
    
    Workflow: (se multi-step)
    1. Step 1 → outcome
    2. Step 2 → outcome
    3. Step 3 → outcome
    
    Args:
        input: {Descrizione aggregato}
            - field1: {Descrizione} (required/optional)
                {tipo | ENUM | "example"}
                {Range/vincolo} (default: {valore})
            - field2: {Descrizione}
                → "VALUE1" | "VALUE2" | "VALUE3"
    
    Returns:
        {Struttura dati esatta o shape}:
        - key1: {Significato e tipo}
        - key2: {Significato e tipo}
        - nested: Array/Object structure
            * subkey1: {Dettaglio}
            * subkey2: {Dettaglio}
    
    Raises: (opzionale)
        Exception: {Quando può fallire}
    
    Performance: (opzionale)
        {Note su ottimizzazioni, limiti, cache}
    
    Idempotency: (se applicabile)
        {Garanzie di safe retry}
    
    Example:
        # {Caso d'uso descrittivo}
        result = await {action}_{entity}(
            field1="concrete_value",
            field2="ENUM_VALUE"
        )
        # Returns: {expected_output}
    
    Example workflow: (se multi-tool)
        # Step 1: {Action}
        step1 = await tool1(...)
        
        # Step 2: {Action}
        step2 = await tool2(
            param=step1["result_key"]
        )
    """
```

---

## Esempi Comparativi

### Esempio 1: Query Semplice

#### ❌ DEBOLE
```python
@mcp.tool()
async def get_user(user_id: str) -> dict:
    """Get user by ID."""
```

**Problemi:**
- Nessun contesto (quando usarlo?)
- Return value vago
- Nessun esempio
- Missing error cases

#### ✅ OTTIMIZZATA
```python
@mcp.tool()
async def get_user_by_id(user_id: str) -> dict:
    """👤 Get user profile by UUID.
    
    Use this to retrieve ANY user's profile by their unique ID.
    Requires JWT token - authenticated query only.
    
    Args:
        user_id: User UUID
            Format: "550e8400-e29b-41d4-a716-446655440000" (RFC 4122)
    
    Returns:
        Full user profile:
        - id, auth0Sub, email, name
        - language, theme, notificationsEnabled
        - isActive, createdAt, updatedAt
    
    Raises:
        Exception: If user_id not found or JWT invalid
    
    Example:
        user = await get_user_by_id(
            user_id="550e8400-e29b-41d4-a716-446655440000"
        )
    """
```

### Esempio 2: Mutation Complessa

#### ❌ DEBOLE
```python
@mcp.tool()
async def sync_events(events: List[dict]) -> dict:
    """Sync activity events."""
```

**Problemi:**
- Nessuna info su idempotency
- Tipo `List[dict]` troppo vago
- Nessun workflow
- Missing deduplication logic

#### ✅ OTTIMIZZATA
```python
@mcp.tool()
async def sync_activity_events(input: SyncActivityEventsInput) -> dict:
    """⬆️ Batch sync minute-level activity events (IDEMPOTENT).
    
    ⚠️ USE THIS for syncing data from HealthKit/GoogleFit.
    Upload multiple activity data points at once with automatic deduplication.
    
    Idempotency guarantee:
    - Same idempotency_key → skips duplicate events
    - Safe to retry on network failure
    - Events matched by timestamp + user_id + source
    
    Workflow:
    1. Collect activity events from device (HealthKit/GoogleFit)
    2. Build events array with timestamps
    3. Generate unique idempotency_key (e.g., "healthkit-sync-20251117-143000")
    4. Call sync_activity_events
    5. If fails → retry with SAME idempotency_key
    
    Args:
        input: Batch sync data
            - user_id: User UUID (required)
            - events: Array of ActivityEventInput (required)
                * timestamp: ISO 8601 (e.g., "2025-11-17T14:30:00Z")
                * steps: Steps count (optional)
                * calories_out: Calories burned (optional)
                * hr_avg: Average heart rate (optional)
            - source: Data source (required)
                → "APPLE_HEALTH" | "GOOGLE_FIT" | "MANUAL"
            - idempotency_key: Unique key for deduplication (required)
    
    Returns:
        SyncResult:
        - syncedCount: Number of NEW events created
        - skippedCount: Duplicates skipped
        - idempotencyKey: Echo of provided key
        - syncedAt: Timestamp
    
    Example:
        # Sync 10 minutes of HealthKit data
        result = await sync_activity_events(
            user_id="uuid",
            events=[
                {"timestamp": "2025-11-17T10:00:00Z", "steps": 150, "calories_out": 8},
                {"timestamp": "2025-11-17T10:01:00Z", "steps": 180, "calories_out": 10}
            ],
            source="APPLE_HEALTH",
            idempotency_key="healthkit-sync-20251117-100000"
        )
        # Returns: {syncedCount: 2, skippedCount: 0, ...}
    """
```

### Esempio 3: ML/AI Tool

#### ❌ DEBOLE
```python
@mcp.tool()
async def forecast(profile_id: str, days: int) -> dict:
    """Forecast weight."""
```

**Problemi:**
- Nessuna info sul modello ML
- Missing confidence intervals
- Nessun requisito sui dati
- Nessuna interpretazione output

#### ✅ OTTIMIZZATA
```python
@mcp.tool()
async def forecast_weight(input: ForecastWeightInput) -> dict:
    """🔮 ML-powered weight forecast using ARIMA time series model.
    
    Predicts future weight trajectory based on historical data.
    Requires at least 14 days of progress records for accurate predictions.
    
    ML model analyzes:
    - Historical weight measurements (daily records)
    - Calorie deficit/surplus patterns
    - Activity level trends
    - Time-of-week effects (weekdays vs weekends)
    
    Uses ARIMA (AutoRegressive Integrated Moving Average) with confidence intervals.
    
    Args:
        input: Forecast parameters
            - profile_id: Profile UUID (required)
            - days_ahead: Forecast horizon (default 7, max 90)
                Recommended: 7 for week, 30 for month
            - confidence_level: Prediction confidence (default 0.95)
                Range: 0.80-0.99 (0.95 = 95% confidence interval)
    
    Returns:
        WeightForecast with predictions:
        - predictions: Array of daily forecasts
            * date: Prediction date (YYYY-MM-DD)
            * predictedWeight: Most likely weight (kg)
            * lowerBound: Lower CI (95% sure weight >= this)
            * upperBound: Upper CI (95% sure weight <= this)
        - confidence: Confidence level used (e.g., 0.95)
        - model: Model name ("ARIMA")
    
    Raises:
        Exception: If insufficient historical data (<14 days)
    
    Example:
        # Forecast next 30 days
        forecast = await forecast_weight(
            profile_id="profile-uuid",
            days_ahead=30,
            confidence_level=0.95
        )
        # Returns: [
        #   {date: "2025-11-18", predictedWeight: 84.2, lowerBound: 83.8, upperBound: 84.6},
        #   {date: "2025-11-19", predictedWeight: 84.0, lowerBound: 83.5, upperBound: 84.5}
        # ]
    
    Interpretation:
        - predictedWeight: Expected weight (centerline on chart)
        - [lowerBound, upperBound]: 95% confidence zone (shaded area)
        - Wider bounds = more uncertainty (normal for longer forecasts)
    """
```

---

## Checklist di Validazione

Prima di committare un nuovo tool, verifica:

### ✅ Struttura Minima
- [ ] Emoji presente e semanticamente corretto
- [ ] Prima frase descrive chiaramente l'azione
- [ ] Args documentati con tipi e vincoli
- [ ] Returns documenta la struttura esatta
- [ ] Almeno UN esempio concreto

### ✅ Contesto
- [ ] Spiega QUANDO usare il tool
- [ ] Differenzia da tool simili (quando usare X vs Y)
- [ ] Documenta prerequisiti (es. "requires JWT token")
- [ ] Indica effetti collaterali (es. "creates PENDING meal")

### ✅ Tool Complessi
- [ ] Workflow multi-step documentato
- [ ] Enum values listati con pipe notation
- [ ] Formati specificati (ISO 8601, YYYY-MM-DD, UUID RFC 4122)
- [ ] Default values indicati
- [ ] Idempotency documentata se applicabile

### ✅ Error Handling
- [ ] Raises documenta errori comuni
- [ ] Edge cases spiegati
- [ ] Limitazioni chiare (es. "max 1000 results")

### ✅ Esempi
- [ ] Valori concreti (no "xxx", "123", "test")
- [ ] Mostra output atteso
- [ ] Multi-step workflow se applicabile
- [ ] Commenti esplicativi inline

### ✅ Performance
- [ ] Note su ottimizzazioni se rilevanti
- [ ] Limiti di paginazione
- [ ] Cache behavior documentato

---

## Pattern Verbali per Categoria

### Query Tools
```python
"""📊 Query {entity} with {filtering/pagination/sorting}.

Returns {granularity} data for {use_case}.
Use this for {when_to_use}.

Args:
    input: Query filters
        - {filter1}: {description} (required/optional)
        - {filter2}: {description} → {ENUM_VALUES}
        - limit: Max results (default X, max Y)

Returns:
    {ResultType}:
    - {field1}: {meaning}
    - {field2}: {meaning}
"""
```

### Mutation Tools
```python
"""✏️ {Action} {entity} with {side_effects}.

{IDEMPOTENT if applicable}.
{When to use vs alternatives}.

Args:
    input: {Entity} data
        - {field1}: {description} (required)
        - {field2}: {description} (optional, default: X)

Returns:
    {Updated entity}:
    - {field}: {new_value_description}
"""
```

### Sync Tools
```python
"""⬆️ Batch sync {data_type} (IDEMPOTENT).

⚠️ USE THIS for {primary_use_case}.
{Deduplication strategy}.

Idempotency:
- Same idempotency_key → {behavior}
- Safe to retry on {failure_scenario}

Workflow:
1. {Step 1}
2. {Step 2}
3. {Step 3}
"""
```

### Analysis Tools (AI/ML)
```python
"""🔮 {AI_capability} using {model/algorithm}.

{What it analyzes}.
{Requirements (e.g., minimum data)}.

{Model details}:
- {Feature 1}
- {Feature 2}

Args:
    input: {Analysis parameters}
        - {param1}: {description}
        - {confidence_param}: {range} (default: X)

Returns:
    {AnalysisResult}:
    - {prediction_field}: {interpretation}
    - {confidence_field}: {interpretation}

Interpretation:
    - {How to read results}
"""
```

---

## Anti-Patterns da Evitare

### ❌ Troppo Generico
```python
"""Process data."""
```

### ❌ Solo Tecnico
```python
"""Execute GraphQL mutation syncActivityEvents with event array."""
```

### ❌ Nessun Esempio
```python
"""Args:
    input: SyncInput object
"""
```

### ❌ Return Vago
```python
"""Returns:
    Object with results
"""
```

### ❌ Enum Impliciti
```python
"""Args:
    meal_type: Type of meal
"""
# Dovrebbe essere: meal_type: Meal category → "BREAKFAST" | "LUNCH" | "DINNER" | "SNACK"
```

---

## Testing delle Descrizioni

### Test Manuale
1. Leggi la descrizione come se fossi un LLM
2. Puoi rispondere a queste domande?
   - Quando usare questo tool?
   - Quali sono i parametri obbligatori?
   - Cosa torna?
   - Cosa fare dopo?
3. Se manca qualcosa → aggiungi alla descrizione

### Test con LLM
Prompt test:
```
Basandoti SOLO sulla descrizione del tool, dimmi:
1. Quando useresti questo tool?
2. Quali parametri sono obbligatori?
3. Cosa aspetti come output?
4. Quali errori potrebbero verificarsi?
```

Se l'LLM non può rispondere → descrizione insufficiente.

---

## Manutenzione

### Quando Aggiornare
- ✅ Nuovo parametro aggiunto
- ✅ Enum values cambiano
- ✅ Behavior cambia (es. diventa idempotent)
- ✅ Nuovi error cases
- ✅ Performance improvements

### Versioning
Se il tool cambia significativamente, considera:
- Deprecation warning nella descrizione old version
- Link alla nuova versione
- Migration guide negli esempi

```python
"""⚠️ DEPRECATED: Use {new_tool_name} instead.

This tool will be removed in v2.0.0.
Migration guide: {url}
"""
```

---

## Risorse

- [MCP Protocol Docs](https://modelcontextprotocol.io/docs)
- [FastMCP Examples](https://github.com/jlowin/fastmcp)
- [Nutrifit GraphQL API Reference](../backend/REFACTOR/graphql-api-reference.md)

---

**Built with ❤️ for Nutrifit MCP Servers**
