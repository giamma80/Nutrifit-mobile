"""UserAuthenticated domain event."""

from dataclasses import dataclass
from datetime import datetime

from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub


@dataclass(frozen=True)
class UserAuthenticated:
    """Domain event: User successfully authenticated.

    Emitted when user authenticates via Auth0 JWT token.
    Can be used for analytics, last login tracking, etc.

    Attributes:
        user_id: Internal user identifier
        auth0_sub: Auth0 subject identifier
        authenticated_at: Timestamp of authentication

    Examples:
        >>> from datetime import datetime
        >>> event = UserAuthenticated(
        ...     user_id=UserId.generate(),
        ...     auth0_sub=Auth0Sub("auth0|123"),
        ...     authenticated_at=datetime.utcnow()
        ... )
        >>> event.authenticated_at is not None
        True
    """

    user_id: UserId
    auth0_sub: Auth0Sub
    authenticated_at: datetime
