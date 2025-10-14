# Domain V2 Repository Strategy

## Current Architecture Problem
```
Domain V2 → MealRepositoryAdapter → MealRepository (Legacy) → Database
```

When legacy code is removed, the adapter will break!

## Solution: Native Domain V2 Repository

### Option 1: Full Domain Repository Implementation

```python
# domain/meal/adapters/meal_repository_v2.py
class MealRepositoryV2(MealRepositoryPort):
    """Native domain V2 repository - no legacy dependencies."""
    
    def __init__(self, db_connection):
        self._db = db_connection
    
    async def save(self, meal: Meal) -> None:
        """Direct domain-to-database persistence."""
        # SQL operations using domain objects directly
        # No conversion to legacy MealRecord needed
        
    async def find_by_id(self, meal_id: MealId) -> Optional[Meal]:
        """Direct database-to-domain conversion."""
        # Query database and build Meal domain object directly
```

### Option 2: Dual Repository Support (Migration Phase)

```python
# domain/meal/integration.py  
class MealIntegrationService:
    def __init__(self):
        self._use_v2_repo = os.getenv("MEAL_REPOSITORY_V2", "false").lower() == "true"
        
        if self._use_v2_repo:
            self._repository = MealRepositoryV2(db_connection)
        else:
            self._repository = MealRepositoryAdapter(legacy_meal_repo)
```

### Option 3: Database Schema Evolution

Current legacy schema:
```sql
CREATE TABLE meals (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    name VARCHAR,
    quantity_g FLOAT,
    image_url VARCHAR,  -- ✅ Already added for V2
    -- legacy fields...
);
```

Domain V2 native schema (future):
```sql
CREATE TABLE meal_aggregates (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    aggregate_data JSONB,  -- Full domain object serialization
    version INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Migration Strategy

### Phase 1: Current (Adapter Pattern)
- ✅ Domain V2 working via adapter
- ✅ Legacy compatibility maintained
- ✅ Feature flags for gradual rollout

### Phase 2: Dual Repository Support
- 🔄 Add native MealRepositoryV2
- 🔄 Feature flag: MEAL_REPOSITORY_V2
- 🔄 Both repositories work simultaneously
- 🔄 Gradual migration of data/users

### Phase 3: Legacy Elimination
- 🔄 All traffic on V2 repository
- 🔄 Remove MealRepositoryAdapter
- 🔄 Remove legacy MealRepository
- 🔄 Clean up legacy code

## Implementation Priority

1. **High Priority**: Complete domain routing (Activity V2)
2. **Medium Priority**: MealRepositoryV2 implementation
3. **Low Priority**: Legacy elimination (after V2 is proven stable)

## Benefits of Native Repository V2

✅ **Independence**: No legacy dependencies
✅ **Performance**: Direct domain-to-DB mapping
✅ **Schema Freedom**: Optimize for domain needs
✅ **Event Sourcing**: Can add domain events persistence
✅ **CQRS**: Separate read/write models possible

## Migration Path Recommendation

1. Keep adapter for now (it works!)
2. Implement Activity Domain Routing first
3. Build MealRepositoryV2 as separate implementation
4. Add feature flag for repository selection
5. Gradual migration when ready
6. Legacy elimination in separate phase