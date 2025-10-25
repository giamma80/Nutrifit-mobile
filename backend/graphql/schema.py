"""Main GraphQL schema for Nutrifit backend.

Integrates CQRS query and mutation resolvers for the meal domain:
- AtomicQueries: Atomic utility queries for testing capabilities in isolation
- AggregateQueries: Aggregate queries for meal data operations
- MealMutations: Commands for meal creation, updates, and deletes

Context Dependencies:
- meal_repository: IMealRepository implementation
- event_bus: IEventBus implementation
- idempotency_cache: IIdempotencyCache implementation
- photo_orchestrator: PhotoOrchestrator instance
- barcode_orchestrator: BarcodeOrchestrator instance
- recognition_service: IVisionProvider implementation
- enrichment_service: INutritionProvider implementation
- barcode_service: IBarcodeProvider implementation
"""

import strawberry

from graphql.resolvers.meal.atomic_queries import AtomicQueries
from graphql.resolvers.meal.aggregate_queries import AggregateQueries
from graphql.resolvers.meal.mutations import MealMutations


@strawberry.type
class Query:
    """Root query type combining all query resolvers."""

    # Atomic queries (testing capabilities in isolation)
    @strawberry.field
    def atomic(self) -> AtomicQueries:
        """Atomic utility queries for testing individual capabilities.

        Returns:
            AtomicQueries resolver instance

        Example:
            query {
              atomic {
                recognizeFood(photoUrl: "https://...") {
                  items { label, displayName, confidence }
                }
              }
            }
        """
        return AtomicQueries()

    # Aggregate queries (meal data operations)
    @strawberry.field
    def meals(self) -> AggregateQueries:
        """Aggregate queries for meal data operations.

        Returns:
            AggregateQueries resolver instance

        Example:
            query {
              meals {
                meal(mealId: "...", userId: "user123") {
                  id, timestamp, totalCalories
                }
              }
            }
        """
        return AggregateQueries()


@strawberry.type
class Mutation:
    """Root mutation type combining all mutation resolvers."""

    # Meal mutations (commands)
    @strawberry.field
    def meal(self) -> MealMutations:
        """Meal domain mutations (CQRS commands).

        Returns:
            MealMutations resolver instance

        Example:
            mutation {
              meal {
                analyzeMealPhoto(input: {...}) {
                  ... on MealAnalysisSuccess {
                    meal { id, entries { name, calories } }
                  }
                  ... on MealAnalysisError {
                    message, code
                  }
                }
              }
            }
        """
        return MealMutations()


def create_schema() -> strawberry.Schema:
    """Create Strawberry schema with integrated resolvers.

    Returns:
        Configured Strawberry Schema instance
    """
    return strawberry.Schema(
        query=Query,
        mutation=Mutation,
    )
