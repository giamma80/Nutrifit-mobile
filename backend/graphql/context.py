"""GraphQL context factory for dependency injection.

Provides all required dependencies for GraphQL resolvers:
- Repositories (meal storage)
- Event bus (domain events)
- Orchestrators (complex workflows)
- Services (external integrations)
- Caches (idempotency, results)
"""

from typing import Any
from dataclasses import dataclass

from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus
from domain.shared.ports.idempotency_cache import IIdempotencyCache
from application.meal.orchestrators.photo_orchestrator import PhotoOrchestrator
from application.meal.orchestrators.barcode_orchestrator import BarcodeOrchestrator
from domain.meal.ports.recognition_service import IVisionProvider
from domain.meal.ports.enrichment_service import INutritionProvider
from domain.meal.ports.barcode_service import IBarcodeProvider


@dataclass
class GraphQLContext:
    """GraphQL context with all dependencies.

    This context is injected into all GraphQL resolvers via the `info` parameter.
    Resolvers access dependencies using `info.context.get("service_name")`.

    Attributes:
        meal_repository: Repository for meal persistence
        event_bus: Event bus for domain events
        idempotency_cache: Cache for idempotent command processing
        photo_orchestrator: Orchestrator for photo analysis workflow
        barcode_orchestrator: Orchestrator for barcode analysis workflow
        recognition_service: Vision provider (OpenAI GPT-4V)
        enrichment_service: Nutrition provider (USDA)
        barcode_service: Barcode provider (OpenFoodFacts)
    """

    meal_repository: IMealRepository
    event_bus: IEventBus
    idempotency_cache: IIdempotencyCache
    photo_orchestrator: PhotoOrchestrator
    barcode_orchestrator: BarcodeOrchestrator
    recognition_service: IVisionProvider
    enrichment_service: INutritionProvider
    barcode_service: IBarcodeProvider

    def get(self, key: str) -> Any:
        """Get dependency by name (for resolver compatibility).

        Args:
            key: Dependency name (e.g., "meal_repository")

        Returns:
            Dependency instance or None if not found

        Example:
            >>> context = info.context
            >>> repository = context.get("meal_repository")
        """
        return getattr(self, key, None)


def create_context(
    meal_repository: IMealRepository,
    event_bus: IEventBus,
    idempotency_cache: IIdempotencyCache,
    photo_orchestrator: PhotoOrchestrator,
    barcode_orchestrator: BarcodeOrchestrator,
    recognition_service: IVisionProvider,
    enrichment_service: INutritionProvider,
    barcode_service: IBarcodeProvider,
) -> GraphQLContext:
    """Create GraphQL context with all dependencies.

    Args:
        meal_repository: Repository implementation
        event_bus: Event bus implementation
        idempotency_cache: Idempotency cache implementation
        photo_orchestrator: Photo orchestrator instance
        barcode_orchestrator: Barcode orchestrator instance
        recognition_service: Vision provider implementation
        enrichment_service: Nutrition provider implementation
        barcode_service: Barcode provider implementation

    Returns:
        GraphQLContext with all dependencies

    Example:
        >>> from graphql.context import create_context
        >>> context = create_context(
        ...     meal_repository=InMemoryMealRepository(),
        ...     event_bus=InMemoryEventBus(),
        ...     # ... other dependencies
        ... )
    """
    return GraphQLContext(
        meal_repository=meal_repository,
        event_bus=event_bus,
        idempotency_cache=idempotency_cache,
        photo_orchestrator=photo_orchestrator,
        barcode_orchestrator=barcode_orchestrator,
        recognition_service=recognition_service,
        enrichment_service=enrichment_service,
        barcode_service=barcode_service,
    )
