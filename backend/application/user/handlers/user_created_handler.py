"""User created event handler."""

from dataclasses import dataclass
import logging

from domain.user.core.events.user_created import UserCreated


logger = logging.getLogger(__name__)


@dataclass
class UserCreatedHandler:
    """Handler for UserCreated domain event.

    Triggered when a new user is created (first authentication).
    Can be used for analytics, logging, onboarding emails, etc.

    Examples:
        >>> handler = UserCreatedHandler()
        >>> await handler.handle(UserCreated(...))
    """

    async def handle(self, event: UserCreated) -> None:
        """Handle UserCreated event.

        Args:
            event: UserCreated domain event

        Examples:
            >>> event = UserCreated(
            ...     user_id=UserId("uuid"),
            ...     auth0_sub=Auth0Sub("auth0|123"),
            ...     occurred_at=datetime.now()
            ... )
            >>> await handler.handle(event)
        """
        logger.info(
            "User created",
            extra={
                "user_id": str(event.user_id),
                "auth0_sub": str(event.auth0_sub),
                "created_at": event.created_at.isoformat(),
            },
        )

        # TODO: Implement additional handlers
        # - Send welcome email
        # - Track analytics event
        # - Initialize default preferences
        # - Create onboarding tasks
