"""UserCreated domain event."""

from dataclasses import dataclass
from datetime import datetime

from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub


@dataclass(frozen=True)
class UserCreated:
    """Domain event: User was created.

    Emitted when a new user is created in the system (first authentication).

    Attributes:
        user_id: Internal user identifier
        auth0_sub: Auth0 subject identifier
        created_at: Timestamp of user creation

    Examples:
        >>> from datetime import datetime
        >>> event = UserCreated(
        ...     user_id=UserId.generate(),
        ...     auth0_sub=Auth0Sub("auth0|123"),
        ...     created_at=datetime.utcnow()
        ... )
        >>> event.auth0_sub.value
        'auth0|123'
    """

    user_id: UserId
    auth0_sub: Auth0Sub
    created_at: datetime
