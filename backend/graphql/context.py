"""GraphQL context factory for dependency injection.

Provides all required dependencies for GraphQL resolvers:
- Repositories (meal storage)
- Event bus (domain events)
- Orchestrators (complex workflows)
- Services (external integrations)
- Caches (idempotency, results)
"""

from typing import Any, Optional, Dict
from strawberry.fastapi import BaseContext
from fastapi import Request

from domain.shared.ports.meal_repository import IMealRepository
from domain.shared.ports.event_bus import IEventBus
from domain.shared.ports.idempotency_cache import IIdempotencyCache
from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)
from domain.user.core.ports.user_repository import IUserRepository
from application.meal.orchestrators.photo_orchestrator import (
    MealAnalysisOrchestrator,
    PhotoOrchestrator,
)
from application.meal.orchestrators.barcode_orchestrator import BarcodeOrchestrator
from application.nutritional_profile.orchestrators.profile_orchestrator import (
    ProfileOrchestrator,
)
from domain.meal.recognition.services.recognition_service import (
    FoodRecognitionService,
)
from domain.meal.nutrition.services.enrichment_service import (
    NutritionEnrichmentService,
)
from domain.meal.barcode.services.barcode_service import BarcodeService


class GraphQLContext(BaseContext):
    """GraphQL context with all dependencies.

    This context is injected into all GraphQL resolvers via the
    `info` parameter. Resolvers access dependencies using
    `info.context.get("service_name")`.

    Attributes:
        meal_repository: Repository for meal persistence
        profile_repository: Repository for nutritional profile persistence
        user_repository: Repository for user data
        event_bus: Event bus for domain events
        idempotency_cache: Cache for idempotent command processing
        photo_orchestrator: Orchestrator for photo analysis workflow
        barcode_orchestrator: Orchestrator for barcode analysis workflow
        profile_orchestrator: Orchestrator for profile calculations
        recognition_service: Vision provider (OpenAI GPT-4V)
        enrichment_service: Nutrition enrichment service (wraps USDA)
        barcode_service: Barcode lookup service
        request: FastAPI request object (for accessing auth_claims from middleware)
        auth_claims: JWT claims from Auth0 middleware (None if not authenticated)
    """

    def __init__(
        self,
        meal_repository: IMealRepository,
        profile_repository: IProfileRepository,
        user_repository: IUserRepository,
        event_bus: IEventBus,
        idempotency_cache: IIdempotencyCache,
        photo_orchestrator: PhotoOrchestrator,
        barcode_orchestrator: BarcodeOrchestrator,
        profile_orchestrator: ProfileOrchestrator,
        recognition_service: FoodRecognitionService,
        enrichment_service: NutritionEnrichmentService,
        barcode_service: BarcodeService,
        meal_orchestrator: "MealAnalysisOrchestrator | None" = None,
        request: Optional[Request] = None,
    ) -> None:
        """Initialize GraphQL context with all dependencies."""
        super().__init__()
        self.meal_repository = meal_repository
        self.profile_repository = profile_repository
        self.user_repository = user_repository
        self.event_bus = event_bus
        self.idempotency_cache = idempotency_cache
        self.photo_orchestrator = photo_orchestrator
        self.meal_orchestrator = meal_orchestrator if meal_orchestrator else photo_orchestrator
        self.barcode_orchestrator = barcode_orchestrator
        self.profile_orchestrator = profile_orchestrator
        self.recognition_service = recognition_service
        self.enrichment_service = enrichment_service
        self.barcode_service = barcode_service
        self.request = request
        # Extract auth_claims from request.state if available
        self.auth_claims: Optional[Dict[str, Any]] = (
            getattr(request.state, "auth_claims", None) if request else None
        )

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
    profile_repository: IProfileRepository,
    user_repository: IUserRepository,
    event_bus: IEventBus,
    idempotency_cache: IIdempotencyCache,
    photo_orchestrator: PhotoOrchestrator,
    barcode_orchestrator: BarcodeOrchestrator,
    profile_orchestrator: ProfileOrchestrator,
    recognition_service: "FoodRecognitionService",
    enrichment_service: NutritionEnrichmentService,
    barcode_service: BarcodeService,
    meal_orchestrator: "MealAnalysisOrchestrator | None" = None,
    request: Optional[Request] = None,
) -> GraphQLContext:
    """Create GraphQL context with all dependencies.

    Args:
        meal_repository: Repository implementation
        profile_repository: Profile repository implementation
        user_repository: User repository implementation
        event_bus: Event bus implementation
        idempotency_cache: Idempotency cache implementation
        photo_orchestrator: Photo orchestrator instance
        barcode_orchestrator: Barcode orchestrator instance
        profile_orchestrator: Profile orchestrator instance
        recognition_service: Vision provider implementation
        enrichment_service: Nutrition enrichment service (domain service)
        barcode_service: Barcode service implementation
        meal_orchestrator: Meal analysis orchestrator (supports photo/text)

    Returns:
        GraphQLContext with all dependencies

    Example:
        >>> from graphql.context import create_context
        >>> context = create_context(
        ...     meal_repository=InMemoryMealRepository(),
        ...     profile_repository=InMemoryProfileRepository(),
        ...     user_repository=InMemoryUserRepository(),
        ...     event_bus=InMemoryEventBus(),
        ...     # ... other dependencies
        ... )
    """
    # Use meal_orchestrator if provided, else fall back to photo_orchestrator
    actual_meal_orchestrator = (
        meal_orchestrator if meal_orchestrator is not None else photo_orchestrator
    )

    ctx = GraphQLContext(
        meal_repository=meal_repository,
        profile_repository=profile_repository,
        user_repository=user_repository,
        event_bus=event_bus,
        idempotency_cache=idempotency_cache,
        photo_orchestrator=photo_orchestrator,
        meal_orchestrator=actual_meal_orchestrator,
        barcode_orchestrator=barcode_orchestrator,
        profile_orchestrator=profile_orchestrator,
        recognition_service=recognition_service,
        enrichment_service=enrichment_service,
        barcode_service=barcode_service,
        request=request,
    )
    return ctx
