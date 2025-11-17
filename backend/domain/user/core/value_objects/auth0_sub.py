"""Auth0Sub value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Auth0Sub:
    """Auth0 subject identifier value object.

    Represents the unique identifier from Auth0 (sub claim in JWT).
    Format: <provider>|<id>

    Examples:
        >>> auth0_sub = Auth0Sub("auth0|123456789")
        >>> auth0_sub.value
        'auth0|123456789'

        >>> auth0_sub = Auth0Sub("google-oauth2|987654321")
        >>> auth0_sub.provider
        'google-oauth2'

    Raises:
        ValueError: If format is invalid (missing pipe or too long)
    """

    value: str

    def __post_init__(self) -> None:
        """Validate Auth0 sub format."""
        if not self.value:
            raise ValueError("Auth0 sub cannot be empty")

        if "|" not in self.value:
            raise ValueError(
                f"Invalid Auth0 sub format: {self.value}. " "Expected format: <provider>|<id>"
            )

        if len(self.value) > 255:
            raise ValueError(
                f"Auth0 sub too long ({len(self.value)} chars). " "Maximum 255 characters allowed"
            )

    @property
    def provider(self) -> str:
        """Extract provider from Auth0 sub.

        Returns:
            Provider name (e.g., 'auth0', 'google-oauth2', 'facebook')

        Examples:
            >>> Auth0Sub("auth0|123").provider
            'auth0'
            >>> Auth0Sub("google-oauth2|456").provider
            'google-oauth2'
        """
        return self.value.split("|", 1)[0]

    @property
    def external_id(self) -> str:
        """Extract external ID from Auth0 sub.

        Returns:
            External provider's user ID

        Examples:
            >>> Auth0Sub("auth0|123").external_id
            '123'
        """
        return self.value.split("|", 1)[1]

    def __str__(self) -> str:
        """String representation returns the value."""
        return self.value

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"Auth0Sub('{self.value}')"
