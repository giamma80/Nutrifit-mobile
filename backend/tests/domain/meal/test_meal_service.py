"""Tests for meal domain services.

Test suite for MealService and MealQueryService with mock dependencies.
Tests application layer coordination and business logic.
"""

from datetime import datetime
from typing import List, Optional

import pytest

from domain.meal.model import (
    Meal,
    MealId,
    NutrientProfile,
    ProductInfo,
    ScaledNutrients,
    UserId,
)
from domain.meal.port import (
    MealEventPort,
    MealRepositoryPort,
    NutritionCalculatorPort,
    ProductLookupPort,
)
from domain.meal.service import MealQueryService, MealService


class MockMealRepository(MealRepositoryPort):
    """Mock implementation of MealRepositoryPort."""

    def __init__(self) -> None:
        self.meals: dict[str, Meal] = {}
        self.idempotency_keys: dict[str, Meal] = {}

    async def save(self, meal: Meal) -> None:
        """Save meal to mock storage."""
        self.meals[meal.id.value] = meal
        if meal.idempotency_key:
            key = f"{meal.user_id.value}:{meal.idempotency_key}"
            self.idempotency_keys[key] = meal

    async def find_by_id(self, meal_id: MealId) -> Optional[Meal]:
        """Find meal by ID."""
        return self.meals.get(meal_id.value)

    async def find_by_user_id(
        self,
        user_id: UserId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Meal]:
        """Find meals for user."""
        user_meals = [meal for meal in self.meals.values() if meal.user_id == user_id]
        return user_meals[offset : offset + limit]

    async def find_by_idempotency_key(
        self,
        user_id: UserId,
        idempotency_key: str,
    ) -> Optional[Meal]:
        """Find meal by idempotency key."""
        key = f"{user_id.value}:{idempotency_key}"
        return self.idempotency_keys.get(key)

    async def delete(self, meal_id: MealId) -> bool:
        """Delete meal."""
        if meal_id.value in self.meals:
            del self.meals[meal_id.value]
            return True
        return False

    async def exists(self, meal_id: MealId) -> bool:
        """Check if meal exists."""
        return meal_id.value in self.meals


class MockProductLookup(ProductLookupPort):
    """Mock implementation of ProductLookupPort."""

    def __init__(self) -> None:
        self.products: dict[str, ProductInfo] = {}

    def add_product(self, barcode: str, product: ProductInfo) -> None:
        """Add product to mock database."""
        self.products[barcode] = product

    async def lookup_by_barcode(self, barcode: str) -> Optional[ProductInfo]:
        """Look up product by barcode."""
        return self.products.get(barcode)

    async def search_products(self, query: str, limit: int = 10) -> List[ProductInfo]:
        """Search products by query."""
        # Simple mock implementation
        return list(self.products.values())[:limit]


class MockNutritionCalculator(NutritionCalculatorPort):
    """Mock implementation of NutritionCalculatorPort."""

    def __init__(self) -> None:
        self.responses: dict[str, NutrientProfile] = {}

    def add_response(self, meal_name: str, profile: NutrientProfile) -> None:
        """Add response for specific meal name."""
        self.responses[meal_name.lower()] = profile

    async def calculate_nutrients(
        self,
        meal_name: str,
        quantity_g: float,
        barcode: Optional[str] = None,
    ) -> Optional[NutrientProfile]:
        """Calculate nutrients for meal."""
        return self.responses.get(meal_name.lower())

    async def enrich_from_ai(
        self,
        meal_name: str,
        quantity_g: float,
    ) -> Optional[NutrientProfile]:
        """AI enrichment mock."""
        return self.responses.get(meal_name.lower())


class MockEventPublisher(MealEventPort):
    """Mock implementation of MealEventPort."""

    def __init__(self) -> None:
        self.events: List[tuple[str, Meal]] = []

    async def meal_created(self, meal: Meal) -> None:
        """Record meal created event."""
        self.events.append(("created", meal))

    async def meal_updated(self, old_meal: Meal, new_meal: Meal) -> None:
        """Record meal updated event."""
        self.events.append(("updated", new_meal))

    async def meal_deleted(self, meal: Meal) -> None:
        """Record meal deleted event."""
        self.events.append(("deleted", meal))

    async def nutrients_calculated(self, meal: Meal) -> None:
        """Record nutrients calculated event."""
        self.events.append(("nutrients_calculated", meal))


@pytest.fixture
def mock_repository() -> MockMealRepository:
    """Create mock meal repository."""
    return MockMealRepository()


@pytest.fixture
def mock_product_lookup() -> MockProductLookup:
    """Create mock product lookup."""
    return MockProductLookup()


@pytest.fixture
def mock_nutrition_calculator() -> MockNutritionCalculator:
    """Create mock nutrition calculator."""
    return MockNutritionCalculator()


@pytest.fixture
def mock_event_publisher() -> MockEventPublisher:
    """Create mock event publisher."""
    return MockEventPublisher()


@pytest.fixture
def meal_service(
    mock_repository: MockMealRepository,
    mock_nutrition_calculator: MockNutritionCalculator,
    mock_product_lookup: MockProductLookup,
    mock_event_publisher: MockEventPublisher,
) -> MealService:
    """Create meal service with mocked dependencies."""
    return MealService(
        meal_repository=mock_repository,
        nutrition_calculator=mock_nutrition_calculator,
        product_lookup=mock_product_lookup,
        event_publisher=mock_event_publisher,
    )


@pytest.fixture
def query_service(mock_repository: MockMealRepository) -> MealQueryService:
    """Create meal query service."""
    return MealQueryService(meal_repository=mock_repository)


class TestMealService:
    """Test cases for MealService."""

    @pytest.mark.asyncio
    async def test_create_meal_basic(
        self,
        meal_service: MealService,
        mock_repository: MockMealRepository,
        mock_event_publisher: MockEventPublisher,
    ) -> None:
        """Test basic meal creation."""
        meal = await meal_service.create_meal(
            user_id="user-123",
            name="Chicken Breast",
            quantity_g=150.0,
            auto_enrich=False,  # Disable enrichment for basic test
        )

        # Verify meal properties
        assert meal.user_id.value == "user-123"
        assert meal.name == "Chicken Breast"
        assert meal.quantity_g == 150.0
        assert isinstance(meal.timestamp, datetime)
        assert meal.nutrients is None  # No enrichment

        # Verify persistence
        saved_meal = await mock_repository.find_by_id(meal.id)
        assert saved_meal == meal

        # Verify event
        assert len(mock_event_publisher.events) == 1
        event_type, event_meal = mock_event_publisher.events[0]
        assert event_type == "created"
        assert event_meal == meal

    @pytest.mark.asyncio
    async def test_create_meal_with_idempotency(
        self,
        meal_service: MealService,
        mock_repository: MockMealRepository,
    ) -> None:
        """Test meal creation with idempotency key."""
        # Create first meal
        meal1 = await meal_service.create_meal(
            user_id="user-123",
            name="Chicken Breast",
            quantity_g=150.0,
            idempotency_key="unique-key-123",
            auto_enrich=False,
        )

        # Try to create duplicate - should return existing
        meal2 = await meal_service.create_meal(
            user_id="user-123",
            name="Different Name",  # Different data
            quantity_g=200.0,
            idempotency_key="unique-key-123",  # Same key
            auto_enrich=False,
        )

        # Should return the same meal
        assert meal2.id == meal1.id
        assert meal2.name == "Chicken Breast"  # Original data
        assert meal2.quantity_g == 150.0

    @pytest.mark.asyncio
    async def test_create_meal_with_barcode_enrichment(
        self,
        meal_service: MealService,
        mock_product_lookup: MockProductLookup,
        mock_event_publisher: MockEventPublisher,
    ) -> None:
        """Test meal creation with barcode-based enrichment."""
        # Setup product data
        nutrient_profile = NutrientProfile(
            calories_per_100g=250.0,
            protein_per_100g=25.0,
            carbs_per_100g=0.0,
            fat_per_100g=15.0,
        )
        product = ProductInfo(
            barcode="1234567890123",
            name="Chicken Breast",
            nutrient_profile=nutrient_profile,
        )
        mock_product_lookup.add_product("1234567890123", product)

        # Create meal with barcode
        meal = await meal_service.create_meal(
            user_id="user-123",
            name="Chicken Breast",
            quantity_g=200.0,  # 200g portion
            barcode="1234567890123",
            auto_enrich=True,
        )

        # Verify enrichment
        assert meal.nutrients is not None
        assert meal.nutrients.calories == 500  # 250 * 2.0
        assert meal.nutrients.protein == 50.0  # 25.0 * 2.0
        assert meal.nutrients.carbs == 0.0
        assert meal.nutrients.fat == 30.0  # 15.0 * 2.0

    @pytest.mark.asyncio
    async def test_create_meal_with_nutrition_calculator_fallback(
        self,
        meal_service: MealService,
        mock_nutrition_calculator: MockNutritionCalculator,
    ) -> None:
        """Test meal creation with nutrition calculator fallback."""
        # Setup nutrition calculator response
        nutrient_profile = NutrientProfile(
            calories_per_100g=180.0,
            protein_per_100g=20.0,
            carbs_per_100g=5.0,
            fat_per_100g=8.0,
        )
        mock_nutrition_calculator.add_response("salmon fillet", nutrient_profile)

        # Create meal without barcode (should use calculator)
        meal = await meal_service.create_meal(
            user_id="user-123",
            name="Salmon Fillet",
            quantity_g=150.0,
            auto_enrich=True,
        )

        # Verify enrichment from calculator
        assert meal.nutrients is not None
        assert meal.nutrients.calories == 270  # 180 * 1.5
        assert meal.nutrients.protein == 30.0  # 20.0 * 1.5

    @pytest.mark.asyncio
    async def test_get_meal(
        self,
        meal_service: MealService,
        mock_repository: MockMealRepository,
    ) -> None:
        """Test retrieving meal by ID."""
        # Create meal first
        created_meal = await meal_service.create_meal(
            user_id="user-123",
            name="Test Meal",
            quantity_g=100.0,
            auto_enrich=False,
        )

        # Retrieve meal
        retrieved_meal = await meal_service.get_meal(created_meal.id.value)

        assert retrieved_meal == created_meal

        # Test non-existent meal
        non_existent = await meal_service.get_meal("non-existent-id")
        assert non_existent is None

    @pytest.mark.asyncio
    async def test_update_meal(
        self,
        meal_service: MealService,
        mock_event_publisher: MockEventPublisher,
    ) -> None:
        """Test updating existing meal."""
        # Create meal first
        original_meal = await meal_service.create_meal(
            user_id="user-123",
            name="Original Name",
            quantity_g=100.0,
            auto_enrich=False,
        )

        # Reset events
        mock_event_publisher.events.clear()

        # Update meal
        new_timestamp = datetime(2024, 1, 16, 15, 30, 0)
        updated_meal = await meal_service.update_meal(
            meal_id=original_meal.id.value,
            name="Updated Name",
            quantity_g=150.0,
            timestamp=new_timestamp,
            recalculate_nutrients=False,
        )

        # Verify updates
        assert updated_meal is not None
        assert updated_meal.name == "Updated Name"
        assert updated_meal.quantity_g == 150.0
        assert updated_meal.timestamp == new_timestamp
        assert updated_meal.id == original_meal.id  # Same ID

        # Verify event
        assert len(mock_event_publisher.events) == 1
        event_type, _ = mock_event_publisher.events[0]
        assert event_type == "updated"

    @pytest.mark.asyncio
    async def test_update_nonexistent_meal(self, meal_service: MealService) -> None:
        """Test updating non-existent meal."""
        result = await meal_service.update_meal(
            meal_id="non-existent",
            name="New Name",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_meal(
        self,
        meal_service: MealService,
        mock_event_publisher: MockEventPublisher,
    ) -> None:
        """Test deleting meal."""
        # Create meal first
        meal = await meal_service.create_meal(
            user_id="user-123",
            name="To Delete",
            quantity_g=100.0,
            auto_enrich=False,
        )

        # Reset events
        mock_event_publisher.events.clear()

        # Delete meal
        deleted = await meal_service.delete_meal(meal.id.value)

        assert deleted is True

        # Verify meal is gone
        retrieved = await meal_service.get_meal(meal.id.value)
        assert retrieved is None

        # Verify event
        assert len(mock_event_publisher.events) == 1
        event_type, event_meal = mock_event_publisher.events[0]
        assert event_type == "deleted"
        assert event_meal == meal

    @pytest.mark.asyncio
    async def test_delete_nonexistent_meal(self, meal_service: MealService) -> None:
        """Test deleting non-existent meal."""
        deleted = await meal_service.delete_meal("non-existent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_recalculate_nutrients(
        self,
        meal_service: MealService,
        mock_nutrition_calculator: MockNutritionCalculator,
        mock_event_publisher: MockEventPublisher,
    ) -> None:
        """Test forcing nutrient recalculation."""
        # Create meal without nutrients
        meal = await meal_service.create_meal(
            user_id="user-123",
            name="Beef Steak",
            quantity_g=200.0,
            auto_enrich=False,
        )

        # Setup nutrition data
        nutrient_profile = NutrientProfile(
            calories_per_100g=300.0,
            protein_per_100g=26.0,
        )
        mock_nutrition_calculator.add_response("beef steak", nutrient_profile)

        # Reset events
        mock_event_publisher.events.clear()

        # Recalculate nutrients
        updated_meal = await meal_service.recalculate_nutrients(meal.id.value)

        # Verify nutrients were calculated
        assert updated_meal is not None
        assert updated_meal.nutrients is not None
        assert updated_meal.nutrients.calories == 600  # 300 * 2.0
        assert updated_meal.nutrients.protein == 52.0  # 26.0 * 2.0

        # Verify event
        assert len(mock_event_publisher.events) == 1
        event_type, _ = mock_event_publisher.events[0]
        assert event_type == "nutrients_calculated"


class TestMealQueryService:
    """Test cases for MealQueryService."""

    @pytest.mark.asyncio
    async def test_find_meal_by_id(
        self,
        query_service: MealQueryService,
        mock_repository: MockMealRepository,
    ) -> None:
        """Test finding meal by ID."""
        # Create test meal directly in repository
        meal = Meal(
            id=MealId.generate(),
            user_id=UserId.from_string("user-123"),
            name="Test Meal",
            quantity_g=100.0,
            timestamp=datetime.utcnow(),
        )
        await mock_repository.save(meal)

        # Find meal
        found_meal = await query_service.find_meal_by_id(meal.id.value)
        assert found_meal == meal

        # Test non-existent
        not_found = await query_service.find_meal_by_id("non-existent")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_find_meals_by_user(
        self,
        query_service: MealQueryService,
        mock_repository: MockMealRepository,
    ) -> None:
        """Test finding meals by user."""
        user_id = UserId.from_string("user-123")

        # Create multiple meals for user
        meal1 = Meal(
            id=MealId.generate(),
            user_id=user_id,
            name="Breakfast",
            quantity_g=100.0,
            timestamp=datetime.utcnow(),
        )
        meal2 = Meal(
            id=MealId.generate(),
            user_id=user_id,
            name="Lunch",
            quantity_g=200.0,
            timestamp=datetime.utcnow(),
        )

        # Create meal for different user
        other_meal = Meal(
            id=MealId.generate(),
            user_id=UserId.from_string("other-user"),
            name="Other Meal",
            quantity_g=150.0,
            timestamp=datetime.utcnow(),
        )

        await mock_repository.save(meal1)
        await mock_repository.save(meal2)
        await mock_repository.save(other_meal)

        # Find meals for user
        user_meals = await query_service.find_meals_by_user("user-123")

        assert len(user_meals) == 2
        meal_names = {meal.name for meal in user_meals}
        assert meal_names == {"Breakfast", "Lunch"}

    @pytest.mark.asyncio
    async def test_meal_exists(
        self,
        query_service: MealQueryService,
        mock_repository: MockMealRepository,
    ) -> None:
        """Test checking if meal exists."""
        # Create test meal
        meal = Meal(
            id=MealId.generate(),
            user_id=UserId.from_string("user-123"),
            name="Test Meal",
            quantity_g=100.0,
            timestamp=datetime.utcnow(),
        )
        await mock_repository.save(meal)

        # Test existing meal
        exists = await query_service.meal_exists(meal.id.value)
        assert exists is True

        # Test non-existent meal
        not_exists = await query_service.meal_exists("non-existent")
        assert not_exists is False

    @pytest.mark.asyncio
    async def test_calculate_daily_totals(
        self,
        query_service: MealQueryService,
        mock_repository: MockMealRepository,
    ) -> None:
        """Test calculating daily nutritional totals."""
        target_date = datetime(2024, 1, 15, 12, 0, 0)
        user_id = UserId.from_string("user-123")

        # Create meals with nutrients
        nutrients1 = ScaledNutrients(
            calories=300,
            protein=25.0,
            carbs=10.0,
            fat=15.0,
        )
        meal1 = Meal(
            id=MealId.generate(),
            user_id=user_id,
            name="Breakfast",
            quantity_g=100.0,
            timestamp=target_date,
            nutrients=nutrients1,
        )

        nutrients2 = ScaledNutrients(
            calories=500,
            protein=30.0,
            carbs=40.0,
            fat=20.0,
        )
        meal2 = Meal(
            id=MealId.generate(),
            user_id=user_id,
            name="Lunch",
            quantity_g=200.0,
            timestamp=target_date,
            nutrients=nutrients2,
        )

        # Meal on different date (should be excluded)
        other_date_meal = Meal(
            id=MealId.generate(),
            user_id=user_id,
            name="Yesterday",
            quantity_g=150.0,
            timestamp=datetime(2024, 1, 14, 12, 0, 0),
            nutrients=ScaledNutrients(calories=200),
        )

        await mock_repository.save(meal1)
        await mock_repository.save(meal2)
        await mock_repository.save(other_date_meal)

        # Calculate daily totals
        totals = await query_service.calculate_daily_totals("user-123", target_date)

        assert totals["date"] == "2024-01-15"
        assert totals["meal_count"] == 2
        assert totals["total_calories"] == 800  # 300 + 500
        assert totals["total_protein"] == 55.0  # 25.0 + 30.0
        assert totals["total_carbs"] == 50.0  # 10.0 + 40.0
        assert totals["total_fat"] == 35.0  # 15.0 + 20.0
