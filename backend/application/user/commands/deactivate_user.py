"""Deactivate user command."""

from dataclasses import dataclass

from domain.user.core.entities.user import User
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.ports.user_repository import IUserRepository
from domain.user.core.exceptions.user_errors import UserNotFoundError


@dataclass
class DeactivateUserCommand:
    """Command to deactivate user account.

    Sets is_active to False. Deactivated users cannot authenticate.
    For GDPR compliance, use DeleteUserCommand to remove all data.

    Examples:
        >>> command = DeactivateUserCommand(repository)
        >>> user = await command.execute(Auth0Sub("auth0|123"))
        >>> user.is_active
        False
    """

    repository: IUserRepository

    async def execute(self, auth0_sub: Auth0Sub) -> User:
        """Execute deactivate user command.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            Deactivated user entity

        Raises:
            UserNotFoundError: If user doesn't exist

        Examples:
            >>> user = await command.execute(Auth0Sub("auth0|123"))
            >>> user.is_active
            False
        """
        # Find user
        user = await self.repository.find_by_auth0_sub(auth0_sub)

        if user is None:
            raise UserNotFoundError(str(auth0_sub))

        # Deactivate
        user.deactivate()

        # Save
        await self.repository.save(user)

        return user
