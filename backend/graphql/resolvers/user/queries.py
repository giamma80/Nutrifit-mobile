"""User domain GraphQL queries."""

from typing import Optional, cast
import strawberry
from strawberry.types import Info

from graphql.types_user import UserType
from application.user.queries.get_user import GetUserQuery
from domain.user.core.value_objects.auth0_sub import Auth0Sub


@strawberry.type
class UserQueries:
    """User domain queries.

    Provides read-only access to user data.
    Requires authentication via JWT token.

    Examples:
        query {
          user {
            me {
              userId
              preferences { data }
            }
          }
        }
    """

    @strawberry.field
    async def me(self, info: Info) -> Optional[UserType]:
        """Get authenticated user profile.

        Returns current user from JWT token claims.
        Creates user on first authentication if not exists.

        Args:
            info: GraphQL context with auth_claims

        Returns:
            Current user or None if not authenticated

        Examples:
            query {
              user {
                me {
                  userId
                  auth0Sub
                  preferences { data }
                  isActive
                  createdAt
                  lastAuthenticatedAt
                }
              }
            }
        """
        # Get auth0_sub from JWT claims
        auth_claims = getattr(info.context.get("request"), "state", None)
        if not auth_claims or not hasattr(auth_claims, "auth_claims"):
            return None

        claims = auth_claims.auth_claims
        auth0_sub_str = claims.get("sub")
        if not auth0_sub_str:
            return None

        # Get user repository from context
        user_repository = info.context.get("user_repository")
        if not user_repository:
            raise RuntimeError("user_repository not found in context")

        # Query user
        query = GetUserQuery(repository=user_repository)
        auth0_sub = Auth0Sub(auth0_sub_str)
        user = await query.by_auth0_sub(auth0_sub)

        return cast(Optional[UserType], user)

    @strawberry.field
    async def exists(self, info: Info) -> bool:
        """Check if current user exists.

        More efficient than `me` when only checking existence.

        Args:
            info: GraphQL context with auth_claims

        Returns:
            True if user exists, False otherwise

        Examples:
            query {
              user {
                exists
              }
            }
        """
        # Get auth0_sub from JWT claims
        auth_claims = getattr(info.context.get("request"), "state", None)
        if not auth_claims or not hasattr(auth_claims, "auth_claims"):
            return False

        claims = auth_claims.auth_claims
        auth0_sub_str = claims.get("sub")
        if not auth0_sub_str:
            return False

        # Get user repository from context
        user_repository = info.context.get("user_repository")
        if not user_repository:
            raise RuntimeError("user_repository not found in context")

        # Check existence
        query = GetUserQuery(repository=user_repository)
        auth0_sub = Auth0Sub(auth0_sub_str)
        return await query.exists(auth0_sub)
