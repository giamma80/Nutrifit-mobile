"""Unit tests for mutation resolvers.

Tests the 5 CQRS command mutations:
- analyzeMealPhoto: Analyze meal from photo (OpenAI → USDA)
- analyzeMealBarcode: Analyze meal from barcode (OpenFoodFacts)
- confirmMealAnalysis: 2-step confirmation with entry selection
- updateMeal: Update meal_type, timestamp, notes
- deleteMeal: Soft delete with authorization

Mock Strategy:
- Mutations use CommandHandlers which orchestrate multiple dependencies
- Each CommandHandler follows a pattern:
  1. Call orchestrator/repository to get/create meal
  2. Call repository.save/update to persist
  3. Call event_bus.publish to emit events
  4. Call idempotency_cache for de-duplication (analyze commands only)
- We mock all these dependencies to test the GraphQL layer in isolation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any
from datetime import datetime, timezone
from uuid import uuid4

from graphql.resolvers.meal.mutations import MealMutations
from domain.meal.core.entities.meal import Meal as DomainMeal
from domain.meal.core.entities.meal_entry import MealEntry as DomainMealEntry
from domain.meal.core.value_objects.meal_id import MealId


@pytest.fixture
def mock_context() -> Any:
    """Create mock Strawberry context with all mutation dependencies.

    Provides mocks for:
    - meal_repository: For persistence (save/update/delete/get_by_id)
    - event_bus: For domain events (publish)
    - idempotency_cache: For command de-duplication (get/set)
    - photo_orchestrator: For photo analysis workflow (analyze)
    - barcode_orchestrator: For barcode analysis workflow (analyze)

    Maintenance Note:
    - If new dependencies are added to mutations.py context, add them here
    - Each mock should be an AsyncMock to support async method calls
    - Use persistent mocks (not recreated on each .get() call)
    """
    mocks = {
        "meal_repository": AsyncMock(),
        "event_bus": AsyncMock(),
        "idempotency_cache": AsyncMock(),
        "photo_orchestrator": AsyncMock(),
        "barcode_orchestrator": AsyncMock(),
    }

    context = MagicMock()
    context.get = MagicMock(side_effect=lambda key: mocks.get(key))
    return context


@pytest.fixture
def mock_info(mock_context: Any) -> Any:
    """Create mock Strawberry Info object."""
    info = MagicMock()
    info.context = mock_context
    return info


@pytest.fixture
def meal_mutations() -> MealMutations:
    """Create MealMutations resolver instance."""
    return MealMutations()


@pytest.fixture
def sample_meal() -> DomainMeal:
    """Create sample domain meal for testing.

    Maintenance Note:
    - If MealEntry signature changes, update the entry creation
    - If Meal requires new mandatory fields, add them here
    - Keep totals in sync with entry values for realistic data
    """
    meal_id = MealId.generate()
    entry = DomainMealEntry(
        id=uuid4(),
        meal_id=meal_id.value,
        name="chicken",
        display_name="Chicken",
        quantity_g=150.0,
        calories=250,
        protein=40.0,
        carbs=0.0,
        fat=8.0,
        fiber=0.0,
        sugar=0.0,
        sodium=100.0,
    )

    return DomainMeal(
        id=meal_id.value,
        user_id="user123",
        timestamp=datetime(2025, 10, 25, 12, 0, 0, tzinfo=timezone.utc),
        meal_type="LUNCH",
        entries=[entry],
        total_calories=250,
        total_protein=40.0,
        total_carbs=0.0,
        total_fat=8.0,
        total_fiber=0.0,
        total_sugar=0.0,
        total_sodium=100.0,
    )


# ============================================
# analyzeMealPhoto Tests
# ============================================


@pytest.mark.asyncio
async def test_analyze_meal_photo_success(
    meal_mutations: MealMutations, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test analyzeMealPhoto mutation success path.

    Mock Strategy:
    - orchestrator.analyze() → returns Meal (from photo analysis workflow)
    - repository.save() → persists meal
    - event_bus.publish() → publishes MealAnalyzed event
    - idempotency_cache.get() → returns None (no cache hit)
    - idempotency_cache.set() → caches meal ID

    Maintenance Note:
    - If AnalyzeMealPhotoCommandHandler workflow changes, update mocks accordingly
    - The handler calls orchestrator.analyze() NOT orchestrator.handle()
    """
    # Arrange
    from graphql.types_meal_mutations import AnalyzeMealPhotoInput, MealType

    # Mock orchestrator to return our sample meal
    orchestrator = mock_info.context.get("photo_orchestrator")
    orchestrator.analyze.return_value = sample_meal

    # Mock repository operations
    repository = mock_info.context.get("meal_repository")
    repository.save.return_value = None  # save returns nothing

    # Mock event bus
    event_bus = mock_info.context.get("event_bus")
    event_bus.publish.return_value = None

    # Mock idempotency cache (no cache hit)
    idempotency_cache = mock_info.context.get("idempotency_cache")
    idempotency_cache.get.return_value = None  # No cached result
    idempotency_cache.set.return_value = None

    input_data = AnalyzeMealPhotoInput(
        user_id="user123",
        photo_url="https://example.com/food.jpg",
        dish_hint="chicken and rice",
        meal_type=MealType.LUNCH,
        idempotency_key="test-key-123",
    )

    # Act
    result = await meal_mutations.analyze_meal_photo(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "MealAnalysisSuccess"
    assert result.meal.id == str(sample_meal.id)
    assert result.meal.total_calories == 250

    # Verify orchestrator was called correctly
    orchestrator.analyze.assert_called_once_with(
        user_id="user123",
        photo_url="https://example.com/food.jpg",
        dish_hint="chicken and rice",
        meal_type="LUNCH",
        timestamp=None,
    )

    # Verify meal was persisted
    repository.save.assert_called_once_with(sample_meal)

    # Verify event was published
    event_bus.publish.assert_called_once()

    # Verify idempotency cache was used
    idempotency_cache.get.assert_called_once_with("test-key-123")
    idempotency_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_meal_photo_service_unavailable(meal_mutations: MealMutations) -> None:
    """Test analyzeMealPhoto when services not available in context.

    Maintenance Note:
    - This tests the early return when context.get() returns None
    - No CommandHandler is instantiated, so no need to mock orchestrator
    """
    # Arrange
    from graphql.types_meal_mutations import AnalyzeMealPhotoInput, MealType

    mock_info = MagicMock()
    mock_info.context.get.return_value = None  # All services unavailable

    input_data = AnalyzeMealPhotoInput(
        user_id="user123",
        photo_url="https://example.com/food.jpg",
        meal_type=MealType.LUNCH,
    )

    # Act
    result = await meal_mutations.analyze_meal_photo(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "MealAnalysisError"
    assert result.code == "SERVICE_UNAVAILABLE"
    assert "Required services not available" in result.message


@pytest.mark.asyncio
async def test_analyze_meal_photo_validation_error(
    meal_mutations: MealMutations, mock_info: Any
) -> None:
    """Test analyzeMealPhoto with orchestrator validation error.

    Mock Strategy:
    - orchestrator.analyze() raises ValueError
    - This triggers the except ValueError block in the resolver

    Maintenance Note:
    - The resolver catches ValueError and returns VALIDATION_ERROR
    - If error handling changes, update assertions
    """
    # Arrange
    from graphql.types_meal_mutations import AnalyzeMealPhotoInput, MealType

    # Mock orchestrator to raise validation error
    orchestrator = mock_info.context.get("photo_orchestrator")
    orchestrator.analyze.side_effect = ValueError("Invalid photo URL")

    # Mock idempotency cache (no cache hit)
    idempotency_cache = mock_info.context.get("idempotency_cache")
    idempotency_cache.get.return_value = None

    input_data = AnalyzeMealPhotoInput(
        user_id="user123",
        photo_url="invalid",
        meal_type=MealType.LUNCH,
    )

    # Act
    result = await meal_mutations.analyze_meal_photo(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "MealAnalysisError"
    assert result.code == "VALIDATION_ERROR"
    assert "Invalid photo URL" in result.message


# ============================================
# analyzeMealBarcode Tests
# ============================================


@pytest.mark.asyncio
async def test_analyze_meal_barcode_success(
    meal_mutations: MealMutations, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test analyzeMealBarcode mutation success path.

    Mock Strategy:
    - barcode_orchestrator.analyze() → returns Meal (from barcode lookup)
    - repository.save() → persists meal
    - event_bus.publish() → publishes MealAnalyzed event
    - idempotency_cache operations for de-duplication

    Maintenance Note:
    - BarcodeOrchestrator has same analyze() signature as PhotoOrchestrator
    - But with different parameters (barcode, quantity_g instead of photo_url)
    """
    # Arrange
    from graphql.types_meal_mutations import AnalyzeMealBarcodeInput, MealType

    # Mock barcode orchestrator
    orchestrator = mock_info.context.get("barcode_orchestrator")
    orchestrator.analyze.return_value = sample_meal

    # Mock repository
    repository = mock_info.context.get("meal_repository")
    repository.save.return_value = None

    # Mock event bus
    event_bus = mock_info.context.get("event_bus")
    event_bus.publish.return_value = None

    # Mock idempotency cache
    idempotency_cache = mock_info.context.get("idempotency_cache")
    idempotency_cache.get.return_value = None
    idempotency_cache.set.return_value = None

    input_data = AnalyzeMealBarcodeInput(
        user_id="user123",
        barcode="8001505005707",
        quantity_g=100.0,
        meal_type=MealType.SNACK,
    )

    # Act
    result = await meal_mutations.analyze_meal_barcode(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "MealAnalysisSuccess"
    assert result.meal.id == str(sample_meal.id)

    # Verify orchestrator was called with correct parameters
    orchestrator.analyze.assert_called_once_with(
        user_id="user123",
        barcode="8001505005707",
        quantity_g=100.0,
        meal_type="SNACK",
        timestamp=None,
    )


@pytest.mark.asyncio
async def test_analyze_meal_barcode_not_found(
    meal_mutations: MealMutations, mock_info: Any
) -> None:
    """Test analyzeMealBarcode when barcode not found.

    Mock Strategy:
    - orchestrator.analyze() raises ValueError (barcode not in OpenFoodFacts)
    - This is caught and returned as BARCODE_NOT_FOUND error

    Maintenance Note:
    - The resolver specifically catches ValueError for barcode errors
    - Returns BARCODE_NOT_FOUND code (different from photo's VALIDATION_ERROR)
    """
    # Arrange
    from graphql.types_meal_mutations import AnalyzeMealBarcodeInput, MealType

    # Mock orchestrator to raise barcode not found error
    orchestrator = mock_info.context.get("barcode_orchestrator")
    orchestrator.analyze.side_effect = ValueError("Barcode not found")

    # Mock idempotency cache
    idempotency_cache = mock_info.context.get("idempotency_cache")
    idempotency_cache.get.return_value = None

    input_data = AnalyzeMealBarcodeInput(
        user_id="user123",
        barcode="0000000000000",
        quantity_g=100.0,
        meal_type=MealType.SNACK,
    )

    # Act
    result = await meal_mutations.analyze_meal_barcode(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "MealAnalysisError"
    assert result.code == "BARCODE_NOT_FOUND"
    assert "Barcode not found" in result.message


# ============================================
# confirmMealAnalysis Tests
# ============================================


@pytest.mark.asyncio
async def test_confirm_meal_analysis_success(
    meal_mutations: MealMutations, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test confirmMealAnalysis mutation success path.

    Mock Strategy:
    - repository.get_by_id() → returns pending meal
    - meal.remove_entry() → called by CommandHandler (domain method)
    - repository.save() → persists confirmed meal
    - event_bus.publish() → publishes MealConfirmed event

    Maintenance Note:
    - ConfirmAnalysisCommandHandler modifies the meal in-place
    - It removes entries NOT in confirmed_entry_ids
    - Then calls repository.save() to persist changes
    """
    # Arrange
    from graphql.types_meal_mutations import ConfirmAnalysisInput

    # Mock repository to return meal, then accept save
    repository = mock_info.context.get("meal_repository")
    repository.get_by_id.return_value = sample_meal
    repository.save.return_value = None  # Handlers use save() not update()

    # Mock event bus
    event_bus = mock_info.context.get("event_bus")
    event_bus.publish.return_value = None

    input_data = ConfirmAnalysisInput(
        meal_id=str(sample_meal.id),
        user_id="user123",
        confirmed_entry_ids=[str(sample_meal.entries[0].id)],
    )

    # Act
    result = await meal_mutations.confirm_meal_analysis(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "ConfirmAnalysisSuccess"
    assert result.meal.id == str(sample_meal.id)
    assert result.confirmed_count == 1

    # Verify repository operations
    repository.get_by_id.assert_called_once()
    repository.save.assert_called_once_with(sample_meal)

    # Verify event published
    event_bus.publish.assert_called_once()


@pytest.mark.asyncio
async def test_confirm_meal_analysis_meal_not_found(
    meal_mutations: MealMutations, mock_info: Any
) -> None:
    """Test confirmMealAnalysis when meal not found.

    Mock Strategy:
    - repository.get_by_id() → returns None
    - CommandHandler raises MealNotFoundError
    - Resolver catches and returns MEAL_NOT_FOUND error

    Maintenance Note:
    - The handler raises MealNotFoundError (custom exception)
    - But this gets caught as generic Exception in the resolver
    - Returns CONFIRMATION_FAILED code (may want to change to MEAL_NOT_FOUND)
    """
    # Arrange
    from graphql.types_meal_mutations import ConfirmAnalysisInput

    # Mock repository to return None (meal not found)
    repository = mock_info.context.get("meal_repository")
    repository.get_by_id.return_value = None

    # Mock event bus (must be present for resolver to proceed)
    event_bus = mock_info.context.get("event_bus")
    event_bus.publish.return_value = None

    input_data = ConfirmAnalysisInput(
        meal_id=str(uuid4()),
        user_id="user123",
        confirmed_entry_ids=[str(uuid4())],
    )

    # Act
    result = await meal_mutations.confirm_meal_analysis(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "ConfirmAnalysisError"
    # The resolver catches all exceptions as CONFIRMATION_FAILED
    # (not specifically MEAL_NOT_FOUND - could be improved)
    assert result.code == "CONFIRMATION_FAILED"


# ============================================
# updateMeal Tests
# ============================================


@pytest.mark.asyncio
async def test_update_meal_success(
    meal_mutations: MealMutations, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test updateMeal mutation success path.

    Mock Strategy:
    - repository.get_by_id() → returns existing meal
    - meal fields updated via setattr() → domain method modifies meal
    - repository.save() → persists changes
    - event_bus.publish() → publishes MealUpdated event

    Maintenance Note:
    - UpdateMealCommandHandler builds an updates dict from non-None fields
    - Then uses setattr() to apply changes to allowed fields
    - Check UpdateMealCommand if allowed_fields set changes
    """
    # Arrange
    from graphql.types_meal_mutations import UpdateMealInput, MealType

    # Mock repository
    repository = mock_info.context.get("meal_repository")
    repository.get_by_id.return_value = sample_meal
    repository.save.return_value = None

    # Mock event bus
    event_bus = mock_info.context.get("event_bus")
    event_bus.publish.return_value = None

    input_data = UpdateMealInput(
        meal_id=str(sample_meal.id),
        user_id="user123",
        meal_type=MealType.DINNER,
        notes="Updated notes",
    )

    # Act
    result = await meal_mutations.update_meal(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "UpdateMealSuccess"
    assert result.meal.id == str(sample_meal.id)

    # Verify meal was fetched and updated
    repository.get_by_id.assert_called_once()
    repository.save.assert_called_once_with(sample_meal)


@pytest.mark.asyncio
async def test_update_meal_not_found(meal_mutations: MealMutations, mock_info: Any) -> None:
    """Test updateMeal when meal not found.

    Mock Strategy:
    - repository.get_by_id() → returns None
    - CommandHandler detects meal is None
    - Raises exception caught as UPDATE_FAILED
    """
    # Arrange
    from graphql.types_meal_mutations import UpdateMealInput

    # Mock repository to return None
    repository = mock_info.context.get("meal_repository")
    repository.get_by_id.return_value = None

    # Mock event bus (must be present for resolver to proceed)
    event_bus = mock_info.context.get("event_bus")
    event_bus.publish.return_value = None

    input_data = UpdateMealInput(
        meal_id=str(uuid4()),
        user_id="user123",
        notes="Test",
    )

    # Act
    result = await meal_mutations.update_meal(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "UpdateMealError"
    assert result.code == "UPDATE_FAILED"


# ============================================
# deleteMeal Tests
# ============================================


@pytest.mark.asyncio
async def test_delete_meal_success(
    meal_mutations: MealMutations, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test deleteMeal mutation success path.

    Mock Strategy:
    - repository.get_by_id() → returns meal to verify ownership
    - repository.delete() → soft deletes meal
    - event_bus.publish() → publishes MealDeleted event

    Maintenance Note:
    - DeleteMealCommandHandler verifies user owns meal before deleting
    - Calls repository.delete() which does soft delete (sets deleted_at)
    """
    # Arrange
    from graphql.types_meal_mutations import DeleteMealInput

    # Mock repository
    repository = mock_info.context.get("meal_repository")
    repository.get_by_id.return_value = sample_meal
    repository.delete.return_value = None  # delete returns nothing

    # Mock event bus
    event_bus = mock_info.context.get("event_bus")
    event_bus.publish.return_value = None

    input_data = DeleteMealInput(
        meal_id=str(sample_meal.id),
        user_id="user123",
    )

    # Act
    result = await meal_mutations.delete_meal(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "DeleteMealSuccess"
    assert result.meal_id == str(sample_meal.id)
    assert "successfully" in result.message

    # Verify repository operations
    repository.get_by_id.assert_called_once()
    repository.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_meal_not_found(meal_mutations: MealMutations, mock_info: Any) -> None:
    """Test deleteMeal when meal not found.

    Mock Strategy:
    - repository.get_by_id() raises ValueError (or returns None)
    - Caught and returned as DELETE_FAILED error

    Maintenance Note:
    - The handler might raise MealNotFoundError
    - But the resolver catches all exceptions as DELETE_FAILED
    """
    # Arrange
    from graphql.types_meal_mutations import DeleteMealInput

    # Mock repository to raise error
    repository = mock_info.context.get("meal_repository")
    repository.get_by_id.side_effect = ValueError("Meal not found")

    input_data = DeleteMealInput(
        meal_id=str(uuid4()),
        user_id="user123",
    )

    # Act
    result = await meal_mutations.delete_meal(  # type: ignore[misc,call-arg]
        info=mock_info,
        input=input_data,
    )

    # Assert
    assert result.__class__.__name__ == "DeleteMealError"
    assert result.code == "MEAL_NOT_FOUND"
