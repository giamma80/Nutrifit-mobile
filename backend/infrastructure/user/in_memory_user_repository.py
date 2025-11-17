"""In-memory User Repository for testing."""

from typing import Dict, Optional

from domain.user.core.entities.user import User
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.ports.user_repository import IUserRepository
from domain.user.core.exceptions.user_errors import UserNotFoundError


class InMemoryUserRepository(IUserRepository):
    """In-memory implementation of User repository for testing.

    Stores users in memory using auth0_sub as key.
    Useful for unit tests and integration tests without MongoDB dependency.

    Examples:
        >>> repo = InMemoryUserRepository()
        >>> user = User.create(Auth0Sub("auth0|123"))
        >>> await repo.save(user)
        >>> found = await repo.find_by_auth0_sub(Auth0Sub("auth0|123"))
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._users: Dict[str, User] = {}

    async def save(self, user: User) -> None:
        """Save or update user in memory.

        Args:
            user: User entity to save
        """
        self._users[str(user.auth0_sub)] = user

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find user by internal user_id.

        Args:
            user_id: Internal user UUID

        Returns:
            User entity or None if not found
        """
        for user in self._users.values():
            if user.user_id == user_id:
                return user
        return None

    async def find_by_auth0_sub(self, auth0_sub: Auth0Sub) -> Optional[User]:
        """Find user by Auth0 subject identifier.

        Args:
            auth0_sub: Auth0 subject from JWT

        Returns:
            User entity or None if not found
        """
        return self._users.get(str(auth0_sub))

    async def exists(self, auth0_sub: Auth0Sub) -> bool:
        """Check if user exists by Auth0 subject.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            True if user exists, False otherwise
        """
        return str(auth0_sub) in self._users

    async def delete(self, auth0_sub: Auth0Sub) -> bool:
        """Delete user by Auth0 subject.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            True if user was deleted

        Raises:
            UserNotFoundError: If user doesn't exist
        """
        key = str(auth0_sub)
        if key not in self._users:
            raise UserNotFoundError(str(auth0_sub))

        del self._users[key]
        return True

    def clear(self) -> None:
        """Clear all users from memory.

        Useful for test cleanup.
        """
        self._users.clear()

    def count(self) -> int:
        """Get total number of users in memory.

        Returns:
            Number of users stored
        """
        return len(self._users)
