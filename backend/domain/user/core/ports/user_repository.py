"""User repository port (interface)."""

from abc import ABC, abstractmethod
from typing import Optional

from domain.user.core.entities.user import User
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub


class IUserRepository(ABC):
    """Repository interface for User aggregate.

    Defines contract for user persistence operations.
    Implementations must handle User entity serialization/deserialization.

    Examples:
        >>> # Implementation example (not actual usage)
        >>> class MongoUserRepository(IUserRepository):
        ...     async def save(self, user: User) -> None:
        ...         # Save to MongoDB
        ...         pass
    """

    @abstractmethod
    async def save(self, user: User) -> None:
        """Save user (create or update).

        Args:
            user: User entity to persist

        Raises:
            RepositoryError: If save operation fails

        Note:
            Implementation should be idempotent (upsert by auth0_sub).
        """
        pass

    @abstractmethod
    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find user by internal ID.

        Args:
            user_id: Internal user identifier

        Returns:
            User entity if found, None otherwise

        Examples:
            >>> user_id = UserId.generate()
            >>> user = await repository.find_by_id(user_id)
            >>> if user:
            ...     print(f"Found user: {user.auth0_sub}")
        """
        pass

    @abstractmethod
    async def find_by_auth0_sub(self, auth0_sub: Auth0Sub) -> Optional[User]:
        """Find user by Auth0 subject identifier.

        Args:
            auth0_sub: Auth0 subject from JWT token

        Returns:
            User entity if found, None otherwise

        Examples:
            >>> auth0_sub = Auth0Sub("auth0|123456")
            >>> user = await repository.find_by_auth0_sub(auth0_sub)
            >>> if user:
            ...     print(f"User ID: {user.user_id}")

        Note:
            This is the primary lookup method (auth0_sub is unique).
        """
        pass

    @abstractmethod
    async def exists(self, auth0_sub: Auth0Sub) -> bool:
        """Check if user exists.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            True if user exists, False otherwise

        Examples:
            >>> auth0_sub = Auth0Sub("auth0|123456")
            >>> if await repository.exists(auth0_sub):
            ...     print("User already registered")

        Note:
            More efficient than find_by_auth0_sub when only checking existence.
        """
        pass

    @abstractmethod
    async def delete(self, auth0_sub: Auth0Sub) -> bool:
        """Delete user by Auth0 subject.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            True if user was deleted, False if not found

        Examples:
            >>> auth0_sub = Auth0Sub("auth0|123456")
            >>> deleted = await repository.delete(auth0_sub)
            >>> if deleted:
            ...     print("User deleted successfully")

        Note:
            Use for GDPR compliance (right to be forgotten).
        """
        pass
