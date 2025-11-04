# 🧪 Testing Strategy - TDD & Best Practices

**Data:** 22 Ottobre 2025  
**Focus:** Test-Driven Development, Dependency Injection, Coverage

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Testing Philosophy](#testing-philosophy)
3. [Test Structure](#test-structure)
4. [Unit Tests](#unit-tests)
5. [Integration Tests](#integration-tests)
6. [E2E Tests](#e2e-tests)
7. [TDD Workflow](#tdd-workflow)
8. [Best Practices](#best-practices)

---

## 🎯 Overview

### Testing Goals
- ✅ **>90% code coverage** (target: 95%)
- ✅ **Fast feedback loop** (<2 min for full suite)
- ✅ **Reliable tests** (no flaky tests)
- ✅ **Clear intent** (test name = documentation)
- ✅ **Easy to maintain** (DRY, no over-mocking)

### GraphQL Operations Coverage

Ogni test DEVE indicare quale operazione GraphQL sta validando.

**Mutations**:
- `analyzeMealPhoto` → OpenAI Vision + USDA enrichment + Repository save
- `analyzeMealBarcode` → OpenFoodFacts lookup + USDA fallback + Repository save
- `analyzeMealDescription` → OpenAI text extraction + USDA enrichment + Repository save
- `confirmMealAnalysis` → Domain logic (confirmation) + Repository update
- `updateMeal` → Domain logic (update) + Repository update
- `deleteMeal` → Domain logic (soft delete) + Repository update

**Queries**:
- `meal` → Repository get_by_id
- `mealHistory` → Repository list_by_user with filters
- `searchMeals` → Repository list_by_user with text search
- `dailySummary` → Repository list_by_user + aggregation
- `recognizeFood` → OpenAI Vision (atomic utility)
- `enrichNutrients` → USDA enrichment (atomic utility)
- `searchFoodByBarcode` → OpenFoodFacts lookup (atomic utility)

---

## 💡 Testing Philosophy

### 1. Test-Driven Development (TDD)

**Workflow**: Red → Green → Refactor

```
1. RED: Write failing test first
2. GREEN: Write minimal code to pass
3. REFACTOR: Improve code quality
4. REPEAT
```

**Benefits**:
- Design emerges from tests
- High test coverage by default
- Confidence in refactoring
- Fewer bugs

---

### 2. Dependency Injection > Mocking

**❌ BAD** (over-mocking):
```python
@patch('infrastructure.ai.openai_client.httpx.AsyncClient')
@patch('infrastructure.ai.openai_client.AsyncOpenAI')
async def test_analyze_photo(mock_openai, mock_httpx):
    # Too much knowledge of implementation
    # Fragile test (breaks on internal changes)
    pass
```

**✅ GOOD** (dependency injection):
```python
@pytest.fixture
def mock_openai_client():
    """Mock the OpenAIClient dependency."""
    return AsyncMock()

@pytest.fixture
def vision_provider(mock_openai_client):
    """Inject mock client into provider."""
    return OpenAIVisionProvider(client=mock_openai_client)

async def test_analyze_photo(vision_provider, mock_openai_client):
    # Test behavior, not implementation
    # Resilient to internal changes
    pass
```

**Why?**
- Tests focus on **behavior**, not **implementation**
- Easy to swap real/mock implementations
- No need to mock HTTP, JSON parsing, etc.

---

### 3. Use Real Models When Possible

**❌ BAD** (stub everything):
```python
mock_result = Mock()
mock_result.dish_title = "Test"
mock_result.items = [Mock()]
```

**✅ GOOD** (real Pydantic models):
```python
mock_result = RecognitionResult(
    dish_title="Spaghetti alla Carbonara",
    items=[
        RecognizedFood(
            label="pasta, cooked",
            display_name="Pasta cotta",
            quantity=Quantity(value=250, unit="g"),
            confidence=0.9
        )
    ]
)
```

**Why?**
- Tests validate real data structures
- Catches validation errors
- More realistic scenarios

---

## 📁 Test Structure

```
tests/
├── unit/                           # Fast, isolated tests
│   ├── domain/
│   │   ├── meal/
│   │   │   ├── core/
│   │   │   │   ├── test_meal_entity.py
│   │   │   │   ├── test_meal_entry_entity.py
│   │   │   │   └── test_meal_factory.py
│   │   │   ├── nutrition/
│   │   │   │   ├── test_nutrient_profile.py
│   │   │   │   └── test_nutrition_service.py
│   │   │   ├── recognition/
│   │   │   │   └── test_recognition_service.py
│   │   │   └── barcode/
│   │   │       └── test_barcode_service.py
│   │   └── shared/
│   │       └── test_value_objects.py
│   ├── application/
│   │   ├── commands/
│   │   │   ├── test_analyze_photo_handler.py
│   │   │   ├── test_analyze_barcode_handler.py
│   │   │   ├── test_confirm_handler.py
│   │   │   ├── test_update_handler.py
│   │   │   └── test_delete_handler.py
│   │   ├── queries/
│   │   │   ├── test_get_meal_handler.py
│   │   │   ├── test_list_meals_handler.py
│   │   │   └── test_daily_summary_handler.py
│   │   └── orchestrators/
│   │       ├── test_photo_orchestrator.py
│   │       └── test_barcode_orchestrator.py
│   └── infrastructure/
│       ├── ai/
│       │   ├── test_openai_client.py
│       │   └── test_vision_provider.py
│       ├── external_apis/
│       │   ├── usda/
│       │   │   ├── test_usda_client.py
│       │   │   ├── test_usda_mapper.py
│       │   │   └── test_usda_provider.py
│       │   └── openfoodfacts/
│       │       ├── test_off_client.py
│       │       └── test_off_provider.py
│       └── persistence/
│           └── test_in_memory_repository.py
│
├── integration/                    # Tests with real dependencies
│   ├── test_openai_integration.py
│   ├── test_usda_integration.py
│   └── test_openfoodfacts_integration.py
│
├── e2e/                           # End-to-end workflows
│   ├── test_photo_workflow.py
│   ├── test_barcode_workflow.py
│   └── test_confirmation_workflow.py
│
├── conftest.py                    # Shared fixtures
└── pytest.ini                     # PyTest configuration
```

---

## 🔬 Unit Tests

### Characteristics
- ✅ **Fast**: <100ms per test
- ✅ **Isolated**: No external dependencies
- ✅ **Focused**: Test ONE behavior
- ✅ **Independent**: Can run in any order

---

### Example 1: Domain Entity

**GraphQL Operation**: All mutations that create/update Meal

```python
# tests/unit/domain/meal/core/test_meal_entity.py
"""
Unit tests for Meal entity

Tests domain invariants and business rules.
No external dependencies.

GraphQL Operations: analyzeMealPhoto, analyzeMealBarcode, analyzeMealDescription,
                    confirmMealAnalysis, updateMeal
"""

import pytest
from uuid import uuid4
from datetime import datetime

from domain.meal.core.entities.meal import Meal
from domain.meal.core.entities.meal_entry import MealEntry
from domain.meal.core.value_objects import MealId, Confidence, Timestamp
from domain.meal.core.exceptions import MealDomainError


class TestMealCreation:
    """Test Meal entity creation."""
    
    def test_create_meal_with_valid_entries_succeeds(self):
        """
        GIVEN: Valid meal data with entries
        WHEN: Creating Meal entity
        THEN: Meal is created successfully
        """
        # Arrange
        entry = MealEntry(
            label="chicken breast, grilled",
            display_name="Petto di pollo alla griglia",
            quantity_g=200,
            confidence=Confidence(0.9)
        )
        
        # Act
        meal = Meal(
            id=MealId.generate(),
            user_id="user123",
            dish_name="Pollo grigliato",
            entries=[entry],
            analysis_type="PHOTO",
            timestamp=Timestamp.now()
        )
        
        # Assert
        assert meal.user_id == "user123"
        assert meal.dish_name == "Pollo grigliato"
        assert len(meal.entries) == 1
        assert not meal.confirmed
    
    def test_create_meal_without_entries_raises_error(self):
        """
        GIVEN: Meal data without entries
        WHEN: Creating Meal entity
        THEN: Raises MealDomainError
        """
        with pytest.raises(MealDomainError, match="at least one entry"):
            Meal(
                id=MealId.generate(),
                user_id="user123",
                dish_name="Empty meal",
                entries=[],  # ❌ Empty
                analysis_type="PHOTO",
                timestamp=Timestamp.now()
            )
    
    def test_dish_name_too_long_raises_error(self):
        """
        GIVEN: Dish name >200 chars
        WHEN: Creating Meal entity
        THEN: Raises MealDomainError
        """
        entry = MealEntry(
            label="test",
            display_name="Test",
            quantity_g=100,
            confidence=Confidence(0.9)
        )
        
        with pytest.raises(MealDomainError, match="Dish name too long"):
            Meal(
                id=MealId.generate(),
                user_id="user123",
                dish_name="A" * 201,  # ❌ Too long
                entries=[entry],
                analysis_type="PHOTO",
                timestamp=Timestamp.now()
            )


class TestMealConfirmation:
    """Test Meal confirmation logic."""
    
    def test_confirm_meal_with_selected_entries_succeeds(self):
        """
        GIVEN: Unconfirmed meal with 3 entries
        WHEN: Confirming with 2 entry IDs
        THEN: Meal is confirmed with 2 entries
        
        GraphQL Operation: confirmMealAnalysis
        """
        # Arrange
        entry1 = MealEntry(label="pasta", display_name="Pasta", quantity_g=250, confidence=Confidence(0.9))
        entry2 = MealEntry(label="eggs", display_name="Uova", quantity_g=50, confidence=Confidence(0.8))
        entry3 = MealEntry(label="bacon", display_name="Pancetta", quantity_g=30, confidence=Confidence(0.7))
        
        meal = Meal(
            id=MealId.generate(),
            user_id="user123",
            dish_name="Carbonara",
            entries=[entry1, entry2, entry3],
            analysis_type="PHOTO",
            timestamp=Timestamp.now()
        )
        
        # Act
        meal.confirm(confirmed_entry_ids=[entry1.id, entry2.id])
        
        # Assert
        assert meal.confirmed
        assert len(meal.entries) == 2
        assert entry1 in meal.entries
        assert entry2 in meal.entries
        assert entry3 not in meal.entries
        assert meal.confirmed_at is not None
    
    def test_confirm_already_confirmed_meal_raises_error(self):
        """
        GIVEN: Already confirmed meal
        WHEN: Attempting to confirm again
        THEN: Raises MealDomainError
        """
        entry = MealEntry(label="test", display_name="Test", quantity_g=100, confidence=Confidence(0.9))
        
        meal = Meal(
            id=MealId.generate(),
            user_id="user123",
            dish_name="Test",
            entries=[entry],
            analysis_type="PHOTO",
            timestamp=Timestamp.now()
        )
        
        meal.confirm(confirmed_entry_ids=[entry.id])
        
        with pytest.raises(MealDomainError, match="Already confirmed"):
            meal.confirm(confirmed_entry_ids=[entry.id])
    
    def test_confirm_with_no_entries_raises_error(self):
        """
        GIVEN: Meal with entries
        WHEN: Confirming with empty entry list
        THEN: Raises MealDomainError
        """
        entry = MealEntry(label="test", display_name="Test", quantity_g=100, confidence=Confidence(0.9))
        
        meal = Meal(
            id=MealId.generate(),
            user_id="user123",
            dish_name="Test",
            entries=[entry],
            analysis_type="PHOTO",
            timestamp=Timestamp.now()
        )
        
        with pytest.raises(MealDomainError, match="at least one entry"):
            meal.confirm(confirmed_entry_ids=[])


class TestMealCalculations:
    """Test Meal aggregate calculations."""
    
    def test_total_calories_sums_all_entries(self):
        """
        GIVEN: Meal with multiple entries
        WHEN: Calculating total calories
        THEN: Returns sum of all entry calories
        """
        entry1 = MealEntry(
            label="pasta",
            display_name="Pasta",
            quantity_g=250,
            confidence=Confidence(0.9),
            nutrients=NutrientProfile(calories=350, protein=12, carbs=70, fat=2, quantity_g=250)
        )
        entry2 = MealEntry(
            label="eggs",
            display_name="Uova",
            quantity_g=50,
            confidence=Confidence(0.8),
            nutrients=NutrientProfile(calories=75, protein=6, carbs=1, fat=5, quantity_g=50)
        )
        
        meal = Meal(
            id=MealId.generate(),
            user_id="user123",
            dish_name="Test",
            entries=[entry1, entry2],
            analysis_type="PHOTO",
            timestamp=Timestamp.now()
        )
        
        assert meal.total_calories == 425  # 350 + 75
```

---

### Example 2: Application Command Handler

**GraphQL Operation**: `analyzeMealPhoto`

```python
# tests/unit/application/commands/test_analyze_photo_handler.py
"""
Unit tests for AnalyzeMealPhotoCommandHandler

Tests command handling logic with mocked dependencies.
Uses dependency injection (no stub abuse).

GraphQL Operation: analyzeMealPhoto
"""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from application.meal.commands.analyze_photo import (
    AnalyzeMealPhotoCommand,
    AnalyzeMealPhotoCommandHandler
)
from application.meal.orchestrators.photo_orchestrator import PhotoOrchestrator
from domain.meal.core.entities.meal import Meal
from domain.meal.core.value_objects import MealId


@pytest.fixture
def mock_orchestrator():
    """Mock PhotoOrchestrator dependency."""
    return AsyncMock(spec=PhotoOrchestrator)


@pytest.fixture
def mock_repository():
    """Mock IMealRepository dependency."""
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    """Mock IEventBus dependency."""
    return AsyncMock()


@pytest.fixture
def handler(mock_orchestrator, mock_repository, mock_event_bus):
    """Create handler with mocked dependencies."""
    return AnalyzeMealPhotoCommandHandler(
        orchestrator=mock_orchestrator,
        repository=mock_repository,
        event_bus=mock_event_bus
    )


@pytest.mark.asyncio
async def test_handle_photo_analysis_success(handler, mock_orchestrator, mock_repository, mock_event_bus):
    """
    GIVEN: Valid photo analysis command
    WHEN: Handler processes command
    THEN: Meal is created, saved, and events published
    
    GraphQL Operation: analyzeMealPhoto
    """
    # Arrange
    command = AnalyzeMealPhotoCommand(
        user_id="user123",
        photo_url="https://example.com/carbonara.jpg",
        dish_hint="carbonara"
    )
    
    # Mock orchestrator to return meal
    mock_meal = Meal(
        id=MealId.generate(),
        user_id="user123",
        dish_name="Spaghetti alla Carbonara",
        entries=[],  # Simplified
        analysis_type="PHOTO",
        timestamp=Timestamp.now()
    )
    mock_orchestrator.orchestrate_photo_analysis.return_value = mock_meal
    
    # Act
    result = await handler.handle(command)
    
    # Assert
    assert result.meal_id == mock_meal.id
    assert result.success is True
    
    # Verify orchestrator was called
    mock_orchestrator.orchestrate_photo_analysis.assert_called_once_with(
        user_id="user123",
        photo_url="https://example.com/carbonara.jpg",
        hint="carbonara"
    )
    
    # Verify meal was saved
    mock_repository.save.assert_called_once_with(mock_meal)
    
    # Verify events were published
    assert mock_event_bus.publish.call_count >= 1


@pytest.mark.asyncio
async def test_handle_photo_analysis_orchestrator_failure(handler, mock_orchestrator):
    """
    GIVEN: Photo analysis command
    WHEN: Orchestrator raises exception
    THEN: Handler propagates exception
    
    GraphQL Operation: analyzeMealPhoto (error case)
    """
    command = AnalyzeMealPhotoCommand(
        user_id="user123",
        photo_url="https://example.com/invalid.jpg",
        dish_hint=None
    )
    
    # Mock orchestrator to raise exception
    mock_orchestrator.orchestrate_photo_analysis.side_effect = ValueError("No food recognized")
    
    # Act & Assert
    with pytest.raises(ValueError, match="No food recognized"):
        await handler.handle(command)
```

---

### Example 3: Infrastructure Provider

**GraphQL Operation**: `analyzeMealPhoto` (OpenAI step)

```python
# tests/unit/infrastructure/ai/test_vision_provider.py
"""
Unit tests for OpenAIVisionProvider

Tests provider logic with mocked OpenAI client.
Uses real Pydantic models (no stubs).

GraphQL Operations: analyzeMealPhoto, analyzeMealDescription, recognizeFood
"""

import pytest
from unittest.mock import AsyncMock

from infrastructure.ai.vision_provider import OpenAIVisionProvider
from domain.meal.recognition.entities.recognized_food import (
    RecognitionResult,
    RecognizedFood,
    Quantity
)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAIClient dependency."""
    return AsyncMock()


@pytest.fixture
def vision_provider(mock_openai_client):
    """Create provider with mocked client."""
    return OpenAIVisionProvider(client=mock_openai_client)


@pytest.mark.asyncio
async def test_analyze_photo_returns_usda_compatible_labels(vision_provider, mock_openai_client):
    """
    GIVEN: Photo URL with hint
    WHEN: Analyzing photo
    THEN: Returns USDA-compatible labels
    
    GraphQL Operation: analyzeMealPhoto
    """
    # Arrange - Use REAL Pydantic model (not stub)
    mock_response = RecognitionResult(
        dish_title="Spaghetti alla Carbonara",
        items=[
            RecognizedFood(
                label="pasta, cooked",  # ✅ USDA-compatible
                display_name="Pasta cotta",
                quantity=Quantity(value=250, unit="g"),
                confidence=0.9
            ),
            RecognizedFood(
                label="eggs",  # ✅ USDA plural
                display_name="Uova",
                quantity=Quantity(value=50, unit="g"),
                confidence=0.8
            )
        ]
    )
    
    mock_openai_client.structured_complete.return_value = mock_response
    
    # Act
    result = await vision_provider.analyze_photo(
        photo_url="https://example.com/carbonara.jpg",
        hint="carbonara"
    )
    
    # Assert - Verify USDA compatibility
    assert result.dish_name == "Spaghetti alla Carbonara"
    assert len(result.items) == 2
    
    # Check labels are USDA-compatible
    assert result.items[0].label == "pasta, cooked"  # ✅ Cooking method
    assert result.items[1].label == "eggs"           # ✅ Plural form
    
    # Check display names are Italian
    assert result.items[0].display_name == "Pasta cotta"
    assert result.items[1].display_name == "Uova"
    
    # Verify OpenAI call
    mock_openai_client.structured_complete.assert_called_once()
    call_kwargs = mock_openai_client.structured_complete.call_args.kwargs
    
    # Verify system prompt is cached (>1024 tokens)
    assert len(call_kwargs["system_prompt"]) > 1024
    
    # Verify temperature for consistency
    assert call_kwargs["temperature"] == 0.1


@pytest.mark.asyncio
async def test_analyze_text_extracts_food_items(vision_provider, mock_openai_client):
    """
    GIVEN: Text description
    WHEN: Analyzing text
    THEN: Returns extracted food items
    
    GraphQL Operation: analyzeMealDescription
    """
    # Arrange
    mock_response = RecognitionResult(
        dish_title="Pollo grigliato con insalata",
        items=[
            RecognizedFood(
                label="chicken breast, grilled",
                display_name="Petto di pollo alla griglia",
                quantity=Quantity(value=200, unit="g"),
                confidence=0.85
            ),
            RecognizedFood(
                label="lettuce, green",
                display_name="Lattuga",
                quantity=Quantity(value=80, unit="g"),
                confidence=0.8
            )
        ]
    )
    
    mock_openai_client.structured_complete.return_value = mock_response
    
    # Act
    result = await vision_provider.analyze_text(
        description="Petto di pollo alla griglia con insalata verde"
    )
    
    # Assert
    assert result.dish_name == "Pollo grigliato con insalata"
    assert len(result.items) == 2
    assert result.items[0].label == "chicken breast, grilled"  # ✅ Specific
```

---

## 🔗 Integration Tests

### Characteristics
- ✅ **Real dependencies**: Actual OpenAI/USDA/OFF APIs
- ✅ **Slower**: 1-5s per test
- ✅ **Environment**: Needs API keys
- ✅ **Marked**: Use `@pytest.mark.integration`

---

### Example: OpenAI Integration

**GraphQL Operation**: `recognizeFood` (atomic utility)

```python
# tests/integration/test_openai_integration.py
"""
Integration tests for OpenAI API

Tests REAL OpenAI API with structured outputs.
Requires OPENAI_API_KEY environment variable.

GraphQL Operations: analyzeMealPhoto, analyzeMealDescription, recognizeFood

Run with: pytest tests/integration -m integration
"""

import pytest
import os

from infrastructure.ai.openai_client import OpenAIClient
from infrastructure.ai.vision_provider import OpenAIVisionProvider


@pytest.fixture(scope="module")
def openai_api_key():
    """Get OpenAI API key from environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    return api_key


@pytest.fixture(scope="module")
def openai_client(openai_api_key):
    """Create real OpenAI client."""
    return OpenAIClient(api_key=openai_api_key)


@pytest.fixture
def vision_provider(openai_client):
    """Create vision provider with real client."""
    return OpenAIVisionProvider(client=openai_client)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyze_photo_with_real_openai(vision_provider):
    """
    GIVEN: Real meal photo URL
    WHEN: Analyzing with OpenAI
    THEN: Returns USDA-compatible labels
    
    GraphQL Operation: analyzeMealPhoto
    
    ⚠️ This test uses real OpenAI API (costs money)
    """
    # Arrange - Use test photo (pasta)
    photo_url = "https://example.com/test_pasta.jpg"  # Replace with real URL
    
    # Act
    result = await vision_provider.analyze_photo(
        photo_url=photo_url,
        hint="pasta"
    )
    
    # Assert
    assert result.dish_name  # Not empty
    assert len(result.items) > 0
    
    # Verify USDA compatibility
    for item in result.items:
        assert item.label  # Not empty
        assert item.display_name  # Italian name
        assert 0 < item.confidence <= 1.0
        assert item.quantity_g > 0
        
        # Check if label looks USDA-compatible
        # (contains cooking method or is specific)
        assert (
            "cooked" in item.label or
            "grilled" in item.label or
            "roasted" in item.label or
            "fried" in item.label or
            "raw" in item.label or
            len(item.label.split()) >= 2  # At least 2 words
        ), f"Label '{item.label}' may not be USDA-compatible"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_system_prompt_caching_works(openai_client):
    """
    GIVEN: Multiple requests with same system prompt
    WHEN: Making sequential calls
    THEN: Second call uses cached prompt (faster + cheaper)
    
    ⚠️ This test verifies prompt caching is working
    """
    from infrastructure.ai.prompts.food_recognition import FOOD_RECOGNITION_SYSTEM_PROMPT
    from infrastructure.ai.vision_provider import RecognitionResult
    
    # First call
    result1 = await openai_client.structured_complete(
        messages=[{"role": "user", "content": "Analyze: pasta"}],
        response_model=RecognitionResult,
        system_prompt=FOOD_RECOGNITION_SYSTEM_PROMPT,
        temperature=0.1
    )
    
    # Second call (should use cache)
    result2 = await openai_client.structured_complete(
        messages=[{"role": "user", "content": "Analyze: chicken"}],
        response_model=RecognitionResult,
        system_prompt=FOOD_RECOGNITION_SYSTEM_PROMPT,
        temperature=0.1
    )
    
    # Check cache stats
    stats = openai_client.get_cache_stats()
    
    assert stats["hits"] >= 1, "Prompt caching not working"
    assert stats["hit_rate_percent"] > 0
    
    print(f"✅ Cache working: {stats['hits']} hits, {stats['hit_rate_percent']}% hit rate")
```

---

## 🌊 E2E Tests

### Characteristics
- ✅ **Complete workflows**: Multi-step operations
- ✅ **Real dependencies**: All adapters
- ✅ **Slowest**: 5-15s per test
- ✅ **Marked**: Use `@pytest.mark.e2e`

---

### Example: Photo Analysis Workflow

**GraphQL Operation**: `analyzeMealPhoto` (complete flow)

```python
# tests/e2e/test_photo_workflow.py
"""
E2E tests for photo analysis workflow

Tests complete flow from photo → recognition → enrichment → save.
Uses real OpenAI + USDA + Repository.

GraphQL Operation: analyzeMealPhoto (full workflow)

Run with: pytest tests/e2e -m e2e
"""

import pytest
import os

from application.meal.commands.analyze_photo import (
    AnalyzeMealPhotoCommand,
    AnalyzeMealPhotoCommandHandler
)
from application.meal.orchestrators.photo_orchestrator import PhotoOrchestrator
from infrastructure.ai.openai_client import OpenAIClient
from infrastructure.ai.vision_provider import OpenAIVisionProvider
from infrastructure.external_apis.usda.client import USDAClient
from infrastructure.external_apis.usda.mapper import USDAMapper
from infrastructure.external_apis.usda.provider import USDANutritionProvider
from infrastructure.persistence.in_memory.meal_repository import InMemoryMealRepository
from domain.meal.recognition.services.recognition_service import FoodRecognitionService
from domain.meal.nutrition.services.enrichment_service import NutritionEnrichmentService
from domain.meal.core.factory import MealFactory


@pytest.fixture(scope="module")
def api_keys():
    """Get API keys from environment."""
    openai_key = os.getenv("OPENAI_API_KEY")
    usda_key = os.getenv("USDA_API_KEY")
    
    if not openai_key or not usda_key:
        pytest.skip("API keys not set")
    
    return {"openai": openai_key, "usda": usda_key}


@pytest.fixture
async def full_stack(api_keys):
    """Create complete application stack with real dependencies."""
    # Infrastructure
    openai_client = OpenAIClient(api_key=api_keys["openai"])
    vision_provider = OpenAIVisionProvider(client=openai_client)
    
    usda_client = USDAClient(api_key=api_keys["usda"])
    usda_mapper = USDAMapper()
    usda_provider = USDANutritionProvider(client=usda_client, mapper=usda_mapper)
    
    repository = InMemoryMealRepository()
    
    # Domain services
    recognition_service = FoodRecognitionService(provider=vision_provider)
    enrichment_service = NutritionEnrichmentService(provider=usda_provider)
    factory = MealFactory()
    
    # Application orchestrator
    orchestrator = PhotoOrchestrator(
        recognition_service=recognition_service,
        enrichment_service=enrichment_service,
        factory=factory
    )
    
    # Command handler
    handler = AnalyzeMealPhotoCommandHandler(
        orchestrator=orchestrator,
        repository=repository,
        event_bus=None  # Skip events in E2E
    )
    
    yield handler, repository
    
    # Cleanup
    await usda_client.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_photo_analysis_workflow(full_stack):
    """
    GIVEN: Real meal photo
    WHEN: Executing complete analyzeMealPhoto workflow
    THEN: Meal is recognized, enriched, and saved
    
    GraphQL Operation: analyzeMealPhoto
    
    Workflow:
    1. OpenAI Vision recognizes food items
    2. USDA enriches each item with nutrients
    3. MealFactory creates Meal aggregate
    4. Repository saves Meal
    5. Events published (skipped in E2E)
    
    ⚠️ Uses real APIs (slow + costs money)
    """
    handler, repository = full_stack
    
    # Arrange
    command = AnalyzeMealPhotoCommand(
        user_id="test_user_e2e",
        photo_url="https://example.com/carbonara.jpg",  # Replace with real URL
        dish_hint="carbonara"
    )
    
    # Act
    result = await handler.handle(command)
    
    # Assert
    assert result.success
    assert result.meal_id is not None
    
    # Verify meal was saved
    saved_meal = await repository.get_by_id(result.meal_id)
    assert saved_meal is not None
    assert saved_meal.user_id == "test_user_e2e"
    assert saved_meal.dish_name  # Not empty
    assert len(saved_meal.entries) > 0
    
    # Verify entries have nutrients
    for entry in saved_meal.entries:
        assert entry.nutrients is not None
        assert entry.nutrients.calories > 0
        assert entry.nutrients.source == "USDA"
        
        # Verify USDA-compatible label
        assert entry.label
        print(f"✅ Entry: {entry.label} → {entry.nutrients.calories} kcal")
    
    # Verify total calories
    assert saved_meal.total_calories > 0
    print(f"✅ Total meal: {saved_meal.total_calories} kcal")
```

---

## 🔄 TDD Workflow

### Step-by-Step Example

**Goal**: Implement `MealEntry.scale_quantity()` method

---

#### Step 1: RED (Failing Test)

```python
# tests/unit/domain/meal/core/test_meal_entry.py

def test_scale_quantity_doubles_nutrients():
    """
    GIVEN: MealEntry with 100g and 100 kcal
    WHEN: Scaling to 200g
    THEN: Nutrients are doubled
    """
    # Arrange
    entry = MealEntry(
        label="chicken breast, grilled",
        display_name="Pollo grigliato",
        quantity_g=100,
        confidence=Confidence(0.9),
        nutrients=NutrientProfile(calories=165, protein=31, carbs=0, fat=3.6, quantity_g=100)
    )
    
    # Act
    scaled_entry = entry.scale_quantity(200)
    
    # Assert
    assert scaled_entry.quantity_g == 200
    assert scaled_entry.nutrients.calories == 330  # 165 * 2
    assert scaled_entry.nutrients.protein == 62    # 31 * 2
```

**Run**: `pytest tests/unit/domain/meal/core/test_meal_entry.py::test_scale_quantity_doubles_nutrients`

**Result**: ❌ FAIL (method doesn't exist)

---

#### Step 2: GREEN (Minimal Implementation)

```python
# domain/meal/core/entities/meal_entry.py

class MealEntry:
    def scale_quantity(self, new_quantity_g: float) -> "MealEntry":
        """Scale entry to new quantity."""
        scale_factor = new_quantity_g / self.quantity_g
        
        return MealEntry(
            id=self.id,
            label=self.label,
            display_name=self.display_name,
            quantity_g=new_quantity_g,
            confidence=self.confidence,
            nutrients=self.nutrients.scale_to_quantity(new_quantity_g) if self.nutrients else None
        )
```

**Run**: `pytest tests/unit/domain/meal/core/test_meal_entry.py::test_scale_quantity_doubles_nutrients`

**Result**: ✅ PASS

---

#### Step 3: REFACTOR (Improve)

```python
# Add validation
def scale_quantity(self, new_quantity_g: float) -> "MealEntry":
    """Scale entry to new quantity."""
    if new_quantity_g <= 0:
        raise ValueError("Quantity must be positive")
    if new_quantity_g > 5000:
        raise ValueError("Quantity too large")
    
    scale_factor = new_quantity_g / self.quantity_g
    
    return MealEntry(
        id=self.id,
        label=self.label,
        display_name=self.display_name,
        quantity_g=new_quantity_g,
        confidence=self.confidence,
        nutrients=self.nutrients.scale_to_quantity(new_quantity_g) if self.nutrients else None,
        image_url=self.image_url  # Don't forget fields!
    )
```

**Add edge case tests**:
```python
def test_scale_quantity_zero_raises_error():
    entry = MealEntry(...)
    with pytest.raises(ValueError, match="positive"):
        entry.scale_quantity(0)

def test_scale_quantity_too_large_raises_error():
    entry = MealEntry(...)
    with pytest.raises(ValueError, match="too large"):
        entry.scale_quantity(6000)
```

---

## ✅ Best Practices

### 1. Test Naming Convention

```python
# ❌ BAD
def test_meal():
    pass

# ✅ GOOD
def test_confirm_meal_with_valid_entry_ids_succeeds():
    pass
```

**Pattern**: `test_<action>_<context>_<expected_result>`

---

### 2. AAA Pattern (Arrange-Act-Assert)

```python
def test_example():
    # Arrange - Setup
    meal = create_test_meal()
    
    # Act - Execute
    result = meal.confirm([entry_id])
    
    # Assert - Verify
    assert result.confirmed
```

---

### 3. Use Fixtures for Reusable Setup

```python
# conftest.py
@pytest.fixture
def sample_meal():
    """Reusable meal fixture."""
    return Meal(...)

# test file
def test_something(sample_meal):
    assert sample_meal.user_id
```

---

### 4. Mark Slow Tests

```python
@pytest.mark.integration
@pytest.mark.slow
async def test_real_openai():
    pass
```

**Run fast tests only**: `pytest -m "not slow"`

---

### 5. Test One Thing Per Test

```python
# ❌ BAD - Tests multiple behaviors
def test_meal_lifecycle():
    meal = create_meal()
    meal.confirm([])
    meal.update(...)
    meal.delete()

# ✅ GOOD - Separate tests
def test_confirm_meal():
    pass

def test_update_meal():
    pass

def test_delete_meal():
    pass
```

---

### 6. Use Parametrize for Multiple Cases

```python
@pytest.mark.parametrize("quantity,expected", [
    (100, 165),
    (200, 330),
    (50, 82.5),
])
def test_scale_nutrients(quantity, expected):
    entry = create_entry(base_calories=165)
    scaled = entry.scale_quantity(quantity)
    assert scaled.nutrients.calories == pytest.approx(expected)
```

---

### 7. Always Check GraphQL Operation

```python
def test_analyze_photo_handler():
    """
    Test photo analysis command handler.
    
    GraphQL Operation: analyzeMealPhoto
    """
    pass
```

---

## 📊 Coverage Goals

```bash
# Run with coverage
pytest --cov=backend --cov-report=html --cov-report=term

# Target: >90%
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
backend/domain/meal/entities/meal.py      150      5    97%
backend/application/commands/...          120      8    93%
backend/infrastructure/ai/...              80     10    87%  ⚠️ Need more tests
-----------------------------------------------------------
TOTAL                                     1500     80    95%  ✅
```

---

## 🚀 Running Tests

```bash
# All tests (slow)
pytest

# Unit tests only (fast)
pytest tests/unit

# Integration tests
pytest tests/integration -m integration

# E2E tests
pytest tests/e2e -m e2e

# Specific test
pytest tests/unit/domain/meal/core/test_meal.py::test_confirm_meal

# With coverage
pytest --cov=backend --cov-report=html

# Parallel (faster)
pytest -n auto

# Watch mode (TDD)
ptw -- --testmon
```

---

## 📝 Summary

### Key Takeaways

1. ✅ **TDD First**: Write test before code
2. ✅ **Dependency Injection**: Mock at boundaries, not internals
3. ✅ **Real Models**: Use real Pydantic models when possible
4. ✅ **Clear Intent**: Test name = documentation
5. ✅ **One Behavior**: Test one thing per test
6. ✅ **GraphQL Mapping**: Always note which operation you're testing
7. ✅ **Fast Feedback**: Unit tests <100ms, integration <5s
8. ✅ **Coverage**: Target >90%

### Test Pyramid

```
      /\
     /E2E\      ← Few (slow, expensive)
    /------\
   /INTEGR.\   ← Some (medium speed)
  /----------\
 /   UNIT     \ ← Many (fast, cheap)
/--------------\
```

**Next**: `06_GRAPHQL_API.md` - Complete schema, resolvers, examples

**Last Updated**: 22 Ottobre 2025
