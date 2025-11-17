"""User entity - aggregate root."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any

from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences


@dataclass
class User:
    """User aggregate root.

    Represents an authenticated user in the system.
    Primary identifier is auth0_sub (Auth0 subject from JWT).

    Invariants:
    - auth0_sub must be unique and immutable
    - created_at cannot be in the future
    - last_authenticated_at cannot be before created_at
    - user_id is generated and immutable

    Examples:
        >>> auth0_sub = Auth0Sub("auth0|123456")
        >>> user = User.create(auth0_sub)
        >>> user.is_active
        True

        >>> user.authenticate()
        >>> user.last_authenticated_at is not None
        True

        >>> prefs = UserPreferences(data={"theme": "dark"})
        >>> user.update_preferences(prefs)
        >>> user.preferences.get("theme")
        'dark'
    """

    user_id: UserId
    auth0_sub: Auth0Sub
    preferences: UserPreferences
    created_at: datetime
    updated_at: datetime
    last_authenticated_at: Optional[datetime] = None
    is_active: bool = True
    _events: List[Any] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """Validate invariants."""
        # Validate created_at is not in future
        now = datetime.utcnow()
        if self.created_at > now:
            raise ValueError(f"created_at cannot be in the future: {self.created_at} > {now}")

        # Validate last_authenticated_at is after created_at
        if self.last_authenticated_at and self.last_authenticated_at < self.created_at:
            raise ValueError(
                "last_authenticated_at cannot be before created_at: "
                f"{self.last_authenticated_at} < {self.created_at}"
            )

    @staticmethod
    def create(auth0_sub: Auth0Sub, preferences: Optional[UserPreferences] = None) -> "User":
        """Factory method to create a new user.

        Args:
            auth0_sub: Auth0 subject identifier from JWT
            preferences: Optional user preferences (defaults to empty)

        Returns:
            New User instance with UserCreated event

        Raises:
            ValueError: If auth0_sub is invalid

        Examples:
            >>> auth0_sub = Auth0Sub("auth0|123")
            >>> user = User.create(auth0_sub)
            >>> user.is_active
            True
            >>> events = user.collect_events()
            >>> len(events)
            1
        """
        from domain.user.core.events.user_created import UserCreated

        now = datetime.utcnow()
        user_id = UserId.generate()
        prefs = preferences or UserPreferences.default()

        user = User(
            user_id=user_id,
            auth0_sub=auth0_sub,
            preferences=prefs,
            created_at=now,
            updated_at=now,
        )

        user._add_event(
            UserCreated(
                user_id=user_id,
                auth0_sub=auth0_sub,
                created_at=now,
            )
        )

        return user

    def authenticate(self, authenticated_at: Optional[datetime] = None) -> None:
        """Record user authentication.

        Updates last_authenticated_at and emits UserAuthenticated event.
        This should be called whenever user successfully authenticates.

        Args:
            authenticated_at: Timestamp of authentication (defaults to now)

        Examples:
            >>> user = User.create(Auth0Sub("auth0|123"))
            >>> user.authenticate()
            >>> user.last_authenticated_at is not None
            True
            >>> events = user.collect_events()
            >>> any(e.__class__.__name__ == "UserAuthenticated" for e in events)
            True
        """
        from domain.user.core.events.user_authenticated import UserAuthenticated

        auth_time = authenticated_at or datetime.utcnow()

        # Validate auth_time is not before creation
        if auth_time < self.created_at:
            raise ValueError(
                f"Authentication time {auth_time} cannot be before "
                f"user creation time {self.created_at}"
            )

        self.last_authenticated_at = auth_time
        self.updated_at = auth_time

        self._add_event(
            UserAuthenticated(
                user_id=self.user_id,
                auth0_sub=self.auth0_sub,
                authenticated_at=auth_time,
            )
        )

    def update_preferences(self, preferences: UserPreferences) -> None:
        """Update user preferences.

        Args:
            preferences: New preferences to set

        Examples:
            >>> user = User.create(Auth0Sub("auth0|123"))
            >>> prefs = UserPreferences(data={"theme": "dark"})
            >>> user.update_preferences(prefs)
            >>> user.preferences.get("theme")
            'dark'
        """
        from domain.user.core.events.user_updated import UserProfileUpdated

        old_preferences = self.preferences
        self.preferences = preferences
        self.updated_at = datetime.utcnow()

        self._add_event(
            UserProfileUpdated(
                user_id=self.user_id,
                auth0_sub=self.auth0_sub,
                old_preferences=old_preferences,
                new_preferences=preferences,
                updated_at=self.updated_at,
            )
        )

    def deactivate(self) -> None:
        """Deactivate user account.

        Sets is_active to False. Deactivated users cannot authenticate.

        Examples:
            >>> user = User.create(Auth0Sub("auth0|123"))
            >>> user.deactivate()
            >>> user.is_active
            False
        """
        if not self.is_active:
            return  # Already deactivated

        self.is_active = False
        self.updated_at = datetime.utcnow()

    def reactivate(self) -> None:
        """Reactivate user account.

        Sets is_active to True. User can authenticate again.

        Examples:
            >>> user = User.create(Auth0Sub("auth0|123"))
            >>> user.deactivate()
            >>> user.reactivate()
            >>> user.is_active
            True
        """
        if self.is_active:
            return  # Already active

        self.is_active = True
        self.updated_at = datetime.utcnow()

    def _add_event(self, event: Any) -> None:
        """Add domain event to internal list.

        Args:
            event: Domain event to add
        """
        self._events.append(event)

    def collect_events(self) -> List[Any]:
        """Collect and clear domain events.

        Returns:
            List of domain events that occurred

        Examples:
            >>> user = User.create(Auth0Sub("auth0|123"))
            >>> events = user.collect_events()
            >>> len(events) > 0
            True
            >>> user.collect_events()  # Events cleared after collection
            []
        """
        events = self._events.copy()
        self._events.clear()
        return events

    def __eq__(self, other: object) -> bool:
        """Equality based on user_id (aggregate identity)."""
        if not isinstance(other, User):
            return False
        return self.user_id == other.user_id

    def __hash__(self) -> int:
        """Hash based on user_id (aggregate identity)."""
        return hash(self.user_id)
