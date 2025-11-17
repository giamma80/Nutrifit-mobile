"""User domain GraphQL mutations."""

from typing import cast
import strawberry
from strawberry.types import Info

from graphql.types_user import UserType, UserPreferencesInput
from application.user.commands.authenticate_user import AuthenticateUserCommand
from application.user.commands.update_preferences import UpdatePreferencesCommand
from application.user.commands.deactivate_user import DeactivateUserCommand
from domain.user.core.value_objects.auth0_sub import Auth0Sub


@strawberry.type
class UserMutations:
    """User domain mutations.

    Provides write operations for user management.
    Requires authentication via JWT token.

    Examples:
        mutation {
          user {
            updatePreferences(preferences: { theme: "dark" }) {
              userId
              preferences { data }
            }
          }
        }
    """

    @strawberry.mutation
    async def authenticate(self, info: Info) -> UserType:
        """Authenticate or create user.

        Called automatically on first login to create user record.
        Updates last_authenticated_at on subsequent logins.

        Args:
            info: GraphQL context with auth_claims

        Returns:
            User entity (created or updated)

        Raises:
            RuntimeError: If user_repository not in context
            ValueError: If auth0_sub missing from JWT

        Examples:
            mutation {
              user {
                authenticate {
                  userId
                  auth0Sub
                  createdAt
                  lastAuthenticatedAt
                }
              }
            }
        """
        # Get auth0_sub from JWT claims
        auth_claims = getattr(info.context.get("request"), "state", None)
        if not auth_claims or not hasattr(auth_claims, "auth_claims"):
            raise ValueError("Missing authentication")

        claims = auth_claims.auth_claims
        auth0_sub_str = claims.get("sub")
        if not auth0_sub_str:
            raise ValueError("Missing 'sub' in JWT claims")

        # Get user repository from context
        user_repository = info.context.get("user_repository")
        if not user_repository:
            raise RuntimeError("user_repository not found in context")

        # Execute command
        command = AuthenticateUserCommand(repository=user_repository)
        auth0_sub = Auth0Sub(auth0_sub_str)
        user = await command.execute(auth0_sub)

        return cast(UserType, user)

    @strawberry.mutation
    async def update_preferences(
        self,
        info: Info,
        preferences: UserPreferencesInput,
    ) -> UserType:
        """Update user preferences.

        Updates app-specific preferences (theme, language, notifications, etc.).
        Does not modify Auth0 profile data.

        Args:
            info: GraphQL context with auth_claims
            preferences: New preferences to set

        Returns:
            Updated user entity

        Raises:
            RuntimeError: If user_repository not in context
            ValueError: If auth0_sub missing from JWT
            UserNotFoundError: If user doesn't exist
            InactiveUserError: If user account is inactive

        Examples:
            mutation {
              user {
                updatePreferences(preferences: {
                  theme: "dark"
                  language: "it"
                  notifications: true
                }) {
                  userId
                  preferences { data }
                  updatedAt
                }
              }
            }
        """
        # Get auth0_sub from JWT claims
        auth_claims = getattr(info.context.get("request"), "state", None)
        if not auth_claims or not hasattr(auth_claims, "auth_claims"):
            raise ValueError("Missing authentication")

        claims = auth_claims.auth_claims
        auth0_sub_str = claims.get("sub")
        if not auth0_sub_str:
            raise ValueError("Missing 'sub' in JWT claims")

        # Get user repository from context
        user_repository = info.context.get("user_repository")
        if not user_repository:
            raise RuntimeError("user_repository not found in context")

        # Execute command
        command = UpdatePreferencesCommand(repository=user_repository)
        auth0_sub = Auth0Sub(auth0_sub_str)
        user = await command.execute(auth0_sub, preferences.to_domain())

        return cast(UserType, user)

    @strawberry.mutation
    async def deactivate(self, info: Info) -> UserType:
        """Deactivate user account.

        Sets is_active to False. Deactivated users cannot authenticate.
        For GDPR compliance (full data deletion), contact support.

        Args:
            info: GraphQL context with auth_claims

        Returns:
            Deactivated user entity

        Raises:
            RuntimeError: If user_repository not in context
            ValueError: If auth0_sub missing from JWT
            UserNotFoundError: If user doesn't exist

        Examples:
            mutation {
              user {
                deactivate {
                  userId
                  isActive
                }
              }
            }
        """
        # Get auth0_sub from JWT claims
        auth_claims = getattr(info.context.get("request"), "state", None)
        if not auth_claims or not hasattr(auth_claims, "auth_claims"):
            raise ValueError("Missing authentication")

        claims = auth_claims.auth_claims
        auth0_sub_str = claims.get("sub")
        if not auth0_sub_str:
            raise ValueError("Missing 'sub' in JWT claims")

        # Get user repository from context
        user_repository = info.context.get("user_repository")
        if not user_repository:
            raise RuntimeError("user_repository not found in context")

        # Execute command
        command = DeactivateUserCommand(repository=user_repository)
        auth0_sub = Auth0Sub(auth0_sub_str)
        user = await command.execute(auth0_sub)

        return cast(UserType, user)
