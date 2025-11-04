# 🚀 Meal Domain - Implementation Guide

**Data:** 22 Ottobre 2025  
**Timeline:** 2-3 settimane (~80-100 ore)  
**Approach:** Iterativo con milestone testabili

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Implementation Phases](#implementation-phases)
3. [Milestone Checklist](#milestone-checklist)
4. [Development Workflow](#development-workflow)
5. [Quality Gates](#quality-gates)

---

## ✅ Prerequisites

### Ambiente
```bash
# Python 3.11+
python --version

# UV package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# MongoDB (optional, per fase finale)
brew install mongodb-community

# Redis (optional, per caching avanzato)
brew install redis
```

### Dipendenze
```toml
# pyproject.toml - Dependencies da aggiungere
[project.dependencies]
openai = "^2.5.0"           # Structured outputs
circuitbreaker = "^1.4.0"   # Circuit breaker pattern
tenacity = "^8.2.0"         # Retry logic
motor = "^3.3.0"            # MongoDB async driver
redis = "^5.0.0"            # Redis client
pydantic = "^2.0"           # Validation
strawberry-graphql = "*"    # GraphQL
httpx = "^0.27.0"           # HTTP client
structlog = "^24.1.0"       # Structured logging
```

Installazione:
```bash
cd backend
uv sync --all-extras --dev
```

### Branch Setup
```bash
# Create feature branch
git checkout -b refactor/meal-domain-v2
```

---

## 🏗️ Implementation Phases

### Phase 0: Cleanup & Preparation (3-4 ore)

**Goal**: Preparare workspace per nuovo codice, preservando client esterni funzionanti.

#### ⚠️ STRATEGIA: Cleanup Selettivo

**Preservare** (risultato di sperimentazione funzionante):
- ✅ `backend/ai_models/usda_client.py` → Da adattare in Phase 2-3
- ✅ `backend/openfoodfacts/adapter.py` → Da adattare in Phase 2-3
- ✅ `backend/ai_models/meal_photo_prompt.py` → Da riutilizzare
- ✅ `backend/ai_models/nutrient_enrichment.py` → Da riutilizzare

**Rimuovere** (architettura vecchia):
- ❌ `backend/domain/meal/*` (eccetto client esterni)
- ❌ `backend/graphql/meal_resolver.py`
- ❌ `backend/graphql/types_meal.py`

---

#### Tasks

##### 1. **Upgrade Dependencies (CRITICAL)**

**OpenAI 1.45.0 → 2.5.0+ per Structured Outputs + Prompt Caching**

```bash
# Aggiorna pyproject.toml
```

```toml
# pyproject.toml [project.dependencies]
# BEFORE:
openai = "1.45.0"
httpx = "0.28.1"

# AFTER:
openai = "^2.5.0"        # Structured outputs + prompt caching
httpx = "^0.28.1"        # Compatibile con OpenAI 2.5+
circuitbreaker = "^1.4.0"  # NUOVO: Circuit breaker pattern
tenacity = "^8.2.0"        # NUOVO: Retry logic
pydantic = "^2.0"          # Validazione (già richiesto da Strawberry)
```

**Vantaggi OpenAI 2.5.0+:**
- ✅ **Structured Outputs**: Validazione nativa Pydantic (no parsing JSON)
- ✅ **Prompt Caching**: System prompt >1024 token → 50% costo ridotto
- ✅ **Reliability**: Schema enforcement lato server
- ✅ **Type Safety**: Pydantic integration diretta

```bash
# Installa dipendenze
cd backend
uv sync

# Verifica versione OpenAI
uv run python -c "import openai; print(f'OpenAI: {openai.__version__}')"
# Expected: 2.5.0 o superiore

# Verifica import circuitbreaker/tenacity
uv run python -c "from circuitbreaker import circuit; from tenacity import retry; print('✓ OK')"
```

**Commit:**
```bash
git add pyproject.toml uv.lock
git commit -m "build(deps): upgrade openai to 2.5.0+ for structured outputs"
```

---

##### 2. **Analyze Dependencies**
   ```bash
   # Find all imports of old meal domain
   grep -r "from backend.domain.meal" backend/ --include="*.py"
   grep -r "from backend.graphql.meal" backend/ --include="*.py"
   ```

##### 3. **Selective Cleanup (Preserve External Clients)**
   ```bash
   # Remove old domain code (KEEP ai_models/ and openfoodfacts/)
   # Manually remove folders EXCEPT:
   # - backend/ai_models/
   # - backend/openfoodfacts/
   
   cd backend/domain/meal
   rm -rf adapters/ application/ entities/ events/ model/ pipeline/ port/ ports/ service/ value_objects/
   rm -f errors.py integration.py meal_photo_refactor.md
   
   # Remove old GraphQL resolvers
   cd ../../graphql
   rm -f meal_resolver.py types_meal.py
   
   # Commit
   git add -A
   git commit -m "refactor(meal): selective cleanup - preserve external clients"
   ```

##### 4. **Create New Structure**
   ```bash
   # Domain layer
   mkdir -p backend/domain/meal/{nutrition,recognition,barcode,core}/{entities,value_objects,services,ports}
   mkdir -p backend/domain/meal/core/{events,exceptions,factories}
   mkdir -p backend/domain/shared/ports
   
   # Application layer
   mkdir -p backend/application/meal/{commands,queries,orchestrators,dtos,event_handlers}
   
   # Infrastructure layer
   mkdir -p backend/infrastructure/{ai/prompts,external_apis/{usda,openfoodfacts},persistence/{in_memory,mongodb,redis},events}
   
   # GraphQL layer
   mkdir -p backend/graphql/resolvers/meal
   
   # Tests
   mkdir -p backend/tests/{unit/{domain,application},integration/{infrastructure,graphql},e2e/meal_flows}
   ```

**Deliverable**: ✅ Clean workspace con nuova struttura

---

### Phase 1: Domain Layer - Core (8-10 ore)

**Goal**: Implementare core domain entities, value objects, events.

#### Step 1.1: Value Objects (2h)
```python
# domain/meal/core/value_objects/meal_id.py
from dataclasses import dataclass
from uuid import UUID, uuid4

@dataclass(frozen=True)
class MealId:
    """Value object for Meal ID."""
    value: UUID
    
    @classmethod
    def generate(cls) -> "MealId":
        return cls(uuid4())
    
    def __str__(self) -> str:
        return str(self.value)
```

```python
# domain/meal/core/value_objects/quantity.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Quantity:
    """Value object for quantity with unit."""
    value: float
    unit: str = "g"
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("Quantity must be positive")
        
        if self.unit not in ["g", "ml", "oz", "cup"]:
            raise ValueError(f"Invalid unit: {self.unit}")
    
    def to_grams(self) -> float:
        """Convert to grams."""
        conversions = {
            "g": 1.0,
            "ml": 1.0,  # Assume density ~1
            "oz": 28.35,
            "cup": 240.0
        }
        return self.value * conversions[self.unit]
```

**Files to create**:
- ✅ `value_objects/meal_id.py`
- ✅ `value_objects/quantity.py`
- ✅ `value_objects/timestamp.py`
- ✅ `value_objects/confidence.py`

**Tests**:
```bash
pytest tests/unit/domain/meal/core/test_value_objects.py -v
```

#### Step 1.2: Domain Events (1h)
```python
# domain/meal/core/events/meal_analyzed.py
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class MealAnalyzed:
    """Domain event: Meal analyzed."""
    meal_id: UUID
    user_id: str
    source: str  # PHOTO | BARCODE | DESCRIPTION
    occurred_at: datetime
    
    @classmethod
    def create(cls, meal_id: UUID, user_id: str, source: str) -> "MealAnalyzed":
        return cls(
            meal_id=meal_id,
            user_id=user_id,
            source=source,
            occurred_at=datetime.utcnow()
        )
```

**Files to create**:
- ✅ `events/meal_analyzed.py`
- ✅ `events/meal_confirmed.py`
- ✅ `events/meal_updated.py`
- ✅ `events/meal_deleted.py`

#### Step 1.3: Entities (3h)
```python
# domain/meal/core/entities/meal_entry.py
from dataclasses import dataclass, field
from uuid import UUID
from typing import Optional

@dataclass
class MealEntry:
    """Entity: Single dish in a meal."""
    id: UUID
    meal_id: UUID
    name: str
    display_name: str
    quantity_g: float
    
    # Nutrients (denormalized for performance)
    calories: int
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    
    # Metadata
    source: str = "MANUAL"  # PHOTO | BARCODE | DESCRIPTION | MANUAL
    confidence: float = 1.0
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    
    def __post_init__(self):
        if self.quantity_g <= 0:
            raise ValueError("Quantity must be positive")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
```

```python
# domain/meal/core/entities/meal.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from .meal_entry import MealEntry

@dataclass
class Meal:
    """
    Aggregate Root: Complete meal with multiple dishes.
    
    A Meal represents a complete eating occasion (breakfast, lunch, etc.)
    and contains one or more MealEntry items (individual dishes).
    
    Invariants:
    - Must have at least one entry
    - Totals must equal sum of entries
    - Timestamp cannot be in the future
    """
    id: UUID
    user_id: str
    timestamp: datetime
    meal_type: str  # BREAKFAST | LUNCH | DINNER | SNACK
    entries: List[MealEntry] = field(default_factory=list)
    
    # Aggregated totals (calculated from entries)
    total_calories: int = 0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    
    # Metadata
    analysis_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_entry(self, entry: MealEntry) -> None:
        """Add entry to meal and recalculate totals."""
        if entry.meal_id != self.id:
            raise ValueError("Entry meal_id must match Meal id")
        
        self.entries.append(entry)
        self._recalculate_totals()
        self.updated_at = datetime.utcnow()
    
    def remove_entry(self, entry_id: UUID) -> None:
        """Remove entry from meal and recalculate totals."""
        self.entries = [e for e in self.entries if e.id != entry_id]
        
        if not self.entries:
            raise ValueError("Meal must have at least one entry")
        
        self._recalculate_totals()
        self.updated_at = datetime.utcnow()
    
    def update_entry(self, entry_id: UUID, updates: dict) -> None:
        """Update an entry and recalculate totals."""
        for entry in self.entries:
            if entry.id == entry_id:
                for key, value in updates.items():
                    if hasattr(entry, key):
                        setattr(entry, key, value)
                break
        else:
            raise ValueError(f"Entry {entry_id} not found")
        
        self._recalculate_totals()
        self.updated_at = datetime.utcnow()
    
    def _recalculate_totals(self) -> None:
        """Recalculate aggregated totals from entries."""
        self.total_calories = sum(e.calories for e in self.entries)
        self.total_protein = sum(e.protein for e in self.entries)
        self.total_carbs = sum(e.carbs for e in self.entries)
        self.total_fat = sum(e.fat for e in self.entries)
    
    def validate(self) -> None:
        """Validate meal invariants."""
        if not self.entries:
            raise ValueError("Meal must have at least one entry")
        
        if self.timestamp > datetime.utcnow():
            raise ValueError("Timestamp cannot be in the future")
        
        # Verify totals match entries
        expected_calories = sum(e.calories for e in self.entries)
        if abs(self.total_calories - expected_calories) > 1:  # Allow 1 calorie rounding
            raise ValueError("Total calories mismatch")
```

**Files to create**:
- ✅ `entities/meal_entry.py`
- ✅ `entities/meal.py`

**Tests**:
```bash
pytest tests/unit/domain/meal/core/test_entities.py -v
```

#### Step 1.4: Factory (1h)
```python
# domain/meal/core/factories/meal_factory.py
from datetime import datetime
from typing import List, Tuple
from uuid import uuid4

from ..entities.meal import Meal, MealEntry
from ...nutrition.entities.nutrient_profile import NutrientProfile
from ...recognition.entities.recognized_food import RecognizedFood

class MealFactory:
    """Factory for creating Meal aggregates."""
    
    @staticmethod
    def create_from_analysis(
        user_id: str,
        dish_name: str | None,
        items: List[Tuple[RecognizedFood, NutrientProfile]],
        source: str,
        timestamp: datetime | None = None,
        meal_type: str = "SNACK",
        photo_url: str | None = None,
        analysis_id: str | None = None
    ) -> Meal:
        """Create Meal from AI analysis results."""
        meal_id = uuid4()
        
        # Create entries from recognized foods + nutrients
        entries = []
        for recognized, nutrients in items:
            entry = MealEntry(
                id=uuid4(),
                meal_id=meal_id,
                name=recognized.label,
                display_name=recognized.display_name,
                quantity_g=recognized.quantity_g,
                calories=nutrients.calories,
                protein=nutrients.protein,
                carbs=nutrients.carbs,
                fat=nutrients.fat,
                fiber=nutrients.fiber,
                sugar=nutrients.sugar,
                sodium=nutrients.sodium,
                source=source,
                confidence=recognized.confidence,
                category=recognized.category,
                image_url=photo_url
            )
            entries.append(entry)
        
        # Create meal
        meal = Meal(
            id=meal_id,
            user_id=user_id,
            timestamp=timestamp or datetime.utcnow(),
            meal_type=meal_type,
            entries=entries,
            analysis_id=analysis_id
        )
        
        # Calculate totals
        meal._recalculate_totals()
        
        return meal
    
    @staticmethod
    def create_manual(
        user_id: str,
        name: str,
        quantity_g: float,
        calories: int,
        protein: float,
        carbs: float,
        fat: float,
        meal_type: str = "SNACK",
        timestamp: datetime | None = None
    ) -> Meal:
        """Create Meal from manual entry."""
        meal_id = uuid4()
        
        entry = MealEntry(
            id=uuid4(),
            meal_id=meal_id,
            name=name,
            display_name=name,
            quantity_g=quantity_g,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            source="MANUAL",
            confidence=1.0
        )
        
        meal = Meal(
            id=meal_id,
            user_id=user_id,
            timestamp=timestamp or datetime.utcnow(),
            meal_type=meal_type,
            entries=[entry]
        )
        
        meal._recalculate_totals()
        
        return meal
```

**Files to create**:
- ✅ `factories/meal_factory.py`

#### Step 1.5: Ports (1h)
```python
# domain/shared/ports/repository.py
from typing import Protocol, Optional, List
from uuid import UUID
from datetime import datetime

from domain.meal.core.entities.meal import Meal

class IMealRepository(Protocol):
    """Repository interface for Meal aggregate."""
    
    async def save(self, meal: Meal) -> None:
        """Persist meal."""
        ...
    
    async def get_by_id(self, meal_id: UUID) -> Optional[Meal]:
        """Get meal by ID."""
        ...
    
    async def list_by_user(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Meal]:
        """List meals for user with optional date range."""
        ...
    
    async def delete(self, meal_id: UUID) -> bool:
        """Delete meal. Returns True if deleted, False if not found."""
        ...
    
    async def exists(self, meal_id: UUID) -> bool:
        """Check if meal exists."""
        ...
```

```python
# domain/shared/ports/event_bus.py
from typing import Protocol, Callable, Awaitable, Type

from domain.meal.core.events.base import DomainEvent

EventHandler = Callable[[DomainEvent], Awaitable[None]]

class IEventBus(Protocol):
    """Event bus interface for publishing domain events."""
    
    async def publish(self, event: DomainEvent) -> None:
        """Publish domain event."""
        ...
    
    async def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: EventHandler
    ) -> None:
        """Subscribe to event type."""
        ...
```

**Files to create**:
- ✅ `domain/shared/ports/repository.py`
- ✅ `domain/shared/ports/event_bus.py`

**Deliverable**: ✅ Core domain layer completo con tests

---

### Phase 2: Domain Layer - Capabilities (12-15 ore)

**Goal**: Implementare Nutrition, Recognition, Barcode capabilities.

#### ⚠️ STRATEGIA: Adattare Client Esistenti

**Comportamento da preservare** (risultato sperimentazione):
- ✅ **USDA Client**: Logica di matching label → USDA foods (in `ai_models/usda_client.py`)
- ✅ **OpenFoodFacts**: Logica barcode lookup (in `openfoodfacts/adapter.py`)
- ✅ **Prompts**: System/user prompts per OpenAI (in `ai_models/meal_photo_prompt.py`)

**Approach**: Non cancellare, ma **adattare alla nuova architettura**.

---

#### Step 2.1: Nutrition Capability (6h)

Vedi documento: `02_DOMAIN_LAYER.md` sezione Nutrition

**Files to create**:
- ✅ `nutrition/entities/nutrient_profile.py`
- ✅ `nutrition/value_objects/macro_nutrients.py`
- ✅ `nutrition/value_objects/micro_nutrients.py`
- ✅ `nutrition/services/enrichment_service.py`
- ✅ `nutrition/ports/nutrition_provider.py` (Port che USDA client implementerà)

**Note**: Port `INutritionProvider` definisce contratto che `usda_client.py` dovrà implementare in Phase 3.

---

#### Step 2.2: Recognition Capability (4h)

Vedi documento: `02_DOMAIN_LAYER.md` sezione Recognition

**Files to create**:
- ✅ `recognition/entities/recognized_food.py`
- ✅ `recognition/value_objects/confidence.py`
- ✅ `recognition/value_objects/food_label.py`
- ✅ `recognition/services/recognition_service.py`
- ✅ `recognition/ports/vision_provider.py` (Port che OpenAI client implementerà)

**Note**: Port `IVisionProvider` definisce contratto che OpenAI client implementerà in Phase 3.

---

#### Step 2.3: Barcode Capability (2h)

Vedi documento: `02_DOMAIN_LAYER.md` sezione Barcode

**Files to create**:
- ✅ `barcode/services/barcode_service.py`
- ✅ `barcode/ports/barcode_provider.py` (Port che OpenFoodFacts implementerà)

**Note**: Port `IBarcodeProvider` definisce contratto che `openfoodfacts/adapter.py` implementerà in Phase 3.

---

**Deliverable**: ✅ Tutte le capabilities con tests (ports definiscono contratti per Phase 3)

---

### Phase 3: Infrastructure Layer (15-18 ore)

**Goal**: Adattare client esistenti + implementare nuovi adapters.

#### ⚠️ STRATEGIA: Adattamento, Non Riscrittura

**Client da adattare** (comportamento testato e funzionante):
1. **USDA Client** (`ai_models/usda_client.py`)
   - ✅ Preservare logica matching label → USDA foods
   - 🔄 Adattare per implementare `INutritionProvider` (Phase 2)
   - 🔄 Aggiungere circuit breaker + retry logic

2. **OpenFoodFacts** (`openfoodfacts/adapter.py`)
   - ✅ Preservare logica barcode lookup
   - 🔄 Adattare per implementare `IBarcodeProvider` (Phase 2)
   - 🔄 Aggiungere circuit breaker

3. **Prompts** (`ai_models/meal_photo_prompt.py`)
   - ✅ Riutilizzare system/user prompts esistenti
   - 🔄 Adattare formato per OpenAI 2.5.0+ structured outputs

---

#### Step 3.1: OpenAI Client with Structured Outputs (5h)

Vedi documento: `04_INFRASTRUCTURE_LAYER.md` sezione OpenAI

**Files to create**:
- ✅ `infrastructure/ai/openai_client.py` (nuovo, con OpenAI 2.5.0+)

**Files to adapt**:
- 🔄 `ai_models/meal_photo_prompt.py` → Migrare a `infrastructure/ai/prompts/food_recognition.py`
  - Mantenere logica prompt esistente
  - Adattare per structured outputs (response_format=Pydantic)

**Key Changes:**
```python
# BEFORE (v1.45.0 - parsing JSON manuale)
response = await client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    response_format={"type": "json_object"}  # Parser manualmente
)
result = json.loads(response.choices[0].message.content)

# AFTER (v2.5.0+ - structured outputs nativi)
response = await client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[...],
    response_format=RecognizedFoodList  # Pydantic model diretto
)
result = response.choices[0].message.parsed  # Già validato!
```

---

#### Step 3.2: USDA Client Adapter (4h)

Vedi documento: `04_INFRASTRUCTURE_LAYER.md` sezione USDA

**Strategy**: **ADATTARE** `ai_models/usda_client.py`, NON riscrivere da zero.

**Files to adapt**:
- 🔄 `ai_models/usda_client.py` → Spostare in `infrastructure/external_apis/usda/client.py`
  - ✅ **Preservare** logica esistente (matching, fallback, caching)
  - 🔄 **Aggiungere** implementazione `INutritionProvider` port
  - 🔄 **Aggiungere** circuit breaker (`@circuit(failure_threshold=5)`)
  - 🔄 **Aggiungere** retry logic (`@retry(...)`)

**Example Adaptation**:
```python
# infrastructure/external_apis/usda/client.py
from backend.domain.meal.nutrition.ports.nutrition_provider import INutritionProvider
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt

class USDAClient(INutritionProvider):  # Implementa port
    """
    Adapter per USDA FoodData Central API.
    
    PRESERVATO DA: backend/ai_models/usda_client.py
    - Logica matching label → USDA foods
    - Fallback categories
    - Caching
    
    AGGIUNTO:
    - Circuit breaker (5 failures → 60s)
    - Retry logic (3 attempts)
    - Port implementation
    """
    
    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(stop=stop_after_attempt(3))
    async def get_nutrients(self, label: str, quantity_g: float) -> NutrientProfile:
        # PRESERVARE logica esistente da ai_models/usda_client.py
        ...
```

**Files to create** (solo se mancanti):
- ✅ `infrastructure/external_apis/usda/mapper.py` (se serve mapping aggiuntivo)
- ✅ `infrastructure/external_apis/usda/categories.py` (se serve categorizzazione)

---

#### Step 3.3: OpenFoodFacts Adapter (3h)

**Strategy**: **ADATTARE** `openfoodfacts/adapter.py`, NON riscrivere.

**Files to adapt**:
- 🔄 `openfoodfacts/adapter.py` → Spostare in `infrastructure/external_apis/openfoodfacts/client.py`
  - ✅ **Preservare** logica barcode lookup esistente
  - 🔄 **Aggiungere** implementazione `IBarcodeProvider` port
  - 🔄 **Aggiungere** circuit breaker
  - 🔄 **Aggiungere** retry logic

**Example Adaptation**:
```python
# infrastructure/external_apis/openfoodfacts/client.py
from backend.domain.meal.barcode.ports.barcode_provider import IBarcodeProvider
from circuitbreaker import circuit

class OpenFoodFactsClient(IBarcodeProvider):  # Implementa port
    """
    Adapter per OpenFoodFacts API.
    
    PRESERVATO DA: backend/openfoodfacts/adapter.py
    - Logica barcode lookup
    - Parsing response
    - Image URL extraction
    
    AGGIUNTO:
    - Circuit breaker
    - Port implementation
    """
    
    @circuit(failure_threshold=5, recovery_timeout=60)
    async def lookup_barcode(self, barcode: str) -> Optional[BarcodeProduct]:
        # PRESERVARE logica esistente da openfoodfacts/adapter.py
        ...
```

**Files to create** (se serve):
- ✅ `infrastructure/external_apis/openfoodfacts/mapper.py`

---

#### Step 3.4: In-Memory Repository (2h)

**Files to create**:
- ✅ `infrastructure/persistence/in_memory/meal_repository.py`

---

#### Step 3.5: Event Bus (2h)

**Files to create**:
- ✅ `infrastructure/events/in_memory_bus.py`

---

#### Step 3.6: Docker Compose Setup (1h)

**Files to create**:
- ✅ `docker-compose.yml` (root del progetto)
- 🔄 Aggiornare `make.sh` con target `docker-up`, `docker-down`, `docker-logs`
- 🔄 Aggiornare `Makefile` per proxy ai nuovi target

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build: 
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - USDA_API_KEY=${USDA_API_KEY}
      - MONGODB_URL=mongodb://mongo:27017
      - REDIS_URL=redis://redis:6379
    depends_on:
      - mongo
      - redis
    volumes:
      - ./backend:/app/backend  # Hot reload

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  mongo_data:
  redis_data:
```

**Aggiornare make.sh**:
```bash
#!/bin/bash
# Aggiungi target:

docker-up() {
    echo "🐳 Starting Docker services..."
    docker-compose up -d
}

docker-down() {
    echo "🛑 Stopping Docker services..."
    docker-compose down
}

docker-logs() {
    echo "📋 Docker logs..."
    docker-compose logs -f backend
}
```

**Aggiornare Makefile**:
```makefile
docker-up:
	@$(SCRIPT) docker-up

docker-down:
	@$(SCRIPT) docker-down

docker-logs:
	@$(SCRIPT) docker-logs
```

---

**Deliverable**: ✅ Infrastructure layer con client adattati + docker-compose + integration tests

---

### Phase 4: Application Layer (10-12 ore)

**Goal**: Implementare CQRS commands, queries, orchestrators.

Vedi documento: `03_APPLICATION_LAYER.md` per dettagli completi.

**Files to create**:
- Commands (6 files)
- Queries (4 files)
- Orchestrators (3 files)
- DTOs (2 files)
- Event Handlers (2 files)

**Deliverable**: ✅ Application layer con tests

---

### Phase 5: GraphQL Layer (8-10 ore)

**Goal**: Implementare GraphQL API con approccio test-first.

**⚠️ CRITICAL STRATEGY**: Implementare **query atomiche PRIMA delle mutations**.

**Rationale**:
1. **Testing isolation**: Query atomiche testano singole capabilities senza orchestrazione complessa
2. **Business logic validation**: Validano OpenAI, USDA, OpenFoodFacts indipendentemente
3. **GraphQL foundation**: Schema e resolvers base funzionanti prima delle mutations
4. **Debug facilitato**: Problemi isolati (recognition vs enrichment vs barcode)
5. **Documentation**: Le query atomiche sono esempi perfetti per SpectaQL

**Implementation Order**:
```
Query atomiche (test singole capabilities)
    ↓
Query aggregate (test data retrieval)
    ↓
Mutations (test orchestrazione completa)
```

---

#### Step 5.1: Update Schema (2h)

```graphql
# graphql/schema.graphql
# Complete schema - vedi 06_GRAPHQL_API.md

type Query {
  # ⚠️ IMPLEMENT FIRST: Atomic queries (testing utilities)
  recognizeFood(photoUrl: String!, hint: String): RecognitionResult!
  enrichNutrients(label: String!, quantityG: Float!): NutrientProfile
  searchFoodByBarcode(barcode: String!): BarcodeProduct
  
  # IMPLEMENT SECOND: Aggregate queries
  meal(id: ID!): MealResult!
  mealHistory(...): MealHistoryResult!
  dailySummary(...): DailySummaryResult!
}

type Mutation {
  # IMPLEMENT LAST: Complex orchestration
  analyzeMealPhoto(input: PhotoAnalysisInput!): MealAnalysisResult!
  analyzeMealBarcode(input: BarcodeAnalysisInput!): MealAnalysisResult!
  analyzeMealDescription(input: TextAnalysisInput!): MealAnalysisResult!
  confirmMealAnalysis(input: ConfirmAnalysisInput!): ConfirmationResult!
  updateMeal(input: UpdateMealInput!): MealUpdateResult!
  deleteMeal(id: ID!, userId: String!): DeleteResult!
}
```

**Files to create**:
- ✅ `graphql/schema.graphql`
- ✅ `graphql/types/meal.py`
- ✅ `graphql/types/nutrition.py`
- ✅ `graphql/types/recognition.py`

---

#### Step 5.2: Atomic Query Resolvers (3h) ⚡ START HERE

**Why atomic queries first?**
- Test OpenAI Vision without full workflow
- Test USDA enrichment without meal creation
- Test OpenFoodFacts lookup without persistence
- Validate GraphQL schema and types
- Fast feedback loop (no orchestration complexity)

```python
# graphql/resolvers/atomic_queries.py
"""
Atomic query resolvers for testing individual capabilities.

These queries are utility endpoints for:
1. Testing/debugging individual services
2. API documentation examples (SpectaQL)
3. Mobile app experimentation

DO NOT use in production workflows - use mutations instead.
"""

import strawberry
from typing import Optional
import structlog

from domain.meal.recognition.services.recognition_service import FoodRecognitionService
from domain.meal.nutrition.services.enrichment_service import NutritionEnrichmentService
from domain.meal.barcode.services.barcode_service import BarcodeService

logger = structlog.get_logger(__name__)


@strawberry.type
class AtomicQuery:
    """Atomic utility queries for testing."""
    
    @strawberry.field
    async def recognize_food(
        self,
        info: strawberry.Info,
        photo_url: str,
        hint: Optional[str] = None
    ) -> RecognitionResult:
        """
        Test OpenAI Vision recognition (atomic operation).
        
        Use case: Test/debug photo recognition without saving meal.
        
        Example:
        ```graphql
        query TestRecognition {
          recognizeFood(
            photoUrl: "https://example.com/carbonara.jpg"
            hint: "carbonara"
          ) {
            dishTitle
            items {
              label  # Should be USDA-compatible
              displayName
              quantityG
              confidence
            }
          }
        }
        ```
        """
        recognition_service: FoodRecognitionService = info.context["recognition_service"]
        
        logger.info("atomic_recognize_food", photo_url=photo_url, has_hint=hint is not None)
        
        result = await recognition_service.recognize_from_photo(
            photo_url=photo_url,
            hint=hint
        )
        
        # Map domain → GraphQL
        return RecognitionResult(
            dish_title=result.dish_name,
            items=[
                RecognizedFood(
                    label=item.label,
                    display_name=item.display_name,
                    quantity_g=item.quantity_g,
                    unit="g",
                    confidence=item.confidence
                )
                for item in result.items
            ],
            confidence=result.confidence,
            processing_time_ms=result.processing_time_ms
        )
    
    @strawberry.field
    async def enrich_nutrients(
        self,
        info: strawberry.Info,
        label: str,
        quantity_g: float
    ) -> Optional[NutrientProfile]:
        """
        Test USDA enrichment (atomic operation).
        
        Use case: Test/debug USDA matching without full workflow.
        
        Example:
        ```graphql
        query TestEnrichment {
          enrichNutrients(
            label: "chicken breast, roasted"
            quantityG: 200
          ) {
            calories
            protein
            carbs
            fat
            source  # Should be "USDA"
            confidence
          }
        }
        ```
        """
        enrichment_service: NutritionEnrichmentService = info.context["enrichment_service"]
        
        logger.info("atomic_enrich_nutrients", label=label, quantity_g=quantity_g)
        
        profile = await enrichment_service.enrich(
            label=label,
            quantity_g=quantity_g
        )
        
        if not profile:
            return None
        
        # Map domain → GraphQL
        return NutrientProfile(
            calories=profile.calories,
            protein=profile.protein,
            carbs=profile.carbs,
            fat=profile.fat,
            fiber=profile.fiber,
            sugar=profile.sugar,
            sodium=profile.sodium,
            source=profile.source,
            confidence=profile.confidence,
            quantity_g=profile.quantity_g
        )
    
    @strawberry.field
    async def search_food_by_barcode(
        self,
        info: strawberry.Info,
        barcode: str
    ) -> Optional[BarcodeProduct]:
        """
        Test OpenFoodFacts lookup (atomic operation).
        
        Use case: Test/debug barcode scanning without meal creation.
        
        Example:
        ```graphql
        query TestBarcode {
          searchFoodByBarcode(barcode: "8001050000000") {
            name
            brand
            imageUrl  # ⚠️ CRITICAL: Must be present
            nutrients {
              calories
              source  # "OpenFoodFacts" or "USDA"
            }
          }
        }
        ```
        """
        barcode_service: BarcodeService = info.context["barcode_service"]
        
        logger.info("atomic_search_barcode", barcode=barcode)
        
        product = await barcode_service.lookup(barcode)
        
        if not product:
            return None
        
        # Map domain → GraphQL
        return BarcodeProduct(
            name=product.name,
            barcode=product.barcode,
            brand=product.brand,
            category=product.category,
            image_url=product.image_url,  # ⚠️ CRITICAL
            nutrients=NutrientProfile(
                calories=product.nutrients.calories,
                protein=product.nutrients.protein,
                carbs=product.nutrients.carbs,
                fat=product.nutrients.fat,
                fiber=product.nutrients.fiber,
                sugar=product.nutrients.sugar,
                sodium=product.nutrients.sodium,
                source=product.nutrients.source,
                confidence=product.nutrients.confidence,
                quantity_g=product.nutrients.quantity_g
            ) if product.nutrients else None
        )
```

**Testing atomic queries**:
```bash
# Test OpenAI recognition
pytest tests/e2e/test_atomic_recognize_food.py -v

# Test USDA enrichment
pytest tests/e2e/test_atomic_enrich_nutrients.py -v

# Test barcode lookup
pytest tests/e2e/test_atomic_search_barcode.py -v
```

**Files to create**:
- ✅ `graphql/resolvers/atomic_queries.py`
- ✅ `tests/e2e/test_atomic_recognize_food.py`
- ✅ `tests/e2e/test_atomic_enrich_nutrients.py`
- ✅ `tests/e2e/test_atomic_search_barcode.py`

**Checkpoint**: ✅ Tutte le atomic queries funzionanti e testate

---

#### Step 5.3: Aggregate Query Resolvers (2h)

Implementare query per retrieval dati (meal, mealHistory, dailySummary).

```python
# graphql/resolvers/meal_queries.py
# ... implementazione query aggregate
```

**Files to create**:
- ✅ `graphql/resolvers/meal_queries.py`
- ✅ `tests/e2e/test_meal_queries.py`

**Checkpoint**: ✅ Query aggregate funzionanti

---

#### Step 5.4: Mutation Resolvers (3h)

**ULTIMO STEP**: Implementare mutations con orchestrazione completa.

A questo punto:
- ✅ Atomic queries validate singole capabilities
- ✅ Business logic è testata e funzionante
- ✅ GraphQL schema è validato
- ✅ Possiamo concentrarci su orchestrazione

```python
# graphql/resolvers/meal_mutations.py
"""
Meal mutations - Complex orchestration.

Prerequisites:
- Atomic queries working (recognition, enrichment, barcode)
- Orchestrators implemented (PhotoOrchestrator, BarcodeOrchestrator)
- Repository working
"""

@strawberry.type
class MealMutation:
    
    @strawberry.mutation
    async def analyze_meal_photo(
        self,
        info: strawberry.Info,
        input: PhotoAnalysisInput
    ) -> MealAnalysisResult:
        """
        Full photo analysis workflow.
        
        Flow:
        1. recognizeFood (atomic - already tested ✅)
        2. enrichNutrients (atomic - already tested ✅)
        3. MealFactory.create_from_analysis
        4. Repository.save
        5. EventBus.publish
        """
        handler = info.context["analyze_photo_handler"]
        # ... implementation
```

**Files to create**:
- ✅ `graphql/resolvers/meal_mutations.py`
- ✅ `tests/e2e/test_meal_mutations.py`

**Checkpoint**: ✅ Mutations funzionanti con orchestrazione completa

---

#### Step 5.5: Update app.py (1h)

Wire everything together.

**Deliverable**: ✅ GraphQL API completo e testato

---

### Phase 6: Testing & Quality (8-10 ore)

**Goal**: >90% coverage, tutti i quality checks passano.

Vedi documento: `05_TESTING_STRATEGY.md`

**Deliverable**: ✅ Test suite completo

---

### Phase 7: MongoDB Migration (Optional) (6-8 ore)

**Goal**: Migrazione da In-Memory a MongoDB.

#### Step 7.1: MongoDB Repository (4h)
```python
# infrastructure/persistence/mongodb/meal_repository.py
# ... implementazione
```

#### Step 7.2: Migration Script (2h)
```python
# scripts/migrate_to_mongodb.py
# ... script migrazione
```

#### Step 7.3: Update DI (1h)
```python
# api/dependencies.py
# Switch to MongoDB based on env
```

**Deliverable**: ✅ MongoDB in produzione

---

## ✅ Milestone Checklist

### Milestone 1: Domain Core ✓
- [ ] Value objects implementati
- [ ] Entities implementate
- [ ] Domain events implementati
- [ ] Factory implementato
- [ ] Ports definiti
- [ ] Tests unit >90% coverage

### Milestone 2: Domain Capabilities ✓
- [ ] Nutrition service implementato
- [ ] Recognition service implementato
- [ ] Barcode service implementato
- [ ] Tests unit >90% coverage

### Milestone 3: Infrastructure ✓
- [ ] OpenAI client implementato
- [ ] USDA client implementato
- [ ] OpenFoodFacts client implementato
- [ ] In-Memory repository implementato
- [ ] Event bus implementato
- [ ] Tests integration passano

### Milestone 4: Application ✓
- [ ] Commands implementati
- [ ] Queries implementate
- [ ] Orchestrators implementati
- [ ] DTOs implementati
- [ ] Event handlers implementati
- [ ] Tests unit >90% coverage

### Milestone 5: GraphQL ✓
- [ ] Schema aggiornato
- [ ] **Atomic queries implementate FIRST** (recognizeFood, enrichNutrients, searchFoodByBarcode)
- [ ] Atomic queries testate (validation singole capabilities)
- [ ] Aggregate queries implementate (meal, mealHistory, dailySummary)
- [ ] **Mutations implementate LAST** (orchestrazione completa)
- [ ] Tests E2E passano

### Milestone 6: Production Ready ✓
- [ ] Test coverage >90%
- [ ] MyPy passa
- [ ] Ruff passa
- [ ] Black passa
- [ ] Documentazione completa
- [ ] MongoDB opzionale configurato

---

## 🔄 Development Workflow

### Daily Workflow
```bash
# 1. Pull latest
git pull origin refactor/meal-domain-v2

# 2. Activate environment
source .venv/bin/activate  # o: uv venv

# 3. Run tests
pytest tests/unit -v

# 4. Code...

# 5. Format & lint
black backend/
ruff check backend/ --fix

# 6. Type check
mypy backend/domain backend/application

# 7. Run tests again
pytest tests/ -v

# 8. Commit
git add -A
git commit -m "feat(meal): implement X"

# 9. Push
git push origin refactor/meal-domain-v2
```

### Before Each Commit
```bash
# Run preflight checks
./scripts/preflight.sh

# Or manually:
pytest tests/unit -v
mypy backend/domain backend/application
ruff check backend/
black --check backend/
```

---

## 🎯 Quality Gates

### Code Quality
- ✅ MyPy: 0 errors (strict mode)
- ✅ Ruff: 0 violations
- ✅ Black: formatted
- ✅ No print() statements
- ✅ All functions typed

### Testing
- ✅ Unit tests: >90% coverage
- ✅ Integration tests: pass
- ✅ E2E tests: pass
- ✅ Test execution: <30s (unit), <2m (integration)

### Architecture
- ✅ No circular dependencies
- ✅ Dependency rule respected (inward only)
- ✅ Ports & Adapters implemented
- ✅ Domain layer has 0 infrastructure imports

### Documentation
- ✅ All public APIs documented
- ✅ README updated
- ✅ Architecture diagrams current
- ✅ GraphQL schema documented

---

## 📚 Next Documents

1. `02_DOMAIN_LAYER.md` - Domain implementation details
2. `03_APPLICATION_LAYER.md` - Application implementation details
3. `04_INFRASTRUCTURE_LAYER.md` - Infrastructure implementation details
4. `05_TESTING_STRATEGY.md` - Testing approach and examples

---

**Last Updated**: 22 Ottobre 2025  
**Status**: Ready for implementation
