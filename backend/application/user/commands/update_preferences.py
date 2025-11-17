"""Update user preferences command."""

from dataclasses import dataclass

from domain.user.core.entities.user import User
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
from domain.user.core.ports.user_repository import IUserRepository
from domain.user.core.exceptions.user_errors import UserNotFoundError, InactiveUserError


@dataclass
class UpdatePreferencesCommand:
    """Command to update user preferences.

    Updates app-specific preferences (theme, language, notifications, etc.).
    Does not modify Auth0 profile data (email, name, etc.).

    Examples:
        >>> command = UpdatePreferencesCommand(repository)
        >>> prefs = UserPreferences(data={"theme": "dark"})
        >>> user = await command.execute(Auth0Sub("auth0|123"), prefs)
    """

    repository: IUserRepository

    async def execute(self, auth0_sub: Auth0Sub, preferences: UserPreferences) -> User:
        """Execute update preferences command.

        Args:
            auth0_sub: Auth0 subject identifier
            preferences: New preferences to set

        Returns:
            Updated user entity

        Raises:
            UserNotFoundError: If user doesn't exist
            InactiveUserError: If user account is inactive

        Examples:
            >>> prefs = UserPreferences(data={"theme": "dark", "lang": "it"})
            >>> user = await command.execute(Auth0Sub("auth0|123"), prefs)
            >>> user.preferences.get("theme")
            'dark'
        """
        # Find user
        user = await self.repository.find_by_auth0_sub(auth0_sub)

        if user is None:
            raise UserNotFoundError(str(auth0_sub))

        if not user.is_active:
            raise InactiveUserError(str(user.user_id))

        # Update preferences
        user.update_preferences(preferences)

        # Save and collect events
        await self.repository.save(user)
        user.collect_events()  # TODO: Publish to event bus

        return user
