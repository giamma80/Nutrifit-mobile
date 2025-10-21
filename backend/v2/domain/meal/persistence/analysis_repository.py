"""
Meal analysis repository interface.

Protocol for temporary meal analysis storage with 24h TTL.
"""

from typing import Protocol, Optional, runtime_checkable

from backend.v2.domain.shared.value_objects import UserId, AnalysisId, MealId
from backend.v2.domain.meal.orchestration.analysis_models import MealAnalysis


@runtime_checkable
class IMealAnalysisRepository(Protocol):
    """
    Repository interface for temporary meal analyses.

    Implementations must provide:
    - Temporary storage with 24h TTL (auto-expiration)
    - Idempotency support (analysis_id uniqueness)
    - User-scoped queries
    - Conversion tracking

    Design Pattern: Repository Pattern + Protocol (Dependency Injection)

    Example:
        >>> repository = MealAnalysisRepositoryMongo(db)
        >>> await repository.save(analysis)
        >>> retrieved = await repository.get_by_id(analysis.analysis_id)
        >>> assert retrieved == analysis
    """

    async def save(self, analysis: MealAnalysis) -> None:
        """
        Save or update meal analysis.

        Implements upsert semantics:
        - If analysis_id exists → update
        - If analysis_id new → insert

        Args:
            analysis: MealAnalysis to save

        Raises:
            RepositoryError: On storage failure

        Example:
            >>> await repository.save(analysis)
        """
        ...

    async def get_by_id(self, analysis_id: AnalysisId) -> Optional[MealAnalysis]:
        """
        Retrieve analysis by ID.

        Args:
            analysis_id: Unique analysis identifier

        Returns:
            MealAnalysis if found, None otherwise

        Example:
            >>> analysis = await repository.get_by_id(
            ...     AnalysisId(value="analysis_abc123def456")
            ... )
            >>> if analysis:
            ...     print(analysis.meal_name)
        """
        ...

    async def get_by_user(
        self,
        user_id: UserId,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[MealAnalysis]:
        """
        Get recent analyses for user.

        Returns analyses ordered by created_at DESC.

        Args:
            user_id: User to fetch analyses for
            limit: Maximum number to return (default 10)
            include_expired: Include expired analyses (default False)

        Returns:
            List of MealAnalysis (may be empty)

        Example:
            >>> recent = await repository.get_by_user(
            ...     UserId(value="user123"),
            ...     limit=5,
            ... )
            >>> for analysis in recent:
            ...     print(f"{analysis.meal_name}: {analysis.created_at}")
        """
        ...

    async def mark_converted(
        self,
        analysis_id: AnalysisId,
        meal_id: MealId,
    ) -> None:
        """
        Mark analysis as converted to permanent meal.

        Sets converted_to_meal_at timestamp.
        Analysis remains in storage until TTL expires.

        Args:
            analysis_id: Analysis to mark as converted
            meal_id: ID of created meal (for reference)

        Raises:
            RepositoryError: If analysis not found

        Example:
            >>> meal_id = MealId(value="507f1f77bcf86cd799439011")
            >>> await repository.mark_converted(analysis_id, meal_id)
        """
        ...

    async def delete_expired(self) -> int:
        """
        Manually delete expired analyses.

        Note: With TTL index, this is automatic.
        This method is for manual cleanup or testing.

        Returns:
            Number of analyses deleted

        Example:
            >>> deleted_count = await repository.delete_expired()
            >>> print(f"Cleaned up {deleted_count} expired analyses")
        """
        ...

    async def exists(self, analysis_id: AnalysisId) -> bool:
        """
        Check if analysis exists.

        Useful for idempotency checks.

        Args:
            analysis_id: Analysis to check

        Returns:
            True if exists, False otherwise

        Example:
            >>> if await repository.exists(analysis_id):
            ...     print("Analysis already processed")
        """
        ...
