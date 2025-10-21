"""
Ports (Interfaces) for Meal Orchestration Dependencies.

Defines abstract interfaces for external services used by the
MealAnalysisOrchestrator. This enables true dependency inversion
and loose coupling between application and infrastructure layers.

Design Pattern: Ports & Adapters (Hexagonal Architecture)
"""

from typing import Protocol, runtime_checkable

from backend.v2.domain.shared.value_objects import Barcode
from backend.v2.domain.meal.recognition.models import (
    RecognitionRequest,
    FoodRecognitionResult,
)


@runtime_checkable
class IBarcodeEnrichmentService(Protocol):
    """
    Port for barcode enrichment service.

    Orchestrates barcode lookup across multiple data sources
    (USDA, OpenFoodFacts) and returns enriched product data.

    This is an interface - implementations may use different
    data sources or enrichment strategies.
    """

    async def enrich(self, barcode: Barcode) -> "BarcodeEnrichmentResult":
        """
        Enrich product information from barcode.

        Args:
            barcode: Product barcode to lookup

        Returns:
            BarcodeEnrichmentResult with nutrient profile and metadata

        Raises:
            BarcodeNotFoundError: If barcode not found in any source
        """
        ...


@runtime_checkable
class IUSDAClient(Protocol):
    """
    Port for USDA FoodData Central API client.

    Provides access to USDA's comprehensive food database
    for nutrient information lookup.

    This is an interface - implementations may use different
    USDA API versions or caching strategies.
    """

    async def search_foods(self, query: str, page_size: int = 25) -> "USDASearchResult":
        """
        Search USDA food database.

        Args:
            query: Search term (e.g., "banana", "chicken breast")
            page_size: Maximum results to return

        Returns:
            USDASearchResult with list of matching foods

        Raises:
            ValueError: If search fails or no results found
        """
        ...

    async def get_food(self, fdc_id: str) -> "USDAFoodItem":
        """
        Get detailed food information by FDC ID.

        Args:
            fdc_id: USDA FoodData Central ID

        Returns:
            USDAFoodItem with complete nutrient data

        Raises:
            ValueError: If food not found
        """
        ...


@runtime_checkable
class IFoodRecognitionService(Protocol):
    """
    Port for AI-powered food recognition service.

    Uses computer vision to identify foods from photos
    and estimate quantities.

    This is an interface - implementations may use different
    AI models (OpenAI, Google Vision, custom models).
    """

    async def recognize(self, request: RecognitionRequest) -> FoodRecognitionResult:
        """
        Recognize foods from photo.

        Args:
            request: Recognition request with image and metadata

        Returns:
            FoodRecognitionResult with identified items and confidence

        Raises:
            ValueError: If recognition fails
        """
        ...


# Re-export result types for convenience (they're already in domain)
# These are imported to keep the port interface self-contained
try:
    from backend.v2.application.barcode.enrichment_service import (
        BarcodeEnrichmentResult,
    )
    from backend.v2.domain.meal.nutrition.usda_models import (
        USDASearchResult,
        USDAFoodItem,
    )
except ImportError:
    # Types available at runtime but not required for Protocol definition
    pass
