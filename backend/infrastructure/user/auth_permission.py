"""Strawberry GraphQL permission for JWT authentication."""

import logging
from typing import Any
from strawberry.permission import BasePermission
from strawberry.types import Info

logger = logging.getLogger(__name__)


class IsAuthenticated(BasePermission):
    """Permission checker for authenticated users.

    Verifies that request.state.auth_claims is set by AuthMiddleware.
    Use this permission on resolvers that require authentication.

    Examples:
        @strawberry.mutation(permission_classes=[IsAuthenticated])
        async def create_post(self, info: Info) -> Post:
            # User is guaranteed to be authenticated
            auth_claims = info.context.auth_claims
            user_id = auth_claims["sub"]
    """

    message = "Not authenticated"

    async def has_permission(self, source: Any, info: Info, **kwargs: Any) -> bool:
        """Check if user is authenticated.

        Args:
            source: Parent resolver result (unused)
            info: GraphQL info with context
            **kwargs: Field arguments (unused)

        Returns:
            True if authenticated, False otherwise
        """
        auth_claims = getattr(info.context, "auth_claims", None)

        if not auth_claims:
            logger.warning("Permission denied: No auth_claims in context")
            return False

        logger.debug(f"Permission granted for sub: {auth_claims.get('sub', 'unknown')}")
        return True
