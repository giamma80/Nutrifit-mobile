# ⚡ Application Layer - Implementation Details

**Data:** 22 Ottobre 2025  
**Layer:** Application (Use Cases & Orchestration)  
**Dependencies:** Domain Layer only

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [CQRS Commands](#cqrs-commands)
3. [CQRS Queries](#cqrs-queries)
4. [Orchestrators](#orchestrators)
5. [DTOs](#dtos)
6. [Event Handlers](#event-handlers)
7. [Testing Strategy](#testing-strategy)

---

## 🎯 Overview

L'Application Layer coordina il domain per implementare use cases. Implementa il pattern **CQRS** (Command Query Responsibility Segregation).

### Principles
- ✅ **Single Responsibility**: Un command/query = un use case
- ✅ **Dependency Inversion**: Dipende da domain ports, non da infra
- ✅ **Orchestration**: Coordina multiple domain services
- ✅ **Transaction Boundaries**: Definisce unit of work
- ✅ **DTO Mapping**: Trasforma domain → DTO per API layer

### Structure
```
application/meal/
├── commands/              # Write operations (CQRS)
│   ├── analyze_photo.py
│   ├── analyze_barcode.py
│   ├── analyze_description.py
│   ├── confirm_analysis.py
│   ├── update_meal.py
│   └── delete_meal.py
│
├── queries/               # Read operations (CQRS)
│   ├── get_meal.py
│   ├── list_meals.py
│   ├── search_meals.py
│   └── daily_summary.py
│
├── orchestrators/         # Complex workflows
│   ├── photo_orchestrator.py
│   ├── barcode_orchestrator.py
│   └── description_orchestrator.py
│
├── dtos/                  # Data Transfer Objects
│   ├── meal_dto.py
│   └── analysis_dto.py
│
└── event_handlers/        # Domain event subscribers
    ├── meal_analyzed_handler.py
    └── meal_confirmed_handler.py
```

---

## 📝 CQRS Commands

Commands sono **write operations** che modificano lo stato del sistema.

### Pattern Structure
```python
# Command: Immutable data class
@dataclass(frozen=True)
class SomeCommand:
    """Command for doing something."""
    field1: str
    field2: int

# Handler: Executes command
class SomeCommandHandler:
    """Handler for SomeCommand."""
    
    def __init__(self, dependencies...):
        self._dep = dependencies
    
    async def handle(self, command: SomeCommand) -> Result:
        """Execute command and return result."""
        # Business logic here
        pass
```

---

### 1. AnalyzeMealPhotoCommand

```python
# application/meal/commands/analyze_photo.py
from dataclasses import dataclass
from typing import Optional
from uuid import UUID
import structlog

from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_analyzed import MealAnalyzed
from domain.shared.ports.repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus
from ..orchestrators.photo_orchestrator import PhotoOrchestrator

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AnalyzeMealPhotoCommand:
    """
    Command: Analyze meal from photo.
    
    This is step 1 of the 2-step meal creation flow:
    1. analyzeMealPhoto → creates meal in "pending" state
    2. confirmMealAnalysis → confirms and persists meal
    """
    user_id: str
    photo_url: str
    dish_hint: Optional[str] = None
    meal_type: str = "SNACK"
    idempotency_key: Optional[str] = None


class AnalyzeMealPhotoCommandHandler:
    """Handler for AnalyzeMealPhotoCommand."""
    
    def __init__(
        self,
        orchestrator: PhotoOrchestrator,
        repository: IMealRepository,
        event_bus: IEventBus
    ):
        self._orchestrator = orchestrator
        self._repository = repository
        self._event_bus = event_bus
    
    async def handle(self, command: AnalyzeMealPhotoCommand) -> Meal:
        """
        Execute photo analysis command.
        
        Flow:
        1. Orchestrate recognition + enrichment
        2. Create Meal aggregate
        3. Persist meal
        4. Publish MealAnalyzed event
        
        Args:
            command: AnalyzeMealPhotoCommand
            
        Returns:
            Analyzed Meal (not yet confirmed by user)
        """
        logger.info(
            "analyzing_meal_photo",
            user_id=command.user_id,
            photo_url=command.photo_url,
            meal_type=command.meal_type
        )
        
        # 1. Orchestrate analysis workflow
        meal = await self._orchestrator.analyze(
            user_id=command.user_id,
            photo_url=command.photo_url,
            dish_hint=command.dish_hint,
            meal_type=command.meal_type
        )
        
        # 2. Persist meal
        await self._repository.save(meal)
        
        logger.info(
            "meal_analyzed",
            meal_id=str(meal.id),
            entry_count=len(meal.entries),
            total_calories=meal.total_calories
        )
        
        # 3. Publish domain event
        event = MealAnalyzed.create(
            meal_id=meal.id,
            user_id=command.user_id,
            source="PHOTO",
            item_count=len(meal.entries),
            average_confidence=meal.average_confidence()
        )
        await self._event_bus.publish(event)
        
        return meal
```

---

### 2. AnalyzeMealBarcodeCommand

```python
# application/meal/commands/analyze_barcode.py
from dataclasses import dataclass
from typing import Optional
import structlog

from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_analyzed import MealAnalyzed
from domain.shared.ports.repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus
from ..orchestrators.barcode_orchestrator import BarcodeOrchestrator

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AnalyzeMealBarcodeCommand:
    """Command: Analyze meal from barcode."""
    user_id: str
    barcode: str
    quantity_g: float
    meal_type: str = "SNACK"
    idempotency_key: Optional[str] = None


class AnalyzeMealBarcodeCommandHandler:
    """Handler for AnalyzeMealBarcodeCommand."""
    
    def __init__(
        self,
        orchestrator: BarcodeOrchestrator,
        repository: IMealRepository,
        event_bus: IEventBus
    ):
        self._orchestrator = orchestrator
        self._repository = repository
        self._event_bus = event_bus
    
    async def handle(self, command: AnalyzeMealBarcodeCommand) -> Meal:
        """
        Execute barcode analysis command.
        
        Flow:
        1. Orchestrate barcode lookup + enrichment
        2. Create Meal aggregate
        3. Persist meal
        4. Publish MealAnalyzed event
        """
        logger.info(
            "analyzing_meal_barcode",
            user_id=command.user_id,
            barcode=command.barcode,
            quantity_g=command.quantity_g
        )
        
        # 1. Orchestrate barcode workflow
        meal = await self._orchestrator.analyze(
            user_id=command.user_id,
            barcode=command.barcode,
            quantity_g=command.quantity_g,
            meal_type=command.meal_type
        )
        
        # 2. Persist meal
        await self._repository.save(meal)
        
        logger.info(
            "meal_analyzed",
            meal_id=str(meal.id),
            product_name=meal.entries[0].name,
            total_calories=meal.total_calories
        )
        
        # 3. Publish event
        event = MealAnalyzed.create(
            meal_id=meal.id,
            user_id=command.user_id,
            source="BARCODE",
            item_count=1,
            average_confidence=1.0  # Barcode = high confidence
        )
        await self._event_bus.publish(event)
        
        return meal
```

---

### 3. ConfirmAnalysisCommand

```python
# application/meal/commands/confirm_analysis.py
from dataclasses import dataclass
from typing import List
from uuid import UUID
import structlog

from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_confirmed import MealConfirmed
from domain.meal.core.exceptions.domain_errors import MealNotFoundError
from domain.shared.ports.repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ConfirmAnalysisCommand:
    """
    Command: Confirm meal analysis.
    
    This is step 2 of the 2-step flow. User selects which
    recognized items to keep and which to reject.
    """
    meal_id: UUID
    user_id: str
    confirmed_entry_ids: List[UUID]


class ConfirmAnalysisCommandHandler:
    """Handler for ConfirmAnalysisCommand."""
    
    def __init__(
        self,
        repository: IMealRepository,
        event_bus: IEventBus
    ):
        self._repository = repository
        self._event_bus = event_bus
    
    async def handle(self, command: ConfirmAnalysisCommand) -> Meal:
        """
        Execute confirmation command.
        
        Flow:
        1. Load meal
        2. Remove unconfirmed entries
        3. Recalculate totals
        4. Persist updated meal
        5. Publish MealConfirmed event
        """
        logger.info(
            "confirming_meal_analysis",
            meal_id=str(command.meal_id),
            confirmed_count=len(command.confirmed_entry_ids)
        )
        
        # 1. Load meal
        meal = await self._repository.get_by_id(command.meal_id)
        if not meal:
            raise MealNotFoundError(f"Meal {command.meal_id} not found")
        
        # Verify ownership
        if meal.user_id != command.user_id:
            raise PermissionError("User doesn't own this meal")
        
        # 2. Remove unconfirmed entries
        total_entries = len(meal.entries)
        entry_ids_to_remove = [
            e.id for e in meal.entries
            if e.id not in command.confirmed_entry_ids
        ]
        
        for entry_id in entry_ids_to_remove:
            try:
                meal.remove_entry(entry_id)
            except ValueError:
                # Last entry - keep it even if unconfirmed
                logger.warning("cannot_remove_last_entry", meal_id=str(meal.id))
                break
        
        # 3. Persist updated meal
        await self._repository.save(meal)
        
        confirmed_count = len(meal.entries)
        rejected_count = total_entries - confirmed_count
        
        logger.info(
            "meal_confirmed",
            meal_id=str(meal.id),
            confirmed_count=confirmed_count,
            rejected_count=rejected_count,
            total_calories=meal.total_calories
        )
        
        # 4. Publish event
        event = MealConfirmed.create(
            meal_id=meal.id,
            user_id=command.user_id,
            confirmed_entry_count=confirmed_count,
            rejected_entry_count=rejected_count
        )
        await self._event_bus.publish(event)
        
        return meal
```

---

### 4. UpdateMealCommand

```python
# application/meal/commands/update_meal.py
from dataclasses import dataclass
from typing import Dict, Any, List
from uuid import UUID
import structlog

from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_updated import MealUpdated
from domain.meal.core.exceptions.domain_errors import MealNotFoundError
from domain.shared.ports.repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class UpdateMealCommand:
    """Command: Update meal fields."""
    meal_id: UUID
    user_id: str
    updates: Dict[str, Any]  # Field updates (e.g., {"meal_type": "LUNCH"})


class UpdateMealCommandHandler:
    """Handler for UpdateMealCommand."""
    
    def __init__(
        self,
        repository: IMealRepository,
        event_bus: IEventBus
    ):
        self._repository = repository
        self._event_bus = event_bus
    
    async def handle(self, command: UpdateMealCommand) -> Meal:
        """
        Execute update command.
        
        Allowed updates:
        - meal_type
        - timestamp
        - notes
        - Entry updates (via entry_id)
        """
        logger.info(
            "updating_meal",
            meal_id=str(command.meal_id),
            updates=list(command.updates.keys())
        )
        
        # 1. Load meal
        meal = await self._repository.get_by_id(command.meal_id)
        if not meal:
            raise MealNotFoundError(f"Meal {command.meal_id} not found")
        
        # Verify ownership
        if meal.user_id != command.user_id:
            raise PermissionError("User doesn't own this meal")
        
        # 2. Apply updates
        updated_fields: List[str] = []
        
        for field, value in command.updates.items():
            if hasattr(meal, field):
                setattr(meal, field, value)
                updated_fields.append(field)
            else:
                logger.warning("unknown_field", field=field)
        
        # 3. Validate invariants
        meal.validate_invariants()
        
        # 4. Persist
        await self._repository.save(meal)
        
        logger.info(
            "meal_updated",
            meal_id=str(meal.id),
            updated_fields=updated_fields
        )
        
        # 5. Publish event
        event = MealUpdated.create(
            meal_id=meal.id,
            user_id=command.user_id,
            updated_fields=updated_fields
        )
        await self._event_bus.publish(event)
        
        return meal
```

---

### 5. DeleteMealCommand

```python
# application/meal/commands/delete_meal.py
from dataclasses import dataclass
from uuid import UUID
import structlog

from domain.meal.core.events.meal_deleted import MealDeleted
from domain.meal.core.exceptions.domain_errors import MealNotFoundError
from domain.shared.ports.repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class DeleteMealCommand:
    """Command: Delete meal."""
    meal_id: UUID
    user_id: str


class DeleteMealCommandHandler:
    """Handler for DeleteMealCommand."""
    
    def __init__(
        self,
        repository: IMealRepository,
        event_bus: IEventBus
    ):
        self._repository = repository
        self._event_bus = event_bus
    
    async def handle(self, command: DeleteMealCommand) -> bool:
        """
        Execute delete command.
        
        Returns:
            True if deleted, False if not found
        """
        logger.info("deleting_meal", meal_id=str(command.meal_id))
        
        # 1. Verify ownership before deletion
        meal = await self._repository.get_by_id(command.meal_id)
        if not meal:
            return False
        
        if meal.user_id != command.user_id:
            raise PermissionError("User doesn't own this meal")
        
        # 2. Delete
        deleted = await self._repository.delete(command.meal_id)
        
        if deleted:
            logger.info("meal_deleted", meal_id=str(command.meal_id))
            
            # 3. Publish event
            event = MealDeleted.create(
                meal_id=command.meal_id,
                user_id=command.user_id
            )
            await self._event_bus.publish(event)
        
        return deleted
```

---

## 🔍 CQRS Queries

Queries sono **read operations** che non modificano stato.

### 1. GetMealQuery

```python
# application/meal/queries/get_meal.py
from dataclasses import dataclass
from typing import Optional
from uuid import UUID
import structlog

from domain.meal.core.entities.meal import Meal
from domain.shared.ports.repository import IMealRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class GetMealQuery:
    """Query: Get single meal by ID."""
    meal_id: UUID
    user_id: str


class GetMealQueryHandler:
    """Handler for GetMealQuery."""
    
    def __init__(self, repository: IMealRepository):
        self._repository = repository
    
    async def handle(self, query: GetMealQuery) -> Optional[Meal]:
        """
        Execute query.
        
        Returns:
            Meal or None if not found/not owned
        """
        meal = await self._repository.get_by_id(query.meal_id)
        
        # Verify ownership
        if meal and meal.user_id != query.user_id:
            logger.warning(
                "meal_access_denied",
                meal_id=str(query.meal_id),
                user_id=query.user_id
            )
            return None
        
        return meal
```

---

### 2. ListMealsQuery

```python
# application/meal/queries/list_meals.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import structlog

from domain.meal.core.entities.meal import Meal
from domain.shared.ports.repository import IMealRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ListMealsQuery:
    """Query: List meals for user with filters."""
    user_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    meal_type: Optional[str] = None
    limit: int = 100
    offset: int = 0


class ListMealsQueryHandler:
    """Handler for ListMealsQuery."""
    
    def __init__(self, repository: IMealRepository):
        self._repository = repository
    
    async def handle(self, query: ListMealsQuery) -> List[Meal]:
        """
        Execute query.
        
        Returns:
            List of meals matching filters
        """
        logger.info(
            "listing_meals",
            user_id=query.user_id,
            start_date=query.start_date,
            end_date=query.end_date,
            limit=query.limit
        )
        
        # Fetch from repository
        meals = await self._repository.list_by_user(
            user_id=query.user_id,
            start_date=query.start_date,
            end_date=query.end_date,
            limit=query.limit,
            offset=query.offset
        )
        
        # Apply meal_type filter if specified
        if query.meal_type:
            meals = [m for m in meals if m.meal_type == query.meal_type]
        
        logger.info("meals_listed", count=len(meals))
        
        return meals
```

---

### 3. DailySummaryQuery

```python
# application/meal/queries/daily_summary.py
from dataclasses import dataclass
from datetime import datetime, timezone
import structlog

from domain.shared.ports.repository import IMealRepository

logger = structlog.get_logger(__name__)


@dataclass
class DailySummary:
    """Daily nutrition summary."""
    date: datetime
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    meal_count: int
    breakfast_calories: int
    lunch_calories: int
    dinner_calories: int
    snack_calories: int


@dataclass(frozen=True)
class DailySummaryQuery:
    """Query: Get daily nutrition summary."""
    user_id: str
    date: datetime


class DailySummaryQueryHandler:
    """Handler for DailySummaryQuery."""
    
    def __init__(self, repository: IMealRepository):
        self._repository = repository
    
    async def handle(self, query: DailySummaryQuery) -> DailySummary:
        """
        Execute query and aggregate daily totals.
        
        Returns:
            DailySummary with aggregated data
        """
        # Get start/end of day
        start = query.date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59)
        
        # Fetch meals for day
        meals = await self._repository.list_by_user(
            user_id=query.user_id,
            start_date=start,
            end_date=end
        )
        
        # Aggregate
        total_calories = sum(m.total_calories for m in meals)
        total_protein = sum(m.total_protein for m in meals)
        total_carbs = sum(m.total_carbs for m in meals)
        total_fat = sum(m.total_fat for m in meals)
        
        # Breakdown by meal type
        breakfast_calories = sum(
            m.total_calories for m in meals if m.meal_type == "BREAKFAST"
        )
        lunch_calories = sum(
            m.total_calories for m in meals if m.meal_type == "LUNCH"
        )
        dinner_calories = sum(
            m.total_calories for m in meals if m.meal_type == "DINNER"
        )
        snack_calories = sum(
            m.total_calories for m in meals if m.meal_type == "SNACK"
        )
        
        summary = DailySummary(
            date=query.date,
            total_calories=total_calories,
            total_protein=total_protein,
            total_carbs=total_carbs,
            total_fat=total_fat,
            meal_count=len(meals),
            breakfast_calories=breakfast_calories,
            lunch_calories=lunch_calories,
            dinner_calories=dinner_calories,
            snack_calories=snack_calories
        )
        
        logger.info(
            "daily_summary_calculated",
            date=query.date.date(),
            total_calories=total_calories,
            meal_count=len(meals)
        )
        
        return summary
```

---

## 🎭 Orchestrators

Orchestrators coordinano **multiple domain services** per workflow complessi.

### 1. PhotoOrchestrator

```python
# application/meal/orchestrators/photo_orchestrator.py
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import uuid4
import structlog

from domain.meal.core.entities.meal import Meal
from domain.meal.core.factories.meal_factory import MealFactory
from domain.meal.recognition.services.recognition_service import FoodRecognitionService
from domain.meal.nutrition.services.enrichment_service import NutritionEnrichmentService

logger = structlog.get_logger(__name__)


class PhotoOrchestrator:
    """
    Orchestrate photo meal analysis workflow.
    
    Flow:
    1. Recognize foods from photo (Recognition Service)
    2. Enrich each food with nutrients (Nutrition Service)
    3. Create Meal aggregate (Factory)
    """
    
    def __init__(
        self,
        recognition_service: FoodRecognitionService,
        nutrition_service: NutritionEnrichmentService,
        meal_factory: MealFactory
    ):
        self._recognition = recognition_service
        self._nutrition = nutrition_service
        self._factory = meal_factory
    
    async def analyze(
        self,
        user_id: str,
        photo_url: str,
        dish_hint: Optional[str] = None,
        meal_type: str = "SNACK",
        timestamp: Optional[datetime] = None
    ) -> Meal:
        """
        Orchestrate complete photo analysis workflow.
        
        Args:
            user_id: User ID
            photo_url: URL of meal photo
            dish_hint: Optional hint from user
            meal_type: BREAKFAST | LUNCH | DINNER | SNACK
            timestamp: Meal timestamp (default: now)
            
        Returns:
            Analyzed Meal aggregate
        """
        logger.info("orchestrating_photo_analysis", photo_url=photo_url)
        
        # 1. Recognize foods from photo
        recognition_result = await self._recognition.recognize_from_photo(
            photo_url=photo_url,
            dish_hint=dish_hint
        )
        
        logger.info(
            "recognition_complete",
            item_count=len(recognition_result.items),
            confidence=recognition_result.confidence
        )
        
        # 2. Enrich each food with nutrients
        enriched_items: List[Tuple[dict, dict]] = []
        
        for food in recognition_result.items:
            # Get nutrients
            nutrients = await self._nutrition.enrich(
                label=food.label,
                quantity_g=food.quantity_g,
                category=food.category
            )
            
            # Convert to dicts for factory
            food_dict = {
                "label": food.label,
                "display_name": food.display_name,
                "quantity_g": food.quantity_g,
                "confidence": food.confidence,
                "category": food.category
            }
            
            nutrients_dict = {
                "calories": nutrients.calories,
                "protein": nutrients.protein,
                "carbs": nutrients.carbs,
                "fat": nutrients.fat,
                "fiber": nutrients.fiber,
                "sugar": nutrients.sugar,
                "sodium": nutrients.sodium
            }
            
            enriched_items.append((food_dict, nutrients_dict))
        
        logger.info("enrichment_complete", item_count=len(enriched_items))
        
        # 3. Create Meal aggregate
        meal = self._factory.create_from_analysis(
            user_id=user_id,
            items=enriched_items,
            source="PHOTO",
            timestamp=timestamp or datetime.now(timezone.utc),
            meal_type=meal_type,
            photo_url=photo_url,
            analysis_id=f"photo_{uuid4().hex[:12]}"
        )
        
        logger.info(
            "photo_analysis_complete",
            meal_id=str(meal.id),
            total_calories=meal.total_calories
        )
        
        return meal
```

---

### 2. BarcodeOrchestrator

```python
# application/meal/orchestrators/barcode_orchestrator.py
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
import structlog

from domain.meal.core.entities.meal import Meal
from domain.meal.core.factories.meal_factory import MealFactory
from domain.meal.barcode.services.barcode_service import BarcodeService
from domain.meal.nutrition.services.enrichment_service import NutritionEnrichmentService

logger = structlog.get_logger(__name__)


class BarcodeOrchestrator:
    """
    Orchestrate barcode meal analysis workflow.
    
    Flow:
    1. Lookup product by barcode (Barcode Service)
    2. Enrich with nutrients if needed (Nutrition Service)
    3. Create Meal aggregate (Factory)
    """
    
    def __init__(
        self,
        barcode_service: BarcodeService,
        nutrition_service: NutritionEnrichmentService,
        meal_factory: MealFactory
    ):
        self._barcode = barcode_service
        self._nutrition = nutrition_service
        self._factory = meal_factory
    
    async def analyze(
        self,
        user_id: str,
        barcode: str,
        quantity_g: float,
        meal_type: str = "SNACK",
        timestamp: Optional[datetime] = None
    ) -> Meal:
        """
        Orchestrate barcode analysis workflow.
        
        Args:
            user_id: User ID
            barcode: Product barcode (EAN/UPC)
            quantity_g: Quantity in grams
            meal_type: BREAKFAST | LUNCH | DINNER | SNACK
            timestamp: Meal timestamp (default: now)
            
        Returns:
            Analyzed Meal aggregate
        """
        logger.info("orchestrating_barcode_analysis", barcode=barcode)
        
        # 1. Lookup product
        product = await self._barcode.lookup_product(barcode)
        
        if not product:
            raise ValueError(f"Product not found for barcode: {barcode}")
        
        logger.info(
            "product_found",
            barcode=barcode,
            name=product["name"]
        )
        
        # 2. Get/enrich nutrients
        if "nutrients" in product and product["nutrients"]:
            # Product already has nutrients
            nutrients_dict = product["nutrients"]
        else:
            # Enrich from USDA
            nutrients = await self._nutrition.enrich(
                label=product["name"],
                quantity_g=100.0,  # Reference quantity
                category=product.get("category")
            )
            
            nutrients_dict = {
                "calories": nutrients.calories,
                "protein": nutrients.protein,
                "carbs": nutrients.carbs,
                "fat": nutrients.fat,
                "fiber": nutrients.fiber,
                "sugar": nutrients.sugar,
                "sodium": nutrients.sodium
            }
        
        # Scale to actual quantity
        factor = quantity_g / 100.0
        scaled_nutrients = {
            "calories": int(nutrients_dict["calories"] * factor),
            "protein": nutrients_dict["protein"] * factor,
            "carbs": nutrients_dict["carbs"] * factor,
            "fat": nutrients_dict["fat"] * factor,
            "fiber": nutrients_dict.get("fiber", 0) * factor if nutrients_dict.get("fiber") else None,
            "sugar": nutrients_dict.get("sugar", 0) * factor if nutrients_dict.get("sugar") else None,
            "sodium": nutrients_dict.get("sodium", 0) * factor if nutrients_dict.get("sodium") else None
        }
        
        # 3. Create Meal aggregate
        food_dict = {
            "label": product["name"],
            "display_name": product.get("display_name", product["name"]),
            "quantity_g": quantity_g,
            "confidence": 1.0,  # Barcode = 100% confidence
            "category": product.get("category")
        }
        
        meal = self._factory.create_from_analysis(
            user_id=user_id,
            items=[(food_dict, scaled_nutrients)],
            source="BARCODE",
            timestamp=timestamp or datetime.now(timezone.utc),
            meal_type=meal_type,
            analysis_id=f"barcode_{uuid4().hex[:12]}"
        )
        
        # Add barcode to entry
        meal.entries[0].barcode = barcode
        
        logger.info(
            "barcode_analysis_complete",
            meal_id=str(meal.id),
            total_calories=meal.total_calories
        )
        
        return meal
```

---

## 🧪 Testing Strategy

### Unit Test Example

```python
# tests/unit/application/meal/commands/test_analyze_photo.py
import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime, timezone

from application.meal.commands.analyze_photo import (
    AnalyzeMealPhotoCommand,
    AnalyzeMealPhotoCommandHandler
)
from domain.meal.core.entities.meal import Meal


@pytest.mark.asyncio
async def test_analyze_photo_command_creates_meal():
    """Test that AnalyzeMealPhotoCommand creates and persists meal."""
    # Arrange
    mock_orchestrator = AsyncMock()
    mock_repository = AsyncMock()
    mock_event_bus = AsyncMock()
    
    # Mock orchestrator returns meal
    mock_meal = Meal(
        id=uuid4(),
        user_id="user123",
        timestamp=datetime.now(timezone.utc),
        meal_type="LUNCH",
        entries=[]
    )
    mock_orchestrator.analyze.return_value = mock_meal
    
    handler = AnalyzeMealPhotoCommandHandler(
        orchestrator=mock_orchestrator,
        repository=mock_repository,
        event_bus=mock_event_bus
    )
    
    command = AnalyzeMealPhotoCommand(
        user_id="user123",
        photo_url="https://example.com/meal.jpg",
        dish_hint="pasta",
        meal_type="LUNCH"
    )
    
    # Act
    result = await handler.handle(command)
    
    # Assert
    assert result.id == mock_meal.id
    mock_orchestrator.analyze.assert_called_once()
    mock_repository.save.assert_called_once_with(mock_meal)
    mock_event_bus.publish.assert_called_once()
```

---

**Next**: `04_INFRASTRUCTURE_LAYER.md` - OpenAI, USDA, Repositories

**Last Updated**: 22 Ottobre 2025
