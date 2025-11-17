"""User authenticated event handler."""

from dataclasses import dataclass
import logging

from domain.user.core.events.user_authenticated import UserAuthenticated


logger = logging.getLogger(__name__)


@dataclass
class UserAuthenticatedHandler:
    """Handler for UserAuthenticated domain event.

    Triggered on every successful authentication (login).
    Can be used for activity tracking, security monitoring, etc.

    Examples:
        >>> handler = UserAuthenticatedHandler()
        >>> await handler.handle(UserAuthenticated(...))
    """

    async def handle(self, event: UserAuthenticated) -> None:
        """Handle UserAuthenticated event.

        Args:
            event: UserAuthenticated domain event

        Examples:
            >>> event = UserAuthenticated(
            ...     user_id=UserId("uuid"),
            ...     authenticated_at=datetime.now(),
            ...     occurred_at=datetime.now()
            ... )
            >>> await handler.handle(event)
        """
        logger.info(
            "User authenticated",
            extra={
                "user_id": str(event.user_id),
                "auth0_sub": str(event.auth0_sub),
                "authenticated_at": event.authenticated_at.isoformat(),
            },
        )

        # TODO: Implement additional handlers
        # - Track last active timestamp
        # - Update user activity metrics
        # - Detect suspicious login patterns
        # - Send login notification email (if enabled)
