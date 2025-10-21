"""
Meal Analysis Orchestration Service.

Coordinates meal analysis from multiple sources with idempotency,
fallback strategies, and temporary storage.

Design Pattern: Service Layer + Dependency Injection + Strategy Pattern
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, cast, List

from backend.v2.domain.shared.value_objects import (
    UserId,
    AnalysisId,
    Barcode,
)
from backend.v2.domain.meal.orchestration.analysis_models import (
    MealAnalysis,
    MealAnalysisMetadata,
    AnalysisSource,
    AnalysisStatus,
)
from backend.v2.domain.meal.nutrition.models import NutrientProfile
from backend.v2.domain.meal.persistence.analysis_repository import (
    IMealAnalysisRepository,
)
from backend.v2.domain.meal.orchestration.ports import (
    IBarcodeEnrichmentService,
    IUSDAClient,
    IFoodRecognitionService,
)
from backend.v2.domain.meal.recognition.models import (
    RecognitionRequest,
    RecognitionStatus,
)


class MealAnalysisOrchestrator:
    """
    Orchestrates meal analysis from multiple sources.

    Responsibilities:
    - Coordinate analysis from photo AI, barcode scan, USDA search
    - Implement idempotency (reuse cached analyses)
    - Apply fallback strategies when primary source fails
    - Store temporary analyses with 24h TTL
    - Track performance metrics

    Dependencies (injected via Ports/Interfaces):
    - repository: IMealAnalysisRepository - Temporary storage with TTL
    - barcode_service: IBarcodeEnrichmentService - Barcode enrichment
    - usda_client: IUSDAClient - USDA FoodData Central API
    - food_recognition_service: IFoodRecognitionService - AI (optional)

    Design Pattern: Dependency Injection + Ports & Adapters
    The orchestrator depends on interfaces (ports), not concrete
    implementations. This enables loose coupling and easy testing.

    Example:
        >>> orchestrator = MealAnalysisOrchestrator(
        ...     repository=mongo_repo,
        ...     barcode_service=barcode_svc,
        ...     usda_client=usda_client,
        ... )
        >>> analysis = await orchestrator.analyze_from_barcode(
        ...     user_id=UserId(value="user123"),
        ...     barcode=Barcode(value="3017620422003"),
        ... )
        >>> print(f"{analysis.meal_name}: {analysis.nutrient_profile}")
    """

    def __init__(
        self,
        repository: IMealAnalysisRepository,
        barcode_service: IBarcodeEnrichmentService,
        usda_client: IUSDAClient,
        food_recognition_service: Optional[IFoodRecognitionService] = None,
    ):
        """
        Initialize orchestrator with dependencies.

        Args:
            repository: Analysis repository with TTL
            barcode_service: Barcode enrichment service
            usda_client: USDA API client
            food_recognition_service: AI food recognition service (optional)
        """
        self.repository = repository
        self.barcode_service = barcode_service
        self.usda_client = usda_client
        self.food_recognition_service = food_recognition_service

    async def analyze_from_barcode(
        self,
        user_id: UserId,
        barcode: Barcode,
        quantity_g: float = 100.0,
        analysis_id: Optional[AnalysisId] = None,
    ) -> MealAnalysis:
        """
        Analyze meal from barcode scan.

        Workflow:
        1. Check idempotency (analysis_id exists?)
        2. Call barcode enrichment service
        3. If not found → fallback to USDA search
        4. Store temporary analysis
        5. Return analysis

        Args:
            user_id: User performing analysis
            barcode: Product barcode
            quantity_g: Quantity in grams (default 100g)
            analysis_id: Optional ID for idempotency

        Returns:
            MealAnalysis with nutrient data

        Raises:
            ValueError: If barcode invalid or no data found

        Example:
            >>> analysis = await orchestrator.analyze_from_barcode(
            ...     user_id=UserId(value="user123"),
            ...     barcode=Barcode(value="3017620422003"),
            ...     quantity_g=150.0,
            ... )
        """
        # 1. Idempotency check
        if analysis_id and await self.repository.exists(analysis_id):
            cached = await self.repository.get_by_id(analysis_id)
            if cached:
                return cached

        # Generate ID if not provided
        if not analysis_id:
            analysis_id = AnalysisId.generate()

        # Track performance
        start_time = datetime.now(timezone.utc)

        # 2. Try barcode enrichment
        try:
            enriched = await self.barcode_service.enrich(barcode)

            # Extract nutrient profile
            nutrient_profile = NutrientProfile(
                calories=int(enriched.profile.calories),
                protein=enriched.profile.protein,
                carbs=enriched.profile.carbs,
                fat=enriched.profile.fat,
                fiber=enriched.profile.fiber,
                sugar=enriched.profile.sugar,
                sodium=enriched.profile.sodium,
                source=enriched.profile.source,
                confidence=enriched.quality.overall_score(),
                quantity_g=100.0,
            )

            # Create metadata
            time_delta = datetime.now(timezone.utc) - start_time
            processing_time = time_delta.total_seconds() * 1000

            metadata = MealAnalysisMetadata(
                source=AnalysisSource.BARCODE_SCAN,
                confidence=enriched.quality.overall_score(),
                processing_time_ms=int(processing_time),
                barcode_value=barcode.value,
            )

            # Create analysis
            analysis = MealAnalysis.create_new(
                user_id=user_id,
                meal_name=enriched.product_name or f"Product {barcode.value}",
                nutrient_profile=nutrient_profile,
                quantity_g=quantity_g,
                metadata=metadata,
                analysis_id=analysis_id,
            )

            # Store and return
            await self.repository.save(analysis)
            return analysis

        except Exception as e:
            # 3. Fallback to USDA search (if barcode not found)
            return await self._fallback_to_usda(
                user_id=user_id,
                search_query=barcode.value,
                quantity_g=quantity_g,
                analysis_id=analysis_id,
                fallback_reason=f"Barcode not found: {str(e)}",
            )

    async def analyze_from_usda_search(
        self,
        user_id: UserId,
        search_query: str,
        quantity_g: float = 100.0,
        analysis_id: Optional[AnalysisId] = None,
    ) -> MealAnalysis:
        """
        Analyze meal from USDA search.

        Args:
            user_id: User performing analysis
            search_query: Food search term (e.g., "banana")
            quantity_g: Quantity in grams
            analysis_id: Optional ID for idempotency

        Returns:
            MealAnalysis with USDA nutrient data

        Raises:
            ValueError: If no results found

        Example:
            >>> analysis = await orchestrator.analyze_from_usda_search(
            ...     user_id=UserId(value="user123"),
            ...     search_query="banana",
            ...     quantity_g=118.0,
            ... )
        """
        # 1. Idempotency check
        if analysis_id and await self.repository.exists(analysis_id):
            cached = await self.repository.get_by_id(analysis_id)
            if cached:
                return cached

        # Generate ID if not provided
        if not analysis_id:
            analysis_id = AnalysisId.generate()

        # Track performance
        start_time = datetime.now(timezone.utc)

        # 2. Search USDA
        results = await self.usda_client.search_foods(query=search_query, page_size=1)

        if not results.foods or len(results.foods) == 0:
            raise ValueError(f"No USDA results for: {search_query}")

        # Get first result
        food_item = results.foods[0]

        # Get detailed nutrients
        food_details = await self.usda_client.get_food(food_item.fdc_id)

        # Extract macros
        protein = 0.0
        carbs = 0.0
        fat = 0.0
        fiber = None
        sugar = None

        for nutrient in food_details.nutrients:
            name = nutrient.name.lower()
            if "protein" in name:
                protein = nutrient.amount
            elif "carbohydrate" in name and "by difference" in name:
                carbs = nutrient.amount
            elif "total lipid" in name or "fat" in name:
                fat = nutrient.amount
            elif "fiber" in name and "total dietary" in name:
                fiber = nutrient.amount
            elif "sugar" in name and "total" in name:
                sugar = nutrient.amount

        # Calculate calories (4-4-9 rule)
        calories = int((protein * 4) + (carbs * 4) + (fat * 9))

        # Create nutrient profile
        nutrient_profile = NutrientProfile(
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            fiber=fiber,
            sugar=sugar,
            sodium=None,
            source="USDA",
            confidence=0.95,
            quantity_g=100.0,
        )

        # Create metadata
        time_delta = datetime.now(timezone.utc) - start_time
        processing_time = time_delta.total_seconds() * 1000

        metadata = MealAnalysisMetadata(
            source=AnalysisSource.USDA_SEARCH,
            confidence=0.95,
            processing_time_ms=int(processing_time),
        )

        # Create analysis
        analysis = MealAnalysis.create_new(
            user_id=user_id,
            meal_name=food_item.description,
            nutrient_profile=nutrient_profile,
            quantity_g=quantity_g,
            metadata=metadata,
            analysis_id=analysis_id,
        )

        # Store and return
        await self.repository.save(analysis)
        return analysis

    async def get_analysis(self, analysis_id: AnalysisId) -> Optional[MealAnalysis]:
        """
        Retrieve existing analysis by ID.

        Args:
            analysis_id: Analysis identifier

        Returns:
            MealAnalysis if found and not expired, None otherwise

        Example:
            >>> analysis = await orchestrator.get_analysis(
            ...     AnalysisId(value="analysis_abc123def456")
            ... )
        """
        analysis = await self.repository.get_by_id(analysis_id)

        # Filter out expired
        if analysis and analysis.is_expired():
            return None

        return analysis

    async def get_recent_analyses(
        self,
        user_id: UserId,
        limit: int = 10,
    ) -> list[MealAnalysis]:
        """
        Get user's recent analyses.

        Args:
            user_id: User to fetch analyses for
            limit: Maximum number to return

        Returns:
            List of recent analyses (newest first)

        Example:
            >>> recent = await orchestrator.get_recent_analyses(
            ...     UserId(value="user123"),
            ...     limit=5,
            ... )
        """
        results = await self.repository.get_by_user(
            user_id=user_id,
            limit=limit,
            include_expired=False,
        )
        return cast(list[MealAnalysis], results)

    async def analyze_from_photo(
        self,
        user_id: UserId,
        image_url: str,
        dish_hint: Optional[str] = None,
        analysis_id: Optional[AnalysisId] = None,
    ) -> List[MealAnalysis]:
        """
        Analyze meal from photo using AI recognition.

        Workflow:
        1. Check idempotency (analysis_id exists?)
        2. Call AI recognition service
        3. For each recognized food:
           a. Search USDA for nutrients
           b. Create MealAnalysis
           c. Store with TTL
        4. Return list of analyses

        Args:
            user_id: User performing analysis
            image_url: URL to meal photo
            dish_hint: Optional hint for better recognition
            analysis_id: Optional ID for idempotency

        Returns:
            List of MealAnalysis (one per recognized food)

        Raises:
            ValueError: If recognition fails or service not configured

        Example:
            >>> analyses = await orchestrator.analyze_from_photo(
            ...     user_id=UserId(value="user123"),
            ...     image_url="https://example.com/pasta.jpg",
            ...     dish_hint="italian food",
            ... )
            >>> for analysis in analyses:
            ...     print(f"{analysis.meal_name}: {analysis.nutrient_profile}")
        """
        if not self.food_recognition_service:
            raise ValueError(
                "Food recognition service not configured. "
                "Pass FoodRecognitionService to orchestrator constructor."
            )

        # 1. Idempotency check
        if analysis_id and await self.repository.exists(analysis_id):
            cached = await self.repository.get_by_id(analysis_id)
            if cached:
                return [cached]

        # Generate ID if not provided
        if not analysis_id:
            analysis_id = AnalysisId.generate()

        # Track performance
        start_time = datetime.now(timezone.utc)

        # 2. Call AI recognition
        request = RecognitionRequest(
            image_url=image_url,
            user_id=user_id.value,
            dish_hint=dish_hint,
        )

        recognition_result = await self.food_recognition_service.recognize(request)

        # Check if recognition succeeded
        if recognition_result.status == RecognitionStatus.FAILED:
            raise ValueError(f"Food recognition failed: {recognition_result.raw_response}")

        # 3. Process each recognized food
        analyses: List[MealAnalysis] = []

        for item in recognition_result.items:
            try:
                # Search USDA for nutrients
                usda_results = await self.usda_client.search_foods(query=item.label, page_size=1)

                if not usda_results.foods or len(usda_results.foods) == 0:
                    continue

                # Get first result
                food_item = usda_results.foods[0]
                food_details = await self.usda_client.get_food(food_item.fdc_id)

                # Extract macros
                protein = 0.0
                carbs = 0.0
                fat = 0.0
                fiber = None
                sugar = None

                for nutrient in food_details.nutrients:
                    name = nutrient.name.lower()
                    if "protein" in name:
                        protein = nutrient.amount
                    elif "carbohydrate" in name and "by difference" in name:
                        carbs = nutrient.amount
                    elif "total lipid" in name or ("fat" in name and "total" in name):
                        fat = nutrient.amount
                    elif "fiber" in name:
                        fiber = nutrient.amount
                    elif "sugars" in name:
                        sugar = nutrient.amount

                # Calculate calories
                calories = int((protein * 4) + (carbs * 4) + (fat * 9))

                # Create nutrient profile
                nutrient_profile = NutrientProfile(
                    calories=calories,
                    protein=protein,
                    carbs=carbs,
                    fat=fat,
                    fiber=fiber,
                    sugar=sugar,
                    source="USDA",
                    confidence=item.confidence,
                    quantity_g=100.0,
                )

                # Create metadata
                time_delta = datetime.now(timezone.utc) - start_time
                processing_time = time_delta.total_seconds() * 1000

                metadata = MealAnalysisMetadata(
                    source=AnalysisSource.AI_VISION,
                    confidence=item.confidence,
                    processing_time_ms=int(processing_time),
                    ai_model_version="gpt-4o",
                    image_url=recognition_result.image_url or image_url,
                )

                # Create analysis
                item_analysis_id = (
                    analysis_id if len(recognition_result.items) == 1 else AnalysisId.generate()
                )

                analysis = MealAnalysis.create_new(
                    user_id=user_id,
                    meal_name=item.display_name,
                    nutrient_profile=nutrient_profile,
                    quantity_g=item.quantity_g,
                    metadata=metadata,
                    analysis_id=item_analysis_id,
                )

                # Store
                await self.repository.save(analysis)
                analyses.append(analysis)

            except Exception:
                # Skip items that fail USDA lookup
                continue

        if not analyses:
            raise ValueError("No USDA matches found for recognized foods")

        return analyses

    async def _fallback_to_usda(
        self,
        user_id: UserId,
        search_query: str,
        quantity_g: float,
        analysis_id: AnalysisId,
        fallback_reason: str,
    ) -> MealAnalysis:
        """
        Fallback to USDA when primary source fails.

        Args:
            user_id: User ID
            search_query: Query for USDA search
            quantity_g: Quantity in grams
            analysis_id: Analysis ID
            fallback_reason: Why fallback was triggered

        Returns:
            MealAnalysis from USDA

        Raises:
            ValueError: If USDA also fails
        """
        try:
            analysis = await self.analyze_from_usda_search(
                user_id=user_id,
                search_query=search_query,
                quantity_g=quantity_g,
                analysis_id=analysis_id,
            )

            # Update metadata with fallback info
            updated_metadata = MealAnalysisMetadata(
                source=analysis.metadata.source,
                confidence=analysis.metadata.confidence * 0.8,
                processing_time_ms=analysis.metadata.processing_time_ms,
                fallback_reason=fallback_reason,
            )

            updated_analysis = MealAnalysis(
                analysis_id=analysis.analysis_id,
                user_id=analysis.user_id,
                meal_name=analysis.meal_name,
                nutrient_profile=analysis.nutrient_profile,
                quantity_g=analysis.quantity_g,
                metadata=updated_metadata,
                status=AnalysisStatus.PARTIAL,
                created_at=analysis.created_at,
                expires_at=analysis.expires_at,
            )

            # Update in storage
            await self.repository.save(updated_analysis)
            return updated_analysis

        except Exception as e:
            # Both sources failed - create FAILED analysis
            metadata = MealAnalysisMetadata(
                source=AnalysisSource.BARCODE_SCAN,
                confidence=0.0,
                processing_time_ms=0,
                fallback_reason=f"{fallback_reason} | USDA failed: {str(e)}",
            )

            now = datetime.now(timezone.utc)
            failed_analysis = MealAnalysis(
                analysis_id=analysis_id,
                user_id=user_id,
                meal_name="Unknown Product",
                nutrient_profile=NutrientProfile(
                    calories=0,
                    protein=0.0,
                    carbs=0.0,
                    fat=0.0,
                    source="ESTIMATED",
                    confidence=0.0,
                    quantity_g=100.0,
                ),
                quantity_g=quantity_g,
                metadata=metadata,
                status=AnalysisStatus.FAILED,
                created_at=now,
                expires_at=now + timedelta(hours=1),  # Short TTL
            )

            await self.repository.save(failed_analysis)
            raise ValueError(f"All sources failed. Barcode: {fallback_reason}, " f"USDA: {str(e)}")
