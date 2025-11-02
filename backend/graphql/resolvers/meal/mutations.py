"""Mutation resolvers for meal domain.

These resolvers execute CQRS commands using Command Handlers from P4.1:
- analyzeMealPhoto: Analyze meal from photo
- analyzeMealText: Analyze meal from text description
- analyzeMealBarcode: Analyze meal from barcode
- confirmMealAnalysis: Confirm analysis (2-step process)
- updateMeal: Update existing meal
- deleteMeal: Soft delete meal
"""

from typing import Union, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
import strawberry

from application.meal.commands.analyze_photo import (
    AnalyzeMealPhotoCommand,
    AnalyzeMealPhotoCommandHandler,
)
from application.meal.commands.analyze_text import (
    AnalyzeMealTextCommand,
    AnalyzeMealTextCommandHandler,
)
from application.meal.commands.analyze_barcode import (
    AnalyzeMealBarcodeCommand,
    AnalyzeMealBarcodeCommandHandler,
)
from application.meal.commands.confirm_analysis import (
    ConfirmAnalysisCommand,
    ConfirmAnalysisCommandHandler,
)
from application.meal.commands.update_meal import (
    UpdateMealCommand,
    UpdateMealCommandHandler,
)
from application.meal.commands.delete_meal import (
    DeleteMealCommand,
    DeleteMealCommandHandler,
)
from graphql.types_meal_mutations import (
    AnalyzeMealPhotoInput,
    AnalyzeMealTextInput,
    AnalyzeMealBarcodeInput,
    ConfirmAnalysisInput,
    UpdateMealInput,
    DeleteMealInput,
    MealAnalysisSuccess,
    MealAnalysisError,
    ConfirmAnalysisSuccess,
    ConfirmAnalysisError,
    UpdateMealSuccess,
    UpdateMealError,
    DeleteMealSuccess,
    DeleteMealError,
)
from graphql.resolvers.meal.aggregate_queries import map_meal_to_graphql


@strawberry.type
class MealMutations:
    """Mutations for meal domain operations."""

    @strawberry.mutation
    async def analyze_meal_photo(
        self, info: strawberry.types.Info, input: AnalyzeMealPhotoInput
    ) -> Union[MealAnalysisSuccess, MealAnalysisError]:
        """Analyze meal from photo.

        Workflow:
        1. Photo → OpenAI recognition
        2. Labels → USDA enrichment
        3. Create Meal aggregate (PENDING state)
        4. Publish MealAnalyzed event
        5. Store in repository

        Args:
            info: Strawberry field info (injected)
            input: AnalyzeMealPhotoInput

        Returns:
            MealAnalysisSuccess or MealAnalysisError

        Example:
            mutation {
              analyzeMealPhoto(input: {
                userId: "user123"
                photoUrl: "https://..."
                dishHint: "pasta"
              }) {
                ... on MealAnalysisSuccess {
                  meal { id, entries { name, calories } }
                }
                ... on MealAnalysisError {
                  message, code
                }
              }
            }
        """
        context = info.context
        orchestrator = context.get("photo_orchestrator")
        repository = context.get("meal_repository")
        event_bus = context.get("event_bus")
        idempotency_cache = context.get("idempotency_cache")

        if not all([orchestrator, repository, event_bus, idempotency_cache]):
            return MealAnalysisError(
                message="Required services not available in context",
                code="SERVICE_UNAVAILABLE",
            )

        try:
            # Map GraphQL input → Command
            command = AnalyzeMealPhotoCommand(
                user_id=input.user_id,
                photo_url=input.photo_url,
                dish_hint=input.dish_hint,
                meal_type=input.meal_type.value,
                timestamp=input.timestamp or datetime.now(timezone.utc),
                idempotency_key=input.idempotency_key,
            )

            # Execute command via handler
            handler = AnalyzeMealPhotoCommandHandler(
                orchestrator=orchestrator,
                repository=repository,
                event_bus=event_bus,
                idempotency_cache=idempotency_cache,
            )

            meal = await handler.handle(command)

            # Map domain entity → GraphQL type
            return MealAnalysisSuccess(
                meal=map_meal_to_graphql(meal),
                analysis_id=meal.analysis_id if hasattr(meal, "analysis_id") else None,
            )

        except ValueError as e:
            return MealAnalysisError(message=str(e), code="VALIDATION_ERROR")
        except Exception as e:
            return MealAnalysisError(message=f"Analysis failed: {str(e)}", code="ANALYSIS_FAILED")

    @strawberry.mutation
    async def analyze_meal_text(
        self, info: strawberry.types.Info, input: AnalyzeMealTextInput
    ) -> Union[MealAnalysisSuccess, MealAnalysisError]:
        """Analyze meal from text description.

        Workflow:
        1. Text → OpenAI recognition
        2. Labels → USDA enrichment
        3. Create Meal aggregate (PENDING state)
        4. Publish MealAnalyzed event
        5. Store in repository

        Args:
            info: Strawberry field info (injected)
            input: AnalyzeMealTextInput

        Returns:
            MealAnalysisSuccess or MealAnalysisError

        Example:
            mutation {
              analyzeMealText(input: {
                userId: "user123"
                textDescription: "150g pasta with tomato sauce"
              }) {
                ... on MealAnalysisSuccess {
                  meal { id, entries { name, calories } }
                }
                ... on MealAnalysisError {
                  message, code
                }
              }
            }
        """
        context = info.context
        orchestrator = context.get("meal_orchestrator")
        repository = context.get("meal_repository")
        event_bus = context.get("event_bus")
        idempotency_cache = context.get("idempotency_cache")

        if not all([orchestrator, repository, event_bus, idempotency_cache]):
            return MealAnalysisError(
                message="Required services not available in context",
                code="SERVICE_UNAVAILABLE",
            )

        try:
            # Map GraphQL input → Command
            command = AnalyzeMealTextCommand(
                user_id=input.user_id,
                text_description=input.text_description,
                meal_type=input.meal_type.value,
                timestamp=input.timestamp or datetime.now(timezone.utc),
                idempotency_key=input.idempotency_key,
            )

            # Execute command via handler
            handler = AnalyzeMealTextCommandHandler(
                orchestrator=orchestrator,
                repository=repository,
                event_bus=event_bus,
                idempotency_cache=idempotency_cache,
            )

            meal = await handler.handle(command)

            # Map domain entity → GraphQL type
            return MealAnalysisSuccess(
                meal=map_meal_to_graphql(meal),
                analysis_id=meal.analysis_id if hasattr(meal, "analysis_id") else None,
            )

        except ValueError as e:
            return MealAnalysisError(message=str(e), code="VALIDATION_ERROR")
        except Exception as e:
            return MealAnalysisError(message=f"Analysis failed: {str(e)}", code="ANALYSIS_FAILED")

    @strawberry.mutation
    async def analyze_meal_barcode(
        self, info: strawberry.types.Info, input: AnalyzeMealBarcodeInput
    ) -> Union[MealAnalysisSuccess, MealAnalysisError]:
        """Analyze meal from barcode.

        Workflow:
        1. Barcode → OpenFoodFacts lookup
        2. Product → USDA enrichment (if needed)
        3. Scale nutrients to quantity
        4. Create Meal aggregate
        5. Publish MealAnalyzed event

        Args:
            info: Strawberry field info (injected)
            input: AnalyzeMealBarcodeInput

        Returns:
            MealAnalysisSuccess or MealAnalysisError
        """
        context = info.context
        orchestrator = context.get("barcode_orchestrator")
        repository = context.get("meal_repository")
        event_bus = context.get("event_bus")
        idempotency_cache = context.get("idempotency_cache")

        if not all([orchestrator, repository, event_bus, idempotency_cache]):
            return MealAnalysisError(
                message="Required services not available",
                code="SERVICE_UNAVAILABLE",
            )

        try:
            # Map GraphQL input → Command
            command = AnalyzeMealBarcodeCommand(
                user_id=input.user_id,
                barcode=input.barcode,
                quantity_g=input.quantity_g,
                meal_type=input.meal_type.value,
                timestamp=input.timestamp or datetime.now(timezone.utc),
                idempotency_key=input.idempotency_key,
            )

            # Execute command via handler
            handler = AnalyzeMealBarcodeCommandHandler(
                orchestrator=orchestrator,
                repository=repository,
                event_bus=event_bus,
                idempotency_cache=idempotency_cache,
            )

            meal = await handler.handle(command)

            return MealAnalysisSuccess(
                meal=map_meal_to_graphql(meal),
                analysis_id=meal.analysis_id if hasattr(meal, "analysis_id") else None,
            )

        except ValueError as e:
            return MealAnalysisError(message=str(e), code="BARCODE_NOT_FOUND")
        except Exception as e:
            return MealAnalysisError(
                message=f"Barcode analysis failed: {str(e)}",
                code="ANALYSIS_FAILED",
            )

    @strawberry.mutation
    async def confirm_meal_analysis(
        self, info: strawberry.types.Info, input: ConfirmAnalysisInput
    ) -> Union[ConfirmAnalysisSuccess, ConfirmAnalysisError]:
        """Confirm meal analysis (2-step process).

        User reviews AI-analyzed entries and confirms which to keep.

        Workflow:
        1. Get PENDING meal by ID
        2. Filter entries by confirmed IDs
        3. Mark meal as CONFIRMED
        4. Update totals
        5. Publish MealConfirmed event

        Args:
            info: Strawberry field info (injected)
            input: ConfirmAnalysisInput

        Returns:
            ConfirmAnalysisSuccess or ConfirmAnalysisError
        """
        context = info.context
        repository = context.get("meal_repository")
        event_bus = context.get("event_bus")

        if not all([repository, event_bus]):
            return ConfirmAnalysisError(
                message="Required services not available",
                code="SERVICE_UNAVAILABLE",
            )

        try:
            # Map GraphQL input → Command
            command = ConfirmAnalysisCommand(
                meal_id=UUID(input.meal_id),
                user_id=input.user_id,
                confirmed_entry_ids=[UUID(eid) for eid in input.confirmed_entry_ids],
            )

            # Execute command via handler
            handler = ConfirmAnalysisCommandHandler(repository=repository, event_bus=event_bus)

            meal = await handler.handle(command)

            # Calculate counts
            confirmed_count = len(input.confirmed_entry_ids)
            # Assume original meal had more entries
            # (would need original meal to calculate)
            rejected_count = 0

            return ConfirmAnalysisSuccess(
                meal=map_meal_to_graphql(meal),
                confirmed_count=confirmed_count,
                rejected_count=rejected_count,
            )

        except ValueError as e:
            return ConfirmAnalysisError(message=str(e), code="MEAL_NOT_FOUND")
        except Exception as e:
            return ConfirmAnalysisError(
                message=f"Confirmation failed: {str(e)}",
                code="CONFIRMATION_FAILED",
            )

    @strawberry.mutation
    async def update_meal(
        self, info: strawberry.types.Info, input: UpdateMealInput
    ) -> Union[UpdateMealSuccess, UpdateMealError]:
        """Update existing meal.

        Allowed updates: meal_type, timestamp, notes

        Args:
            info: Strawberry field info (injected)
            input: UpdateMealInput

        Returns:
            UpdateMealSuccess or UpdateMealError
        """
        context = info.context
        repository = context.get("meal_repository")
        event_bus = context.get("event_bus")

        if not all([repository, event_bus]):
            return UpdateMealError(
                message="Required services not available",
                code="SERVICE_UNAVAILABLE",
            )

        try:
            # Map GraphQL input → Command
            # Build updates dict from provided fields
            updates: Dict[str, Any] = {}
            if input.meal_type is not None:
                updates["meal_type"] = input.meal_type.value
            if input.timestamp is not None:
                updates["timestamp"] = input.timestamp
            if input.notes is not None:
                updates["notes"] = input.notes

            command = UpdateMealCommand(
                meal_id=UUID(input.meal_id),
                user_id=input.user_id,
                updates=updates,
            )

            # Execute command via handler
            handler = UpdateMealCommandHandler(repository=repository, event_bus=event_bus)

            meal = await handler.handle(command)

            return UpdateMealSuccess(meal=map_meal_to_graphql(meal))

        except ValueError as e:
            # Distinguish between validation errors and not found errors
            error_msg = str(e)
            if "at least one entry" in error_msg or "invariant" in error_msg.lower():
                code = "VALIDATION_ERROR"
            else:
                code = "MEAL_NOT_FOUND"
            return UpdateMealError(message=error_msg, code=code)
        except Exception as e:
            return UpdateMealError(message=f"Update failed: {str(e)}", code="UPDATE_FAILED")

    @strawberry.mutation
    async def delete_meal(
        self, info: strawberry.types.Info, input: DeleteMealInput
    ) -> Union[DeleteMealSuccess, DeleteMealError]:
        """Delete meal (soft delete).

        Args:
            info: Strawberry field info (injected)
            input: DeleteMealInput

        Returns:
            DeleteMealSuccess or DeleteMealError
        """
        context = info.context
        repository = context.get("meal_repository")
        event_bus = context.get("event_bus")

        if not all([repository, event_bus]):
            return DeleteMealError(
                message="Required services not available",
                code="SERVICE_UNAVAILABLE",
            )

        try:
            # Map GraphQL input → Command
            command = DeleteMealCommand(meal_id=UUID(input.meal_id), user_id=input.user_id)

            # Execute command via handler
            handler = DeleteMealCommandHandler(repository=repository, event_bus=event_bus)

            await handler.handle(command)

            return DeleteMealSuccess(meal_id=input.meal_id, message="Meal deleted successfully")

        except ValueError as e:
            return DeleteMealError(message=str(e), code="MEAL_NOT_FOUND")
        except Exception as e:
            return DeleteMealError(message=f"Delete failed: {str(e)}", code="DELETE_FAILED")
