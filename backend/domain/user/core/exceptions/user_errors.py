"""User domain exceptions."""


class UserDomainError(Exception):
    """Base exception for User domain errors."""

    pass


class UserNotFoundError(UserDomainError):
    """User was not found in the repository."""

    def __init__(self, identifier: str):
        """Initialize with user identifier.

        Args:
            identifier: User ID or Auth0 sub that was not found
        """
        self.identifier = identifier
        super().__init__(f"User not found: {identifier}")


class InvalidAuth0SubError(UserDomainError):
    """Auth0 subject identifier is invalid."""

    def __init__(self, auth0_sub: str, reason: str):
        """Initialize with invalid auth0_sub and reason.

        Args:
            auth0_sub: Invalid Auth0 sub value
            reason: Reason why it's invalid
        """
        self.auth0_sub = auth0_sub
        self.reason = reason
        super().__init__(f"Invalid Auth0 sub '{auth0_sub}': {reason}")


class UserAlreadyExistsError(UserDomainError):
    """User with given identifier already exists."""

    def __init__(self, identifier: str):
        """Initialize with user identifier.

        Args:
            identifier: User ID or Auth0 sub that already exists
        """
        self.identifier = identifier
        super().__init__(f"User already exists: {identifier}")


class InactiveUserError(UserDomainError):
    """User account is inactive/deactivated."""

    def __init__(self, user_id: str):
        """Initialize with user ID.

        Args:
            user_id: ID of inactive user
        """
        self.user_id = user_id
        super().__init__(f"User account is inactive: {user_id}")
