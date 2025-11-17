"""UserProfileUpdated domain event."""

from dataclasses import dataclass
from datetime import datetime

from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences


@dataclass(frozen=True)
class UserProfileUpdated:
    """Domain event: User profile was updated.

    Emitted when user preferences are modified.
    Contains both old and new values for audit/analytics.

    Attributes:
        user_id: Internal user identifier
        auth0_sub: Auth0 subject identifier
        old_preferences: Previous preferences state
        new_preferences: New preferences state
        updated_at: Timestamp of update

    Examples:
        >>> from datetime import datetime
        >>> old = UserPreferences.default()
        >>> new = UserPreferences(data={"theme": "dark"})
        >>> event = UserProfileUpdated(
        ...     user_id=UserId.generate(),
        ...     auth0_sub=Auth0Sub("auth0|123"),
        ...     old_preferences=old,
        ...     new_preferences=new,
        ...     updated_at=datetime.utcnow()
        ... )
        >>> event.new_preferences.get("theme")
        'dark'
    """

    user_id: UserId
    auth0_sub: Auth0Sub
    old_preferences: UserPreferences
    new_preferences: UserPreferences
    updated_at: datetime
