"""User profile updated event handler."""

from dataclasses import dataclass
import logging

from domain.user.core.events.user_updated import UserProfileUpdated


logger = logging.getLogger(__name__)


@dataclass
class UserProfileUpdatedHandler:
    """Handler for UserProfileUpdated domain event.

    Triggered when user preferences are updated.
    Can be used for analytics, cache invalidation, etc.

    Examples:
        >>> handler = UserProfileUpdatedHandler()
        >>> await handler.handle(UserProfileUpdated(...))
    """

    async def handle(self, event: UserProfileUpdated) -> None:
        """Handle UserProfileUpdated event.

        Args:
            event: UserProfileUpdated domain event

        Examples:
            >>> event = UserProfileUpdated(
            ...     user_id=UserId("uuid"),
            ...     updated_at=datetime.now(),
            ...     occurred_at=datetime.now()
            ... )
            >>> await handler.handle(event)
        """
        logger.info(
            "User profile updated",
            extra={
                "user_id": str(event.user_id),
                "auth0_sub": str(event.auth0_sub),
                "updated_at": event.updated_at.isoformat(),
            },
        )

        # TODO: Implement additional handlers
        # - Invalidate user cache
        # - Track preferences analytics
        # - Sync preferences to third-party services
        # - Notify connected devices of preference changes
