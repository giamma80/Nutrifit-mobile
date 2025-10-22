# 🧠 Domain Layer - Implementation Details

**Data:** 22 Ottobre 2025  
**Layer:** Domain (Pure Business Logic)  
**Dependencies:** NONE (domain must be independent)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Core Domain](#core-domain)
3. [Nutrition Capability](#nutrition-capability)
4. [Recognition Capability](#recognition-capability)
5. [Barcode Capability](#barcode-capability)
6. [Testing Strategy](#testing-strategy)

---

## 🎯 Overview

Il Domain Layer contiene la **business logic pura** senza dipendenze da framework o infrastructure.

### Principles
- ✅ **Zero dependencies** su infrastructure/application
- ✅ **Immutability** per value objects
- ✅ **Invariants enforcement** in entities
- ✅ **Rich domain model** (comportamento + dati)
- ✅ **Domain events** per comunicazione asincrona

### Structure
```
domain/meal/
├── core/              # Core meal domain
│   ├── entities/      # Meal, MealEntry
│   ├── value_objects/ # MealId, Quantity, Timestamp
│   ├── events/        # MealAnalyzed, MealConfirmed
│   ├── exceptions/    # DomainError hierarchy
│   └── factories/     # MealFactory
│
├── nutrition/         # Nutrition capability
│   ├── entities/
│   ├── value_objects/
│   ├── services/
│   └── ports/
│
├── recognition/       # Recognition capability
│   ├── entities/
│   ├── value_objects/
│   ├── services/
│   └── ports/
│
└── barcode/          # Barcode capability
    ├── services/
    └── ports/
```

---

## 🏛️ Core Domain

### 1. Value Objects

Value objects sono **immutabili** e si comparano per valore, non per identità.

#### 1.1 MealId
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
        """Generate new meal ID."""
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, id_str: str) -> "MealId":
        """Create from string representation."""
        return cls(UUID(id_str))
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __repr__(self) -> str:
        return f"MealId({self.value})"
```

#### 1.2 Quantity
```python
# domain/meal/core/value_objects/quantity.py
from dataclasses import dataclass
from typing import Literal

Unit = Literal["g", "ml", "oz", "cup", "tbsp", "tsp"]

@dataclass(frozen=True)
class Quantity:
    """Value object for quantity with unit."""
    value: float
    unit: Unit = "g"
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError(f"Quantity must be positive, got {self.value}")
        
        if self.unit not in ["g", "ml", "oz", "cup", "tbsp", "tsp"]:
            raise ValueError(f"Invalid unit: {self.unit}")
    
    def to_grams(self) -> float:
        """Convert to grams (base unit)."""
        conversions = {
            "g": 1.0,
            "ml": 1.0,      # Assume density ~1 for liquids
            "oz": 28.35,
            "cup": 240.0,
            "tbsp": 15.0,
            "tsp": 5.0
        }
        return self.value * conversions[self.unit]
    
    def scale(self, factor: float) -> "Quantity":
        """Scale quantity by factor."""
        return Quantity(self.value * factor, self.unit)
    
    def __str__(self) -> str:
        return f"{self.value:.1f}{self.unit}"
```

#### 1.3 Timestamp
```python
# domain/meal/core/value_objects/timestamp.py
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True)
class Timestamp:
    """Value object for UTC timestamp."""
    value: datetime
    
    def __post_init__(self):
        if self.value.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware")
        
        if self.value > datetime.now(timezone.utc):
            raise ValueError("Timestamp cannot be in the future")
    
    @classmethod
    def now(cls) -> "Timestamp":
        """Create timestamp for current moment."""
        return cls(datetime.now(timezone.utc))
    
    @classmethod
    def from_iso(cls, iso_string: str) -> "Timestamp":
        """Create from ISO 8601 string."""
        dt = datetime.fromisoformat(iso_string)
        return cls(dt)
    
    def to_iso(self) -> str:
        """Convert to ISO 8601 string."""
        return self.value.isoformat()
    
    def is_today(self) -> bool:
        """Check if timestamp is today."""
        now = datetime.now(timezone.utc)
        return self.value.date() == now.date()
```

#### 1.4 Confidence
```python
# domain/meal/core/value_objects/confidence.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Confidence:
    """Value object for confidence score (0.0 - 1.0)."""
    value: float
    
    def __post_init__(self):
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.value}")
    
    @classmethod
    def high(cls) -> "Confidence":
        """High confidence (>0.8)."""
        return cls(0.9)
    
    @classmethod
    def medium(cls) -> "Confidence":
        """Medium confidence (0.5-0.8)."""
        return cls(0.7)
    
    @classmethod
    def low(cls) -> "Confidence":
        """Low confidence (<0.5)."""
        return cls(0.4)
    
    def is_reliable(self) -> bool:
        """Check if confidence is reliable (>0.7)."""
        return self.value > 0.7
    
    def __float__(self) -> float:
        return self.value
```

---

### 2. Entities

Entities hanno **identità** e possono cambiare stato nel tempo.

#### 2.1 MealEntry
```python
# domain/meal/core/entities/meal_entry.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

@dataclass
class MealEntry:
    """
    Entity: Single dish in a meal.
    
    Represents an individual food item (piatto) within a complete meal (pasto).
    Example: "Pasta al pomodoro" is a MealEntry in "Pranzo" Meal.
    """
    id: UUID
    meal_id: UUID
    
    # Food identification
    name: str                    # Machine-readable label (e.g., "pasta")
    display_name: str            # User-friendly name (e.g., "Pasta al Pomodoro")
    quantity_g: float           # Quantity in grams
    
    # Macronutrients (denormalized for query performance)
    calories: int
    protein: float              # grams
    carbs: float                # grams
    fat: float                  # grams
    
    # Micronutrients (optional)
    fiber: Optional[float] = None      # grams
    sugar: Optional[float] = None      # grams
    sodium: Optional[float] = None     # milligrams
    
    # Metadata
    source: str = "MANUAL"             # PHOTO | BARCODE | DESCRIPTION | MANUAL
    confidence: float = 1.0            # 0.0 - 1.0
    category: Optional[str] = None     # vegetables, fruits, meat, etc.
    barcode: Optional[str] = None      # EAN/UPC code
    image_url: Optional[str] = None    # Photo URL
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate invariants."""
        if self.quantity_g <= 0:
            raise ValueError(f"Quantity must be positive, got {self.quantity_g}")
        
        if self.calories < 0:
            raise ValueError(f"Calories cannot be negative, got {self.calories}")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")
        
        if self.source not in ["PHOTO", "BARCODE", "DESCRIPTION", "MANUAL"]:
            raise ValueError(f"Invalid source: {self.source}")
    
    def scale_nutrients(self, target_quantity_g: float) -> "MealEntry":
        """Create new entry with scaled nutrients to target quantity."""
        factor = target_quantity_g / self.quantity_g
        
        return MealEntry(
            id=uuid4(),  # New entry
            meal_id=self.meal_id,
            name=self.name,
            display_name=self.display_name,
            quantity_g=target_quantity_g,
            calories=int(self.calories * factor),
            protein=self.protein * factor,
            carbs=self.carbs * factor,
            fat=self.fat * factor,
            fiber=self.fiber * factor if self.fiber else None,
            sugar=self.sugar * factor if self.sugar else None,
            sodium=self.sodium * factor if self.sodium else None,
            source=self.source,
            confidence=self.confidence,
            category=self.category,
            barcode=self.barcode,
            image_url=self.image_url
        )
    
    def update_quantity(self, new_quantity_g: float) -> None:
        """Update quantity and scale nutrients accordingly."""
        if new_quantity_g <= 0:
            raise ValueError("Quantity must be positive")
        
        factor = new_quantity_g / self.quantity_g
        
        self.quantity_g = new_quantity_g
        self.calories = int(self.calories * factor)
        self.protein *= factor
        self.carbs *= factor
        self.fat *= factor
        
        if self.fiber:
            self.fiber *= factor
        if self.sugar:
            self.sugar *= factor
        if self.sodium:
            self.sodium *= factor
    
    def is_reliable(self) -> bool:
        """Check if entry has reliable data (confidence > 0.7)."""
        return self.confidence > 0.7
```

#### 2.2 Meal (Aggregate Root)
```python
# domain/meal/core/entities/meal.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from .meal_entry import MealEntry
from ..value_objects.timestamp import Timestamp

@dataclass
class Meal:
    """
    Aggregate Root: Complete meal with multiple dishes.
    
    A Meal represents a complete eating occasion (breakfast, lunch, etc.)
    and contains one or more MealEntry items (individual dishes).
    
    Example:
        Meal = "Pranzo del 22 Ottobre"
        ├─ MealEntry 1 = "Pasta al pomodoro" (150g)
        ├─ MealEntry 2 = "Insalata mista" (100g)
        └─ MealEntry 3 = "Pane integrale" (50g)
    
    Invariants:
    - Must have at least one entry
    - Totals must equal sum of entries
    - Timestamp cannot be in the future
    """
    id: UUID
    user_id: str
    timestamp: datetime
    meal_type: str                    # BREAKFAST | LUNCH | DINNER | SNACK
    
    # Aggregate content
    entries: List[MealEntry] = field(default_factory=list)
    
    # Aggregated totals (calculated from entries)
    total_calories: int = 0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    total_fiber: float = 0.0
    total_sugar: float = 0.0
    total_sodium: float = 0.0
    
    # Metadata
    analysis_id: Optional[str] = None
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate invariants after initialization."""
        if self.timestamp.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware")
        
        if self.meal_type not in ["BREAKFAST", "LUNCH", "DINNER", "SNACK"]:
            raise ValueError(f"Invalid meal_type: {self.meal_type}")
    
    def add_entry(self, entry: MealEntry) -> None:
        """
        Add entry to meal and recalculate totals.
        
        Args:
            entry: MealEntry to add
            
        Raises:
            ValueError: If entry.meal_id doesn't match this meal's id
        """
        if entry.meal_id != self.id:
            raise ValueError(f"Entry meal_id {entry.meal_id} doesn't match Meal id {self.id}")
        
        self.entries.append(entry)
        self._recalculate_totals()
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_entry(self, entry_id: UUID) -> None:
        """
        Remove entry from meal and recalculate totals.
        
        Args:
            entry_id: ID of entry to remove
            
        Raises:
            ValueError: If meal would have no entries after removal
        """
        self.entries = [e for e in self.entries if e.id != entry_id]
        
        if not self.entries:
            raise ValueError("Meal must have at least one entry")
        
        self._recalculate_totals()
        self.updated_at = datetime.now(timezone.utc)
    
    def update_entry(self, entry_id: UUID, **updates) -> None:
        """
        Update an entry and recalculate totals.
        
        Args:
            entry_id: ID of entry to update
            **updates: Field updates (e.g., quantity_g=200)
            
        Raises:
            ValueError: If entry not found
        """
        for entry in self.entries:
            if entry.id == entry_id:
                # Update fields
                for key, value in updates.items():
                    if hasattr(entry, key):
                        setattr(entry, key, value)
                    else:
                        raise ValueError(f"Invalid field: {key}")
                
                # Re-validate entry
                entry.__post_init__()
                break
        else:
            raise ValueError(f"Entry {entry_id} not found in meal {self.id}")
        
        self._recalculate_totals()
        self.updated_at = datetime.now(timezone.utc)
    
    def _recalculate_totals(self) -> None:
        """Recalculate aggregated totals from entries."""
        self.total_calories = sum(e.calories for e in self.entries)
        self.total_protein = sum(e.protein for e in self.entries)
        self.total_carbs = sum(e.carbs for e in self.entries)
        self.total_fat = sum(e.fat for e in self.entries)
        self.total_fiber = sum(e.fiber or 0.0 for e in self.entries)
        self.total_sugar = sum(e.sugar or 0.0 for e in self.entries)
        self.total_sodium = sum(e.sodium or 0.0 for e in self.entries)
    
    def validate_invariants(self) -> None:
        """
        Validate all meal invariants.
        
        Raises:
            ValueError: If any invariant is violated
        """
        if not self.entries:
            raise ValueError("Meal must have at least one entry")
        
        if self.timestamp > datetime.now(timezone.utc):
            raise ValueError("Timestamp cannot be in the future")
        
        # Verify totals match entries
        expected_calories = sum(e.calories for e in self.entries)
        if abs(self.total_calories - expected_calories) > 1:  # Allow 1 cal rounding
            raise ValueError(
                f"Total calories mismatch: {self.total_calories} != {expected_calories}"
            )
    
    def get_nutrient_distribution(self) -> dict:
        """
        Get macronutrient distribution as percentages.
        
        Returns:
            Dict with protein_pct, carbs_pct, fat_pct
        """
        total_cals_from_macros = (
            self.total_protein * 4 +  # 4 cal/g protein
            self.total_carbs * 4 +    # 4 cal/g carbs
            self.total_fat * 9        # 9 cal/g fat
        )
        
        if total_cals_from_macros == 0:
            return {"protein_pct": 0, "carbs_pct": 0, "fat_pct": 0}
        
        return {
            "protein_pct": (self.total_protein * 4 / total_cals_from_macros) * 100,
            "carbs_pct": (self.total_carbs * 4 / total_cals_from_macros) * 100,
            "fat_pct": (self.total_fat * 9 / total_cals_from_macros) * 100,
        }
    
    def is_high_protein(self) -> bool:
        """Check if meal is high protein (>30% calories from protein)."""
        distribution = self.get_nutrient_distribution()
        return distribution["protein_pct"] > 30
    
    def average_confidence(self) -> float:
        """Calculate average confidence across all entries."""
        if not self.entries:
            return 0.0
        return sum(e.confidence for e in self.entries) / len(self.entries)
```

---

### 3. Domain Events

Events rappresentano fatti che sono accaduti nel domain.

#### 3.1 Base Event
```python
# domain/meal/core/events/base.py
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events."""
    event_id: UUID
    occurred_at: datetime
    
    def __post_init__(self):
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
```

#### 3.2 MealAnalyzed
```python
# domain/meal/core/events/meal_analyzed.py
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .base import DomainEvent

@dataclass(frozen=True)
class MealAnalyzed(DomainEvent):
    """Domain event: Meal has been analyzed."""
    meal_id: UUID
    user_id: str
    source: str              # PHOTO | BARCODE | DESCRIPTION
    item_count: int
    average_confidence: float
    
    @classmethod
    def create(
        cls,
        meal_id: UUID,
        user_id: str,
        source: str,
        item_count: int,
        average_confidence: float
    ) -> "MealAnalyzed":
        """Create new MealAnalyzed event."""
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            meal_id=meal_id,
            user_id=user_id,
            source=source,
            item_count=item_count,
            average_confidence=average_confidence
        )
```

#### 3.3 MealConfirmed
```python
# domain/meal/core/events/meal_confirmed.py
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .base import DomainEvent

@dataclass(frozen=True)
class MealConfirmed(DomainEvent):
    """Domain event: Meal has been confirmed by user."""
    meal_id: UUID
    user_id: str
    confirmed_entry_count: int
    rejected_entry_count: int
    
    @classmethod
    def create(
        cls,
        meal_id: UUID,
        user_id: str,
        confirmed_entry_count: int,
        rejected_entry_count: int
    ) -> "MealConfirmed":
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            meal_id=meal_id,
            user_id=user_id,
            confirmed_entry_count=confirmed_entry_count,
            rejected_entry_count=rejected_entry_count
        )
```

#### 3.4 MealUpdated & MealDeleted
```python
# domain/meal/core/events/meal_updated.py
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4

from .base import DomainEvent

@dataclass(frozen=True)
class MealUpdated(DomainEvent):
    """Domain event: Meal has been updated."""
    meal_id: UUID
    user_id: str
    updated_fields: List[str]
    
    @classmethod
    def create(cls, meal_id: UUID, user_id: str, updated_fields: List[str]) -> "MealUpdated":
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            meal_id=meal_id,
            user_id=user_id,
            updated_fields=updated_fields
        )


# domain/meal/core/events/meal_deleted.py
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .base import DomainEvent

@dataclass(frozen=True)
class MealDeleted(DomainEvent):
    """Domain event: Meal has been deleted."""
    meal_id: UUID
    user_id: str
    
    @classmethod
    def create(cls, meal_id: UUID, user_id: str) -> "MealDeleted":
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            meal_id=meal_id,
            user_id=user_id
        )
```

---

### 4. Exceptions

```python
# domain/meal/core/exceptions/domain_errors.py

class MealDomainError(Exception):
    """Base exception for meal domain."""
    pass


class InvalidMealError(MealDomainError):
    """Meal invariants violated."""
    pass


class MealNotFoundError(MealDomainError):
    """Meal not found."""
    pass


class EntryNotFoundError(MealDomainError):
    """Entry not found in meal."""
    pass


class InvalidQuantityError(MealDomainError):
    """Invalid quantity specified."""
    pass


class InvalidTimestampError(MealDomainError):
    """Invalid timestamp (e.g., in the future)."""
    pass
```

---

### 5. Factory

```python
# domain/meal/core/factories/meal_factory.py
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from uuid import uuid4

from ..entities.meal import Meal, MealEntry

class MealFactory:
    """Factory for creating Meal aggregates."""
    
    @staticmethod
    def create_from_analysis(
        user_id: str,
        items: List[Tuple[dict, dict]],  # (recognized_food, nutrients)
        source: str,
        timestamp: Optional[datetime] = None,
        meal_type: str = "SNACK",
        photo_url: Optional[str] = None,
        analysis_id: Optional[str] = None
    ) -> Meal:
        """
        Create Meal from AI analysis results.
        
        Args:
            user_id: User ID
            items: List of (recognized_food, nutrients) tuples
            source: PHOTO | BARCODE | DESCRIPTION
            timestamp: Meal timestamp (default: now)
            meal_type: BREAKFAST | LUNCH | DINNER | SNACK
            photo_url: Optional photo URL
            analysis_id: Optional analysis ID
            
        Returns:
            New Meal aggregate with all entries
        """
        meal_id = uuid4()
        timestamp = timestamp or datetime.now(timezone.utc)
        
        # Create entries from analysis
        entries = []
        for recognized, nutrients in items:
            entry = MealEntry(
                id=uuid4(),
                meal_id=meal_id,
                name=recognized["label"],
                display_name=recognized["display_name"],
                quantity_g=recognized["quantity_g"],
                calories=nutrients["calories"],
                protein=nutrients["protein"],
                carbs=nutrients["carbs"],
                fat=nutrients["fat"],
                fiber=nutrients.get("fiber"),
                sugar=nutrients.get("sugar"),
                sodium=nutrients.get("sodium"),
                source=source,
                confidence=recognized["confidence"],
                category=recognized.get("category"),
                image_url=photo_url
            )
            entries.append(entry)
        
        # Create meal
        meal = Meal(
            id=meal_id,
            user_id=user_id,
            timestamp=timestamp,
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
        timestamp: Optional[datetime] = None
    ) -> Meal:
        """
        Create Meal from manual entry.
        
        Args:
            user_id: User ID
            name: Food name
            quantity_g: Quantity in grams
            calories: Calories
            protein: Protein (g)
            carbs: Carbs (g)
            fat: Fat (g)
            meal_type: BREAKFAST | LUNCH | DINNER | SNACK
            timestamp: Meal timestamp (default: now)
            
        Returns:
            New Meal aggregate with single entry
        """
        meal_id = uuid4()
        timestamp = timestamp or datetime.now(timezone.utc)
        
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
            timestamp=timestamp,
            meal_type=meal_type,
            entries=[entry]
        )
        
        meal._recalculate_totals()
        
        return meal
```

---

## 🥗 Nutrition Capability

### 1. Entities

```python
# domain/meal/nutrition/entities/nutrient_profile.py
from dataclasses import dataclass
from typing import Optional, Literal

NutrientSource = Literal["USDA", "BARCODE_DB", "CATEGORY", "AI_ESTIMATE"]

@dataclass
class NutrientProfile:
    """Complete nutrient profile for a food item."""
    
    # Macronutrients (required)
    calories: int
    protein: float          # grams
    carbs: float           # grams
    fat: float             # grams
    
    # Micronutrients (optional)
    fiber: Optional[float] = None      # grams
    sugar: Optional[float] = None      # grams
    sodium: Optional[float] = None     # milligrams
    
    # Metadata
    source: NutrientSource = "USDA"
    confidence: float = 0.9
    quantity_g: float = 100.0          # Reference quantity
    
    def __post_init__(self):
        if self.quantity_g <= 0:
            raise ValueError("Quantity must be positive")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
    
    def scale_to_quantity(self, target_g: float) -> "NutrientProfile":
        """Scale nutrients to target quantity."""
        factor = target_g / self.quantity_g
        
        return NutrientProfile(
            calories=int(self.calories * factor),
            protein=self.protein * factor,
            carbs=self.carbs * factor,
            fat=self.fat * factor,
            fiber=self.fiber * factor if self.fiber else None,
            sugar=self.sugar * factor if self.sugar else None,
            sodium=self.sodium * factor if self.sodium else None,
            source=self.source,
            confidence=self.confidence,
            quantity_g=target_g
        )
    
    def calories_from_macros(self) -> int:
        """Calculate calories from macronutrients (4-4-9 rule)."""
        return int(
            self.protein * 4 +
            self.carbs * 4 +
            self.fat * 9
        )
    
    def is_high_quality(self) -> bool:
        """Check if data is high quality (USDA/Barcode, confidence > 0.8)."""
        return (
            self.source in ["USDA", "BARCODE_DB"] and
            self.confidence > 0.8
        )
```

### 2. Services

```python
# domain/meal/nutrition/services/enrichment_service.py
from typing import Optional
import structlog

from ..entities.nutrient_profile import NutrientProfile
from ..ports.nutrition_provider import INutritionProvider

logger = structlog.get_logger(__name__)

class NutritionEnrichmentService:
    """
    Domain service for enriching food items with nutrients.
    
    Strategy (cascade):
    1. USDA database (high quality)
    2. Category profile (medium quality)
    3. Generic fallback (low quality)
    """
    
    def __init__(
        self,
        usda_provider: INutritionProvider,
        category_provider: INutritionProvider,
        fallback_provider: INutritionProvider
    ):
        self._usda = usda_provider
        self._category = category_provider
        self._fallback = fallback_provider
    
    async def enrich(
        self,
        label: str,
        quantity_g: float,
        category: Optional[str] = None
    ) -> NutrientProfile:
        """
        Enrich food label with nutrient data.
        
        Args:
            label: Food label (e.g., "chicken breast")
            quantity_g: Quantity in grams
            category: Optional category hint
            
        Returns:
            NutrientProfile scaled to quantity
        """
        # Try USDA first
        try:
            profile = await self._usda.get_nutrients(label, 100.0)
            if profile:
                logger.info("usda_enrichment_success", label=label)
                return profile.scale_to_quantity(quantity_g)
        except Exception as e:
            logger.warning("usda_enrichment_failed", label=label, error=str(e))
        
        # Try category profile
        if category:
            try:
                profile = await self._category.get_nutrients(category, 100.0)
                if profile:
                    logger.info("category_enrichment_success", label=label, category=category)
                    return profile.scale_to_quantity(quantity_g)
            except Exception as e:
                logger.warning("category_enrichment_failed", category=category, error=str(e))
        
        # Fallback to generic
        logger.info("fallback_enrichment", label=label)
        profile = await self._fallback.get_nutrients("generic", 100.0)
        return profile.scale_to_quantity(quantity_g)
```

### 3. Ports

```python
# domain/meal/nutrition/ports/nutrition_provider.py
from typing import Protocol, Optional

from ..entities.nutrient_profile import NutrientProfile

class INutritionProvider(Protocol):
    """Interface for nutrition data providers."""
    
    async def get_nutrients(
        self,
        identifier: str,
        quantity_g: float
    ) -> Optional[NutrientProfile]:
        """
        Get nutrient profile for identifier.
        
        Args:
            identifier: Food identifier (label, category, or FDC ID)
            quantity_g: Reference quantity
            
        Returns:
            NutrientProfile or None if not found
        """
        ...
```

---

## 🔍 Recognition Capability

### 1. Entities

```python
# domain/meal/recognition/entities/recognized_food.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class RecognizedFood:
    """Single food item recognized from photo/text."""
    label: str                      # Machine-readable (e.g., "pasta")
    display_name: str               # User-friendly (e.g., "Spaghetti al Pomodoro")
    quantity_g: float              # Estimated quantity
    confidence: float              # 0.0 - 1.0
    category: Optional[str] = None # USDA category
    
    def __post_init__(self):
        if self.quantity_g <= 0:
            raise ValueError("Quantity must be positive")
        
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
    
    def is_reliable(self) -> bool:
        """Check if recognition is reliable (confidence > 0.7)."""
        return self.confidence > 0.7


@dataclass
class FoodRecognitionResult:
    """Complete recognition result from photo/text."""
    items: list[RecognizedFood]
    dish_name: Optional[str] = None    # Overall dish name
    confidence: float = 0.0            # Average confidence
    processing_time_ms: int = 0
    
    def __post_init__(self):
        if not self.items:
            raise ValueError("Recognition must have at least one item")
        
        # Calculate average confidence if not provided
        if self.confidence == 0.0:
            self.confidence = sum(i.confidence for i in self.items) / len(self.items)
```

### 2. Services

```python
# domain/meal/recognition/services/recognition_service.py
from typing import Optional
import structlog

from ..entities.recognized_food import FoodRecognitionResult
from ..ports.vision_provider import IVisionProvider

logger = structlog.get_logger(__name__)

class FoodRecognitionService:
    """Domain service for AI-powered food recognition."""
    
    def __init__(self, vision_provider: IVisionProvider):
        self._vision = vision_provider
    
    async def recognize_from_photo(
        self,
        photo_url: str,
        dish_hint: Optional[str] = None
    ) -> FoodRecognitionResult:
        """
        Recognize food items from photo.
        
        Args:
            photo_url: URL of photo
            dish_hint: Optional hint from user
            
        Returns:
            FoodRecognitionResult with recognized items
        """
        logger.info("recognizing_food_from_photo", photo_url=photo_url)
        
        result = await self._vision.analyze_photo(photo_url, dish_hint)
        
        logger.info(
            "recognition_complete",
            item_count=len(result.items),
            confidence=result.confidence
        )
        
        return result
    
    async def recognize_from_text(
        self,
        description: str
    ) -> FoodRecognitionResult:
        """
        Extract food items from text description.
        
        Args:
            description: Text description
            
        Returns:
            FoodRecognitionResult with extracted items
        """
        logger.info("recognizing_food_from_text", text_length=len(description))
        
        result = await self._vision.analyze_text(description)
        
        logger.info(
            "recognition_complete",
            item_count=len(result.items),
            confidence=result.confidence
        )
        
        return result
```

### 3. Ports

```python
# domain/meal/recognition/ports/vision_provider.py
from typing import Protocol, Optional

from ..entities.recognized_food import FoodRecognitionResult

class IVisionProvider(Protocol):
    """Interface for vision AI providers."""
    
    async def analyze_photo(
        self,
        photo_url: str,
        hint: Optional[str] = None
    ) -> FoodRecognitionResult:
        """Analyze photo and recognize food items."""
        ...
    
    async def analyze_text(
        self,
        description: str
    ) -> FoodRecognitionResult:
        """Extract food items from text."""
        ...
```

---

## 🧪 Testing Strategy

### Unit Tests Example

```python
# tests/unit/domain/meal/core/test_meal_entity.py
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from domain.meal.core.entities.meal import Meal, MealEntry

def test_meal_add_entry_updates_totals():
    """Test that adding entry updates meal totals."""
    # Arrange
    meal_id = uuid4()
    meal = Meal(
        id=meal_id,
        user_id="user123",
        timestamp=datetime.now(timezone.utc),
        meal_type="LUNCH"
    )
    
    entry = MealEntry(
        id=uuid4(),
        meal_id=meal_id,
        name="pasta",
        display_name="Pasta",
        quantity_g=100,
        calories=150,
        protein=5.0,
        carbs=30.0,
        fat=2.0
    )
    
    # Act
    meal.add_entry(entry)
    
    # Assert
    assert meal.total_calories == 150
    assert meal.total_protein == 5.0
    assert meal.total_carbs == 30.0
    assert meal.total_fat == 2.0


def test_meal_cannot_remove_last_entry():
    """Test that removing last entry raises error."""
    # Arrange
    meal_id = uuid4()
    entry = MealEntry(
        id=uuid4(),
        meal_id=meal_id,
        name="pasta",
        display_name="Pasta",
        quantity_g=100,
        calories=150,
        protein=5.0,
        carbs=30.0,
        fat=2.0
    )
    
    meal = Meal(
        id=meal_id,
        user_id="user123",
        timestamp=datetime.now(timezone.utc),
        meal_type="LUNCH",
        entries=[entry]
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="at least one entry"):
        meal.remove_entry(entry.id)
```

---

**Next**: `03_APPLICATION_LAYER.md` - CQRS Commands, Queries, Orchestrators

**Last Updated**: 22 Ottobre 2025
