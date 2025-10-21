# FASE 4 - Meal Analysis Orchestration

**Data inizio:** 20 ottobre 2025  
**Obiettivo:** Orchestratore completo per analisi pasti multi-sorgente (AI Vision + Barcode + USDA + Category)

---

## 🎯 Obiettivi

### Funzionalità Core
1. **Orchestrazione Multi-Source**
   - AI Vision per riconoscimento foto
   - Barcode enrichment per prodotti confezionati
   - USDA search per alimenti generici
   - Category profiles come fallback

2. **Temporary Analysis Storage**
   - Storage temporaneo analysis (24h TTL)
   - Idempotency per evitare duplicati
   - Conversion analysis → meal entry

3. **Gestione Errori Graceful**
   - Fallback strategy tra sources
   - Partial results handling
   - Error context enrichment

---

## 📦 Componenti da Implementare

### 1. Domain Models (`domain/meal/orchestration/`)

```python
# analysis_models.py

class AnalysisSource(str, Enum):
    """Source of meal analysis."""
    AI_VISION = "AI_VISION"          # Foto analizzata con AI
    BARCODE_SCAN = "BARCODE_SCAN"    # Scansione barcode
    USDA_SEARCH = "USDA_SEARCH"      # Ricerca USDA manuale
    CATEGORY_PROFILE = "CATEGORY"    # Profile da categoria
    MANUAL_ENTRY = "MANUAL"          # Inserimento manuale


class AnalysisStatus(str, Enum):
    """Status of meal analysis."""
    PENDING = "PENDING"              # In attesa processing
    PROCESSING = "PROCESSING"        # In elaborazione
    COMPLETED = "COMPLETED"          # Completata con successo
    PARTIAL = "PARTIAL"              # Completata parzialmente
    FAILED = "FAILED"                # Fallita
    EXPIRED = "EXPIRED"              # Scaduta (>24h)


class MealAnalysisMetadata(BaseModel):
    """Metadata for meal analysis."""
    model_config = ConfigDict(frozen=True)
    
    source: AnalysisSource
    confidence: float = Field(ge=0.0, le=1.0)
    processing_time_ms: int = Field(ge=0)
    ai_model_version: Optional[str] = None
    image_url: Optional[str] = None
    barcode_value: Optional[str] = None
    fallback_reason: Optional[str] = None  # Se usato fallback


class MealAnalysis(BaseModel):
    """
    Temporary meal analysis result.
    
    Valid for 24h, then converted to MealEntry or expired.
    Supports idempotency via analysis_id.
    """
    model_config = ConfigDict(frozen=True)
    
    # Identity
    analysis_id: AnalysisId
    user_id: UserId
    
    # Content
    meal_name: str = Field(min_length=1, max_length=200)
    nutrient_profile: NutrientProfile
    quantity_g: float = Field(gt=0, description="Quantity in grams")
    
    # Metadata
    metadata: MealAnalysisMetadata
    status: AnalysisStatus = AnalysisStatus.COMPLETED
    
    # Timestamps
    created_at: datetime
    expires_at: datetime  # created_at + 24h
    converted_to_meal_at: Optional[datetime] = None
    
    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, v: datetime, info: ValidationInfo) -> datetime:
        """Ensure expires_at is after created_at."""
        created_at = info.data.get("created_at")
        if created_at and v <= created_at:
            raise ValueError("expires_at must be after created_at")
        return v
    
    def is_expired(self) -> bool:
        """Check if analysis is expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_convertible(self) -> bool:
        """Check if can be converted to meal entry."""
        return (
            self.status == AnalysisStatus.COMPLETED
            and not self.is_expired()
            and self.converted_to_meal_at is None
        )
```

---

### 2. Orchestrator Service (`application/meal/`)

```python
# orchestration_service.py

class MealAnalysisOrchestrator:
    """
    Orchestrates meal analysis from multiple sources.
    
    Dependency Injection Pattern:
    - ai_vision_client: IAIVisionClient
    - barcode_service: BarcodeEnrichmentService
    - usda_client: IUSDAClient
    - category_repository: ICategoryProfileRepository
    - analysis_repository: IMealAnalysisRepository
    
    Flow:
    1. Check idempotency (analysis_id già processato?)
    2. Try primary source (AI/Barcode/USDA)
    3. Fallback to secondary sources if needed
    4. Store temporary analysis (24h TTL)
    5. Return MealAnalysis with metadata
    """
    
    def __init__(
        self,
        ai_vision_client: IAIVisionClient,
        barcode_service: BarcodeEnrichmentService,
        usda_client: IUSDAClient,
        category_repository: ICategoryProfileRepository,
        analysis_repository: IMealAnalysisRepository,
    ):
        self.ai_vision = ai_vision_client
        self.barcode = barcode_service
        self.usda = usda_client
        self.categories = category_repository
        self.analyses = analysis_repository
    
    async def analyze_from_photo(
        self,
        user_id: UserId,
        image_data: bytes,
        analysis_id: Optional[AnalysisId] = None,
    ) -> MealAnalysis:
        """Analyze meal from photo using AI vision."""
        pass
    
    async def analyze_from_barcode(
        self,
        user_id: UserId,
        barcode: Barcode,
        quantity_g: float,
        analysis_id: Optional[AnalysisId] = None,
    ) -> MealAnalysis:
        """Analyze meal from barcode scan."""
        pass
    
    async def analyze_from_usda_search(
        self,
        user_id: UserId,
        food_name: str,
        quantity_g: float,
        analysis_id: Optional[AnalysisId] = None,
    ) -> MealAnalysis:
        """Analyze meal from USDA search."""
        pass
    
    async def convert_to_meal(
        self,
        analysis_id: AnalysisId,
    ) -> MealId:
        """
        Convert temporary analysis to permanent meal entry.
        
        Returns MealId of created meal.
        Marks analysis as converted.
        """
        pass
    
    async def get_analysis(
        self,
        analysis_id: AnalysisId,
    ) -> Optional[MealAnalysis]:
        """Retrieve temporary analysis by ID."""
        pass
    
    async def _check_idempotency(
        self,
        analysis_id: AnalysisId,
    ) -> Optional[MealAnalysis]:
        """Check if analysis already exists."""
        pass
    
    async def _apply_fallback_strategy(
        self,
        user_id: UserId,
        primary_error: Exception,
        meal_name: str,
        quantity_g: float,
    ) -> MealAnalysis:
        """Apply fallback strategy on primary source failure."""
        pass
```

---

### 3. Repository Interface (`domain/meal/persistence/`)

```python
# analysis_repository.py

class IMealAnalysisRepository(Protocol):
    """Repository for temporary meal analyses."""
    
    async def save(self, analysis: MealAnalysis) -> None:
        """Save analysis to temporary storage."""
        ...
    
    async def get_by_id(
        self, analysis_id: AnalysisId
    ) -> Optional[MealAnalysis]:
        """Retrieve analysis by ID."""
        ...
    
    async def get_by_user(
        self,
        user_id: UserId,
        limit: int = 10,
    ) -> list[MealAnalysis]:
        """Get recent analyses for user."""
        ...
    
    async def mark_converted(
        self,
        analysis_id: AnalysisId,
        meal_id: MealId,
    ) -> None:
        """Mark analysis as converted to meal."""
        ...
    
    async def delete_expired(self) -> int:
        """Delete expired analyses. Returns count deleted."""
        ...
```

---

### 4. Infrastructure Implementation (`infrastructure/database/`)

```python
# analysis_repository_mongo.py

class MealAnalysisRepositoryMongo(IMealAnalysisRepository):
    """MongoDB implementation of analysis repository."""
    
    def __init__(self, db: Database):
        self.collection = db["meal_analyses"]
        # TTL index on expires_at for auto-cleanup
        self.collection.create_index(
            "expires_at",
            expireAfterSeconds=0,
        )
        self.collection.create_index("user_id")
        self.collection.create_index("analysis_id", unique=True)
    
    async def save(self, analysis: MealAnalysis) -> None:
        doc = {
            "analysis_id": analysis.analysis_id.value,
            "user_id": analysis.user_id.value,
            "meal_name": analysis.meal_name,
            "nutrient_profile": analysis.nutrient_profile.to_dict(),
            "quantity_g": analysis.quantity_g,
            "metadata": analysis.metadata.model_dump(),
            "status": analysis.status.value,
            "created_at": analysis.created_at,
            "expires_at": analysis.expires_at,
            "converted_to_meal_at": analysis.converted_to_meal_at,
        }
        await self.collection.update_one(
            {"analysis_id": doc["analysis_id"]},
            {"$set": doc},
            upsert=True,
        )
```

---

## 🧪 Test Strategy

### Unit Tests (`tests/unit/application/meal/`)

```python
# test_orchestration_service.py

@pytest.mark.asyncio
async def test_analyze_from_barcode_success(
    orchestrator: MealAnalysisOrchestrator,
    mock_barcode_service: AsyncMock,
    sample_barcode: Barcode,
):
    """Test successful barcode analysis."""
    # ARRANGE
    mock_barcode_service.enrich.return_value = BarcodeEnrichmentResult(...)
    
    # ACT
    analysis = await orchestrator.analyze_from_barcode(
        user_id=UserId(value="user123"),
        barcode=sample_barcode,
        quantity_g=150.0,
    )
    
    # ASSERT
    assert analysis.metadata.source == AnalysisSource.BARCODE_SCAN
    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.quantity_g == 150.0
    assert not analysis.is_expired()


@pytest.mark.asyncio
async def test_idempotency_returns_existing(
    orchestrator: MealAnalysisOrchestrator,
    mock_analysis_repository: AsyncMock,
    existing_analysis: MealAnalysis,
):
    """Test idempotency returns existing analysis."""
    # ARRANGE
    mock_analysis_repository.get_by_id.return_value = existing_analysis
    
    # ACT
    analysis = await orchestrator.analyze_from_barcode(
        user_id=existing_analysis.user_id,
        barcode=Barcode(value="123"),
        quantity_g=100.0,
        analysis_id=existing_analysis.analysis_id,
    )
    
    # ASSERT
    assert analysis == existing_analysis
    # Verify no new processing occurred
    mock_barcode_service.enrich.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_to_category_on_barcode_error(
    orchestrator: MealAnalysisOrchestrator,
    mock_barcode_service: AsyncMock,
    mock_category_repository: AsyncMock,
):
    """Test fallback to category profile on barcode error."""
    # ARRANGE
    mock_barcode_service.enrich.side_effect = BarcodeNotFoundError(...)
    mock_category_repository.get_by_name.return_value = CategoryProfile(...)
    
    # ACT
    analysis = await orchestrator.analyze_from_barcode(...)
    
    # ASSERT
    assert analysis.metadata.source == AnalysisSource.CATEGORY_PROFILE
    assert analysis.metadata.fallback_reason == "Barcode not found"
    assert analysis.status == AnalysisStatus.PARTIAL
```

### Integration Tests (`tests/integration/`)

```python
# test_meal_analysis_flow.py

@pytest.mark.asyncio
async def test_complete_barcode_flow():
    """Test complete flow: analyze → store → retrieve → convert."""
    # 1. Analyze barcode
    analysis = await orchestrator.analyze_from_barcode(...)
    
    # 2. Verify stored
    stored = await repository.get_by_id(analysis.analysis_id)
    assert stored == analysis
    
    # 3. Convert to meal
    meal_id = await orchestrator.convert_to_meal(analysis.analysis_id)
    
    # 4. Verify marked as converted
    updated = await repository.get_by_id(analysis.analysis_id)
    assert updated.converted_to_meal_at is not None
```

---

## 📊 Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| AI Vision Analysis | <2000ms | Include AI inference |
| Barcode Analysis | <300ms | USDA + OFF combined |
| USDA Search | <500ms | Single API call |
| Storage Write | <50ms | MongoDB upsert |
| Idempotency Check | <10ms | Indexed query |

---

## 🔄 Fallback Strategy

```
PRIMARY SOURCES:
1. AI Vision (photo) → USDA search → Category profile
2. Barcode scan → USDA search → Category profile  
3. USDA search → Category profile

FALLBACK RULES:
- If primary fails → try secondary
- If all fail → return error with context
- Partial success → status=PARTIAL + fallback_reason
```

---

## 📝 API Contract (GraphQL)

```graphql
type Mutation {
  analyzeMealFromPhoto(
    userId: ID!
    imageData: Upload!
    analysisId: ID
  ): MealAnalysis!
  
  analyzeMealFromBarcode(
    userId: ID!
    barcode: String!
    quantityG: Float!
    analysisId: ID
  ): MealAnalysis!
  
  convertAnalysisToMeal(
    analysisId: ID!
  ): Meal!
}

type Query {
  getMealAnalysis(analysisId: ID!): MealAnalysis
  getRecentAnalyses(userId: ID!, limit: Int = 10): [MealAnalysis!]!
}
```

---

## ✅ Definition of Done

- [ ] Domain models with Pydantic V2
- [ ] Orchestrator with full DI
- [ ] Repository interface + MongoDB impl
- [ ] Unit tests (>90% coverage)
- [ ] Integration tests E2E
- [ ] Performance logging
- [ ] Error handling graceful
- [ ] Documentation completa
- [ ] Mypy strict pass
- [ ] All tests green

---

## 🚀 Next Steps After FASE 4

1. **FASE 5** - GraphQL API Layer
2. **FASE 6** - Mobile Integration
3. **FASE 7** - Performance Optimization
4. **FASE 8** - Production Deployment
