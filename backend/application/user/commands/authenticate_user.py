"""Authenticate user command."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.user.core.entities.user import User
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
from domain.user.core.ports.user_repository import IUserRepository


@dataclass
class AuthenticateUserCommand:
    """Command to authenticate or create user on first login.

    This command is executed after successful JWT verification.
    Creates user on first authentication, updates last_authenticated_at on subsequent logins.

    Examples:
        >>> command = AuthenticateUserCommand(repository)
        >>> user = await command.execute(Auth0Sub("auth0|123"))
    """

    repository: IUserRepository

    async def execute(
        self,
        auth0_sub: Auth0Sub,
        authenticated_at: Optional[datetime] = None,
        initial_preferences: Optional[UserPreferences] = None,
    ) -> User:
        """Execute authentication command.

        Args:
            auth0_sub: Auth0 subject from verified JWT
            authenticated_at: Authentication timestamp (defaults to now)
            initial_preferences: Preferences for new users (defaults to empty)

        Returns:
            User entity (created or updated)

        Examples:
            >>> user = await command.execute(Auth0Sub("auth0|123"))
            >>> user.last_authenticated_at is not None
            True
        """
        # Check if user exists
        user = await self.repository.find_by_auth0_sub(auth0_sub)

        if user is None:
            # First login - create user
            user = User.create(auth0_sub, initial_preferences)
            user.authenticate(authenticated_at)
        else:
            # Existing user - update last authentication
            user.authenticate(authenticated_at)

        # Save and collect events
        await self.repository.save(user)
        user.collect_events()  # TODO: Publish to event bus

        return user
