# Meal Management Domain - Implementation Plan

## Objective

Complete the Meal Management Domain by consolidating:
- Existing domain/meal/ (photo analysis focus)
- repository/meals.py (CRUD operations)
- GraphQL meal operations in app.py

Create a unified DDD-compliant domain with feature flag `MEAL_DOMAIN_V2`.

## Current State Analysis

### ✅ Already Implemented
- **domain/meal/model/**: MealItem, MealAnalysisResult, MealAnalysisRequest
- **domain/meal/application/**: MealAnalysisService (photo analysis)
- **domain/meal/ports/**: MealPhotoAnalyzer, MealNormalizationService
- **domain/meal/pipeline/**: Normalization pipeline
- **domain/meal/errors.py**: Domain-specific exceptions

### 🔄 Legacy Code to Migrate
- **repository/meals.py** (152 lines):
  - MealRecord (data structure)
  - MealRepository interface + InMemoryMealRepository
  - CRUD operations: add, find_by_idempotency, list, update, delete
- **app.py GraphQL operations**:
  - log_meal mutation (lines 342-409)
  - update_meal mutation (lines 420-470)
  - delete_meal mutation (lines 475-477)
  - meal_entries query (lines 214-217)
  - daily_summary aggregation logic

## Domain Architecture Design

### Core Domain Model

```
domain/meal/
├── model/
│   ├── meal.py              # 🎯 Meal aggregate root + value objects
│   ├── nutrition.py         # NutrientProfile, ProductInfo value objects
│   └── __init__.py          # Existing: MealItem, MealAnalysisResult
├── application/
│   ├── meal_service.py      # 🎯 Core CRUD business logic
│   ├── meal_analysis_service.py # ✅ Existing photo analysis
│   └── meal_enrichment_service.py # 🎯 Nutrient enrichment logic
├── ports/
│   ├── meal_repository.py   # 🎯 Persistence abstraction
│   ├── product_service.py   # 🎯 External product lookup
│   └── __init__.py          # Existing: analysis ports
├── adapters/
│   ├── meal_repository_adapter.py   # 🎯 Bridge to legacy repository
│   ├── product_service_adapter.py   # 🎯 Bridge to OpenFoodFacts
│   └── __init__.py
└── integration.py          # 🎯 GraphQL integration layer + feature flag
```

## Implementation Plan

### Phase 1: Core Domain Model (Week 1)

**1.1 Meal Aggregate Root**
```python
# domain/meal/model/meal.py
@dataclass(frozen=True)
class Meal:
    id: MealId
    user_id: UserId  
    name: str
    quantity_g: float
    timestamp: datetime
    nutrient_profile: Optional[NutrientProfile]
    barcode: Optional[str]
    idempotency_key: Optional[str]
    
    def update_nutrients(self, profile: NutrientProfile) -> 'Meal'
    def change_quantity(self, quantity_g: float) -> 'Meal'
    def total_calories(self) -> Optional[int]
```

**1.2 Value Objects**
```python
# domain/meal/model/nutrition.py
@dataclass(frozen=True)
class NutrientProfile:
    calories_per_100g: Optional[float]
    protein_per_100g: Optional[float]
    carbs_per_100g: Optional[float]
    # ... other nutrients
    
    def scale_to_quantity(self, quantity_g: float) -> 'ScaledNutrients'

@dataclass(frozen=True)  
class ScaledNutrients:
    calories: Optional[int]
    protein: Optional[float]
    # ... scaled values for actual quantity

@dataclass(frozen=True)
class ProductInfo:
    barcode: str
    name: str
    nutrient_profile: NutrientProfile
```

### Phase 2: Application Services (Week 1-2)

**2.1 MealService - Core CRUD Logic**
```python
# domain/meal/application/meal_service.py
class MealService:
    def __init__(
        self,
        meal_repository: MealRepositoryPort,
        product_service: ProductServicePort,
        enrichment_service: MealEnrichmentService,
    ):
    
    def create_meal(self, command: CreateMealCommand) -> Meal
    def update_meal(self, command: UpdateMealCommand) -> Meal  
    def delete_meal(self, meal_id: MealId) -> bool
    def find_meal(self, meal_id: MealId) -> Optional[Meal]
    def find_by_idempotency(self, user_id: UserId, key: str) -> Optional[Meal]
    def list_meals(self, query: MealListQuery) -> List[Meal]
```

**2.2 MealEnrichmentService - Product Logic**
```python
# domain/meal/application/meal_enrichment_service.py
class MealEnrichmentService:
    def enrich_with_product(self, barcode: str, quantity_g: float) -> Optional[ScaledNutrients]
    def should_recalculate_nutrients(self, old_meal: Meal, updates: dict) -> bool
```

### Phase 3: Ports & Adapters (Week 2)

**3.1 Repository Port**
```python
# domain/meal/ports/meal_repository.py
class MealRepositoryPort(Protocol):
    def save(self, meal: Meal) -> None
    def find_by_id(self, meal_id: MealId) -> Optional[Meal]
    def find_by_idempotency(self, user_id: UserId, key: str) -> Optional[Meal]
    def list_by_user(self, user_id: UserId, filters: MealFilters) -> List[Meal]
    def delete(self, meal_id: MealId) -> bool
```

**3.2 Repository Adapter**
```python
# domain/meal/adapters/meal_repository_adapter.py
class MealRepositoryAdapter(MealRepositoryPort):
    def __init__(self, legacy_repo: MealRepository):
        
    def save(self, meal: Meal) -> None:
        # Convert Meal -> MealRecord
        # Call legacy_repo.add() or update()
        
    def find_by_id(self, meal_id: MealId) -> Optional[Meal]:
        # legacy_repo.get() -> convert MealRecord -> Meal
```

### Phase 4: Integration Layer (Week 2-3)

**4.1 GraphQL Integration Service**
```python
# domain/meal/integration.py
class MealIntegrationService:
    def __init__(self, meal_service: MealService):
    
    # GraphQL mutation handlers
    def log_meal_v2(self, input: LogMealInput) -> MealEntry
    def update_meal_v2(self, input: UpdateMealInput) -> MealEntry
    def delete_meal_v2(self, meal_id: str) -> bool
    
    # Feature flag support
    def _is_enabled(self) -> bool:
        return os.getenv("MEAL_DOMAIN_V2", "false").lower() == "true"
```

**4.2 Feature Flag Integration**
- Add `MEAL_DOMAIN_V2=false` to .env/.env.example
- Modify GraphQL resolvers to use new service when flag enabled
- Graceful fallback to legacy repository when flag disabled

### Phase 5: Testing (Week 3)

**5.1 Unit Tests**
- Meal aggregate root behavior
- Application services logic
- Repository adapter correctness

**5.2 Integration Tests**  
- GraphQL mutation equivalence vs legacy
- End-to-end meal lifecycle
- Feature flag switching behavior

**5.3 Performance Tests**
- Benchmark new domain vs legacy repository
- Memory usage optimization
- Concurrent access patterns

## Success Criteria

### Functional Requirements
- ✅ **Feature Parity**: All existing GraphQL operations work identically
- ✅ **Data Consistency**: Meal data identical between domain and legacy
- ✅ **Idempotency**: Duplicate prevention works as before
- ✅ **Nutrient Enrichment**: Barcode lookup and scaling preserved

### Non-Functional Requirements  
- ✅ **Performance**: <10% overhead vs legacy repository
- ✅ **Memory**: No significant memory increase
- ✅ **Backward Compatibility**: Zero breaking changes to GraphQL API
- ✅ **Feature Flag**: Seamless switching between v1/v2

### Quality Gates
- ✅ **Test Coverage**: >90% unit test coverage
- ✅ **Type Safety**: Full mypy strict compliance
- ✅ **Code Quality**: flake8 + black compliance
- ✅ **Documentation**: Complete API docs and migration guide

## Rollout Strategy

### Development Phase
1. **Feature flag off by default** in .env (safe development)
2. **Test suite uses fixtures** to enable MEAL_DOMAIN_V2
3. **Integration tests validate equivalence** vs legacy

### Production Rollout
1. **Canary deployment**: Enable flag for 5% of traffic
2. **Monitor metrics**: Response times, error rates, data consistency
3. **Gradual rollout**: 25% → 50% → 100% over 2 weeks
4. **Legacy cleanup**: Remove repository/meals.py after 100% migration

## Estimated Timeline

- **Week 1**: Domain model + Core application services
- **Week 2**: Ports/adapters + Repository bridge  
- **Week 3**: Integration layer + Testing
- **Week 4**: Documentation + Production readiness

**Total Effort**: ~3-4 weeks for complete implementation and rollout.