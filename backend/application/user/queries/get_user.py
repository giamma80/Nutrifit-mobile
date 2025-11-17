"""Get user query."""

from dataclasses import dataclass
from typing import Optional

from domain.user.core.entities.user import User
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.ports.user_repository import IUserRepository


@dataclass
class GetUserQuery:
    """Query to get user by identifier.

    Read-only operation that retrieves user from repository.

    Examples:
        >>> query = GetUserQuery(repository)
        >>> user = await query.by_auth0_sub(Auth0Sub("auth0|123"))
        >>> user = await query.by_id(UserId("uuid-here"))
    """

    repository: IUserRepository

    async def by_auth0_sub(self, auth0_sub: Auth0Sub) -> Optional[User]:
        """Get user by Auth0 subject.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            User entity or None if not found

        Examples:
            >>> user = await query.by_auth0_sub(Auth0Sub("auth0|123"))
            >>> if user:
            ...     print(user.preferences)
        """
        return await self.repository.find_by_auth0_sub(auth0_sub)

    async def by_id(self, user_id: UserId) -> Optional[User]:
        """Get user by internal user ID.

        Args:
            user_id: Internal user UUID

        Returns:
            User entity or None if not found

        Examples:
            >>> user = await query.by_id(UserId("uuid-here"))
        """
        return await self.repository.find_by_id(user_id)

    async def exists(self, auth0_sub: Auth0Sub) -> bool:
        """Check if user exists.

        More efficient than by_auth0_sub when you only need existence check.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            True if user exists, False otherwise

        Examples:
            >>> exists = await query.exists(Auth0Sub("auth0|123"))
        """
        return await self.repository.exists(auth0_sub)
