"""MongoDB User Repository implementation."""

from typing import Optional, Any, Dict

from domain.user.core.entities.user import User
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
from domain.user.core.ports.user_repository import IUserRepository
from domain.user.core.exceptions.user_errors import UserNotFoundError


class MongoUserRepository(IUserRepository):
    """MongoDB implementation of User repository.

    Stores minimal user data (app-specific only):
    - user_id: Internal UUID
    - auth0_sub: Auth0 subject (primary lookup key)
    - preferences: App-specific settings (JSON)
    - created_at: User creation timestamp
    - updated_at: Last update timestamp
    - last_authenticated_at: Last authentication timestamp
    - is_active: Account status

    Auth0 is the source of truth for email, name, picture, etc.

    Examples:
        >>> repo = MongoUserRepository(db)
        >>> user = User.create(Auth0Sub("auth0|123"))
        >>> await repo.save(user)
        >>> found = await repo.find_by_auth0_sub(Auth0Sub("auth0|123"))
    """

    def __init__(self, db: Any) -> None:
        """Initialize repository with MongoDB database.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.users

    async def save(self, user: User) -> None:
        """Save or update user.

        Uses auth0_sub as unique identifier for upsert.

        Args:
            user: User entity to save

        Examples:
            >>> user = User.create(Auth0Sub("auth0|123"))
            >>> await repo.save(user)
        """
        document = {
            "user_id": str(user.user_id),
            "auth0_sub": str(user.auth0_sub),
            "preferences": user.preferences.data,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_authenticated_at": user.last_authenticated_at,
            "is_active": user.is_active,
        }

        # Upsert by auth0_sub (unique identifier)
        await self.collection.update_one(
            {"auth0_sub": str(user.auth0_sub)}, {"$set": document}, upsert=True
        )

    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find user by internal user_id.

        Args:
            user_id: Internal user UUID

        Returns:
            User entity or None if not found

        Examples:
            >>> user = await repo.find_by_id(UserId("uuid-here"))
        """
        document = await self.collection.find_one({"user_id": str(user_id)})

        if not document:
            return None

        return self._document_to_entity(document)

    async def find_by_auth0_sub(self, auth0_sub: Auth0Sub) -> Optional[User]:
        """Find user by Auth0 subject identifier.

        This is the primary lookup method since auth0_sub is immutable
        and used for authentication.

        Args:
            auth0_sub: Auth0 subject from JWT

        Returns:
            User entity or None if not found

        Examples:
            >>> user = await repo.find_by_auth0_sub(Auth0Sub("auth0|123"))
        """
        document = await self.collection.find_one({"auth0_sub": str(auth0_sub)})

        if not document:
            return None

        return self._document_to_entity(document)

    async def exists(self, auth0_sub: Auth0Sub) -> bool:
        """Check if user exists by Auth0 subject.

        More efficient than find_by_auth0_sub when you only need
        existence check.

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            True if user exists, False otherwise

        Examples:
            >>> exists = await repo.exists(Auth0Sub("auth0|123"))
        """
        count = await self.collection.count_documents({"auth0_sub": str(auth0_sub)}, limit=1)
        return bool(count > 0)

    async def delete(self, auth0_sub: Auth0Sub) -> bool:
        """Delete user by Auth0 subject.

        For GDPR compliance - removes all app-specific user data.
        Note: Does not delete data from Auth0 (requires Management API call).

        Args:
            auth0_sub: Auth0 subject identifier

        Returns:
            True if user was deleted

        Raises:
            UserNotFoundError: If user doesn't exist

        Examples:
            >>> await repo.delete(Auth0Sub("auth0|123"))
        """
        result = await self.collection.delete_one({"auth0_sub": str(auth0_sub)})

        if result.deleted_count == 0:
            raise UserNotFoundError(str(auth0_sub))

        return True

    def _document_to_entity(self, document: Dict[str, Any]) -> User:
        """Convert MongoDB document to User entity.

        Args:
            document: MongoDB document

        Returns:
            User entity instance
        """
        return User(
            user_id=UserId(document["user_id"]),
            auth0_sub=Auth0Sub(document["auth0_sub"]),
            preferences=UserPreferences(data=document.get("preferences", {})),
            created_at=document["created_at"],
            updated_at=document["updated_at"],
            last_authenticated_at=document.get("last_authenticated_at"),
            is_active=document.get("is_active", True),
        )
