# 🎓 V2 Service Layer - Examples & Best Practices

**Document Type:** Technical Reference & Examples  
**Version:** 1.0  
**Date:** 20 Ottobre 2025  
**Target:** Backend/v2/domain/  

---

## 📚 Table of Contents

1. [Example Services](#example-services)
   - [FoodRecognitionService](#foodrecognitionservice)
   - [MealPersistenceService](#mealpersistenceservice)
2. [Best Practices: Models](#best-practices-models)
3. [Best Practices: Services](#best-practices-services)
4. [Best Practices: Dependency Injection](#best-practices-dependency-injection)
5. [Best Practices: Testing](#best-practices-testing)
6. [Best Practices: Mocking](#best-practices-mocking)
7. [Best Practices: Persistenza](#best-practices-persistenza)
8. [Best Practices: Performance & Latenza](#best-practices-performance--latenza)
9. [Best Practices: Robustezza](#best-practices-robustezza)
10. [Quick Reference](#quick-reference)

---

## 🔬 Example Services

### FoodRecognitionService

**Location:** `backend/v2/domain/meal/recognition/service.py`

**Responsibilities:**
- Riconoscimento AI di cibi da immagini
- Estrazione cibi da testo
- Caching per ridurre costi API
- Retry logic per transient failures
- Rate limit handling

**Full Implementation:**

```python
"""Optimized food recognition service with caching, retry, and error handling."""

from __future__ import annotations

import time
import asyncio
import hashlib
from typing import Protocol, Optional, List
from datetime import timedelta
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .models import RecognitionRequest, RecognitionResult, RecognitionStatus
from ...shared.value_objects import FoodItem
from ...shared.errors import ExternalServiceError, RateLimitError

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════
# INTERFACES (Protocol Pattern)
# ═══════════════════════════════════════════════════════════

class IAIVisionClient(Protocol):
    """Interface for AI Vision clients (OpenAI, Google Vision, etc.)."""
    
    async def analyze_food_image(
        self, 
        image_url: str, 
        dish_hint: Optional[str] = None,
        timeout: float = 30.0
    ) -> dict:
        """Analyze food image and return structured response."""
        ...


class ICache(Protocol):
    """Interface for cache layer (Redis, Memory, etc.)."""
    
    async def get(self, key: str) -> Optional[dict]:
        """Get cached value by key."""
        ...
    
    async def set(self, key: str, value: dict, ttl: timedelta) -> None:
        """Set cached value with TTL."""
        ...


# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

class RecognitionConfig:
    """
    Configuration for FoodRecognitionService.
    
    BEST PRACTICE: Centralize all magic numbers in a config class.
    Makes values easy to change without hunting through code.
    """
    
    # Timeouts (seconds)
    VISION_TIMEOUT_SEC: float = 30.0
    TEXT_TIMEOUT_SEC: float = 10.0
    
    # Cache TTL
    VISION_CACHE_TTL: timedelta = timedelta(hours=24)
    TEXT_CACHE_TTL: timedelta = timedelta(hours=6)
    
    # Retry configuration
    MAX_RETRIES: int = 3
    RETRY_MIN_WAIT_SEC: float = 1.0
    RETRY_MAX_WAIT_SEC: float = 10.0
    
    # Quality thresholds
    MIN_ITEM_CONFIDENCE: float = 0.3
    TEXT_EXTRACTION_BASE_CONFIDENCE: float = 0.7


# ═══════════════════════════════════════════════════════════
# SERVICE
# ═══════════════════════════════════════════════════════════

class FoodRecognitionService:
    """
    Service for AI-powered food recognition.
    
    BEST PRACTICES DEMONSTRATED:
    1. Dependency Injection (constructor)
    2. Interface-based dependencies (Protocol)
    3. Optional dependencies (cache is optional)
    4. Configuration object
    5. Retry logic with exponential backoff
    6. Timeout protection
    7. Cache-aside pattern
    8. Structured logging
    9. Metrics collection
    10. Typed exceptions
    
    Example Usage:
        >>> service = FoodRecognitionService(
        ...     ai_client=openai_client,
        ...     cache=redis_cache,
        ... )
        >>> request = RecognitionRequest(
        ...     image_url="https://example.com/pizza.jpg",
        ...     user_id="user_123",
        ... )
        >>> result = await service.recognize_food(request)
        >>> print(result.items)  # List[FoodItem]
    """

    def __init__(
        self,
        ai_client: IAIVisionClient,
        cache: Optional[ICache] = None,
        config: Optional[RecognitionConfig] = None,
    ) -> None:
        """
        Initialize with dependencies.
        
        BEST PRACTICE: Constructor Dependency Injection
        - All dependencies passed explicitly
        - Easy to test (pass mocks)
        - Clear what service needs
        - Optional dependencies default to None
        
        Args:
            ai_client: AI vision client (required)
            cache: Cache layer (optional - graceful degradation)
            config: Configuration (optional - uses defaults)
        """
        self._ai_client = ai_client
        self._cache = cache
        self._config = config or RecognitionConfig()
        
        # Internal state
        self._metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'errors': 0,
            'timeouts': 0,
            'rate_limits': 0,
        }

    # ═══════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((ExternalServiceError, TimeoutError)),
        reraise=True,
    )
    async def recognize_food(
        self, 
        request: RecognitionRequest
    ) -> RecognitionResult:
        """
        Recognize food items in image.
        
        BEST PRACTICES DEMONSTRATED:
        - Retry decorator (tenacity)
        - Cache-aside pattern
        - Timeout protection
        - Structured logging
        - Metrics tracking
        
        Flow:
        1. Check cache (cache hit → return immediately)
        2. Call AI API (with timeout)
        3. Parse response
        4. Store in cache
        5. Return result
        
        Raises:
            RateLimitError: If API rate limit exceeded
            TimeoutError: If API call times out
            ExternalServiceError: For other API errors
        """
        start_time = time.time()
        
        # ─────────────────────────────────────────────────────
        # STEP 1: Cache lookup
        # ─────────────────────────────────────────────────────
        cache_key = self._get_cache_key(request)
        if self._cache and (cached := await self._cache.get(cache_key)):
            self._metrics['cache_hits'] += 1
            
            logger.info(
                "food_recognition_cache_hit",
                user_id=request.user_id,
                cache_key=cache_key,
                latency_ms=int((time.time() - start_time) * 1000),
            )
            
            # BEST PRACTICE: Use Pydantic for deserialization
            return RecognitionResult.parse_obj(cached)

        self._metrics['cache_misses'] += 1

        try:
            # ─────────────────────────────────────────────────
            # STEP 2: Call AI API (with timeout)
            # ─────────────────────────────────────────────────
            vision_result = await self._call_vision_api(request)
            
            processing_time_ms = int((time.time() - start_time) * 1000)

            # ─────────────────────────────────────────────────
            # STEP 3: Parse response
            # ─────────────────────────────────────────────────
            items = self._parse_vision_response(vision_result)
            dish_name = vision_result.get("dish_name")
            confidence = self._calculate_average_confidence(items)

            result = RecognitionResult(
                items=items,
                dish_name=dish_name,
                confidence=confidence,
                processing_time_ms=processing_time_ms,
                status=RecognitionStatus.SUCCESS,
                raw_response=str(vision_result),
            )

            # ─────────────────────────────────────────────────
            # STEP 4: Store in cache
            # ─────────────────────────────────────────────────
            if self._cache:
                await self._cache.set(
                    cache_key,
                    result.dict(),
                    ttl=self._config.VISION_CACHE_TTL,
                )

            logger.info(
                "food_recognition_success",
                user_id=request.user_id,
                items_count=len(items),
                confidence=confidence,
                processing_time_ms=processing_time_ms,
                cached=False,
            )

            self._metrics['api_calls'] += 1
            return result

        except RateLimitError:
            self._metrics['rate_limits'] += 1
            logger.error(
                "food_recognition_rate_limited",
                user_id=request.user_id,
                service="ai_vision",
            )
            raise

        except TimeoutError as e:
            self._metrics['timeouts'] += 1
            logger.error(
                "food_recognition_timeout",
                user_id=request.user_id,
                timeout_sec=self._config.VISION_TIMEOUT_SEC,
            )
            raise ExternalServiceError(f"Vision API timeout: {e}")

        except Exception as e:
            self._metrics['errors'] += 1
            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.error(
                "food_recognition_failed",
                user_id=request.user_id,
                error_type=type(e).__name__,
                error=str(e),
                processing_time_ms=processing_time_ms,
            )

            raise ExternalServiceError(f"Food recognition failed: {e}") from e

    async def extract_text_description(
        self, 
        description: str
    ) -> RecognitionResult:
        """
        Extract food items from text description.
        
        Note: Should use AI structured output, not heuristics.
        Simplified implementation for example.
        """
        start_time = time.time()
        
        cache_key = f"text_extraction:{hashlib.sha256(description.encode()).hexdigest()[:16]}"
        if self._cache and (cached := await self._cache.get(cache_key)):
            return RecognitionResult.parse_obj(cached)

        try:
            # In production: call AI with text extraction prompt
            items = await self._extract_with_ai(description)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            result = RecognitionResult(
                items=items,
                dish_name=description,
                confidence=self._config.TEXT_EXTRACTION_BASE_CONFIDENCE,
                processing_time_ms=processing_time_ms,
                status=RecognitionStatus.SUCCESS,
                raw_response=description,
            )

            if self._cache:
                await self._cache.set(
                    cache_key,
                    result.dict(),
                    ttl=self._config.TEXT_CACHE_TTL,
                )

            return result

        except Exception as e:
            logger.error(
                "text_extraction_failed",
                description=description,
                error=str(e),
            )
            raise ExternalServiceError(f"Text extraction failed: {e}") from e

    def get_metrics(self) -> dict:
        """
        Get service metrics for monitoring.
        
        BEST PRACTICE: Expose internal metrics for observability.
        Useful for dashboards, alerts, debugging.
        """
        return {
            **self._metrics,
            'cache_hit_rate': (
                self._metrics['cache_hits'] 
                / max(1, self._metrics['cache_hits'] + self._metrics['cache_misses'])
            ),
        }

    # ═══════════════════════════════════════════════════════
    # PRIVATE METHODS
    # ═══════════════════════════════════════════════════════

    async def _call_vision_api(self, request: RecognitionRequest) -> dict:
        """
        Call Vision API with timeout and error classification.
        
        BEST PRACTICE: Isolate external calls in separate method.
        - Easier to mock in tests
        - Centralized error handling
        - Timeout management
        """
        try:
            result = await asyncio.wait_for(
                self._ai_client.analyze_food_image(
                    image_url=request.image_url,
                    dish_hint=request.dish_hint,
                ),
                timeout=self._config.VISION_TIMEOUT_SEC,
            )
            return result

        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Vision API exceeded {self._config.VISION_TIMEOUT_SEC}s"
            )

        except Exception as e:
            # BEST PRACTICE: Classify errors by examining message
            error_msg = str(e).lower()
            
            if any(kw in error_msg for kw in ['rate', 'quota', '429']):
                raise RateLimitError(f"AI Vision rate limited: {e}")
            
            if any(kw in error_msg for kw in ['timeout', 'deadline']):
                raise TimeoutError(f"AI Vision timeout: {e}")
            
            if any(kw in error_msg for kw in ['auth', 'unauthorized', '401', '403']):
                raise ExternalServiceError(f"AI Vision auth failed: {e}")
            
            raise ExternalServiceError(f"AI Vision call failed: {e}") from e

    def _get_cache_key(self, request: RecognitionRequest) -> str:
        """Generate cache key for request."""
        key_parts = [request.image_url]
        if request.dish_hint:
            key_parts.append(request.dish_hint)
        
        key_string = "|".join(key_parts)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return f"food_recognition:{key_hash}"

    def _parse_vision_response(self, response: dict) -> List[FoodItem]:
        """Parse AI response to domain objects."""
        items = []

        for item_data in response.get("items", []):
            try:
                confidence = float(item_data["confidence"])
                
                # Filter low confidence items
                if confidence < self._config.MIN_ITEM_CONFIDENCE:
                    logger.debug(
                        "vision_item_filtered_low_confidence",
                        item=item_data["label"],
                        confidence=confidence,
                    )
                    continue

                # BEST PRACTICE: Use Pydantic models for validation
                item = FoodItem(
                    label=item_data["label"],
                    display_name=item_data.get("display_name", item_data["label"]),
                    quantity_g=float(item_data["quantity_g"]),
                    confidence=confidence,
                    category=item_data.get("category"),
                    nutrients=None,  # Enriched later
                )
                items.append(item)

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(
                    "vision_item_parse_error",
                    item_data=item_data,
                    error_type=type(e).__name__,
                    error=str(e),
                )
                continue

        return items

    def _calculate_average_confidence(self, items: List[FoodItem]) -> float:
        """Calculate average confidence across items."""
        if not items:
            return 0.0

        total_confidence = sum(item.confidence for item in items)
        return round(total_confidence / len(items), 2)

    async def _extract_with_ai(self, description: str) -> List[FoodItem]:
        """Use AI for text extraction (stub for example)."""
        # TODO: Implement with OpenAI structured output
        raise NotImplementedError(
            "AI text extraction not implemented. "
            "Use ai_client.extract_food_from_text() with structured output."
        )
```

---

### MealPersistenceService

**Location:** `backend/v2/domain/meal/persistence/service.py`

**Responsibilities:**
- Salvare analisi temporanee (cache)
- Confermare meal entries (persistenza definitiva)
- Gestire transazioni atomiche
- Implementare idempotency checks
- Batch insert per performance

**Full Implementation:**

```python
"""Optimized persistence service with transactions, idempotency, and batch operations."""

from __future__ import annotations

import time
import hashlib
from typing import Protocol, Optional, List
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import structlog

from .models import (
    MealAnalysis,
    ConfirmationRequest,
    ConfirmationResult,
    ConfirmationStatus,
)
from ...shared.value_objects import UserId, MealId, FoodItem
from ...shared.errors import ValidationError, ConflictError, NotFoundError

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════
# INTERFACES (Repository Pattern)
# ═══════════════════════════════════════════════════════════

class IMealRepository(Protocol):
    """
    Interface for meal repository.
    
    BEST PRACTICE: Repository pattern
    - Domain doesn't know about MongoDB
    - Easy to swap implementations
    - Testable with mocks
    """
    
    async def create_batch(
        self, 
        meals: List[MealRecord],
    ) -> List[MealRecord]:
        """Batch create meals (single DB query)."""
        ...
    
    async def exists_by_idempotency_key(self, key: str) -> bool:
        """Check if meal with idempotency key exists."""
        ...
    
    async def find_by_idempotency_key(
        self, 
        key: str
    ) -> Optional[MealRecord]:
        """Find meal by idempotency key."""
        ...


class IAnalysisRepository(Protocol):
    """Interface for analysis repository (temporary storage)."""
    
    async def store(self, analysis: MealAnalysis) -> None:
        """Store analysis temporarily."""
        ...
    
    async def get_by_id(self, analysis_id: str) -> Optional[MealAnalysis]:
        """Get analysis by ID."""
        ...
    
    async def delete(self, analysis_id: str) -> bool:
        """Delete analysis. Returns True if deleted."""
        ...
    
    async def get_by_user(
        self, 
        user_id: UserId, 
        limit: int
    ) -> List[MealAnalysis]:
        """Get user analyses."""
        ...


class ITransactionManager(Protocol):
    """
    Interface for database transaction management.
    
    BEST PRACTICE: Transaction abstraction
    - Service doesn't know about MongoDB sessions
    - Easy to test (mock context manager)
    - Supports different databases
    """
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transaction.
        
        Usage:
            async with tx_manager.transaction():
                await repo.create(...)
                await other_repo.update(...)
                # Auto-commit on success, auto-rollback on exception
        """
        ...


# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

class PersistenceConfig:
    """Configuration for MealPersistenceService."""
    
    # Analysis cache
    ANALYSIS_DEFAULT_LIMIT: int = 10
    ANALYSIS_MAX_LIMIT: int = 100
    ANALYSIS_TTL_HOURS: int = 24
    
    # Confirmation
    MAX_ITEMS_PER_CONFIRMATION: int = 50
    ENABLE_IDEMPOTENCY_CHECK: bool = True
    
    # Batch operations
    BATCH_INSERT_SIZE: int = 100


# ═══════════════════════════════════════════════════════════
# SERVICE
# ═══════════════════════════════════════════════════════════

class MealPersistenceService:
    """
    Service handling meal analysis and entry persistence.
    
    BEST PRACTICES DEMONSTRATED:
    1. Repository pattern (no DB coupling)
    2. Transaction management (atomicity)
    3. Idempotency checks (prevent duplicates)
    4. Batch operations (performance)
    5. Validation (fail-fast)
    6. Typed exceptions (explicit errors)
    7. Metrics collection
    8. Structured logging
    
    Example Usage:
        >>> service = MealPersistenceService(
        ...     meal_repo=mongo_meal_repo,
        ...     analysis_repo=redis_analysis_repo,
        ...     transaction_manager=mongo_tx_manager,
        ... )
        >>> 
        >>> # Store temporary analysis
        >>> await service.store_analysis(analysis)
        >>> 
        >>> # Confirm and persist
        >>> request = ConfirmationRequest(...)
        >>> result = await service.confirm_meal(request)
        >>> print(result.meal_ids)  # List of created meal IDs
    """

    def __init__(
        self,
        meal_repo: IMealRepository,
        analysis_repo: IAnalysisRepository,
        transaction_manager: ITransactionManager,
        config: Optional[PersistenceConfig] = None,
    ) -> None:
        """
        Initialize with dependencies.
        
        BEST PRACTICE: All repositories injected
        - No global imports
        - Testable with mocks
        - Clear dependencies
        """
        self._meal_repo = meal_repo
        self._analysis_repo = analysis_repo
        self._tx_manager = transaction_manager
        self._config = config or PersistenceConfig()
        
        self._metrics = {
            'analyses_stored': 0,
            'meals_confirmed': 0,
            'idempotency_hits': 0,
            'transaction_rollbacks': 0,
        }

    # ═══════════════════════════════════════════════════════
    # ANALYSIS OPERATIONS
    # ═══════════════════════════════════════════════════════

    async def store_analysis(self, analysis: MealAnalysis) -> None:
        """
        Store meal analysis in temporary cache.
        
        BEST PRACTICE: Validate before persistence
        - Fail-fast on invalid data
        - Clear error messages
        """
        # Validation
        if not analysis.food_items:
            raise ValidationError("Analysis must contain at least one food item")
        
        if not analysis.analysis_id:
            raise ValidationError("Analysis must have an ID")

        try:
            await self._analysis_repo.store(analysis)
            
            self._metrics['analyses_stored'] += 1

            logger.info(
                "analysis_stored",
                analysis_id=str(analysis.analysis_id),
                user_id=str(analysis.user_id),
                items_count=len(analysis.food_items),
                source=analysis.source,
            )

        except Exception as e:
            logger.error(
                "analysis_storage_error",
                analysis_id=str(analysis.analysis_id),
                error_type=type(e).__name__,
                error=str(e),
            )
            raise  # BEST PRACTICE: Re-raise, don't swallow

    async def get_analysis(self, analysis_id: str) -> MealAnalysis:
        """
        Get stored analysis by ID.
        
        BEST PRACTICE: Explicit errors
        - NotFoundError (not None)
        - Caller knows exactly what happened
        
        Raises:
            NotFoundError: If analysis not found
            ValidationError: If invalid ID
        """
        if not analysis_id:
            raise ValidationError("Analysis ID required")

        try:
            analysis = await self._analysis_repo.get_by_id(analysis_id)
            
            if not analysis:
                raise NotFoundError(
                    f"Analysis not found: {analysis_id}. "
                    "It may have expired or been confirmed."
                )
            
            return analysis

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(
                "analysis_retrieval_error",
                analysis_id=analysis_id,
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    async def get_user_analyses(
        self, 
        user_id: UserId, 
        limit: Optional[int] = None
    ) -> List[MealAnalysis]:
        """
        Get recent analyses for user.
        
        BEST PRACTICE: Validate and cap limits
        - Prevent abuse (excessive queries)
        - Protect database
        """
        limit = limit or self._config.ANALYSIS_DEFAULT_LIMIT
        if limit > self._config.ANALYSIS_MAX_LIMIT:
            limit = self._config.ANALYSIS_MAX_LIMIT

        try:
            return await self._analysis_repo.get_by_user(user_id, limit)

        except Exception as e:
            logger.error(
                "user_analyses_error",
                user_id=str(user_id),
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    # ═══════════════════════════════════════════════════════
    # MEAL CONFIRMATION (Critical Path)
    # ═══════════════════════════════════════════════════════

    async def confirm_meal(
        self, 
        request: ConfirmationRequest
    ) -> ConfirmationResult:
        """
        Confirm analysis and create persistent meal entries.
        
        BEST PRACTICES DEMONSTRATED:
        - Atomic transaction (all-or-nothing)
        - Idempotency check (prevent duplicates)
        - Batch insert (single DB query)
        - Proper rollback on error
        - Structured error handling
        
        Flow:
        1. Validate request
        2. Start transaction
        3. Check idempotency (if enabled)
        4. Batch create meals
        5. Delete analysis
        6. Commit transaction
        
        On error: Transaction auto-rollbacks
        
        Returns:
            ConfirmationResult with status and meal IDs
        """
        start_time = time.time()

        # ─────────────────────────────────────────────────────
        # STEP 1: Validation
        # ─────────────────────────────────────────────────────
        self._validate_confirmation_request(request)

        try:
            # ─────────────────────────────────────────────────
            # STEP 2: ATOMIC TRANSACTION
            # ─────────────────────────────────────────────────
            async with self._tx_manager.transaction():
                
                # STEP 3: Idempotency check
                if self._config.ENABLE_IDEMPOTENCY_CHECK:
                    await self._check_idempotency(request)
                
                # STEP 4: Batch create meals
                meal_records = [
                    self._create_meal_record(
                        request.user_id,
                        food_item,
                        request.meal_time,
                    )
                    for food_item in request.food_items
                ]
                
                # BEST PRACTICE: Batch insert (1 query vs N queries)
                created_meals = await self._meal_repo.create_batch(meal_records)
                meal_ids = [meal.meal_id for meal in created_meals]
                
                # STEP 5: Delete analysis
                deleted = await self._analysis_repo.delete(request.analysis_id)
                if not deleted:
                    logger.warning(
                        "analysis_already_deleted",
                        analysis_id=request.analysis_id,
                    )
                
                # Transaction commits automatically here

            processing_time_ms = int((time.time() - start_time) * 1000)
            
            self._metrics['meals_confirmed'] += len(meal_ids)

            result = ConfirmationResult(
                status=ConfirmationStatus.SUCCESS,
                meal_ids=meal_ids,
                processing_time_ms=processing_time_ms,
            )

            logger.info(
                "meal_confirmation_success",
                analysis_id=request.analysis_id,
                user_id=str(request.user_id),
                meal_count=len(meal_ids),
                processing_time_ms=processing_time_ms,
            )

            return result

        except ConflictError as e:
            # BEST PRACTICE: Handle idempotency gracefully
            self._metrics['idempotency_hits'] += 1
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.warning(
                "meal_confirmation_idempotency_hit",
                analysis_id=request.analysis_id,
                user_id=str(request.user_id),
                error=str(e),
            )
            
            return ConfirmationResult(
                status=ConfirmationStatus.DUPLICATE,
                meal_ids=[],
                processing_time_ms=processing_time_ms,
                error_message=str(e),
            )

        except Exception as e:
            # BEST PRACTICE: Transaction auto-rollbacks on exception
            self._metrics['transaction_rollbacks'] += 1
            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.error(
                "meal_confirmation_error",
                analysis_id=request.analysis_id,
                user_id=str(request.user_id),
                error_type=type(e).__name__,
                error=str(e),
                processing_time_ms=processing_time_ms,
            )

            # Return ERROR status (don't raise exception to GraphQL)
            return ConfirmationResult(
                status=ConfirmationStatus.ERROR,
                meal_ids=[],
                processing_time_ms=processing_time_ms,
                error_message=str(e),
            )

    def _validate_confirmation_request(
        self, 
        request: ConfirmationRequest
    ) -> None:
        """
        Validate confirmation request.
        
        BEST PRACTICE: Centralized validation
        - Single place for all checks
        - Clear error messages
        - Fail-fast
        """
        if not request.food_items:
            raise ValidationError("At least one food item required")
        
        if len(request.food_items) > self._config.MAX_ITEMS_PER_CONFIRMATION:
            raise ValidationError(
                f"Too many items. Max: {self._config.MAX_ITEMS_PER_CONFIRMATION}"
            )
        
        # Validate all items have nutrients
        for i, item in enumerate(request.food_items):
            if not item.nutrients:
                raise ValidationError(
                    f"Item {i} ({item.name}) missing nutrient data"
                )

    async def _check_idempotency(
        self, 
        request: ConfirmationRequest
    ) -> None:
        """
        Check if meals already exist (idempotency).
        
        BEST PRACTICE: Idempotency for user actions
        - Prevents duplicate meals if user clicks "Confirm" twice
        - Uses hash of key fields
        - DB index for fast lookup
        
        Raises:
            ConflictError: If any meal already exists
        """
        keys = [
            self._generate_idempotency_key(
                request.user_id,
                item,
                self._parse_meal_time(request.meal_time),
            )
            for item in request.food_items
        ]
        
        for key in keys:
            if await self._meal_repo.exists_by_idempotency_key(key):
                existing = await self._meal_repo.find_by_idempotency_key(key)
                raise ConflictError(
                    f"Meal '{existing.name}' already logged at this time. "
                    f"Meal ID: {existing.meal_id}"
                )

    def _create_meal_record(
        self,
        user_id: UserId,
        food_item: FoodItem,
        meal_time: Optional[str] = None,
    ) -> MealRecord:
        """Create meal repository record from food item."""
        logged_at = self._parse_meal_time(meal_time)
        
        idempotency_key = self._generate_idempotency_key(
            user_id, food_item, logged_at
        )

        return MealRecord(
            meal_id=MealId.generate(),
            user_id=user_id,
            name=food_item.name,
            quantity_g=food_item.nutrients.quantity_g,
            calories=food_item.nutrients.calories,
            protein=food_item.nutrients.protein,
            carbs=food_item.nutrients.carbs,
            fat=food_item.nutrients.fat,
            fiber=food_item.nutrients.fiber,
            sugar=food_item.nutrients.sugar,
            sodium=food_item.nutrients.sodium,
            barcode=food_item.barcode,
            brand=food_item.brand,
            logged_at=logged_at,
            idempotency_key=idempotency_key,
            nutrient_snapshot_json=food_item.nutrients.to_dict(),
            enrichment_source=food_item.nutrients.source,
        )

    def _parse_meal_time(self, meal_time: Optional[str]) -> datetime:
        """
        Parse meal time with proper timezone handling.
        
        BEST PRACTICE: Always use timezone-aware datetimes
        - Prevents timezone bugs
        - Explicit about UTC
        - Warnings for naive datetimes
        """
        if not meal_time:
            return datetime.now(timezone.utc)
        
        try:
            dt = datetime.fromisoformat(meal_time)
            
            # Ensure UTC
            if dt.tzinfo is None:
                logger.warning(
                    "meal_time_missing_timezone",
                    meal_time=meal_time,
                    assuming_utc=True,
                )
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt
            
        except ValueError as e:
            logger.warning(
                "invalid_meal_time",
                meal_time=meal_time,
                error=str(e),
                using_current_time=True,
            )
            return datetime.now(timezone.utc)

    def _generate_idempotency_key(
        self, 
        user_id: UserId, 
        food_item: FoodItem, 
        logged_at: datetime
    ) -> str:
        """
        Generate idempotency key for meal entry.
        
        BEST PRACTICE: Hash for storage efficiency
        - Includes all distinguishing fields
        - Case-insensitive (name.lower())
        - SHA256 for uniqueness
        - Prefix for namespacing
        
        Format: meal:<hash>
        Hash of: user_id|name|quantity|timestamp|barcode
        """
        key_parts = [
            str(user_id),
            food_item.name.lower().strip(),
            f"{food_item.nutrients.quantity_g:.3f}",
            logged_at.isoformat(),
            food_item.barcode or "",
        ]
        
        key_string = "|".join(key_parts)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        
        return f"meal:{key_hash}"

    def get_metrics(self) -> dict:
        """Get service metrics for monitoring."""
        return {
            **self._metrics,
            'idempotency_hit_rate': (
                self._metrics['idempotency_hits']
                / max(1, self._metrics['meals_confirmed'])
            ),
        }
```

---

## 📐 Best Practices: Models

### 1. Use Pydantic for All Models

**✅ GOOD:**
```python
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class FoodItem(BaseModel):
    """Domain model for food item."""
    
    label: str = Field(..., description="Internal identifier")
    name: str = Field(..., min_length=1, max_length=200)
    quantity_g: float = Field(..., gt=0, description="Quantity in grams")
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: Optional[str] = None
    nutrients: Optional[NutrientProfile] = None
    
    @validator('name')
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
    
    class Config:
        frozen = True  # Immutable
        use_enum_values = True
```

**❌ BAD:**
```python
# No validation, mutable, error-prone
class FoodItem:
    def __init__(self, label, name, quantity_g):
        self.label = label  # No validation
        self.name = name    # Can be empty
        self.quantity_g = quantity_g  # Can be negative!
```

**Why Pydantic:**
- ✅ Automatic validation
- ✅ Type safety
- ✅ JSON serialization/deserialization
- ✅ IDE autocomplete
- ✅ OpenAPI schema generation

---

### 2. Immutable Models (Value Objects)

**✅ GOOD:**
```python
from pydantic import BaseModel

class UserId(BaseModel):
    """Value object for user ID."""
    
    value: str = Field(..., regex=r'^user_[a-zA-Z0-9]+$')
    
    class Config:
        frozen = True  # Immutable
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, s: str) -> 'UserId':
        return cls(value=s)
```

**❌ BAD:**
```python
# Just using strings everywhere
user_id = "user_123"  # No validation, can be changed accidentally
```

**Benefits:**
- ✅ Thread-safe (immutable)
- ✅ Can be used as dict keys
- ✅ Validation at creation
- ✅ Clear intent (UserId vs str)

---

### 3. Separate DTOs from Domain Models

**Structure:**
```
domain/
├── meal/
│   ├── models.py              # Domain models (business logic)
│   │   ├── MealAnalysis       # Core domain
│   │   ├── ConfirmationRequest
│   │   └── ConfirmationResult
│   │
│   └── persistence/
│       └── models.py          # Repository models
│           └── MealRecord     # DB representation
│
graphql/
└── types/
    └── meal_types.py          # GraphQL DTOs
        ├── MealPhotoAnalysisType
        └── ConfirmMealInput
```

**Why Separate:**
- ✅ Domain models independent of API
- ✅ DB schema changes don't affect API
- ✅ Clear boundaries
- ✅ Each layer has its own concerns

---

### 4. Use Enums for Constants

**✅ GOOD:**
```python
from enum import Enum

class RecognitionStatus(str, Enum):
    """Status of food recognition."""
    
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"

class NutrientSource(str, Enum):
    """Source of nutrient data."""
    
    USDA = "USDA"
    OPENFOODFACTS = "OPENFOODFACTS"
    MANUAL = "MANUAL"
    ESTIMATED = "ESTIMATED"
```

**❌ BAD:**
```python
# Magic strings everywhere
status = "success"  # Typo possible
source = "usda"     # Inconsistent casing
```

---

## 🔧 Best Practices: Services

### 1. Constructor Dependency Injection

**✅ GOOD:**
```python
class FoodRecognitionService:
    def __init__(
        self,
        ai_client: IAIVisionClient,
        cache: Optional[ICache] = None,
        config: Optional[RecognitionConfig] = None,
    ):
        self._ai_client = ai_client
        self._cache = cache
        self._config = config or RecognitionConfig()
```

**❌ BAD:**
```python
# Global import - hard to test, tightly coupled
from infrastructure.ai.openai_client import openai_client

class FoodRecognitionService:
    def __init__(self):
        pass  # Uses global openai_client
```

**Benefits:**
- ✅ Testable (inject mocks)
- ✅ Flexible (swap implementations)
- ✅ Clear dependencies
- ✅ No global state

---

### 2. Use Protocol (Interface) for Dependencies

**✅ GOOD:**
```python
from typing import Protocol

class IAIVisionClient(Protocol):
    """Interface for AI Vision clients."""
    
    async def analyze_food_image(
        self, 
        image_url: str, 
        dish_hint: Optional[str] = None
    ) -> dict:
        ...

# Service depends on interface
class FoodRecognitionService:
    def __init__(self, ai_client: IAIVisionClient):
        self._ai_client = ai_client
```

**❌ BAD:**
```python
# Depends on concrete class
from infrastructure.ai.openai_client import OpenAIClient

class FoodRecognitionService:
    def __init__(self, ai_client: OpenAIClient):
        self._ai_client = ai_client
```

**Benefits:**
- ✅ Domain layer independent
- ✅ Easy to mock in tests
- ✅ Multiple implementations possible
- ✅ Loose coupling

---

### 3. Configuration Objects

**✅ GOOD:**
```python
class RecognitionConfig:
    """Service configuration."""
    
    VISION_TIMEOUT_SEC: float = 30.0
    CACHE_TTL: timedelta = timedelta(hours=24)
    MAX_RETRIES: int = 3
    MIN_CONFIDENCE: float = 0.3

class FoodRecognitionService:
    def __init__(
        self, 
        ai_client: IAIVisionClient,
        config: Optional[RecognitionConfig] = None,
    ):
        self._config = config or RecognitionConfig()
```

**❌ BAD:**
```python
# Magic numbers scattered everywhere
async def recognize_food(self, image_url: str):
    result = await asyncio.wait_for(
        self._client.call(image_url),
        timeout=30.0  # What is 30? Seconds? Minutes?
    )
    
    if result.confidence < 0.3:  # Where did 0.3 come from?
        return None
```

**Benefits:**
- ✅ Centralized configuration
- ✅ Easy to change
- ✅ Self-documenting
- ✅ Environment-specific configs

---

### 4. Return Result Objects (Not Tuples)

**✅ GOOD:**
```python
@dataclass
class RecognitionResult:
    items: List[FoodItem]
    dish_name: Optional[str]
    confidence: float
    processing_time_ms: int
    status: RecognitionStatus

async def recognize_food(self, request: RecognitionRequest) -> RecognitionResult:
    # ...
    return RecognitionResult(
        items=items,
        dish_name=dish_name,
        confidence=0.9,
        processing_time_ms=250,
        status=RecognitionStatus.SUCCESS,
    )
```

**❌ BAD:**
```python
# Tuple hell
async def recognize_food(self, image_url: str) -> tuple:
    # ...
    return (items, "Pizza", 0.9, 250, "SUCCESS")

# Caller has to remember order
items, dish, conf, time, status = await service.recognize_food(url)
```

**Benefits:**
- ✅ Named fields
- ✅ Type-safe
- ✅ Self-documenting
- ✅ Easy to extend

---

### 5. Fail-Fast Validation

**✅ GOOD:**
```python
async def confirm_meal(self, request: ConfirmationRequest):
    # Validate IMMEDIATELY
    if not request.food_items:
        raise ValidationError("At least one food item required")
    
    if len(request.food_items) > 50:
        raise ValidationError("Too many items. Max: 50")
    
    for item in request.food_items:
        if not item.nutrients:
            raise ValidationError(f"Item {item.name} missing nutrients")
    
    # Now proceed with business logic
    async with self._tx_manager.transaction():
        # ...
```

**❌ BAD:**
```python
async def confirm_meal(self, request: ConfirmationRequest):
    # Start transaction WITHOUT validation
    async with self._tx_manager.transaction():
        # ... halfway through ...
        if not request.food_items:  # Too late!
            raise ValidationError("...")
```

**Benefits:**
- ✅ Fails before expensive operations
- ✅ Clear error messages
- ✅ No partial state
- ✅ Better UX

---

### 6. Metrics Collection

**✅ GOOD:**
```python
class FoodRecognitionService:
    def __init__(self, ...):
        self._metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'errors': 0,
            'timeouts': 0,
        }
    
    async def recognize_food(self, request):
        if cached:
            self._metrics['cache_hits'] += 1
        else:
            self._metrics['cache_misses'] += 1
            self._metrics['api_calls'] += 1
    
    def get_metrics(self) -> dict:
        return {
            **self._metrics,
            'cache_hit_rate': self._metrics['cache_hits'] / 
                             (self._metrics['cache_hits'] + self._metrics['cache_misses'])
        }
```

**Benefits:**
- ✅ Observability
- ✅ Debugging
- ✅ Performance tuning
- ✅ Dashboards/Alerts

---

## 💉 Best Practices: Dependency Injection

### 1. Manual DI (Simple & Explicit)

**Setup (Application Layer):**
```python
# backend/v2/application/meal/di_container.py

from backend.v2.domain.meal.recognition.service import FoodRecognitionService
from backend.v2.domain.meal.persistence.service import MealPersistenceService
from backend.v2.infrastructure.ai.openai_client import OpenAIClient
from backend.v2.infrastructure.cache.redis_cache import RedisCache
from backend.v2.infrastructure.database.repositories.meal_repository import MongoMealRepository


class ServiceContainer:
    """Dependency injection container."""
    
    def __init__(self, settings):
        # Infrastructure layer
        self._openai_client = OpenAIClient(settings.openai_api_key)
        self._redis_cache = RedisCache(settings.redis_uri)
        self._meal_repo = MongoMealRepository(settings.mongodb_uri)
        self._tx_manager = MongoTransactionManager(settings.mongodb_uri)
        
        # Domain services
        self._recognition_service = FoodRecognitionService(
            ai_client=self._openai_client,
            cache=self._redis_cache,
        )
        
        self._persistence_service = MealPersistenceService(
            meal_repo=self._meal_repo,
            analysis_repo=self._redis_cache,
            transaction_manager=self._tx_manager,
        )
    
    @property
    def recognition_service(self) -> FoodRecognitionService:
        return self._recognition_service
    
    @property
    def persistence_service(self) -> MealPersistenceService:
        return self._persistence_service
```

**Usage (GraphQL Resolver):**
```python
# backend/v2/graphql/context.py

from backend.v2.application.meal.di_container import ServiceContainer

def get_context() -> dict:
    container = ServiceContainer(settings)
    
    return {
        'recognition_service': container.recognition_service,
        'persistence_service': container.persistence_service,
    }


# backend/v2/graphql/mutations/analyze_meal.py

@strawberry.mutation
async def analyze_meal_photo(
    self,
    input: AnalyzeMealPhotoInput,
    info: Info,
) -> MealPhotoAnalysis:
    # Get service from context
    service = info.context['recognition_service']
    
    result = await service.recognize_food(...)
    return MealPhotoAnalysis.from_domain(result)
```

---

### 2. Testing with DI

**Easy to Test:**
```python
# test_food_recognition_service.py

import pytest
from unittest.mock import AsyncMock

async def test_recognition_with_cache_hit():
    # ARRANGE: Create mocks
    mock_ai_client = AsyncMock(spec=IAIVisionClient)
    mock_cache = AsyncMock(spec=ICache)
    
    mock_cache.get.return_value = {
        'items': [...],
        'status': 'SUCCESS',
    }
    
    # Inject mocks
    service = FoodRecognitionService(
        ai_client=mock_ai_client,
        cache=mock_cache,
    )
    
    # ACT
    result = await service.recognize_food(request)
    
    # ASSERT
    assert result.status == RecognitionStatus.SUCCESS
    mock_ai_client.analyze_food_image.assert_not_called()  # Cache hit!
    assert service.get_metrics()['cache_hits'] == 1
```

---

## 🧪 Best Practices: Testing

### 1. AAA Pattern (Arrange-Act-Assert)

**✅ GOOD:**
```python
async def test_confirm_meal_success():
    # ARRANGE - Setup test data and mocks
    mock_meal_repo = AsyncMock()
    mock_meal_repo.create_batch.return_value = [sample_meal]
    
    service = MealPersistenceService(
        meal_repo=mock_meal_repo,
        # ...
    )
    
    request = ConfirmationRequest(...)
    
    # ACT - Execute the operation
    result = await service.confirm_meal(request)
    
    # ASSERT - Verify outcome
    assert result.status == ConfirmationStatus.SUCCESS
    assert len(result.meal_ids) == 1
    mock_meal_repo.create_batch.assert_awaited_once()
```

---

### 2. Shared Fixtures (conftest.py)

**✅ GOOD:**
```python
# conftest.py

import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_meal_repo() -> AsyncMock:
    """Mock meal repository with default behaviors."""
    repo = AsyncMock(spec=IMealRepository)
    repo.create_batch.return_value = []
    repo.exists_by_idempotency_key.return_value = False
    return repo

@pytest.fixture
def sample_food_item() -> FoodItem:
    """Sample food item for tests."""
    return FoodItem(
        label="pizza",
        name="Pizza Margherita",
        quantity_g=200.0,
        confidence=0.9,
        nutrients=NutrientProfile(...),
    )

# Use in tests
async def test_something(mock_meal_repo, sample_food_item):
    # Fixtures automatically injected
    service = MealPersistenceService(meal_repo=mock_meal_repo)
    # ...
```

---

### 3. Parametrized Tests

**✅ GOOD:**
```python
@pytest.mark.parametrize(
    "analysis_id,expected_error",
    [
        ("", "Analysis ID required"),
        (None, "Analysis ID required"),
        ("   ", "Analysis ID required"),
    ],
)
async def test_get_analysis_invalid_ids(
    persistence_service,
    analysis_id,
    expected_error,
):
    with pytest.raises(ValidationError, match=expected_error):
        await persistence_service.get_analysis(analysis_id)
```

**Benefits:**
- ✅ Test multiple scenarios in one function
- ✅ Clear test cases
- ✅ Less code duplication

---

### 4. Test Error Paths

**✅ GOOD:**
```python
async def test_confirm_meal_repo_error():
    # Simulate DB error
    mock_meal_repo.create_batch.side_effect = Exception("DB connection lost")
    
    result = await service.confirm_meal(request)
    
    # Should handle gracefully
    assert result.status == ConfirmationStatus.ERROR
    assert "DB connection lost" in result.error_message
    assert service.get_metrics()['transaction_rollbacks'] == 1
```

**Test All Error Scenarios:**
- ✅ Validation errors
- ✅ Repository errors
- ✅ External API errors
- ✅ Timeout errors
- ✅ Rate limit errors
- ✅ Transaction rollbacks

---

### 5. Coverage Target: >90%

**pytest.ini:**
```ini
[pytest]
addopts =
    --cov=backend/v2/domain
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90
    -v
```

**Run:**
```bash
pytest backend/v2/tests/unit/domain/meal/

# Output shows coverage
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
domain/meal/recognition/service.py        245     12    95%   78-82
domain/meal/persistence/service.py        290      8    97%   
---------------------------------------------------------------------
TOTAL                                     535     20    96%
```

---

## 🎭 Best Practices: Mocking

### 1. Use AsyncMock for Async Functions

**✅ GOOD:**
```python
from unittest.mock import AsyncMock

mock_client = AsyncMock(spec=IAIVisionClient)
mock_client.analyze_food_image.return_value = {...}

# Works with await
result = await mock_client.analyze_food_image("url")
```

**❌ BAD:**
```python
from unittest.mock import Mock

mock_client = Mock()  # Regular Mock doesn't work with await!
mock_client.analyze_food_image.return_value = {...}

result = await mock_client.analyze_food_image("url")  # ERROR!
```

---

### 2. Mock at Interface Level

**✅ GOOD:**
```python
# Mock the interface
mock_repo = AsyncMock(spec=IMealRepository)
mock_repo.create_batch.return_value = [meal1, meal2]

service = MealPersistenceService(meal_repo=mock_repo)
```

**❌ BAD:**
```python
# Mock concrete implementation
from infrastructure.database.repositories.meal_repository import MongoMealRepository

with patch('infrastructure.database...MongoMealRepository') as mock:
    # Fragile, coupled to implementation
```

---

### 3. Verify Behavior (Not Just Return Values)

**✅ GOOD:**
```python
async def test_batch_insert_called_once():
    result = await service.confirm_meal(request)
    
    # Verify correct behavior
    mock_repo.create_batch.assert_awaited_once()
    
    # Verify correct arguments
    call_args = mock_repo.create_batch.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0].name == "Pizza"
```

---

### 4. Mock Context Managers

**✅ GOOD:**
```python
# Mock transaction context manager
class MockTransactionManager:
    async def transaction(self):
        class TransactionContext:
            async def __aenter__(self):
                return AsyncMock()
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False
        
        return TransactionContext()

service = MealPersistenceService(
    meal_repo=mock_repo,
    transaction_manager=MockTransactionManager(),
)
```

---

## 💾 Best Practices: Persistenza

### 1. Repository Pattern

**✅ GOOD:**
```python
# Interface in domain layer
class IMealRepository(Protocol):
    async def create_batch(self, meals: List[MealRecord]) -> List[MealRecord]:
        ...

# Implementation in infrastructure layer
class MongoMealRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db.meals
    
    async def create_batch(self, meals: List[MealRecord]) -> List[MealRecord]:
        docs = [meal.dict(by_alias=True) for meal in meals]
        result = await self._collection.insert_many(docs)
        
        for meal, inserted_id in zip(meals, result.inserted_ids):
            meal.id = str(inserted_id)
        
        return meals
```

**Benefits:**
- ✅ Domain independent of DB
- ✅ Easy to test
- ✅ Swap DB implementations

---

### 2. Batch Operations

**✅ GOOD (1 query):**
```python
# Batch insert
meals = [meal1, meal2, meal3, meal4, meal5]
created = await repository.create_batch(meals)
```

**❌ BAD (N queries):**
```python
# N+1 problem
for meal in meals:
    await repository.create(meal)  # 5 separate DB calls!
```

**Performance:**
- 1 item: ~5ms
- 5 items (separate): ~25ms (5×5ms)
- 5 items (batch): ~7ms (80% faster!)

---

### 3. Atomic Transactions

**✅ GOOD:**
```python
async with transaction_manager.transaction():
    # All operations in same transaction
    await meal_repo.create_batch(meals)
    await analysis_repo.delete(analysis_id)
    # Commits automatically
    
# If exception → rollback automatically
```

**❌ BAD:**
```python
# Not atomic
await meal_repo.create_batch(meals)
# If error here, meals are orphaned!
await analysis_repo.delete(analysis_id)
```

---

### 4. Idempotency Keys

**✅ GOOD:**
```python
# Generate unique key
key = f"meal:{hash(user_id|name|quantity|timestamp)}"

# Check before insert
if await repo.exists_by_idempotency_key(key):
    raise ConflictError("Already exists")

# Save with key
meal.idempotency_key = key
await repo.create(meal)
```

**Database Index:**
```python
# MongoDB index
await collection.create_index(
    "idempotency_key",
    unique=True,
    name="idx_idempotency_key",
)
```

**Benefits:**
- ✅ Prevents duplicates
- ✅ Safe retries
- ✅ Idempotent APIs

---

### 5. Soft Delete vs Hard Delete

**✅ GOOD (Soft Delete):**
```python
class MealRecord(BaseModel):
    deleted_at: Optional[datetime] = None
    
    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

# Soft delete
async def delete(self, meal_id: MealId):
    await collection.update_one(
        {'_id': meal_id},
        {'$set': {'deleted_at': datetime.now(timezone.utc)}}
    )

# Query excludes deleted
async def find_by_user(self, user_id: UserId):
    return await collection.find({
        'user_id': user_id,
        'deleted_at': None,  # Exclude deleted
    }).to_list()
```

**Benefits:**
- ✅ Recoverable
- ✅ Audit trail
- ✅ Analytics on deleted data

---

## ⚡ Best Practices: Performance & Latenza

### 1. Caching Strategy

**Cache-Aside Pattern:**
```python
async def recognize_food(self, request):
    # 1. Check cache
    if cached := await cache.get(key):
        return cached  # Fast path
    
    # 2. Cache miss → call API
    result = await ai_client.analyze(...)
    
    # 3. Store in cache
    await cache.set(key, result, ttl=24h)
    
    return result
```

**Metrics:**
- Cache hit: ~2ms
- Cache miss: ~500ms
- Savings: 99.6% faster

**When to Cache:**
- ✅ External API responses (expensive)
- ✅ Complex computations
- ✅ Static/slow-changing data

**When NOT to Cache:**
- ❌ User-specific data (privacy)
- ❌ Real-time data
- ❌ Large blobs (use CDN)

---

### 2. Timeout Protection

**✅ GOOD:**
```python
# Always set timeouts
result = await asyncio.wait_for(
    client.call_api(),
    timeout=30.0,  # 30 seconds max
)
```

**❌ BAD:**
```python
# No timeout → can hang forever
result = await client.call_api()
```

**Timeout Guidelines:**
- Internal services: 5-10s
- External APIs: 30s
- AI/ML inference: 60s

---

### 3. Retry with Backoff

**✅ GOOD (Tenacity):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type(ExternalServiceError),
)
async def call_external_api():
    # Retries: 1s, 2s, 4s, 8s (max 10s)
    return await client.call()
```

**Retry Only:**
- ✅ Transient errors (5xx, network)
- ✅ Timeouts
- ❌ Client errors (4xx) - don't retry
- ❌ Rate limits - backoff differently

---

### 4. Parallel Execution

**✅ GOOD:**
```python
# Run in parallel
results = await asyncio.gather(
    recognize_food(item1),
    recognize_food(item2),
    recognize_food(item3),
)

# 3 items: ~500ms (parallel)
# vs 1500ms (sequential)
```

**⚠️ Watch Out:**
- Rate limits
- Resource exhaustion
- Error handling

---

### 5. Database Indexing

**✅ GOOD:**
```python
# Indexes for common queries
await collection.create_index("user_id")  # Query by user
await collection.create_index("logged_at")  # Query by date
await collection.create_index([
    ("user_id", 1),
    ("logged_at", -1)
])  # Compound index

# Query uses index (fast)
meals = await collection.find({
    'user_id': user_id,
    'logged_at': {'$gte': start_date}
}).to_list()
```

**Performance:**
- Without index: O(n) - scan entire collection
- With index: O(log n) - 1000x faster for large datasets

---

### 6. Query Optimization

**✅ GOOD:**
```python
# Project only needed fields
meals = await collection.find(
    {'user_id': user_id},
    {'_id': 1, 'name': 1, 'calories': 1}  # Only these fields
).to_list()
```

**❌ BAD:**
```python
# Fetch everything
meals = await collection.find({'user_id': user_id}).to_list()
```

**Savings:**
- Full document: 5KB
- Projected: 0.5KB
- 10x less data transfer

---

## 🛡️ Best Practices: Robustezza

### 1. Typed Exceptions

**✅ GOOD:**
```python
# Domain errors
class DomainError(Exception):
    """Base domain exception."""
    pass

class ValidationError(DomainError):
    """Invalid input."""
    pass

class NotFoundError(DomainError):
    """Resource not found."""
    pass

class ConflictError(DomainError):
    """Conflict (e.g. idempotency)."""
    pass

class ExternalServiceError(DomainError):
    """External service failed."""
    pass

class RateLimitError(ExternalServiceError):
    """Rate limit exceeded."""
    pass

# Usage
if not analysis:
    raise NotFoundError(f"Analysis {id} not found")
```

**❌ BAD:**
```python
# Generic exceptions
raise Exception("Something went wrong")
raise ValueError("Bad value")
```

**Benefits:**
- ✅ Specific error handling
- ✅ Clear intent
- ✅ Better logging

---

### 2. Graceful Degradation

**✅ GOOD:**
```python
# Cache is optional
class FoodRecognitionService:
    def __init__(
        self,
        ai_client: IAIVisionClient,
        cache: Optional[ICache] = None,  # Optional!
    ):
        self._cache = cache
    
    async def recognize_food(self, request):
        # Check cache only if available
        if self._cache and (cached := await self._cache.get(key)):
            return cached
        
        # Works even without cache
        result = await self._ai_client.analyze(...)
        
        # Store if cache available
        if self._cache:
            await self._cache.set(key, result)
        
        return result
```

**Benefits:**
- ✅ Works without Redis
- ✅ Degrades gracefully
- ✅ Development easier

---

### 3. Circuit Breaker (Advanced)

**✅ GOOD:**
```python
from aiobreaker import CircuitBreaker

class FoodRecognitionService:
    def __init__(self, ai_client):
        self._ai_client = ai_client
        self._circuit_breaker = CircuitBreaker(
            fail_max=5,  # Open after 5 failures
            timeout=60,  # Stay open for 60s
        )
    
    async def recognize_food(self, request):
        try:
            result = await self._circuit_breaker.call(
                self._ai_client.analyze,
                image_url=request.image_url,
            )
            return result
        
        except CircuitBreakerError:
            # Circuit open → fail fast
            raise ExternalServiceError("AI service unavailable")
```

**States:**
1. **CLOSED**: Normal operation
2. **OPEN**: Too many failures → reject immediately
3. **HALF-OPEN**: Test if service recovered

**Benefits:**
- ✅ Fail fast (don't wait for timeout)
- ✅ Give service time to recover
- ✅ Prevent cascade failures

---

### 4. Structured Logging

**✅ GOOD:**
```python
import structlog

logger = structlog.get_logger(__name__)

async def recognize_food(self, request):
    logger.info(
        "food_recognition_started",
        user_id=request.user_id,
        image_url=request.image_url,
        has_hint=bool(request.dish_hint),
    )
    
    try:
        result = await self._ai_client.analyze(...)
        
        logger.info(
            "food_recognition_success",
            user_id=request.user_id,
            items_count=len(result.items),
            confidence=result.confidence,
            processing_time_ms=result.processing_time_ms,
        )
        
    except Exception as e:
        logger.error(
            "food_recognition_failed",
            user_id=request.user_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise
```

**Benefits:**
- ✅ Machine-parseable (JSON)
- ✅ Easy to search/filter
- ✅ Context-rich
- ✅ Works with ELK, Datadog, etc.

---

### 5. Validation Layers

**Multiple Validation Layers:**

```
┌─────────────────────────────────────────┐
│ GraphQL Layer (Strawberry)              │
│ • Type validation                       │
│ • Required fields                       │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ Application Layer (Use Cases)           │
│ • Business rules                        │
│ • Authorization                         │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ Domain Layer (Services)                 │
│ • Domain invariants                     │
│ • Value object validation               │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ Infrastructure Layer (Repositories)     │
│ • DB constraints                        │
│ • Unique indexes                        │
└─────────────────────────────────────────┘
```

**Example:**
```python
# GraphQL: Type validation
@strawberry.input
class AnalyzeMealInput:
    image_url: str  # Must be string
    user_id: str    # Required

# Application: Business rules
async def analyze_meal_photo(input: AnalyzeMealInput):
    if not input.image_url.startswith('http'):
        raise ValidationError("Invalid URL")

# Domain: Invariants
class FoodItem(BaseModel):
    quantity_g: float = Field(gt=0)  # Must be positive
    
# Infrastructure: DB constraints
await collection.create_index("idempotency_key", unique=True)
```

---

### 6. Health Checks

**✅ GOOD:**
```python
class FoodRecognitionService:
    async def health_check(self) -> dict:
        """Check service health."""
        checks = {}
        
        # Check AI client
        try:
            await asyncio.wait_for(
                self._ai_client.ping(),
                timeout=5.0,
            )
            checks['ai_client'] = 'healthy'
        except Exception as e:
            checks['ai_client'] = f'unhealthy: {e}'
        
        # Check cache
        if self._cache:
            try:
                await self._cache.ping()
                checks['cache'] = 'healthy'
            except Exception as e:
                checks['cache'] = f'unhealthy: {e}'
        
        return {
            'service': 'FoodRecognitionService',
            'status': 'healthy' if all(
                v == 'healthy' for v in checks.values()
            ) else 'degraded',
            'checks': checks,
            'metrics': self.get_metrics(),
        }
```

**Endpoint:**
```python
@app.get("/health")
async def health():
    recognition_health = await recognition_service.health_check()
    persistence_health = await persistence_service.health_check()
    
    return {
        'status': 'healthy',
        'services': [recognition_health, persistence_health],
    }
```

---

## 📋 Quick Reference

### Service Checklist

When creating a new service, ensure:

- [ ] ✅ Constructor dependency injection
- [ ] ✅ All dependencies are interfaces (Protocol)
- [ ] ✅ Configuration object (no magic numbers)
- [ ] ✅ Timeout protection on external calls
- [ ] ✅ Retry logic for transient failures
- [ ] ✅ Caching for expensive operations
- [ ] ✅ Structured logging with context
- [ ] ✅ Metrics collection
- [ ] ✅ Typed exceptions
- [ ] ✅ Validation (fail-fast)
- [ ] ✅ Return result objects (not tuples)
- [ ] ✅ Health check method
- [ ] ✅ Test coverage >90%
- [ ] ✅ Docstrings with examples

### Testing Checklist

When testing a service:

- [ ] ✅ Test happy path
- [ ] ✅ Test validation errors
- [ ] ✅ Test external service errors
- [ ] ✅ Test timeout scenarios
- [ ] ✅ Test rate limit handling
- [ ] ✅ Test cache hits/misses
- [ ] ✅ Test idempotency
- [ ] ✅ Test transaction rollback
- [ ] ✅ Test batch operations
- [ ] ✅ Verify metrics updated
- [ ] ✅ Use shared fixtures
- [ ] ✅ Parametrize similar tests
- [ ] ✅ Mock at interface level
- [ ] ✅ Verify behavior, not just return values

### Performance Checklist

For performance-critical services:

- [ ] ✅ Cache expensive operations
- [ ] ✅ Batch database operations
- [ ] ✅ Use database indexes
- [ ] ✅ Parallelize independent operations
- [ ] ✅ Set appropriate timeouts
- [ ] ✅ Project only needed fields (queries)
- [ ] ✅ Monitor cache hit rate
- [ ] ✅ Profile hot paths
- [ ] ✅ Use async I/O throughout
- [ ] ✅ Avoid N+1 queries

### Robustness Checklist

For production-ready services:

- [ ] ✅ Typed exceptions (domain errors)
- [ ] ✅ Graceful degradation
- [ ] ✅ Circuit breaker (optional)
- [ ] ✅ Structured logging
- [ ] ✅ Health checks
- [ ] ✅ Metrics/observability
- [ ] ✅ Retry with backoff
- [ ] ✅ Idempotency keys
- [ ] ✅ Atomic transactions
- [ ] ✅ Validation at multiple layers

---

## 🎓 Summary

### Key Takeaways

1. **Dependency Injection**: Constructor injection with interfaces
2. **Testability**: 100% of services must be testable with mocks
3. **Performance**: Cache, batch, timeout, retry
4. **Robustness**: Typed errors, graceful degradation, circuit breakers
5. **Observability**: Structured logging, metrics, health checks
6. **Validation**: Fail-fast with clear error messages
7. **Persistence**: Repository pattern, transactions, idempotency
8. **Testing**: AAA pattern, >90% coverage, parametrize

### Anti-Patterns to Avoid

❌ Global imports (tight coupling)  
❌ Magic numbers (use config)  
❌ Generic exceptions (use typed)  
❌ N+1 queries (use batch)  
❌ No timeouts (can hang forever)  
❌ Swallowing errors (always re-raise or handle explicitly)  
❌ No validation (fail-late bugs)  
❌ Mutable state (thread-safety issues)  

---

**Follow these practices and your V2 services will be:**
- 🧪 **Testable**: 100% coverage
- ⚡ **Fast**: Caching, batching, indexing
- 🛡️ **Robust**: Error handling, retries, graceful degradation
- 📊 **Observable**: Metrics, logging, health checks
- 🔧 **Maintainable**: Clean architecture, clear boundaries

**Happy coding! 🚀**
