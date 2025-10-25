"""Atomic query resolvers for meal domain.

These resolvers test individual capabilities in isolation:
- recognizeFood: Test IVisionProvider (OpenAI recognition)
- enrichNutrients: Test INutritionProvider (USDA enrichment)
- searchFoodByBarcode: Test IBarcodeProvider (OpenFoodFacts lookup)

Strategy: Start with atomic queries BEFORE building complex operations.
"""

from typing import Optional
import strawberry

from application.meal.queries.recognize_food import (
    RecognizeFoodQuery,
    RecognizeFoodQueryHandler,
)
from application.meal.queries.enrich_nutrients import (
    EnrichNutrientsQuery,
    EnrichNutrientsQueryHandler,
)
from application.meal.queries.search_food_by_barcode import (
    SearchFoodByBarcodeQuery,
    SearchFoodByBarcodeQueryHandler,
)
from graphql.types_meal_new import (
    FoodRecognitionResult,
    RecognizedFood,
    NutrientProfile,
    BarcodeProduct,
)


@strawberry.type
class AtomicQueries:
    """Atomic utility queries for testing individual capabilities."""

    @strawberry.field
    async def recognize_food(
        self,
        info: strawberry.types.Info,
        photo_url: Optional[str] = None,
        text: Optional[str] = None,
        dish_hint: Optional[str] = None,
    ) -> FoodRecognitionResult:
        """Recognize food from photo or text (atomic utility query).

        Tests IVisionProvider capability in isolation.

        Args:
            info: Strawberry field info (injected)
            photo_url: URL of food photo (mutually exclusive with text)
            text: Text description of meal (mutually exclusive with photo_url)
            dish_hint: Optional hint about the dish

        Returns:
            FoodRecognitionResult with recognized items

        Example:
            query {
              recognizeFood(photoUrl: "https://...") {
                items { label, displayName, quantityG, confidence }
                averageConfidence
                itemCount
              }
            }
        """
        # Get dependencies from Strawberry context
        context = info.context
        recognition_service = context.get("recognition_service")

        if not recognition_service:
            raise ValueError("RecognitionService not available in context")

        # Create query
        query = RecognizeFoodQuery(
            photo_url=photo_url, text=text, dish_hint=dish_hint
        )

        # Execute via handler
        handler = RecognizeFoodQueryHandler(recognition_service=recognition_service)
        result = await handler.handle(query)

        # Map domain entity → GraphQL type
        items = [
            RecognizedFood(
                label=item.label,
                display_name=item.display_name,
                quantity_g=item.quantity_g,
                confidence=item.confidence,
            )
            for item in result.items
        ]

        return FoodRecognitionResult(
            items=items,
            average_confidence=result.average_confidence,  # type: ignore[attr-defined]
        )

    @strawberry.field
    async def enrich_nutrients(
        self, info: strawberry.types.Info, label: str, quantity_g: float
    ) -> Optional[NutrientProfile]:
        """Enrich nutrients from USDA (atomic utility query).

        Tests INutritionProvider capability with cascade strategy:
        USDA → Category → Fallback

        Args:
            info: Strawberry field info (injected)
            label: Food label (e.g., "roasted_chicken")
            quantity_g: Quantity in grams

        Returns:
            NutrientProfile or None if enrichment fails

        Example:
            query {
              enrichNutrients(label: "banana", quantityG: 120) {
                calories, protein, carbs, fat
                isHighQuality
              }
            }
        """
        context = info.context
        enrichment_service = context.get("enrichment_service")

        if not enrichment_service:
            raise ValueError("EnrichmentService not available in context")

        # Create query
        query = EnrichNutrientsQuery(food_label=label, quantity_g=quantity_g)

        # Execute via handler
        handler = EnrichNutrientsQueryHandler(enrichment_service=enrichment_service)
        profile = await handler.handle(query)

        if not profile:
            return None

        # Map domain entity → GraphQL type
        return NutrientProfile(
            calories=profile.calories,
            protein=profile.protein,
            carbs=profile.carbs,
            fat=profile.fat,
            fiber=profile.fiber,
            sugar=profile.sugar,
            sodium=profile.sodium,
            quantity_g=profile.quantity_g,
        )

    @strawberry.field
    async def search_food_by_barcode(
        self, info: strawberry.types.Info, barcode: str
    ) -> Optional[BarcodeProduct]:
        """Lookup product by barcode (atomic utility query).

        Tests IBarcodeProvider capability (OpenFoodFacts integration).

        Args:
            info: Strawberry field info (injected)
            barcode: Product barcode (EAN/UPC)

        Returns:
            BarcodeProduct or None if not found

        Example:
            query {
              searchFoodByBarcode(barcode: "8001505005707") {
                name, brand, displayName
                nutrients { calories, protein }
                hasImage
              }
            }
        """
        context = info.context
        barcode_service = context.get("barcode_service")

        if not barcode_service:
            raise ValueError("BarcodeService not available in context")

        # Create query
        query = SearchFoodByBarcodeQuery(barcode=barcode)

        # Execute via handler
        handler = SearchFoodByBarcodeQueryHandler(barcode_service=barcode_service)

        try:
            product = await handler.handle(query)
        except ValueError:
            # Barcode not found
            return None

        # Map nutrients if present
        nutrients = None
        if product.nutrients:
            nutrients = NutrientProfile(
                calories=product.nutrients.calories,
                protein=product.nutrients.protein,
                carbs=product.nutrients.carbs,
                fat=product.nutrients.fat,
                fiber=product.nutrients.fiber,
                sugar=product.nutrients.sugar,
                sodium=product.nutrients.sodium,
                quantity_g=product.serving_size_g or 100.0,
            )

        # Map domain entity → GraphQL type
        return BarcodeProduct(
            barcode=product.barcode,
            name=product.name,
            brand=product.brand,
            nutrients=nutrients,
            serving_size_g=product.serving_size_g,
            image_url=product.image_url,
        )
